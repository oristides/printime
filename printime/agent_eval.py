#!/usr/bin/env python3
"""Simulate real-world agent evals: SKILL.md only, execute commands, exact match grading."""

from __future__ import annotations

import json
import os
import re
import shlex
import signal
import subprocess
import sys
import tempfile
import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence

from printime.eval_runner import (
    AttemptScore,
    commands_match_exactly,
    expected_argv,
    load_eval_config,
    load_evals,
    parse_command_string,
    score_attempts,
    validate_command_argv,
)


@dataclass
class CommandRun:
    attempt: int
    argv: List[str]
    returncode: int
    output: str
    exact_match: bool


@dataclass
class AgentSimResult:
    case_id: str
    prompt: str
    attempts: List[List[str]] = field(default_factory=list)
    runs: List[CommandRun] = field(default_factory=list)
    raw_outputs: List[str] = field(default_factory=list)
    score: Optional[AttemptScore] = None
    error: Optional[str] = None


def default_skill_dir() -> Path:
    pkg_root = Path(__file__).resolve().parent.parent
    return pkg_root / 'skills' / 'printime-cli'


def default_evals_path() -> Path:
    return default_skill_dir() / 'evals.json'


def _vlog(verbose: bool, msg: str, *, log: Optional[Callable[[str], None]] = None) -> None:
    if not verbose:
        return
    (log or (lambda m: print(m, file=sys.stderr)))(msg)


def load_skill_md(skill_dir: Path, *, verbose: bool = False, log: Optional[Callable[[str], None]] = None) -> str:
    path = skill_dir / 'SKILL.md'
    if not path.is_file():
        raise FileNotFoundError(f'SKILL.md not found: {path}')
    text = path.read_text(encoding='utf-8')
    _vlog(verbose, f'  loaded SKILL.md only ({len(text)} chars)', log=log)
    return text


def build_agent_system_prompt(*, skill_md: str) -> str:
    return textwrap.dedent(f"""
    You are an AI agent operating the printime thermal printer CLI.

    You have NO other context — no repo, no chat history, no files beyond the skill below.
    Do not invent flags. Follow the skill exactly.

    The harness runs every command you output and shows you stdout/stderr in follow-up messages.
    You have at most 4 command attempts. Stay in this conversation — do not restart.

    # SKILL.md

    {skill_md}
    """).strip()


def build_initial_task_prompt(
    user_prompt: str,
    *,
    max_attempts: int,
    context_fixture: Optional[Dict[str, Any]] = None,
) -> str:
    context_block = ''
    if context_fixture:
        lines = '\n'.join(f'- {k}: {v}' for k, v in context_fixture.items())
        context_block = f'\n\nConversation context:\n{lines}\n'
    return textwrap.dedent(f"""
    User request (natural language):
    "{user_prompt}"
    {context_block}
    You may read SKILL.md and run `printime --help` or `printime <intent> --help` in this session if needed.

    When ready, reply with ONE line only:
    - Must start with: printime
    - No markdown fences, no explanation
    - The harness will execute that line (attempt 1 of {max_attempts})
    """).strip()


def build_wrong_command_feedback(
    run: CommandRun,
    *,
    attempt: int,
    max_attempts: int,
) -> str:
    cmd = shlex.join(run.argv) if run.argv else '(empty)'
    output = run.output or '(no output)'
    if len(output) > MAX_FEEDBACK_CHARS:
        output = output[:MAX_FEEDBACK_CHARS] + f'\n… ({len(run.output) - MAX_FEEDBACK_CHARS} chars truncated)'
    if not run.argv:
        return textwrap.dedent(f"""
        No printime command found in your reply.

        Reply with ONE line starting with printime (attempt {attempt} of {max_attempts}).
        """).strip()
    return textwrap.dedent(f"""
    Not the expected command. Try another printime command.

    You proposed: {cmd}
    Harness exit code: {run.returncode}
    Harness output:
    {output}

    Reply with ONE line only — your next printime command (attempt {attempt + 1} of {max_attempts}).
    You may run printime --help in this session first if you need to.
    """).strip()


