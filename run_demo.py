"""
Demo runner script - simulates the full flow without ASI:One API.
This demonstrates the tool integration and decision logic.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from tools import calculate_uptime, get_clause, get_status_history, check_notice_period
import db


def simulate_demo():
    """Simulate the demo scenario step by step."""
    print("="*60)
    print("CLAWBACK DEMO - SLA Credit Recovery")
    print("="*60)
    print()

    # Initialize database
    db.init_db()
    print("[INIT] Database initialized")

    # Create claim
    claim_id = "DEMO-001"
    db.create_claim(claim_id, "VendorA", "INC-2026-001")
    print(f"[CLAIM] Created claim {claim_id}")
    print()

    # Step 1: Retrieve SLA clauses
    print("-" * 60)
    print("STEP 1: Retrieve SLA Clauses")
    print("-" * 60)

    uptime_clause = get_clause("VendorA", "uptime")
    print(f"Uptime Clause: {uptime_clause['clause_text']}")
    db.log_event(claim_id, "tool_call",
                 {"tool": "get_clause", "topic": "uptime"},
                 uptime_clause, step_number=1)

    maintenance_clause = get_clause("VendorA", "maintenance_exclusion")
    print(f"Maintenance Clause: {maintenance_clause['clause_text']}")
    db.log_event(claim_id, "tool_call",
                 {"tool": "get_clause", "topic": "maintenance_exclusion"},
                 maintenance_clause, step_number=2)
    print()

    # Step 2: Calculate uptime (assuming maintenance is valid)
    print("-" * 60)
    print("STEP 2: Calculate Uptime (assuming valid maintenance)")
    print("-" * 60)

    uptime_with_exclusion = calculate_uptime(78, 35, 44640)
    print(f"Uptime with 35min excluded: {uptime_with_exclusion['uptime_percentage']}%")
    print(f"Credit eligible: {uptime_with_exclusion['credit_eligible']}")
    db.log_event(claim_id, "tool_call",
                 {"tool": "calculate_uptime", "incident_minutes": 78, "excluded_minutes": 35},
                 uptime_with_exclusion, step_number=3)
    print()

    # Step 3: Verify maintenance notice period
    print("-" * 60)
    print("STEP 3: Verify Maintenance Notice Period")
    print("-" * 60)

    notice_check = check_notice_period(
        "2026-10-04T18:30:00Z",
        "2026-10-05T14:45:00Z",
        72
    )
    print(f"Notice posted: 2026-10-04T18:30:00Z")
    print(f"Maintenance starts: 2026-10-05T14:45:00Z")
    print(f"Actual notice: {notice_check['actual_hours']} hours")
    print(f"Required notice: {notice_check['required_hours']} hours")
    print(f"Notice valid: {notice_check['valid']}")
    db.log_event(claim_id, "tool_call",
                 {"tool": "check_notice_period", "notice_time": "2026-10-04T18:30:00Z"},
                 notice_check, step_number=4)
    print()

    # Step 4: Decision - maintenance exclusion is invalid
    print("-" * 60)
    print("STEP 4: Decision - Maintenance Exclusion INVALID")
    print("-" * 60)

    print("REASONING:")
    print("- Notice was posted only 20.25 hours before maintenance")
    print("- SLA requires 72 hours notice")
    print("- Therefore, maintenance exclusion is INVALID")
    print()

    db.log_event(claim_id, "decision",
                 {"reasoning": "Maintenance exclusion invalid due to insufficient notice"},
                 {"decision": "exclude 0 minutes from downtime"},
                 step_number=5)

    # Step 5: Recalculate uptime with invalid maintenance
    print("-" * 60)
    print("STEP 5: Recalculate Uptime (maintenance exclusion INVALID)")
    print("-" * 60)

    uptime_without_exclusion = calculate_uptime(78, 0, 44640)
    print(f"Uptime with 0min excluded: {uptime_without_exclusion['uptime_percentage']}%")
    print(f"SLA threshold: 99.9%")
    print(f"Credit eligible: {uptime_without_exclusion['credit_eligible']}")
    print(f"Credit tier: {uptime_without_exclusion['credit_tier']}")
    db.log_event(claim_id, "tool_call",
                 {"tool": "calculate_uptime", "incident_minutes": 78, "excluded_minutes": 0},
                 uptime_without_exclusion, step_number=6)
    print()

    # Step 6: File claim
    print("-" * 60)
    print("STEP 6: File Claim")
    print("-" * 60)

    claim_message = """
    We request a 10% credit for the outage on 2026-10-05.

    The maintenance exclusion claimed by VendorA is invalid.
    Per the SLA clause: "Scheduled maintenance windows are excluded from
    uptime calculations only if notice is provided at least 72 hours in advance."

    The maintenance notice was posted only 20.25 hours before the maintenance
    window (2026-10-04T18:30:00Z vs 2026-10-05T14:45:00Z), which is less than
    the required 72 hours.

    Actual uptime: 99.8253% (below 99.9% SLA threshold)
    Total downtime: 78 minutes
    Credit tier: tier1
    """

    print("Claim message:")
    print(claim_message)
    db.log_event(claim_id, "file_claim",
                 {"vendor": "VendorA", "message": claim_message},
                 {"status": "submitted"},
                 step_number=7)

    db.update_claim(claim_id, status="submitted", amount=100.0)
    print()

    # Step 7: Simulate vendor rejection
    print("-" * 60)
    print("STEP 7: Vendor Rejection (simulated)")
    print("-" * 60)

    vendor_response = {
        "status": "rejected",
        "reason": "35 minutes were scheduled maintenance. These minutes are excluded from uptime calculations per our SLA.",
        "requires_rebuttal": True
    }

    print(f"Vendor response: {vendor_response['status']}")
    print(f"Reason: {vendor_response['reason']}")
    db.log_event(claim_id, "vendor_response",
                 {"vendor": "VendorA"},
                 vendor_response,
                 step_number=8)
    print()

    # Step 8: File rebuttal
    print("-" * 60)
    print("STEP 8: File Rebuttal")
    print("-" * 60)

    rebuttal_message = """
    Your rejection is incorrect. The maintenance exclusion is invalid because:

    1. The SLA requires 72 hours notice for maintenance exclusions
    2. Notice was posted only 20.25 hours before the maintenance window
    3. Therefore, the maintenance cannot be excluded from uptime calculations

    We request approval of the 10% credit per the SLA terms.
    """

    print("Rebuttal message:")
    print(rebuttal_message)
    db.log_event(claim_id, "file_rebuttal",
                 {"vendor": "VendorA", "message": rebuttal_message},
                 {"status": "submitted"},
                 step_number=9)
    print()

    # Step 9: Vendor approval
    print("-" * 60)
    print("STEP 9: Vendor Approval (simulated)")
    print("-" * 60)

    vendor_approval = {
        "status": "approved",
        "reason": "Your rebuttal is correct. The maintenance notice was posted only 20 hours in advance, which is less than the required 72 hours. The exclusion is invalid, and we will process the credit.",
        "requires_rebuttal": False
    }

    print(f"Vendor response: {vendor_approval['status']}")
    print(f"Reason: {vendor_approval['reason']}")
    db.log_event(claim_id, "vendor_response",
                 {"vendor": "VendorA"},
                 vendor_approval,
                 step_number=10)
    print()

    # Final result
    print("="*60)
    print("FINAL RESULT")
    print("="*60)
    print(f"Claim ID: {claim_id}")
    print(f"Status: APPROVED")
    print(f"Credit Amount: $100.00 (10% of monthly bill)")
    print(f"Reason: Invalid maintenance exclusion (insufficient notice)")
    print()

    db.update_claim(claim_id, status="approved")

    # Show event log
    print("="*60)
    print("EVENT LOG")
    print("="*60)
    events = db.get_events(claim_id)
    for event in events:
        print(f"[{event['timestamp']}] {event['type']}")
        if event['step_number'] is not None:
            print(f"  Step: {event['step_number']}")
    print()

    print("Demo complete! Check the dashboard at http://localhost:3000")
    print("Start the API with: uvicorn api:app --reload")


if __name__ == "__main__":
    simulate_demo()
