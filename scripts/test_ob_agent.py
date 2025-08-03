"""Simple test to verify OB responds using the API key from `.env`."""

from __future__ import annotations

import os

from dotenv import load_dotenv

from fracmaster_toolbox.ob_agent import OB


def main() -> None:
    """Send a basic prompt to OB and print the response."""
    load_dotenv()
    if not os.getenv("OPENAI_API_KEY"):
        print("OPENAI_API_KEY not set; skipping OB agent test.")
        return
    ob = OB()
    response = ob.send_message("Hello OB")
    print("OB response:", response)


if __name__ == "__main__":
    main()
