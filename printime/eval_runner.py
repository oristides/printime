#!/usr/bin/env python3
"""Validate and score agent-interpreted printime commands against eval cases."""

from __future__ import annotations

import json
import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

DEFAULT_MAX_ATTEMPTS = 4


@dataclass
class ValidationResult:
    ok: bool
    intent: Optional[str] = None
    error: Optional[str] = None
    args: Any = None


@dataclass
class AttemptScore:
    case_id: str
    attempts: int
    first_correct: bool
    correct_at: Optional[int]
    score: float
    matched_intent: Optional[str] = None


def load_evals(path: Path) -> List[Dict[str, Any]]:
    data = json.loads(path.read_text(encoding='utf-8'))
    return list(data.get('cases', []))


def load_eval_config(path: Path) -> Dict[str, Any]:
    data = json.loads(path.read_text(encoding='utf-8'))
    simulation = data.get('simulation', {})
    scoring = simulation.get('scoring', {})
    return {
        'max_attempts': int(scoring.get('max_attempts', DEFAULT_MAX_ATTEMPTS)),
    }


def parse_command_string(command: str) -> List[str]:
    return shlex.split(command.strip())


def expected_argv(case: Dict[str, Any]) -> List[str]:
    """Exact expected command argv for a case."""
    cmd = case.get('expected') or case.get('golden')
    if not cmd:
        raise ValueError(f"case {case.get('id', '?')} missing 'expected' command")
    return parse_command_string(cmd)


def commands_match_exactly(actual: Sequence[str], expected: Sequence[str]) -> bool:
    """True when argv lists match; optional --title may equal template default."""
    from printime.template_defaults import strip_default_title_flag
    from printime.text_encoding import decode_cli_escapes

    def norm(argv: Sequence[str]) -> List[str]:
        decoded = [decode_cli_escapes(tok) if idx else tok for idx, tok in enumerate(argv)]
        return strip_default_title_flag(decoded)

    return norm(actual) == norm(expected)


def validate_command_argv(argv: Sequence[str]) -> ValidationResult:
    """Return whether argv parses as a valid printime command."""
    if not argv:
        return ValidationResult(ok=False, error='empty argv')
    if argv[0] != 'printime':
        return ValidationResult(ok=False, error='must start with printime')

    from printime.cli_parser import create_parser

    parser = create_parser()
    try:
        args = parser.parse_args(list(argv[1:]))
    except SystemExit:
        return ValidationResult(ok=False, error='argparse rejected argv')

    intent = getattr(args, 'intent', None) or getattr(args, 'command', None)
    if intent in (None, 'eval'):
        return ValidationResult(ok=False, error='no subcommand', args=args)
    return ValidationResult(ok=True, intent=intent, args=args)


def case_accepts(case: Dict[str, Any], argv: Sequence[str]) -> bool:
    """True when argv exactly matches the case expected command."""
    try:
        return commands_match_exactly(argv, expected_argv(case))
    except ValueError:
        return False


def score_attempts(
    case: Dict[str, Any],
    attempts: Sequence[Sequence[str]],
    *,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
) -> AttemptScore:
    """Score up to max_attempts tries. Exact command match only."""
    expected = expected_argv(case)
    capped = [list(a) for a in attempts[:max_attempts]]

    correct_at: Optional[int] = None
    matched_intent: Optional[str] = None
    for idx, argv in enumerate(capped, start=1):
        if commands_match_exactly(argv, expected):
            correct_at = idx
            vr = validate_command_argv(argv)
            matched_intent = vr.intent
            break

    if correct_at is None:
        return AttemptScore(
            case_id=case['id'],
            attempts=max_attempts,
            first_correct=False,
            correct_at=None,
            score=0.0,
        )
    return AttemptScore(
        case_id=case['id'],
        attempts=correct_at,
        first_correct=(correct_at == 1),
        correct_at=correct_at,
        score=1.0 / correct_at,
        matched_intent=matched_intent,
    )


def run_golden_evals(evals_path: Path) -> List[AttemptScore]:
    """Score each case's expected command as a single first attempt."""
    config = load_eval_config(evals_path)
    scores = []
    for case in load_evals(evals_path):
        if not (case.get('expected') or case.get('golden')):
            continue
        argv = expected_argv(case)
        scores.append(score_attempts(case, [argv], max_attempts=config['max_attempts']))
    return scores


def format_eval_report(scores: Sequence[AttemptScore]) -> str:
    lines = ['Eval report', '=' * 40]
    total = len(scores)
    first_hits = sum(1 for s in scores if s.first_correct)
    avg_score = sum(s.score for s in scores) / total if total else 0.0
    lines.append(f'Cases: {total}  first-try: {first_hits}/{total}  avg score: {avg_score:.2f}')
    lines.append('')
    for s in scores:
        mark = 'OK' if s.first_correct else ('LATE' if s.correct_at else 'FAIL')
        lines.append(
            f'  [{mark}] {s.case_id}  attempts={s.attempts}  score={s.score:.2f}  intent={s.matched_intent}'
        )
    return '\n'.join(lines)


def cmd_eval(args) -> int:
    evals_path = Path(args.file)
    if not evals_path.is_file():
        print(f'Error: evals file not found: {evals_path}', file=__import__('sys').stderr)
        return 1

    if getattr(args, 'validate', None):
        argv = parse_command_string(args.validate)
        result = validate_command_argv(argv)
        if result.ok:
            print(f'OK intent={result.intent}')
            return 0
        print(f'INVALID: {result.error}', file=__import__('sys').stderr)
        return 1

    if getattr(args, 'score', None):
        case = next((c for c in load_evals(evals_path) if c['id'] == args.case), None)
        if not case:
            print(f'Error: unknown case {args.case}', file=__import__('sys').stderr)
            return 1
        config = load_eval_config(evals_path)
        max_attempts = getattr(args, 'max_attempts', None) or config['max_attempts']
        attempts = [parse_command_string(line) for line in args.score.strip().splitlines() if line.strip()]
        score = score_attempts(case, attempts, max_attempts=max_attempts)
        print(json.dumps(score.__dict__, indent=2))
        return 0

    scores = run_golden_evals(evals_path)
    print(format_eval_report(scores))
    return 0 if all(s.first_correct for s in scores) else 1
