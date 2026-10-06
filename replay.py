"""
Replay mode - runs saved scenarios deterministically for demo backup.
This is useful when the network fails or for consistent demo runs.
"""
import json
import sys
from pathlib import Path
from typing import Dict, Any, List
import time

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))
import db
from tools import calculate_uptime, get_clause, check_notice_period


def load_replay_scenario(scenario_file: Path) -> Dict[str, Any]:
    """Load a replay scenario from JSON file."""
    with open(scenario_file, 'r') as f:
        return json.load(f)


def run_replay(scenario: Dict[str, Any], delay: float = 1.0):
    """
    Run a replay scenario deterministically.

    Args:
        scenario: The scenario data with pre-defined steps
        delay: Delay between steps in seconds (for demo pacing)
    """
    print("="*60)
    print("REPLAY MODE - Deterministic Demo Run")
    print("="*60)
    print(f"Scenario: {scenario.get('name', 'Unnamed')}")
    print(f"Description: {scenario.get('description', 'No description')}")
    print()

    # Initialize database
    db.init_db()

    # Create claim
    claim_id = scenario.get('claim_id', f"REPLAY-{int(time.time())}")
    db.create_claim(claim_id, scenario['vendor'], scenario.get('incident_id'))
    print(f"[REPLAY] Claim ID: {claim_id}")
    print()

    # Run each step
    steps = scenario.get('steps', [])
    for i, step in enumerate(steps, 1):
        print(f"[STEP {i}/{len(steps)}] {step['description']}")
        print("-" * 60)

        # Execute the step
        if step['type'] == 'tool_call':
            tool_name = step['tool']
            args = step['arguments']

            if tool_name == 'calculate_uptime':
                result = calculate_uptime(**args)
            elif tool_name == 'get_clause':
                result = get_clause(**args)
            elif tool_name == 'check_notice_period':
                result = check_notice_period(**args)
            else:
                result = {"error": f"Unknown tool: {tool_name}"}

            print(f"Tool: {tool_name}")
            print(f"Result: {json.dumps(result, indent=2, default=str)}")

            # Log to database
            db.log_event(claim_id, "tool_call", {"tool": tool_name, "arguments": args}, result, step_number=i)

        elif step['type'] == 'decision':
            print(f"Decision: {step['decision']}")
            print(f"Reasoning: {step['reasoning']}")
            db.log_event(claim_id, "decision", {"reasoning": step['reasoning']}, {"decision": step['decision']}, step_number=i)

        elif step['type'] == 'file_claim':
            print(f"Claim message: {step['message'][:100]}...")
            db.log_event(claim_id, "file_claim", {"message": step['message']}, {"status": "submitted"}, step_number=i)

        elif step['type'] == 'vendor_response':
            print(f"Vendor response: {step['status']}")
            print(f"Reason: {step['reason']}")
            db.log_event(claim_id, "vendor_response", {}, step, step_number=i)

        elif step['type'] == 'file_rebuttal':
            print(f"Rebuttal message: {step['message'][:100]}...")
            db.log_event(claim_id, "file_rebuttal", {"message": step['message']}, {"status": "submitted"}, step_number=i)

        print()

        # Delay for pacing
        if delay > 0:
            time.sleep(delay)

    # Final result
    print("="*60)
    print("REPLAY COMPLETE")
    print("="*60)
    print(f"Claim ID: {claim_id}")
    print(f"Final status: {scenario.get('final_status', 'completed')}")
    print(f"Credit amount: ${scenario.get('credit_amount', 0)}")
    print()

    db.update_claim(claim_id, status=scenario.get('final_status', 'completed'), amount=scenario.get('credit_amount'))

    print("Replay data saved to database. View in dashboard at http://localhost:3000")


