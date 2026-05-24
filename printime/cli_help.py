#!/usr/bin/env python3
"""Helpful argparse errors — suggestions and subcommand help on mistakes."""

from __future__ import annotations

import argparse
import difflib
import re
import sys
from typing import Dict, Iterable, List, Optional

# Populated by cli.main() — maps command path → parser for contextual --help.
PARSER_REGISTRY: Dict[str, argparse.ArgumentParser] = {}


def _closest(word: str, choices: Iterable[str], cutoff: float = 0.6) -> Optional[str]:
    matches = difflib.get_close_matches(word, list(choices), n=1, cutoff=cutoff)
    return matches[0] if matches else None


def _option_names(parser: argparse.ArgumentParser) -> List[str]:
    names: List[str] = []
    for action in parser._actions:
        for opt in getattr(action, 'option_strings', []):
            if opt.startswith('--'):
                names.append(opt[2:])
    return names


def _suggest_options(bad_args: List[str], parser: argparse.ArgumentParser) -> List[str]:
    known = _option_names(parser)
    hints: List[str] = []
    for arg in bad_args:
        if not arg.startswith('-'):
            continue
        key = arg.lstrip('-')
        suggestion = _closest(key, known)
        if suggestion:
            hints.append(f"Unknown option {arg!r}. Did you mean --{suggestion}?")
        else:
            hints.append(f"Unknown option {arg!r}. Run with --help to see available flags.")
    return hints


def active_parser(fallback: argparse.ArgumentParser) -> argparse.ArgumentParser:
    """Pick the subcommand parser matching sys.argv (e.g. print, anytype.print)."""
    args = sys.argv[1:]
    if not args:
        return PARSER_REGISTRY.get('', fallback)
    if args[0] == 'anytype' and len(args) > 1 and not args[1].startswith('-'):
        return PARSER_REGISTRY.get(f'anytype.{args[1]}', PARSER_REGISTRY.get('anytype', fallback))
    if not args[0].startswith('-'):
        return PARSER_REGISTRY.get(args[0], fallback)
    return fallback


class HelpfulArgumentParser(argparse.ArgumentParser):
    """Print suggestions and subcommand help when the user makes a typo."""

    def error(self, message: str) -> None:
        hints: List[str] = []
        choice_match = re.search(
            r"invalid choice: '([^']+)' \(choose from '([^']+)'(?:, '([^']+)')*\)",
            message,
        )
        if choice_match:
            typo = choice_match.group(1)
            choices = re.findall(r"'([^']+)'", message.split('choose from', 1)[-1])
            suggestion = _closest(typo, choices)
            if suggestion:
                hints.append(f"Did you mean {suggestion!r}?")
            hints.append('Run printime --help to list commands.')

        unknown_match = re.search(r'unrecognized arguments: (.+)', message)
        help_parser = active_parser(self)
        if unknown_match:
            bad_args = unknown_match.group(1).split()
            hints.extend(_suggest_options(bad_args, help_parser))

        print(f'Error: {message}', file=sys.stderr)
        for hint in hints:
            print(hint, file=sys.stderr)
        if hints:
            print(file=sys.stderr)
        help_parser.print_help()
        sys.exit(2)
