from __future__ import annotations

import argparse

from aios.application.scheduler_app import (
    run_all_due_once,
    run_settlement_due_once,
    serve,
)


def main() -> None:
    parser = argparse.ArgumentParser(prog="aios")
    subcommands = parser.add_subparsers(dest="command", required=True)

    scheduler = subcommands.add_parser("scheduler")
    scheduler_subcommands = scheduler.add_subparsers(
        dest="scheduler_command",
        required=True,
    )
    scheduler_subcommands.add_parser("run-once")
    scheduler_subcommands.add_parser("serve")

    settlement = subcommands.add_parser("settlement")
    settlement_subcommands = settlement.add_subparsers(
        dest="settlement_command",
        required=True,
    )
    settlement_subcommands.add_parser("run-once")

    args = parser.parse_args()
    if args.command == "scheduler" and args.scheduler_command == "run-once":
        result = run_all_due_once()
        print(
            "research_runs="
            f"{len(result.research.runs)} research_errors="
            f"{len(result.research.errors)} settlements="
            f"{len(result.settlement.settled)} settlement_errors="
            f"{len(result.settlement.errors)}"
        )
        return
    if args.command == "scheduler" and args.scheduler_command == "serve":
        serve()
        return
    if args.command == "settlement" and args.settlement_command == "run-once":
        settlement_result = run_settlement_due_once()
        print(
            f"settlements={len(settlement_result.settled)} "
            f"errors={len(settlement_result.errors)}"
        )
        return
    parser.error("unsupported command")