def save_demo_scenario(output_file: Path):
    """
    Save the demo scenario as a replay file.
    This creates a deterministic version of the demo for backup.
    """
    demo_scenario = {
        "name": "Demo Scenario - Invalid Maintenance Exclusion",
        "description": "VendorA outage with invalid maintenance exclusion (insufficient notice)",
        "vendor": "VendorA",
        "incident_id": "INC-2026-001",
        "claim_id": "DEMO-REPLAY",
        "final_status": "approved",
        "credit_amount": 100.0,
        "steps": [
            {
                "step": 1,
                "type": "tool_call",
                "description": "Retrieve uptime clause",
                "tool": "get_clause",
                "arguments": {"vendor": "VendorA", "topic": "uptime"}
            },
            {
                "step": 2,
                "type": "tool_call",
                "description": "Retrieve maintenance exclusion clause",
                "tool": "get_clause",
                "arguments": {"vendor": "VendorA", "topic": "maintenance_exclusion"}
            },
            {
                "step": 3,
                "type": "tool_call",
                "description": "Calculate uptime with maintenance excluded",
                "tool": "calculate_uptime",
                "arguments": {"incident_minutes": 78, "excluded_minutes": 35, "month_minutes": 44640}
            },
            {
                "step": 4,
                "type": "tool_call",
                "description": "Check maintenance notice period",
                "tool": "check_notice_period",
                "arguments": {
                    "notice_time": "2026-10-04T18:30:00Z",
                    "window_start": "2026-10-05T14:45:00Z",
                    "required_hours": 72
                }
            },
            {
                "step": 5,
                "type": "decision",
                "description": "Maintenance exclusion is invalid",
                "decision": "Exclude 0 minutes from downtime",
                "reasoning": "Notice was posted only 20.25 hours before maintenance, less than required 72 hours"
            },
            {
                "step": 6,
                "type": "tool_call",
                "description": "Recalculate uptime without exclusion",
                "tool": "calculate_uptime",
                "arguments": {"incident_minutes": 78, "excluded_minutes": 0, "month_minutes": 44640}
            },
            {
                "step": 7,
                "type": "file_claim",
                "description": "File initial claim",
                "message": "We request a 10% credit for the outage on 2026-10-05. The maintenance exclusion is invalid due to insufficient notice (20.25 hours vs required 72 hours)."
            },
            {
                "step": 8,
                "type": "vendor_response",
                "description": "Vendor rejects claim",
                "status": "rejected",
                "reason": "35 minutes were scheduled maintenance. These minutes are excluded from uptime calculations per our SLA."
            },
            {
                "step": 9,
                "type": "file_rebuttal",
                "description": "File rebuttal with notice period evidence",
                "message": "Your rejection is incorrect. The maintenance exclusion is invalid because the SLA requires 72 hours notice, but only 20.25 hours were provided."
            },
            {
                "step": 10,
                "type": "vendor_response",
                "description": "Vendor approves claim",
                "status": "approved",
                "reason": "Your rebuttal is correct. The maintenance notice was posted only 20 hours in advance, which is less than the required 72 hours. The exclusion is invalid."
            }
        ]
    }

    with open(output_file, 'w') as f:
        json.dump(demo_scenario, f, indent=2)

    print(f"Demo scenario saved to {output_file}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Replay mode for Clawback demo")
    parser.add_argument("--save", action="store_true", help="Save demo scenario to file")
    parser.add_argument("--run", type=str, help="Run replay from file")
    parser.add_argument("--delay", type=float, default=1.0, help="Delay between steps in seconds")
    parser.add_argument("--output", type=str, default="demo_replay.json", help="Output file for saved scenario")

    args = parser.parse_args()

    if args.save:
        save_demo_scenario(Path(args.output))
    elif args.run:
        scenario = load_replay_scenario(Path(args.run))
        run_replay(scenario, delay=args.delay)
    else:
        # Default: save and run
        output_file = Path(args.output)
        save_demo_scenario(output_file)
        print()
        scenario = load_replay_scenario(output_file)
        run_replay(scenario, delay=args.delay)
