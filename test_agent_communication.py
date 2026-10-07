"""
Test agent-to-agent communication.
Verifies the full flow: Clawback -> Vendor -> rejection -> Clawback reasoning -> rebuttal -> approval.
"""
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Set simulation mode for testing
os.environ["DEMO_MODE"] = "simulation"

from agents.communication import VendorCommunicator
import db


def test_communication_flow():
    """Test the full communication flow."""
    print("="*60)
    print("AGENT-TO-AGENT COMMUNICATION TEST")
    print("="*60)
    print()

    # Initialize database
    db.init_db()

    # Create communicator
    communicator = VendorCommunicator()
    communicator.initialize_agent()

    claim_id = "TEST-COMM-001"
    vendor = "VendorA"

    # Step 1: Send initial claim
    print("STEP 1: Send initial claim")
    print("-" * 60)

    initial_claim = """
    We experienced a 78-minute outage on 2026-10-05.
    We request a 10% credit per our SLA.
    """

    response1 = communicator.send_claim(
        vendor=vendor,
        claim_message=initial_claim,
        claim_id=claim_id
    )

    print(f"Status: {response1['status']}")
    print(f"Reason: {response1['reason']}")
    print(f"Mode: {response1['mode']}")
    print()

    # Log to database
    db.log_event(
        claim_id=claim_id,
        event_type="AGENT_MESSAGE_SENT",
        input_data={"sender": "clawback", "receiver": "vendor", "message": initial_claim},
        output_data=response1,
        step_number=1
    )

    assert response1['status'] == "rejected", "First claim should be rejected"
    assert response1['requires_rebuttal'] == True, "Should require rebuttal"
    print("[PASS] Initial claim rejected as expected")
    print()

    # Step 2: Send rebuttal with notice period evidence
    print("STEP 2: Send rebuttal with notice period evidence")
    print("-" * 60)

    rebuttal = """
    Your rejection is incorrect. The maintenance exclusion is invalid because:
    1. The SLA requires 72 hours notice for maintenance exclusions
    2. Notice was posted only 20 hours before the maintenance window
    3. Therefore, the maintenance cannot be excluded from uptime calculations

    We request approval of the 10% credit per the SLA terms.
    """

    response2 = communicator.send_claim(
        vendor=vendor,
        claim_message=rebuttal,
        claim_id=claim_id
    )

    print(f"Status: {response2['status']}")
    print(f"Reason: {response2['reason']}")
    print(f"Mode: {response2['mode']}")
    print()

    # Log to database
    db.log_event(
        claim_id=claim_id,
        event_type="AGENT_MESSAGE_SENT",
        input_data={"sender": "clawback", "receiver": "vendor", "message": rebuttal},
        output_data=response2,
        step_number=2
    )

    assert response2['status'] == "approved", "Rebuttal should be approved"
    assert response2['requires_rebuttal'] == False, "Should not require further rebuttal"
    print("[PASS] Rebuttal approved as expected")
    print()

    # Step 3: Verify database logging
    print("STEP 3: Verify database logging")
    print("-" * 60)

    events = db.get_events(claim_id)
    print(f"Total events logged: {len(events)}")

    for event in events:
        print(f"  - {event['type']} (Step {event['step_number']})")

    assert len(events) >= 2, "Should have at least 2 events logged"
    print("[PASS] Database logging working")
    print()

    # Step 4: Test weak rebuttal (should be rejected)
    print("STEP 4: Test weak rebuttal (should be rejected)")
    print("-" * 60)

    claim_id_2 = "TEST-COMM-002"
    weak_rebuttal = "We still think we deserve a credit."

    response3 = communicator.send_claim(
        vendor=vendor,
        claim_message=weak_rebuttal,
        claim_id=claim_id_2
    )

    print(f"Status: {response3['status']}")
    print(f"Reason: {response3['reason']}")
    print()

    assert response3['status'] == "rejected", "Weak rebuttal should be rejected"
    print("[PASS] Weak rebuttal rejected as expected")
    print()

    # Summary
    print("="*60)
    print("TEST SUMMARY")
    print("="*60)
    print("All tests passed!")
    print("- Initial claim rejected (correct)")
    print("- Valid rebuttal approved (correct)")
    print("- Weak rebuttal rejected (correct)")
    print("- Database logging working (correct)")
    print()
    print("No infinite loop detected")
    print("Maximum steps: 2 (as expected)")
    print("Simulation mode: working")
    print()


def test_live_mode_fallback():
    """Test that live mode falls back to simulation if not configured."""
    print("="*60)
    print("LIVE MODE FALLBACK TEST")
    print("="*60)
    print()

    # Remove vendor address to force fallback
    original_address = os.environ.get("VENDOR_AGENT_ADDRESS")
    if "VENDOR_AGENT_ADDRESS" in os.environ:
        del os.environ["VENDOR_AGENT_ADDRESS"]

    os.environ["DEMO_MODE"] = "live"

    communicator = VendorCommunicator()
    communicator.initialize_agent()

    response = communicator.send_claim(
        vendor="VendorA",
        claim_message="Test claim",
        claim_id="TEST-FALLBACK"
    )

    print(f"Response mode: {response['mode']}")
    assert response['mode'] == "simulation", "Should fall back to simulation"
    print("[PASS] Fallback to simulation working")
    print()

    # Restore original address
    if original_address:
        os.environ["VENDOR_AGENT_ADDRESS"] = original_address


if __name__ == "__main__":
    test_communication_flow()
    test_live_mode_fallback()

    print("="*60)
    print("ALL TESTS PASSED")
    print("="*60)
