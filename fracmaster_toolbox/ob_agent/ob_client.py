"""Client wrapper and OB class for interacting with OpenAI's API."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Dict
from datetime import datetime

from dotenv import load_dotenv
from openai import OpenAI

from .ob_prompts import DEFAULT_ROLE, ROLE_PROMPTS

# Configure logging with daily file naming. Logs are written to the repository
# `logs/` directory so they can be inspected outside of runtime.
LOG_DIR = Path(__file__).resolve().parents[2] / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Create a log file with today's date
log_filename = LOG_DIR / f"ob_agent_{datetime.now().strftime('%Y-%m-%d')}.log"

logger = logging.getLogger("ob_agent")
logger.setLevel(logging.INFO)

if not logger.handlers:
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    file_handler = logging.FileHandler(log_filename, encoding="utf-8")
    file_handler.setFormatter(formatter)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)


class OB:
    """Base class for interacting with OB via OpenAI's API."""

    def __init__(self, role: str = DEFAULT_ROLE) -> None:
        """Initialise the OpenAI client and set the initial role."""
        load_dotenv()
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise EnvironmentError("OPENAI_API_KEY not found in environment")
        self.client = OpenAI(api_key=api_key)
        self.role = role

    def set_role(self, role: str) -> None:
        """Switch between predefined OB roles."""
        if role not in ROLE_PROMPTS:
            raise ValueError(f"Unknown role: {role}")
        self.role = role

    def send_message(self, prompt: str) -> str:
        """Send a message to OB and return the response text."""
        system_prompt = ROLE_PROMPTS.get(self.role, ROLE_PROMPTS[DEFAULT_ROLE])
        # Log an excerpt of the payload to avoid huge log files
        logger.info("Role: %s | Prompt: %s", self.role, prompt[:1000])
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
        )
        content = response.choices[0].message.content
        logger.info("Response: %s", content[:1000])
        return content