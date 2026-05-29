#!/usr/bin/env python3
"""Create the printime argument parser (intents + legacy commands)."""

from __future__ import annotations


def create_parser():
    """Build the full CLI parser tree."""
    from printime.cli import build_parser
    return build_parser()
