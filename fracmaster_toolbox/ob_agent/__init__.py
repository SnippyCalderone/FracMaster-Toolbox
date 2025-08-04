"""OB agent package for managing prompts and OpenAI interactions."""

from typing import Any, Dict
import json

from .ob_client import OB


def call_ob_agent(role: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Send a JSON payload to OB for the given role and return the parsed JSON response."""
    ob = OB(role=role)
    response = ob.send_message(json.dumps(payload))
    return json.loads(response)


__all__ = ["OB", "call_ob_agent"]
