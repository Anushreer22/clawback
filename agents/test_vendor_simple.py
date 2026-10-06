"""
Simple test for vendor agent - run vendor agent separately, then this.
"""
import asyncio
from uagents import Agent, Context, Model
from uagents.setup import fund_agent_if_low
from agents.vendor_agent import ClaimMessage, ClaimResponse


# Create a test agent
test_agent = Agent(
    name="test_agent",
    seed="test_agent_seed",
    port=8002,
)

fund_agent_if_low(test_agent.wallet.address())

# Vendor agent address (update after running vendor_agent.py)
VENDOR_ADDRESS = "agent1q...@https://127.0.0.1:8001"  # Replace with actual address


@test_agent.on_message(model=ClaimResponse)
async def handle_claim_response(ctx: Context, sender: str, msg: ClaimResponse):
    """Handle claim response."""
    ctx.logger.info(f"Claim {msg.claim_id} status: {msg.status}")
    ctx.logger.info(f"Reason: {msg.reason}")
    ctx.logger.info(f"Requires rebuttal: {msg.requires_rebuttal}")


@test_agent.on_event("startup")
async def startup(ctx: Context):
    """Send test messages on startup."""
    ctx.logger.info(f"Test agent started at {test_agent.address}")
    ctx.logger.info(f"Vendor agent address: {VENDOR_ADDRESS}")

    # Wait a bit
    await asyncio.sleep(2)

    # Send initial claim
    claim = ClaimMessage(
        claim_id="TEST-001",
        vendor="VendorA",
        message="We experienced a 78-minute outage on 2026-10-05. We request a 10% credit per our SLA.",
        incident_id="INC-2026-001"
    )
    await ctx.send(VENDOR_ADDRESS, claim)
    ctx.logger.info("Sent initial claim")

    # Wait for response
    await asyncio.sleep(3)

    # Send rebuttal
    rebuttal = ClaimMessage(
        claim_id="TEST-001",
        vendor="VendorA",
        message="The maintenance exclusion is invalid. The notice was posted only 20 hours before the maintenance window, which is less than the required 72 hours per the SLA clause.",
        incident_id="INC-2026-001"
    )
    await ctx.send(VENDOR_ADDRESS, rebuttal)
    ctx.logger.info("Sent rebuttal")


if __name__ == "__main__":
    test_agent.run()