PRINTIME_CMD_RE = re.compile(
    r'(?:^|\n|\s)(printime\s+(?:[^\n`|;]+))',
    re.IGNORECASE,
)


def extract_printime_command(text: str) -> Optional[str]:
    """First printime command line from agent output."""
    commands = []
    seen: set[str] = set()
    for line in text.splitlines():
        line = line.strip().strip('`')
        if line.lower().startswith('printime'):
            cmd = ' '.join(line.split())
            if cmd not in seen:
                seen.add(cmd)
                commands.append(cmd)
    if not commands:
        for match in PRINTIME_CMD_RE.finditer(text):
            cmd = ' '.join(match.group(1).strip().split())
            if cmd not in seen:
                seen.add(cmd)
                commands.append(cmd)
    return commands[0] if commands else None


DEFAULT_AGENT_TIMEOUT = 120
DEFAULT_PRINTIME_TIMEOUT = 60
MAX_FEEDBACK_CHARS = 1500
MAX_NO_COMMAND_NUDGES = 2


@dataclass
class AgentSession:
    """One cursor agent chat per eval case — follow-ups use --resume, not new agents."""

    chat_id: str
    isolated_dir: Path
    verbose: bool = False
    log: Optional[Callable[[str], None]] = None
    turn: int = 0

    @classmethod
    def start(
        cls,
        isolated_dir: Path,
        *,
        verbose: bool = False,
        log: Optional[Callable[[str], None]] = None,
    ) -> AgentSession:
        rc, out = _run_subprocess(
            ['cursor', 'agent', 'create-chat'],
            cwd=isolated_dir,
            timeout=30,
            label='create-chat',
        )
        if rc != 0 or not out.strip():
            raise RuntimeError(f'cursor agent create-chat failed: {out}')
        chat_id = out.strip().splitlines()[-1].strip()
        _vlog(verbose, f'  agent session: {chat_id}', log=log)
        return cls(chat_id=chat_id, isolated_dir=isolated_dir, verbose=verbose, log=log)

    def send(self, message: str, *, timeout: int = DEFAULT_AGENT_TIMEOUT) -> str:
        self.turn += 1
        cmd = [
            'cursor', 'agent', '--print', '--force',
            '--resume', self.chat_id,
            '--workspace', str(self.isolated_dir),
            message,
        ]
        _vlog(
            self.verbose,
            f'  agent message turn {self.turn} (session {self.chat_id[:8]}…, {len(message)} chars)',
            log=self.log,
        )
        rc, combined = _run_subprocess(
            cmd,
            cwd=self.isolated_dir,
            timeout=timeout,
            verbose=self.verbose,
            log=self.log,
            label='cursor agent',
        )
        _vlog(self.verbose, f'  agent exit code: {rc}', log=self.log)
        if rc != 0 and not combined:
            raise RuntimeError('cursor agent failed with no output')
        return combined


def _kill_process_tree(proc: subprocess.Popen, *, log: Optional[Callable[[str], None]] = None) -> None:
    """Terminate process group started with start_new_session=True."""
    if proc.poll() is not None:
        return
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        proc.terminate()
    except PermissionError:
        proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            proc.kill()
        proc.wait(timeout=5)
    if log:
        log(f'  killed lingering subprocess pid={proc.pid}')


def _run_subprocess(
    cmd: Sequence[str],
    *,
    cwd: Optional[Path] = None,
    env: Optional[Dict[str, str]] = None,
    timeout: int,
    verbose: bool = False,
    log: Optional[Callable[[str], None]] = None,
    label: str = 'subprocess',
) -> tuple[int, str]:
    proc = subprocess.Popen(
        list(cmd),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=str(cwd) if cwd else None,
        env=env,
        start_new_session=True,
    )
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        _kill_process_tree(proc, log=log if verbose else None)
        raise RuntimeError(f'{label} timed out after {timeout}s') from exc
    combined = '\n'.join(part for part in (stdout, stderr) if part).strip()
    return proc.returncode, combined


