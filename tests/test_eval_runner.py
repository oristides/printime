"""Tests for agent command eval scoring and validation."""

from pathlib import Path

import pytest


class TestValidateCommand:
    def test_valid_checklist_command(self):
        from printime.eval_runner import validate_command_argv

        result = validate_command_argv([
            'printime', 'checklist', '--title', 'Tasks', '--items', 'Votar',
        ])
        assert result.ok is True
        assert result.intent == 'checklist'

    def test_valid_task_command(self):
        from printime.eval_runner import validate_command_argv

        result = validate_command_argv([
            'printime', 'task', '--body', 'comer arroz hoy',
        ])
        assert result.ok is True
        assert result.intent == 'task'

    def test_invalid_unknown_subcommand(self):
        from printime.eval_runner import validate_command_argv

        result = validate_command_argv(['printime', 'not-a-command'])
        assert result.ok is False

    def test_url_intent(self):
        from printime.eval_runner import validate_command_argv

        result = validate_command_argv([
            'printime', 'url', 'https://example.com/post',
        ])
        assert result.ok is True
        assert result.intent == 'url'


class TestExactMatch:
    def test_exact_match_only(self):
        from printime.eval_runner import case_accepts, commands_match_exactly

        expected = ['printime', 'task', '--body', 'comer arroz hoy']
        assert commands_match_exactly(expected, expected) is True
        assert case_accepts({'expected': 'printime task --body "comer arroz hoy"'}, expected) is True
        assert case_accepts(
            {'expected': 'printime task --body "comer arroz hoy"'},
            ['printime', 'task', '--body', 'comer arroz'],
        ) is False
        assert case_accepts(
            {'expected': 'printime task --body "comer arroz hoy"'},
            ['printime', 'checklist', '--items', 'comer arroz hoy'],
        ) is False


class TestScoreAttempts:
    def test_first_attempt_exact_scores_one(self):
        from printime.eval_runner import score_attempts

        case = {'id': 'task-arroz', 'expected': 'printime task --body "comer arroz hoy"'}
        attempts = [['printime', 'task', '--body', 'comer arroz hoy']]
        result = score_attempts(case, attempts, max_attempts=4)
        assert result.first_correct is True
        assert result.attempts == 1
        assert result.score == 1.0

    def test_wrong_attempts_before_exact_lower_score(self):
        from printime.eval_runner import score_attempts

        case = {'id': 'task-arroz', 'expected': 'printime task --body "comer arroz hoy"'}
        attempts = [
            ['printime', 'checklist', '--items', 'comer arroz'],
            ['printime', 'note', '--body', 'comer arroz'],
            ['printime', 'task', '--body', 'comer arroz hoy'],
        ]
        result = score_attempts(case, attempts, max_attempts=4)
        assert result.first_correct is False
        assert result.correct_at == 3
        assert result.attempts == 3
        assert result.score == pytest.approx(1 / 3)

    def test_never_exact_scores_zero_and_counts_max_attempts(self):
        from printime.eval_runner import score_attempts

        case = {'id': 'task-arroz', 'expected': 'printime task --body "comer arroz hoy"'}
        attempts = [
            ['printime', 'checklist', '--items', 'x'],
            ['printime', 'print', '--text', 'x'],
            ['printime', 'note', '--body', 'x'],
        ]
        result = score_attempts(case, attempts, max_attempts=4)
        assert result.correct_at is None
        assert result.attempts == 4
        assert result.score == 0.0

    def test_partial_contains_does_not_pass(self):
        from printime.eval_runner import score_attempts

        case = {'id': 'task-arroz', 'expected': 'printime task --body "comer arroz hoy"'}
        attempts = [['printime', 'task', '--body', 'comer arroz']]
        result = score_attempts(case, attempts, max_attempts=4)
        assert result.score == 0.0
        assert result.attempts == 4

    def test_default_title_equivalent_in_eval_match(self):
        from printime.eval_runner import commands_match_exactly

        with_title = ['printime', 'task', '--title', 'Task', '--body', 'buy milk']
        without_title = ['printime', 'task', '--body', 'buy milk']
        assert commands_match_exactly(with_title, without_title) is True
        assert commands_match_exactly(without_title, with_title) is True

    def test_custom_title_not_stripped(self):
        from printime.eval_runner import commands_match_exactly

        custom = ['printime', 'task', '--title', 'Hoje', '--body', 'buy milk']
        default = ['printime', 'task', '--body', 'buy milk']
        assert commands_match_exactly(custom, default) is False

    def test_escape_sequences_match_real_newlines(self):
        from printime.eval_runner import commands_match_exactly

        expected = ['printime', 'print', '--markdown', '--text', '# Title\n\n- item']
        actual = ['printime', 'print', '--markdown', '--text', r'# Title\n\n- item']
        assert commands_match_exactly(actual, expected) is True


class TestTemplateDefaults:
    def test_ensure_template_title_when_omitted(self):
        from printime.template_defaults import ensure_template_title

        ctx = ensure_template_title({'content': 'x'}, 'task')
        assert ctx['title'] == 'Task'

    def test_ensure_template_title_preserves_custom(self):
        from printime.template_defaults import ensure_template_title

        ctx = ensure_template_title({'title': 'Compras', 'content': 'x'}, 'checklist')
        assert ctx['title'] == 'Compras'


class TestDecodeCliEscapes:
    def test_newlines_in_text_arg(self):
        from printime.text_encoding import decode_cli_escapes

        assert decode_cli_escapes(r'# Sprint\n\n- fix') == '# Sprint\n\n- fix'
        assert decode_cli_escapes('line1\\nline2') == 'line1\nline2'


class TestEvalsFile:
    def test_load_evals_json(self):
        from printime.eval_runner import load_evals

        path = Path(__file__).resolve().parents[1] / 'skills' / 'printime-cli' / 'evals.json'
        if not path.exists():
            pytest.skip('evals.json not yet created')
        cases = load_evals(path)
        assert len(cases) >= 20
        assert all('id' in c and 'prompt' in c and ('expected' in c or 'golden' in c) for c in cases)
        assert all('accept' not in c for c in cases)


class TestAgentEvalContext:
    def test_load_skill_md_only(self):
        from printime.agent_eval import build_agent_system_prompt, load_skill_md, default_skill_dir

        skill_dir = default_skill_dir()
        if not (skill_dir / 'SKILL.md').is_file():
            pytest.skip('SKILL.md not found')
        skill_md = load_skill_md(skill_dir)
        assert 'Printime CLI' in skill_md

        prompt = build_agent_system_prompt(skill_md=skill_md)
        assert '# SKILL.md' in prompt
        assert 'printime note --help' not in prompt


class TestRunPrintimeCommand:
    def test_executes_valid_preview_command(self):
        from printime.agent_eval import run_printime_command

        rc, output = run_printime_command([
            'printime', 'task', '--body', 'eval test body',
        ])
        assert rc == 0
        assert output

    def test_markdown_text_unescapes_newlines(self):
        from printime.agent_eval import run_printime_command

        rc, output = run_printime_command([
            'printime', 'print', '--markdown', '--text', r'# Sprint\n\n- fix bug',
        ])
        assert rc == 0
        assert 'Sprint' in output
        assert 'fix bug' in output
        assert r'\n' not in output.split('Preview only')[0]
