"""OB agent package for managing prompts and OpenAI interactions."""

from typing import Any, Dict
import json
import time

from .ob_client import OB, logger


def call_ob_agent(role: str, payload: Dict[str, Any], retries: int = 2, delay: float = 1.0) -> Dict[str, Any]:
    """Send ``payload`` to OB and return the parsed JSON response.

    This helper wraps :class:`OB` with basic retry and JSON parsing logic so the
    GUI can display clean errors instead of crashing.  Any large payloads are
    logged only as excerpts.
    """

    message = json.dumps(payload)
    last_error: Exception | None = None

    for attempt in range(1, retries + 2):  # initial try + retries
        try:
            logger.info("OB call start | task=%s | payload=%s", role, message[:1000])
            response = OB(role=role).send_message(message)
            logger.info("OB call success | task=%s | response=%s", role, response[:1000])
            return json.loads(response)
        except json.JSONDecodeError as e:
            logger.warning("OB returned invalid JSON on attempt %d: %s", attempt, e)
            last_error = e
            message = f"{message}\n\nReturn ONLY valid JSON with no extra text."
        except Exception as e:  # network/timeouts/etc.
            logger.error("OB call failed on attempt %d: %s", attempt, e)
            last_error = e

        if attempt <= retries:
            time.sleep(delay)

    err_msg = f"OB agent failure after {retries + 1} attempts: {last_error}"
    logger.error(err_msg)
    return {"error": err_msg}


__all__ = ["OB", "call_ob_agent"]
