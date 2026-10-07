"""
Real agent-to-agent communication module for Clawback.
Handles uAgents Chat Protocol communication between Clawback and Vendor agents.
"""
import os
import asyncio
from typing import Dict, Any, Optional

try:
    from uagents import Agent, Context
except ImportError:
    Agent = None
    Context = None

# Check demo mode
DEMO_MODE = os.getenv("DEMO_MODE", "simulation").lower()

# Import message models only when needed (lazy import to avoid initialization issues)
ClaimMessage = None
ClaimResponse = None
vendor_agent = None


class VendorCommunicator:
    """
    Handles communication with the vendor agent.
    Supports both simulation and live modes.
    """

    def __init__(self):
        self.claim_history = {}  # Track claim attempts for simulation
        self.vendor_address = os.getenv("VENDOR_AGENT_ADDRESS")
        self.clawback_agent = None

    def _resolve_vendor(self, vendor_address: str):
        """Resolve vendor address to (target_address, resolver)."""
        from uagents.resolver import RulesBasedResolver
        if "@" in vendor_address:
            target_addr, endpoint = vendor_address.split("@", 1)
            if not endpoint.startswith("http://") and not endpoint.startswith("https://"):
                endpoint = f"http://{endpoint}"
            if not endpoint.endswith("/submit"):
                endpoint = f"{endpoint.rstrip('/')}/submit"
            endpoints = [endpoint]
            if "https://127.0.0.1" in endpoint:
                endpoints.append(endpoint.replace("https://127.0.0.1", "http://127.0.0.1"))
            elif "https://localhost" in endpoint:
                endpoints.append(endpoint.replace("https://localhost", "http://localhost"))
            return target_addr, RulesBasedResolver(rules={target_addr: endpoints})
        elif vendor_address.startswith("http://") or vendor_address.startswith("https://"):
            endpoint = vendor_address if vendor_address.endswith("/submit") else f"{vendor_address.rstrip('/')}/submit"
            from agents.vendor_agent import get_vendor_agent
            target_addr = get_vendor_agent().address
            return target_addr, RulesBasedResolver(rules={target_addr: [endpoint]})
        else:
            target_addr = vendor_address
            vendor_endpoint = os.getenv("VENDOR_ENDPOINT", "http://127.0.0.1:8001/submit")
            if not vendor_endpoint.endswith("/submit"):
                vendor_endpoint = f"{vendor_endpoint.rstrip('/')}/submit"
            return target_addr, RulesBasedResolver(rules={target_addr: [vendor_endpoint]})

    def initialize_agent(self):
        """Initialize the clawback agent for uAgents communication."""
        demo_mode = os.getenv("DEMO_MODE", "simulation").lower()
        self.vendor_address = os.getenv("VENDOR_AGENT_ADDRESS")

        if demo_mode == "live":
            if not self.vendor_address:
                print("[WARNING] VENDOR_AGENT_ADDRESS not set in live mode, falling back to simulation")
                return

            try:
                from uagents import Agent, Context
                from uagents.setup import fund_agent_if_low
                from agents.vendor_agent import ClaimMessage as CM, ClaimResponse as CR, get_vendor_agent

                global ClaimMessage, ClaimResponse, vendor_agent
                ClaimMessage = CM
                ClaimResponse = CR
                vendor_agent = get_vendor_agent()

                self.clawback_agent = Agent(
                    name="clawback_agent",
                    seed="clawback_agent_seed",
                    port=8002,
                )
                fund_agent_if_low(self.clawback_agent.wallet.address())

                # Set up response handler
                self._setup_response_handler()
            except Exception as e:
                print(f"[ERROR] Failed to initialize uAgents: {e}")
                self.clawback_agent = None
                raise RuntimeError(f"Failed to initialize uAgents in live mode: {e}")

    def _setup_response_handler(self):
        """Set up handler for vendor responses."""
        from uagents import Context
        from agents.vendor_agent import ClaimResponse
        pending_responses = {}

        @self.clawback_agent.on_message(model=ClaimResponse)
        async def handle_vendor_response(ctx: Context, sender: str, response: ClaimResponse):
            claim_id = response.claim_id
            if claim_id in pending_responses:
                pending_responses[claim_id].set_result(response)

        self.pending_responses = pending_responses

    async def send_claim_async(
        self,
        vendor: str,
        claim_message: str,
        claim_id: str,
        incident_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send a claim to the vendor agent asynchronously.

        Args:
            vendor: Vendor name
            claim_message: The claim message
            claim_id: Claim ID
            incident_id: Optional incident ID

        Returns:
            Vendor response
        """
        demo_mode = os.getenv("DEMO_MODE", "simulation").lower()
        vendor_address = self.vendor_address or os.getenv("VENDOR_AGENT_ADDRESS")

        if demo_mode != "live":
            return self._simulate_claim(vendor, claim_message, claim_id)

        if not vendor_address:
            print("[WARNING] VENDOR_AGENT_ADDRESS not set, falling back to simulation")
            return self._simulate_claim(vendor, claim_message, claim_id)

        from uagents.query import send_sync_message
        from agents.vendor_agent import ClaimMessage as CM, ClaimResponse as CR

        # Create message
        msg = CM(
            claim_id=claim_id,
            vendor=vendor,
            message=claim_message,
            incident_id=incident_id
        )

        # Send message and await response
        try:
            target_addr, resolver = self._resolve_vendor(vendor_address)
            response = await send_sync_message(
                destination=target_addr,
                message=msg,
                response_type=CR,
                resolver=resolver,
                timeout=30
            )

            if isinstance(response, CR):
                return {
                    "vendor": vendor,
                    "claim_id": claim_id,
                    "status": response.status,
                    "reason": response.reason,
                    "requires_rebuttal": response.requires_rebuttal,
                    "mode": "live"
                }
            else:
                return {
                    "vendor": vendor,
                    "claim_id": claim_id,
                    "status": "error",
                    "reason": f"Unexpected response from vendor agent: {response}",
                    "requires_rebuttal": False,
                    "mode": "live"
                }
        except asyncio.TimeoutError:
            return {
                "vendor": vendor,
                "claim_id": claim_id,
                "status": "error",
                "reason": "Timeout waiting for vendor response",
                "requires_rebuttal": False,
                "mode": "live"
            }
        except Exception as e:
            return {
                "vendor": vendor,
                "claim_id": claim_id,
                "status": "error",
                "reason": f"Communication error: {str(e)}",
                "requires_rebuttal": False,
                "mode": "live"
            }

    def send_claim(
        self,
        vendor: str,
        claim_message: str,
        claim_id: str,
        incident_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send a claim to the vendor agent (synchronous wrapper).

        Args:
            vendor: Vendor name
            claim_message: The claim message
            claim_id: Claim ID
            incident_id: Optional incident ID

        Returns:
            Vendor response
        """
        demo_mode = os.getenv("DEMO_MODE", "simulation").lower()
        vendor_address = self.vendor_address or os.getenv("VENDOR_AGENT_ADDRESS")

        if demo_mode != "live" or not vendor_address:
            return self._simulate_claim(vendor, claim_message, claim_id)

        # Run async method in event loop
        try:
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    return executor.submit(
                        asyncio.run,
                        self.send_claim_async(vendor, claim_message, claim_id, incident_id)
                    ).result()
            else:
                return loop.run_until_complete(
                    self.send_claim_async(vendor, claim_message, claim_id, incident_id)
                )
        except Exception as e:
            if demo_mode == "live":
                print(f"[ERROR] Live communication failed: {e}")
                return {
                    "vendor": vendor,
                    "claim_id": claim_id,
                    "status": "error",
                    "reason": f"Communication error: {str(e)}",
                    "requires_rebuttal": False,
                    "mode": "live"
                }
            return self._simulate_claim(vendor, claim_message, claim_id)

    def _simulate_claim(
        self,
        vendor: str,
        claim_message: str,
        claim_id: str
    ) -> Dict[str, Any]:
        """
        Simulate vendor response (deterministic).

        Args:
            vendor: Vendor name
            claim_message: The claim message
            claim_id: Claim ID

        Returns:
            Simulated vendor response
        """
        # Track claim attempts
        if claim_id not in self.claim_history:
            self.claim_history[claim_id] = {
                "attempts": 0,
                "status": "new"
            }

        self.claim_history[claim_id]["attempts"] += 1
        attempts = self.claim_history[claim_id]["attempts"]

        # Check if this is a rebuttal
        message_lower = claim_message.lower()
        is_rebuttal = (
            "rebuttal" in message_lower or
            "notice period" in message_lower or
            "72 hour" in message_lower or
            "72-hour" in message_lower or
            "20 hour" in message_lower or
            "insufficient notice" in message_lower
        )

        if is_rebuttal and attempts == 2:
            # Valid rebuttal - approve
            self.claim_history[claim_id]["status"] = "approved"
            return {
                "vendor": vendor,
                "claim_id": claim_id,
                "status": "approved",
                "reason": "Your rebuttal is correct. The maintenance notice was posted only 20 hours in advance, which is less than the required 72 hours. The exclusion is invalid, and we will process the credit.",
                "requires_rebuttal": False,
                "mode": "simulation"
            }
        elif is_rebuttal:
            # Rebuttal but not valid (e.g., wrong argument)
            return {
                "vendor": vendor,
                "claim_id": claim_id,
                "status": "rejected",
                "reason": "Your rebuttal does not address the maintenance exclusion correctly. The 35 minutes of scheduled maintenance are excluded from uptime calculations.",
                "requires_rebuttal": True,
                "mode": "simulation"
            }
        else:
            # First claim - reject
            self.claim_history[claim_id]["status"] = "rejected"
            return {
                "vendor": vendor,
                "claim_id": claim_id,
                "status": "rejected",
                "reason": "35 minutes were scheduled maintenance. These minutes are excluded from uptime calculations per our SLA.",
                "requires_rebuttal": True,
                "mode": "simulation"
            }


# Global communicator instance
_communicator = None


def get_communicator() -> VendorCommunicator:
    """Get or create the global communicator instance."""
    global _communicator
    if _communicator is None:
        _communicator = VendorCommunicator()
        _communicator.initialize_agent()
    return _communicator
