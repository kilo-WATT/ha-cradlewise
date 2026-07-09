"""Command-line interface for the dry-run research scaffold."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from typing import Any

from .auth_probe import authentication_preview
from .provisioning_probe import provisioning_preview
from .redaction import redact
from .safety import (
    SafetyError,
    assert_dry_run,
    install_network_guard,
    reject_secret_arguments,
)
from .self_check import run_self_checks


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Dry-run-only Cradlewise MQTT provisioning research probe."
    )
    parser.add_argument(
        "command",
        nargs="?",
        choices=("all", "auth-preview", "provisioning-preview", "self-check"),
        default="all",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit safe JSON output.",
    )
    parser.add_argument(
        "--live-auth",
        action="store_true",
        help=(
            "Reserved for a separately approved future phase; currently blocked."
        ),
    )
    parser.add_argument(
        "--live-provisioning",
        action="store_true",
        help=(
            "Reserved for a separately approved future phase; currently blocked."
        ),
    )
    return parser


def _run(command: str) -> dict[str, Any]:
    report: dict[str, Any] = {
        "mode": "dry_run",
        "network_enabled": False,
    }

    if command == "self-check":
        report["self_check"] = run_self_checks()

    if command in {"all", "auth-preview"}:
        report["authentication"] = authentication_preview()

    if command in {"all", "provisioning-preview"}:
        report["provisioning"] = provisioning_preview()

    return redact(report)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the mandatory dry-run probe."""
    arguments = list(sys.argv[1:] if argv is None else argv)

    try:
        reject_secret_arguments(arguments)
        args = _parser().parse_args(arguments)
        if args.live_auth or args.live_provisioning:
            raise SafetyError("live_action_not_implemented")
        assert_dry_run(True)
        install_network_guard()
        report = _run(args.command)
    except SafetyError as error:
        print(
            json.dumps(
                {"result": "blocked", "category": error.category},
                sort_keys=True,
            )
        )
        return 2

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(json.dumps(report, indent=2, sort_keys=True))

    return 0