def run_printime_command(argv: Sequence[str], *, timeout: int = DEFAULT_PRINTIME_TIMEOUT) -> tuple[int, str]:
    """Execute a printime command in eval-safe preview mode."""
    env = os.environ.copy()
    env['PRINTIME_EVAL'] = '1'
    return _run_subprocess(
        argv,
        env=env,
        timeout=timeout,
        label='printime',
    )


def _describe_run(
    case: Dict[str, Any],
    run: CommandRun,
    *,
    log: Callable[[str], None],
) -> None:
    cmd = shlex.join(run.argv) if run.argv else '(empty)'
    log(f'    attempt {run.attempt}: {cmd}')
    if not run.argv:
        log('      grade: NO COMMAND')
        return
    vr = validate_command_argv(run.argv)
    if not vr.ok:
        log(f'      parse: INVALID ({vr.error})')
    else:
        log(f'      parse: OK intent={vr.intent}')
    if run.exact_match:
        log('      grade: EXACT MATCH')
    else:
        expected = shlex.join(expected_argv(case))
        log(f'      grade: WRONG (expected: {expected})')
    if run.output:
        first_line = run.output.splitlines()[0][:100]
        log(f'      output: {first_line}…')


def _log_agent_output(output: str, *, log: Callable[[str], None], max_chars: int = 800) -> None:
    if len(output) <= max_chars:
        for line in output.splitlines():
            log(f'    | {line}')
        return
    for line in output[:max_chars].splitlines():
        log(f'    | {line}')
    log(f'    | … ({len(output) - max_chars} more chars truncated)')


def _write_fixture_files(
    isolated_dir: Path,
    case: Dict[str, Any],
    *,
    verbose: bool = False,
    log: Optional[Callable[[str], None]] = None,
) -> None:
    for rel_path, content in (case.get('fixture_files') or {}).items():
        path = isolated_dir / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8')
        _vlog(verbose, f'  fixture file: {rel_path} ({len(content)} chars)', log=log)


