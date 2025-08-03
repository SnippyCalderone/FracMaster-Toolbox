"""Test script to verify OB responds using the API key from `.env` with CLI role switching and interactive mode."""

from __future__ import annotations

import argparse
import os

from dotenv import load_dotenv
from fracmaster_toolbox.ob_agent import OB
from fracmaster_toolbox.ob_agent.ob_prompts import ROLE_PROMPTS, DEFAULT_ROLE


def main() -> None:
    """Send prompts to OB with the selected role and print the responses."""
    load_dotenv()
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY not set; skipping OB agent test.")
        return

    parser = argparse.ArgumentParser(description="Test OB agent with role switching.")
    parser.add_argument(
        "--role",
        type=str,
        default=DEFAULT_ROLE,
        help=f"Role for OB (options: {', '.join(ROLE_PROMPTS.keys())})"
    )
    parser.add_argument(
        "--prompt",
        type=str,
        help="Single prompt to send to OB (if omitted, interactive mode will start)."
    )

    args = parser.parse_args()

    # Validate role
    if args.role not in ROLE_PROMPTS:
        print(f"❌ Invalid role: '{args.role}'")
        print(f"Available roles: {', '.join(ROLE_PROMPTS.keys())}")
        return

    ob = OB(role=args.role)

    # Single-prompt mode
    if args.prompt:
        response = ob.send_message(args.prompt)
        print(f"\n[OB - {args.role}] {response}")
        return

    # Interactive mode
    print(f"🟢 Interactive mode started (Role: {args.role})")
    print("Type 'exit' or 'quit' to end the session.\n")

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in {"exit", "quit"}:
            print("👋 Exiting interactive mode.")
            break
        if not user_input:
            continue
        response = ob.send_message(user_input)
        print(f"[OB - {args.role}] {response}\n")


if __name__ == "__main__":
    main()