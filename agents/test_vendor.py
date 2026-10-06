"""
Test script for vendor agent messaging.
First tests simple hello protocol, then tests claim handling.
"""
import asyncio
from uagents import Agent, Context, Model
from uagents.setup import fund_agent_if_low
from agents.vendor_agent import vendor_agent, ClaimMessage, ClaimResponse


class HelloMessage(Model):
    """Simple hello message."""
    message: str


class HelloResponse(Model):
    """Simple hello response."""
    message: str


# Create a test agent
test_agent = Agent(
    name="test_agent",
    seed="test_agent_seed",
    port=8002,
)

fund_agent_if_low(test_agent.wallet.address())


@test_agent.on_message(model=HelloResponse)
async def handle_hello_response(ctx: Context, sender: str, msg: HelloResponse):
    """Handle hello response."""
    ctx.logger.info(f"Received hello response: {msg.message}")


@test_agent.on_message(model=ClaimResponse)
async def handle_claim_response(ctx: Context, sender: str, msg: ClaimResponse):
    """Handle claim response."""
    ctx.logger.info(f"Claim {msg.claim_id} status: {msg.status}")
    ctx.logger.info(f"Reason: {msg.reason}")


@test_agent.on_event("startup")
async def startup(ctx: Context):
    """Send test messages on startup."""
    ctx.logger.info(f"Test agent started at {test_agent.address}")

    # Wait a bit for vendor agent to be ready
    await asyncio.sleep(2)

    # Test 1: Send hello (this will fail since vendor agent doesn't handle hello)
    # We'll skip this and go straight to claim testing

    # Test 2: Send a claim
    claim = ClaimMessage(
        claim_id="TEST-001",
        vendor="VendorA",
        message="We experienced a 78-minute outage on 2026-10-05. We request a 10% credit per our SLA.",
        incident_id="INC-2026-001"
    )
    await ctx.send(vendor_agent.address, claim)
    ctx.logger.info("Sent initial claim")

    # Wait for response, then send rebuttal
    await asyncio.sleep(3)

    # Test 3: Send rebuttal with correct notice period argument
    rebuttal = ClaimMessage(
        claim_id="TEST-001",
        vendor="VendorA",
        message="The maintenance exclusion is invalid. The notice was posted only 20 hours before the maintenance window, which is less than the required 72 hours per the SLA clause.",
        incident_id="INC-2026-001"
    )
    await ctx.send(vendor_agent.address, rebuttal)
    ctx.logger.info("Sent rebuttal")


if __name__ == "__main__":
    # Run both agents
    import threading

    def run_vendor():
        vendor_agent.run()

    def run_test():
        test_agent.run()

    # Start vendor agent in background
    vendor_thread = threading.Thread(target=run_vendor, daemon=True)
    vendor_thread.start()

    # Wait for vendor to start
    asyncio.sleep(3)

    # Start test agent
    test_agent.run()
