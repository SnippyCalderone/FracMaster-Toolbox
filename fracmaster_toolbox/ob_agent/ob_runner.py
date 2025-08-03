"""CLI entry point for testing OB locally."""

from __future__ import annotations

import argparse

from .ob_client import OB
from .ob_prompts import ROLE_PROMPTS


def main() -> None:
    """Run the OB agent from the command line."""
    parser = argparse.ArgumentParser(description="Send a prompt to OB")
    parser.add_argument("prompt", help="Prompt to send to OB")
    parser.add_argument(
        "--role", default="default", choices=list(ROLE_PROMPTS.keys()), help="OB role to use"
    )
    args = parser.parse_args()

    ob = OB(role=args.role)
    print(ob.send_message(args.prompt))


if __name__ == "__main__":
    main()
