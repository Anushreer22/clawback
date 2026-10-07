"""
Clawback agent - the main SLA credit recovery agent.
Uses ASI:One with tool calling to automate claim processing.
"""
import json
import os
from typing import Dict, Any, List
from openai import OpenAI
from dotenv import load_dotenv

# Import deterministic tools
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from tools import calculate_uptime, get_clause, get_status_history, check_notice_period, file_claim
import db

# Import communication module for agent-to-agent messaging
from agents.communication import get_communicator

# Load environment variables
load_dotenv()

ASI_KEY = os.getenv("ASI_KEY", "")
MODEL = os.getenv("ASI_MODEL", "asi1-mini")

if not ASI_KEY:
    raise ValueError("ASI_KEY environment variable not set. Please set it in .env file.")

# Initialize OpenAI client with ASI:One
client = OpenAI(
    base_url="https://api.asi1.ai/v1",
    api_key=ASI_KEY
)

# System prompt for the agent
SYSTEM_PROMPT = """You are an SLA credit recovery agent. Your job is to help customers recover credits from vendors when SLA terms are violated.

IMPORTANT RULES:
1. Always read the contract clause before claiming. Use the get_clause tool to retrieve exact contract language.
2. NEVER do math yourself. Always use the calculate_uptime tool for any uptime calculations.
3. If a claim is rejected, re-read the clause and check whether the rejection is valid using the available tools.
4. For maintenance exclusions, always check the notice period using check_notice_period.
5. If confidence is low or the amount is above the cap, ask for human approval before proceeding.
6. Be thorough - gather all relevant facts before making a claim.
7. Cite specific contract clauses and data points in your reasoning.

Your workflow:
1. Analyze the incident data
2. Check the SLA terms
3. Calculate actual uptime (considering exclusions)
4. Verify if maintenance exclusions are valid (check notice periods)
5. File a claim if justified
6. Handle rejections with evidence-based rebuttals
7. Report final outcome

Be professional, precise, and evidence-based in all communications."""

