# Phase 5: Agent-to-Agent Communication Guide

## Overview

Phase 5 implements real uAgents Chat Protocol communication between the Clawback Agent and Vendor Agent, while maintaining simulation mode as a fallback.

## Development Modes

### Simulation Mode (Default)

Uses deterministic vendor responses without requiring network connectivity or running agents.

```bash
# Set environment variable (or omit to use default)
export DEMO_MODE=simulation

# Run the agent
python agents/clawback_agent.py
```

**Advantages:**
- No network required
- No agent setup needed
- Deterministic results
- Works for demos even if Agentverse is down

### Live Mode

Uses real uAgents Chat Protocol for agent-to-agent communication.

```bash
# Set environment variables
export DEMO_MODE=live
export VENDOR_AGENT_ADDRESS=agent1q...@https://127.0.0.1:8001

# Run the agent
python agents/clawback_agent.py
```

**Advantages:**
- Real agent-to-agent communication
- Demonstrates uAgents integration
- Actual message passing over Chat Protocol

## Running Instructions

### 1. Starting Vendor Agent Locally

Open a terminal and run:

```bash
cd C:\Users\ANUSHREE R\clawback
python agents/vendor_agent.py
```

The vendor agent will start on port 8001 and display its address (e.g., `agent1q...@https://127.0.0.1:8001`).

### 2. Starting Clawback Agent Locally (Live Mode)

Open another terminal:

```bash
cd C:\Users\ANUSHREE R\clawback

# Set environment variables
set DEMO_MODE=live
set VENDOR_AGENT_ADDRESS=agent1q...@https://127.0.0.1:8001

# Run the agent (requires ASI_KEY in .env)
python agents/clawback_agent.py
```

**Note:** Replace `agent1q...@https://127.0.0.1:8001` with the actual address displayed by the vendor agent.

### 3. Running the Live Communication Demo

With both agents running:

```bash
# Terminal 1: Vendor agent
python agents/vendor_agent.py

# Terminal 2: Clawback agent
set DEMO_MODE=live
set VENDOR_AGENT_ADDRESS=agent1q...@https://127.0.0.1:8001
python agents/clawback_agent.py
```

The Clawback agent will:
1. Send a claim to the vendor agent
2. Receive a rejection
3. Reason about the rejection using ASI:One
4. Send a rebuttal with evidence
5. Receive approval from the vendor

### 4. Registering/Deploying Vendor Agent on Agentverse

To deploy the vendor agent to Agentverse for remote access:

```bash
# Install agentverse CLI
pip install agentverse-cli

# Login to Agentverse
agentverse login

# Register the agent
agentverse register

# Your agent will get a persistent address like:
# agent1qxyz...@agentverse.ai
```

Then configure the Clawback agent:

```bash
set VENDOR_AGENT_ADDRESS=agent1qxyz...@agentverse.ai
set DEMO_MODE=live
python agents/clawback_agent.py
```

### 5. Configuring VENDOR_AGENT_ADDRESS

The `VENDOR_AGENT_ADDRESS` format depends on the deployment:

**Local Agent:**
```
agent1q...@https://127.0.0.1:8001
```

**Agentverse Agent:**
```
agent1q...@agentverse.ai
```

**Testnet Agent:**
```
agent1q...@testnet.agentverse.ai
```

### 6. Running the Simulation Fallback

If live mode fails or you want to use simulation:

```bash
# Omit DEMO_MODE or set to simulation
set DEMO_MODE=simulation

# Run the agent
python agents/clawback_agent.py
```

Or run the deterministic replay:

```bash
python replay.py --run demo_replay.json --delay 0.5
```

## Testing

### Test Agent Communication

```bash
python test_agent_communication.py
```

This test verifies:
- Initial claim rejection
- Valid rebuttal approval
- Weak rebuttal rejection
- Database logging
- Live mode fallback to simulation

### Test All Tools

```bash
python test_tools.py
```

### Test Scenarios

```bash
python test_scenarios/run_scenarios.py
```

## Architecture

### Communication Flow