def simulate_case(
    case: Dict[str, Any],
    *,
    isolated_dir: Path,
    skill_md: str,
    max_attempts: int = 4,
    dry_run: bool = False,
    verbose: bool = False,
    log: Optional[Callable[[str], None]] = None,
) -> AgentSimResult:
    log = log or (lambda m: print(m, file=sys.stderr))
    result = AgentSimResult(case_id=case['id'], prompt=case['prompt'])
    context_fixture = case.get('context_fixture')
    expected = expected_argv(case)

    _vlog(verbose, '', log=log)
    _vlog(verbose, f'── case: {case["id"]} ──', log=log)
    _vlog(verbose, f'  prompt: {case["prompt"]!r}', log=log)
    _vlog(verbose, f'  expected: {shlex.join(expected)}', log=log)
    _vlog(verbose, f'  max attempts: {max_attempts}', log=log)
    if case.get('notes'):
        _vlog(verbose, f'  notes: {case["notes"]}', log=log)

    if case.get('requires_context') and not context_fixture and not case.get('force_run'):
        result.error = 'requires_context (no context_fixture in eval case)'
        _vlog(verbose, f'  skip: {result.error}', log=log)
        return result

    _write_fixture_files(isolated_dir, case, verbose=verbose, log=log)

    if dry_run:
        _vlog(verbose, '  mode: dry-run (expected command only, agent not invoked)', log=log)
        result.attempts.append(expected)
        exact = True
        result.runs.append(CommandRun(1, expected, 0, '[dry-run]', exact))
        result.score = score_attempts(case, result.attempts, max_attempts=max_attempts)
        if verbose:
            _describe_run(case, result.runs[0], log=log)
        return result

    system = build_agent_system_prompt(skill_md=skill_md)
    initial = build_initial_task_prompt(
        case['prompt'],
        max_attempts=max_attempts,
        context_fixture=context_fixture,
    )
    command_attempts = 0
    no_command_nudges = 0

    try:
        session = AgentSession.start(isolated_dir, verbose=verbose, log=log)
        agent_out = session.send(f'{system}\n\n---\n\n{initial}')
        result.raw_outputs.append(agent_out)
    except (RuntimeError, subprocess.TimeoutExpired, OSError) as exc:
        result.error = str(exc)
        _vlog(verbose, f'  error: {result.error}', log=log)
        return result

    while command_attempts < max_attempts:
        if verbose:
            _vlog(verbose, f'  grading command attempt {command_attempts + 1}/{max_attempts}', log=log)
            _vlog(verbose, '  agent reply:', log=log)
            _log_agent_output(agent_out, log=log)

        cmd_str = extract_printime_command(agent_out)
        if not cmd_str:
            no_command_nudges += 1
            run = CommandRun(
                command_attempts + 1,
                [],
                1,
                'No printime command found in agent output.',
                False,
            )
            result.runs.append(run)
            if verbose:
                _describe_run(case, run, log=log)
            if no_command_nudges >= MAX_NO_COMMAND_NUDGES:
                command_attempts += 1
                result.attempts.append([])
                no_command_nudges = 0
                if command_attempts >= max_attempts:
                    break
            try:
                agent_out = session.send(build_wrong_command_feedback(
                    run, attempt=command_attempts, max_attempts=max_attempts,
                ))
                result.raw_outputs.append(agent_out)
            except (RuntimeError, subprocess.TimeoutExpired, OSError) as exc:
                result.error = str(exc)
                _vlog(verbose, f'  error: {result.error}', log=log)
            continue

        no_command_nudges = 0
        argv = parse_command_string(cmd_str)
        command_attempts += 1
        result.attempts.append(argv)
        exact = commands_match_exactly(argv, expected)

        if exact:
            rc, output = 0, '[exact match — command not re-run]'
            _vlog(verbose, '  exact match — case done', log=log)
        else:
            try:
                rc, output = run_printime_command(argv)
            except (OSError, subprocess.TimeoutExpired) as exc:
                rc, output = 1, str(exc)

        run = CommandRun(command_attempts, argv, rc, output, exact)
        result.runs.append(run)

        if verbose:
            _describe_run(case, run, log=log)
            if output and not exact:
                _vlog(verbose, '  command output:', log=log)
                _log_agent_output(output, log=log, max_chars=400)

        if exact:
            break
        if command_attempts >= max_attempts:
            break

        try:
            agent_out = session.send(build_wrong_command_feedback(
                run, attempt=command_attempts, max_attempts=max_attempts,
            ))
            result.raw_outputs.append(agent_out)
        except (RuntimeError, subprocess.TimeoutExpired, OSError) as exc:
            result.error = str(exc)
            _vlog(verbose, f'  error: {result.error}', log=log)
            break

    result.score = score_attempts(case, result.attempts, max_attempts=max_attempts)
    if result.score and verbose:
        s = result.score
        _vlog(
            verbose,
            f'  final: score={s.score:.2f}  attempts={s.attempts}'
            f'  first_correct={s.first_correct}',
            log=log,
        )
    return result


