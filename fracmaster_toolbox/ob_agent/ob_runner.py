import argparse
import json
import os
from dotenv import load_dotenv
from colorama import Fore, Style
from fracmaster_toolbox.ob_agent.ob_client import OB

def interactive_mode(ob: OB):
    """Interactive loop for talking to OB."""
    print(f"{Fore.GREEN}🟢 Interactive mode started (Role: {ob.role}){Style.RESET_ALL}")
    print(f"{Fore.YELLOW}Type 'exit' or 'quit' to end the session.{Style.RESET_ALL}\n")

    merged_stages = []  # Persistent store of merged stage data

    while True:
        user_input = input(f"{Fore.CYAN}You:{Style.RESET_ALL} ")
        if user_input.lower() in {"exit", "quit"}:
            print(f"{Fore.MAGENTA}👋 Exiting interactive mode.{Style.RESET_ALL}")
            break

        response = ob.send_message(user_input)

        try:
            # Try to parse OB response for JSON stage data
            stage_data = json.loads(response)
            if isinstance(stage_data, list):
                merged_stages = merge_stage_data(merged_stages, stage_data)

                if has_unresolved_nulls(merged_stages):
                    print(f"{Fore.YELLOW}[OB - {ob.role}] Missing data detected. Current stage data: {json.dumps(merged_stages, indent=2)}{Style.RESET_ALL}")
                    print(f"{Fore.YELLOW}OB will now prompt you to provide the missing depths...{Style.RESET_ALL}")
                else:
                    print(f"{Fore.GREEN}[OB - {ob.role}] ✅ All stages are resolved! Here's the final merged preview:{Style.RESET_ALL}")
                    print(json.dumps(merged_stages, indent=2))
                    print(f"{Fore.MAGENTA}Confirm if this looks correct before OB finalizes these values.{Style.RESET_ALL}")

            else:
                print(f"{Fore.RED}Unexpected OB response format. Showing raw response:\n{response}{Style.RESET_ALL}")

        except json.JSONDecodeError:
            # OB might still be asking for clarification, not giving JSON yet
            print(f"{Fore.YELLOW}[OB - {ob.role}] {response}{Style.RESET_ALL}")


def merge_stage_data(existing_stages, new_stages):
    """Merge new stage data into the existing stage list while preserving previous data."""
    stage_map = {s["stage"]: s for s in existing_stages}

    for new_stage in new_stages:
        stage_num = new_stage["stage"]
        if stage_num in stage_map:
            for key in ["top", "bottom", "plug"]:
                if new_stage[key] is not None:
                    stage_map[stage_num][key] = new_stage[key]
        else:
            stage_map[stage_num] = new_stage

    return list(stage_map.values())


def has_unresolved_nulls(stages):
    """Check if any stage still has null values."""
    return any(
        s["top"] is None or s["bottom"] is None or s["plug"] is None
        for s in stages
    )


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description="Run OB agent in CLI mode")
    parser.add_argument("--role", type=str, default="default", help="Set OB's role")
    parser.add_argument("--prompt", type=str, help="Send a single prompt to OB (non-interactive)")
    args = parser.parse_args()

    ob = OB(role=args.role)

    if args.prompt:
        response = ob.send_message(args.prompt)
        print(f"{Fore.GREEN}[OB - {args.role}] {Style.RESET_ALL}{response}")
    else:
        interactive_mode(ob)


if __name__ == "__main__":
    main()