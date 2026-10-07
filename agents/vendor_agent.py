"""
Vendor agent - scripted opponent for SLA claims.
Built with uagents framework.
"""
import asyncio
from uagents import Agent, Context, Model
from uagents.setup import fund_agent_if_low
from typing import Optional


class ClaimMessage(Model):
    """Message for filing a claim."""
    claim_id: str
    vendor: str
    message: str
    incident_id: Optional[str] = None


class ClaimResponse(Model):
    """Response to a claim."""
    claim_id: str
    status: str  # "approved", "rejected", "pending"
    reason: str
    requires_rebuttal: bool = False


# Track claim history for this session
claim_history = {}

# Global agent instance (lazy initialization)
_vendor_agent = None


def get_vendor_agent():
    """Get or create the vendor agent instance."""
    global _vendor_agent
    if _vendor_agent is None:
        _vendor_agent = Agent(
            name="vendor_agent",
            seed="vendor_agent_seed",
            port=8001,
        )
        fund_agent_if_low(_vendor_agent.wallet.address())
        _setup_vendor_agent_handlers()
    return _vendor_agent


def _setup_vendor_agent_handlers():
    """Set up message handlers for the vendor agent."""
    vendor_agent = _vendor_agent

    @vendor_agent.on_message(model=ClaimMessage)
    async def handle_claim(ctx: Context, sender: str, msg: ClaimMessage):
        """
        Handle incoming claims with scripted behavior:
        1. First claim: reject with "35 minutes were scheduled maintenance"
        2. If rebuttal cites notice period correctly: approve
        3. If rebuttal is weak: reject again
        """
        ctx.logger.info(f"Received claim {msg.claim_id} from {sender}: {msg.message}")

        # Resolve claim key to track conversation history (handle variations like -REBUTTAL)
        claim_key = msg.claim_id
        if claim_key not in claim_history:
            for existing_id in list(claim_history.keys()):
                cleaned = claim_key.lower().replace("-rebuttal", "").replace("_rebuttal", "")
                if existing_id in claim_key or cleaned == existing_id.lower():
                    claim_key = existing_id
                    break

        if claim_key not in claim_history:
            # First time - reject with maintenance excuse
            response = ClaimResponse(
                claim_id=msg.claim_id,
                status="rejected",
                reason="35 minutes were scheduled maintenance. These minutes are excluded from uptime calculations per our SLA.",
                requires_rebuttal=True
            )
            claim_history[claim_key] = {
                "status": "rejected",
                "attempts": 1,
                "original_message": msg.message
            }
        else:
            # This is a rebuttal
            history = claim_history[claim_key]
            history["attempts"] += 1

            # Check if rebuttal mentions notice period (72 hours) or the 20-hour notice
            message_lower = msg.message.lower()
            has_notice_argument = (
                "72 hour" in message_lower or
                "72-hour" in message_lower or
                "notice period" in message_lower or
                "20 hour" in message_lower or
                "insufficient notice" in message_lower
            )

            if has_notice_argument and history["attempts"] >= 2:
                # Valid rebuttal - approve
                response = ClaimResponse(
                    claim_id=msg.claim_id,
                    status="approved",
                    reason="Your rebuttal is correct. The maintenance notice was posted only 20 hours in advance, which is less than the required 72 hours. The exclusion is invalid, and we will process the credit.",
                    requires_rebuttal=False
                )
                claim_history[claim_key]["status"] = "approved"
            else:
                # Weak or incorrect rebuttal - reject again
                response = ClaimResponse(
                    claim_id=msg.claim_id,
                    status="rejected",
                    reason="Your rebuttal does not address the maintenance exclusion correctly. The 35 minutes of scheduled maintenance are excluded from uptime calculations.",
                    requires_rebuttal=True
                )
                claim_history[claim_key]["status"] = "rejected"

        # Send response
        await ctx.send(sender, response)
        ctx.logger.info(f"Sent response for claim {msg.claim_id}: {response.status}")

    @vendor_agent.on_event("startup")
    async def startup(ctx: Context):
        """Log when agent starts."""
        ctx.logger.info(f"Vendor agent started at {vendor_agent.address}")


# For backward compatibility, expose a vendor_agent property
# that lazily initializes the agent
class VendorAgentProxy:
    """Proxy for lazy agent initialization."""

    def __getattr__(self, name):
        agent = get_vendor_agent()
        return getattr(agent, name)


vendor_agent = VendorAgentProxy()


if __name__ == "__main__":
    # Initialize and run the agent
    agent = get_vendor_agent()
    agent.run()