def run_agent_simulation(
    evals_path: Path,
    *,
    skill_dir: Optional[Path] = None,
    case_id: Optional[str] = None,
    dry_run: bool = False,
    verbose: bool = False,
    max_attempts: Optional[int] = None,
) -> List[AgentSimResult]:
    log = lambda m: print(m, file=sys.stderr)
    skill_dir = skill_dir or default_skill_dir()
    config = load_eval_config(evals_path)
    max_attempts = max_attempts or config['max_attempts']

    _vlog(verbose, 'Agent simulation', log=log)
    _vlog(verbose, f'  evals: {evals_path}', log=log)
    _vlog(verbose, f'  skill: {skill_dir}', log=log)
    _vlog(verbose, '  context: SKILL.md only', log=log)
    _vlog(verbose, '  session: one cursor agent chat per case (--resume follow-ups)', log=log)
    _vlog(verbose, f'  grading: exact command match, max {max_attempts} attempts', log=log)
    if dry_run:
        _vlog(verbose, '  dry-run: yes', log=log)

    skill_md = load_skill_md(skill_dir, verbose=verbose, log=log)
    cases = load_evals(evals_path)
    if case_id:
        cases = [c for c in cases if c['id'] == case_id]

    results: List[AgentSimResult] = []
    with tempfile.TemporaryDirectory(prefix='printime-eval-') as tmp:
        isolated_dir = Path(tmp)
        (isolated_dir / 'SKILL.md').write_text(skill_md, encoding='utf-8')
        _vlog(verbose, f'  isolated cwd: {isolated_dir}', log=log)

        for idx, case in enumerate(cases, start=1):
            if verbose:
                _vlog(verbose, f'[{idx}/{len(cases)}]', log=log)
            results.append(simulate_case(
                case,
                isolated_dir=isolated_dir,
                skill_md=skill_md,
                max_attempts=max_attempts,
                dry_run=dry_run,
                verbose=verbose,
                log=log,
            ))
    return results


def format_simulation_report(results: Sequence[AgentSimResult]) -> str:
    lines = ['Agent simulation report', '=' * 40]
    scored = [r for r in results if r.score is not None]
    skipped = [r for r in results if r.error]
    if scored:
        first_hits = sum(1 for r in scored if r.score and r.score.first_correct)
        avg = sum(r.score.score for r in scored if r.score) / len(scored)
        lines.append(
            f'Cases: {len(results)}  scored: {len(scored)}  skipped: {len(skipped)}'
            f'  first-try: {first_hits}/{len(scored)}  avg score: {avg:.2f}'
        )
    else:
        lines.append(f'Cases: {len(results)}  scored: 0  skipped: {len(skipped)}')
    lines.append('')
    for r in results:
        if r.error:
            lines.append(f'  [SKIP] {r.case_id}: {r.error}')
            continue
        if not r.score:
            lines.append(f'  [FAIL] {r.case_id}: no score')
            continue
        s = r.score
        mark = 'OK' if s.first_correct else ('LATE' if s.correct_at else 'FAIL')
        last_cmd = shlex.join(r.attempts[-1]) if r.attempts and r.attempts[-1] else '(none)'
        lines.append(
            f'  [{mark}] {r.case_id}  score={s.score:.2f}  attempts={s.attempts}  last={last_cmd}'
        )
    return '\n'.join(lines)


def cmd_eval_simulate(args) -> int:
    evals_path = Path(args.file) if args.file else default_evals_path()
    verbose = getattr(args, 'verbose', False)
    max_attempts = getattr(args, 'max_attempts', None)
    results = run_agent_simulation(
        evals_path,
        skill_dir=Path(args.skill_dir) if getattr(args, 'skill_dir', None) else None,
        case_id=getattr(args, 'case', None),
        dry_run=getattr(args, 'dry_run', False),
        verbose=verbose,
        max_attempts=max_attempts,
    )
    print(format_simulation_report(results))

    if getattr(args, 'json', False):
        payload = []
        for r in results:
            payload.append({
                'case_id': r.case_id,
                'prompt': r.prompt,
                'attempts': [shlex.join(a) if a else '' for a in r.attempts],
                'runs': [
                    {
                        'attempt': run.attempt,
                        'command': shlex.join(run.argv) if run.argv else '',
                        'returncode': run.returncode,
                        'exact_match': run.exact_match,
                        'output': run.output,
                    }
                    for run in r.runs
                ],
                'score': r.score.__dict__ if r.score else None,
                'error': r.error,
            })
        print(json.dumps(payload, indent=2))

    scored = [r for r in results if r.score is not None]
    if not scored:
        return 1
    return 0 if all(r.score and r.score.first_correct for r in scored) else 1
