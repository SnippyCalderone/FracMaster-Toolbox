# OB Agent

This module manages OB's prompts and interactions with OpenAI's API.

## How it works
- `ob_client.py` exposes the `OB` class which loads the API key from a `.env` file,
  initialises the OpenAI client, and logs all requests and responses to
  `logs/ob_agent.log`.
- `ob_prompts.py` stores reusable prompts and role definitions.
- `ob_runner.py` provides a simple CLI for sending prompts to OB.

## Adding new prompts
Update `ob_prompts.py` and append a new entry to the `ROLE_PROMPTS` dictionary.
Use `OB.set_role("your_role")` to activate the new role.

## Running tests
1. Create a `.env` file with `OPENAI_API_KEY=<your key>`.
2. Run `python scripts/test_ob_agent.py` to send a test prompt to OB.