```
ASI:One Agent
    ↓
file_claim tool
    ↓
VendorCommunicator (checks DEMO_MODE)
    ↓
┌─────────────────┬─────────────────┐
│  Simulation     │     Live        │
│  Mode           │     Mode        │
├─────────────────┼─────────────────┤
│ Deterministic   │ uAgents Chat    │
│ responses       │ Protocol        │
│ (no network)    │ (real agents)   │
└─────────────────┴─────────────────┘
    ↓                 ↓
Vendor Response  Vendor Response
    ↓                 ↓
Logged to SQLite  Logged to SQLite
    ↓                 ↓
Fed back to      Fed back to
ASI:One          ASI:One
    ↓                 ↓
ASI:One reasons  ASI:One reasons
about rejection  about rejection
    ↓                 ↓
Generates rebuttal  Generates rebuttal
    ↓                 ↓
Sends rebuttal   Sends rebuttal
    ↓                 ↓
Vendor approves   Vendor approves
```

### Message Models

**ClaimMessage:**
```python
{
    "claim_id": str,
    "vendor": str,
    "message": str,
    "incident_id": Optional[str]
}
```

**ClaimResponse:**
```python
{
    "claim_id": str,
    "status": str,  # "approved", "rejected", "error"
    "reason": str,
    "requires_rebuttal": bool
}
```

### Database Logging

Two new event types:

- `AGENT_MESSAGE_SENT`: Logged when Clawback sends a message to Vendor
- `AGENT_MESSAGE_RECEIVED`: Logged when Clawback receives a response

Each log includes:
- timestamp
- claim_id
- sender
- receiver
- payload
- result
- step_number

## Troubleshooting

### Vendor Agent Not Starting

**Error:** `RuntimeError: There is no current event loop`

**Solution:** The vendor agent now uses lazy initialization. It will only initialize when actually used. This is expected behavior.

### Live Mode Falls Back to Simulation

**Error:** `[WARNING] Failed to initialize uAgents: ...`

**Solution:**
1. Check that uagents is installed: `pip list | grep uagents`
2. Check that VENDOR_AGENT_ADDRESS is set correctly
3. Check that the vendor agent is running (if using local address)
4. The system will automatically fall back to simulation mode if live mode fails

### ASI:One Agent Not Receiving Vendor Response

**Error:** Vendor response not added to conversation

**Solution:** Check the console output for `[VENDOR_RESPONSE]` message. If missing, ensure:
1. `DEMO_MODE=live` is set
2. VENDOR_AGENT_ADDRESS is correct
3. Vendor agent is running and responding

### Timeout Waiting for Vendor Response

**Error:** `Timeout waiting for vendor response`

**Solution:**
1. Check vendor agent is running
2. Check network connectivity
3. Check VENDOR_AGENT_ADDRESS is correct
4. System will fall back to simulation automatically

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DEMO_MODE` | `simulation` | Mode: `simulation` or `live` |
| `VENDOR_AGENT_ADDRESS` | (empty) | Vendor agent address (required for live mode) |
| `ASI_KEY` | (required) | ASI:One API key |
| `ASI_MODEL` | `asi1-mini` | ASI:One model name |
| `APPROVAL_CAP` | `1000` | Approval threshold in dollars |
| `CONFIDENCE_THRESHOLD` | `0.7` | Minimum confidence for auto-approval |

### .env File Example

```bash
# ASI:One API Configuration
ASI_KEY=your_asi_api_key_here
ASI_MODEL=asi1-mini

# Demo Mode Configuration
DEMO_MODE=simulation

# Vendor Agent Configuration (for live mode)
VENDOR_AGENT_ADDRESS=agent1q...@https://127.0.0.1:8001

# Approval Gate Configuration
APPROVAL_CAP=1000
CONFIDENCE_THRESHOLD=0.7
```

## Verification Checklist

- [x] Simulation mode works (no network required)
- [x] Live mode falls back to simulation if not configured
- [x] Database logging for agent messages
- [x] Vendor response fed back to ASI:One
- [x] Replay mode still works
- [x] Unit tests pass
- [x] Communication tests pass
- [x] No infinite loops
- [x] Maximum 10 steps enforced
- [x] Lazy initialization prevents event loop errors

## Next Steps

For production deployment:
1. Deploy vendor agent to Agentverse
2. Configure VENDOR_AGENT_ADDRESS with Agentverse address
3. Set DEMO_MODE=live
4. Monitor agent communication logs
5. Set up health checks for both agents
