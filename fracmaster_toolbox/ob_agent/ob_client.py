"""Client wrapper and OB class for interacting with OpenAI's API."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Dict

from dotenv import load_dotenv
from openai import OpenAI

from .ob_prompts import DEFAULT_ROLE, ROLE_PROMPTS

# Configure logging
LOG_FILE = Path(__file__).resolve().parents[2] / "logs" / "ob_agent.log"
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


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
        logger.info("Role: %s | Prompt: %s", self.role, prompt)
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
        )
        content = response.choices[0].message["content"]
        logger.info("Response: %s", content)
        return content