# Tool schemas for OpenAI function calling
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "calculate_uptime",
            "description": "Calculate uptime percentage and determine credit tier based on incident data",
            "parameters": {
                "type": "object",
                "properties": {
                    "incident_minutes": {
                        "type": "integer",
                        "description": "Total downtime in minutes"
                    },
                    "excluded_minutes": {
                        "type": "integer",
                        "description": "Minutes excluded from downtime (e.g., valid maintenance windows)"
                    },
                    "month_minutes": {
                        "type": "integer",
                        "description": "Total minutes in the month (default 44640 for 31-day month)"
                    }
                },
                "required": ["incident_minutes", "excluded_minutes", "month_minutes"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_clause",
            "description": "Retrieve the exact clause text from a vendor's SLA contract",
            "parameters": {
                "type": "object",
                "properties": {
                    "vendor": {
                        "type": "string",
                        "description": "Vendor name (e.g., 'VendorA')"
                    },
                    "topic": {
                        "type": "string",
                        "description": "Clause topic (e.g., 'maintenance_exclusion', 'uptime', 'claim_window')"
                    }
                },
                "required": ["vendor", "topic"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_status_history",
            "description": "Retrieve maintenance notice timestamps for a vendor within a time window",
            "parameters": {
                "type": "object",
                "properties": {
                    "vendor": {
                        "type": "string",
                        "description": "Vendor name (e.g., 'VendorA')"
                    },
                    "window_start": {
                        "type": "string",
                        "description": "ISO 8601 timestamp for window start"
                    },
                    "window_end": {
                        "type": "string",
                        "description": "ISO 8601 timestamp for window end"
                    }
                },
                "required": ["vendor", "window_start", "window_end"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_notice_period",
            "description": "Validate if a maintenance notice was posted with sufficient lead time",
            "parameters": {
                "type": "object",
                "properties": {
                    "notice_time": {
                        "type": "string",
                        "description": "ISO 8601 timestamp when notice was posted"
                    },
                    "window_start": {
                        "type": "string",
                        "description": "ISO 8601 timestamp when maintenance window starts"
                    },
                    "required_hours": {
                        "type": "integer",
                        "description": "Required notice period in hours"
                    }
                },
                "required": ["notice_time", "window_start", "required_hours"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "file_claim",
            "description": "File a claim with a vendor agent over the Chat Protocol",
            "parameters": {
                "type": "object",
                "properties": {
                    "vendor": {
                        "type": "string",
                        "description": "Vendor name (e.g., 'VendorA')"
                    },
                    "claim_message": {
                        "type": "string",
                        "description": "The claim message to send to the vendor"
                    },
                    "claim_id": {
                        "type": "string",
                        "description": "Optional claim ID for tracking. When filing a rebuttal, reuse the same claim ID to maintain conversation history.",
                        "default": None
                    }
                },
                "required": ["vendor", "claim_message"]
            }
        }
    }
]

# Tool registry mapping function names to actual functions
TOOL_REGISTRY = {
    "calculate_uptime": calculate_uptime,
    "get_clause": get_clause,
    "get_status_history": get_status_history,
    "check_notice_period": check_notice_period,
    "file_claim": file_claim
}

# Get communicator for agent-to-agent messaging
communicator = get_communicator()


def log_event(tool_call, result: Any, claim_id: str = None, step_number: int = None) -> None:
    """
    Log a tool call and its result to console and database.
    """
    print(f"[TOOL] {tool_call.function.name}({tool_call.function.arguments})")
    print(f"[RESULT] {json.dumps(result, indent=2, default=str)}")

    # Log to database if claim_id is provided
    if claim_id:
        db.log_event(
            claim_id=claim_id,
            event_type="tool_call",
            input_data={
                "tool": tool_call.function.name,
                "arguments": json.loads(tool_call.function.arguments)
            },
            output_data=result,
            step_number=step_number
        )


def log_agent_message(
    claim_id: str,
    message_type: str,
    sender: str,
    receiver: str,
    payload: Dict[str, Any],
    result: Dict[str, Any],
    step_number: int = None
) -> None:
    """
    Log agent-to-agent communication to console and database.

    Args:
        claim_id: Claim ID
        message_type: Type of message (SENT or RECEIVED)
        sender: Sender agent name
        receiver: Receiver agent name
        payload: Message payload
        result: Result/response
        step_number: Step number
    """
    event_type = f"AGENT_MESSAGE_{message_type}"
    print(f"[{event_type}] {sender} -> {receiver}")
    print(f"[PAYLOAD] {json.dumps(payload, indent=2, default=str)}")
    print(f"[RESULT] {json.dumps(result, indent=2, default=str)}")

    # Log to database
    if claim_id:
        db.log_event(
            claim_id=claim_id,
            event_type=event_type,
            input_data={
                "sender": sender,
                "receiver": receiver,
                "payload": payload
            },
            output_data=result,
            step_number=step_number
        )


def check_approval_gate(claim_id: str, claim_value: float, confidence: float = 0.8) -> bool:
    """
    Check if a claim requires human approval based on value and confidence.

    Args:
        claim_id: The claim ID
        claim_value: The monetary value of the claim
        confidence: Agent's confidence level (0-1)

    Returns:
        True if approval is required, False otherwise
    """
    # Get configuration from environment
    approval_cap = float(os.getenv("APPROVAL_CAP", "1000"))
    confidence_threshold = float(os.getenv("CONFIDENCE_THRESHOLD", "0.7"))

    requires_approval = (claim_value > approval_cap) or (confidence < confidence_threshold)

    if requires_approval:
        reason = []
        if claim_value > approval_cap:
            reason.append(f"Claim value ${claim_value} exceeds cap ${approval_cap}")
        if confidence < confidence_threshold:
            reason.append(f"Confidence {confidence} below threshold {confidence_threshold}")

        db.create_approval(
            claim_id=claim_id,
            claim_value=claim_value,
            confidence=confidence,
            reason="; ".join(reason)
        )
        print(f"[APPROVAL] Claim {claim_id} requires human approval: {'; '.join(reason)}")

    return requires_approval


def run_agent(goal: str, max_steps: int = 10, claim_id: str = None) -> str:
    """
    Run the Clawback agent loop.

    Args:
        goal: The user's goal/request
        max_steps: Maximum number of tool calls before stopping (safety limit)
        claim_id: Optional claim ID for tracking

    Returns:
        The agent's final response
    """
    # Generate claim ID if not provided
    if not claim_id:
        claim_id = f"CLAIM-{int(__import__('time').time())}"

    # Initialize database
    db.init_db()

    # Create claim record
    db.create_claim(claim_id, vendor="VendorA")

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": goal}
    ]

    print(f"[AGENT] Starting with goal: {goal}")
    print(f"[AGENT] Claim ID: {claim_id}\n")

    for step in range(max_steps):
        try:
            resp = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                tools=TOOLS,
                tool_choice="auto"
            )
        except Exception as e:
            return f"Error calling ASI:One API: {e}"

        msg = resp.choices[0].message
        messages.append(msg)

        # If no tool calls, we're done
        if not msg.tool_calls:
            print(f"[AGENT] Final response: {msg.content}\n")

            # Check approval gate for final decision
            # Extract claim value from response (simple heuristic)
            if "credit" in msg.content.lower() or "approved" in msg.content.lower():
                # Default to tier1 value (10% of typical bill)
                claim_value = 100.0  # Placeholder - would be calculated from actual bill
                confidence = 0.8  # Default confidence

                if check_approval_gate(claim_id, claim_value, confidence):
                    return f"Claim {claim_id} requires human approval before proceeding. Please check the approval inbox."

            db.update_claim(claim_id, status="completed")
            return msg.content

        # Execute tool calls
        for call in msg.tool_calls:
            try:
                # Parse arguments
                args = json.loads(call.function.arguments)
                if call.function.name == "file_claim" and not args.get("claim_id"):
                    args["claim_id"] = claim_id

                # Execute the tool
                result = TOOL_REGISTRY[call.function.name](**args)

                # Log the event
                log_event(call, result, claim_id=claim_id, step_number=step)

                # Special handling for file_claim - log agent communication
                if call.function.name == "file_claim":
                    vendor = args.get("vendor", "Unknown")
                    mode = result.get("mode", "simulation")
                    log_agent_message(
                        claim_id=claim_id,
                        message_type="SENT",
                        sender="clawback_agent",
                        receiver=f"vendor_agent ({vendor})",
                        payload={"message": args.get("claim_message")},
                        result=result,
                        step_number=step
                    )

                    # If this is a real vendor response (not just "submitted"),
                    # add it to the conversation as a user message so ASI:One can reason about it
                    if result.get("status") in ["approved", "rejected", "error"]:
                        vendor_response_msg = f"""
Vendor Response ({mode} mode):
Status: {result['status']}
Reason: {result['reason']}
Requires Rebuttal: {result.get('requires_rebuttal', False)}

Please analyze this response and determine the next action.
If rejected and requires rebuttal, use the available tools to gather evidence and file a rebuttal.
If approved, report the final outcome.
"""
                        messages.append({
                            "role": "user",
                            "content": vendor_response_msg
                        })
                        print(f"[VENDOR_RESPONSE] Added to conversation for ASI:One reasoning")

                # Add result to conversation
                messages.append({
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": json.dumps(result, default=str)
                })

            except Exception as e:
                error_msg = f"Error executing tool {call.function.name}: {e}"
                print(f"[ERROR] {error_msg}")
                messages.append({
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": json.dumps({"error": error_msg})
                })

    return "Agent stopped after reaching maximum steps limit."


if __name__ == "__main__":
    # Test with the demo scenario
    demo_goal = """
    We experienced an outage with VendorA on 2026-10-05.
    The incident ID is INC-2026-001.
    Total downtime was 78 minutes, with 35 minutes overlapping a maintenance window.
    The maintenance notice was posted on 2026-10-04 at 18:30 UTC.
    The maintenance window was from 2026-10-05 14:45 to 15:20 UTC.
    October has 31 days (44640 minutes).

    Please help us recover any SLA credits we're entitled to.
    """

    result = run_agent(demo_goal, claim_id="DEMO-001")
    print("\n" + "="*50)
    print("FINAL RESULT:")
    print("="*50)
    print(result)
