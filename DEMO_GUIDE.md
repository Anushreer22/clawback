# Demo Guide - Clawback SLA Credit Recovery Agent

## Quick Start Demo

### Option 1: Run Deterministic Replay (Recommended for Demo)

This is the safest option for demos - it runs the same scenario every time, perfect for rehearsal and backup.

```bash
# Save the demo scenario
python replay.py --save

# Run the replay with 0.5 second delay between steps
python replay.py --run demo_replay.json --delay 0.5
```

### Option 2: Run Interactive Demo

This runs the demo with simulated vendor responses.

```bash
python run_demo.py
```

### Option 3: Run with ASI:One (Requires API Key)

This uses the actual AI agent with tool calling.

```bash
# Set up your API key first
cp .env.example .env
# Edit .env and add your ASI_KEY

# Run the agent
python agents/clawback_agent.py
```

## Demo Script (4 minutes)

### Introduction (30 seconds)
- "We've built an automated agent that recovers SLA credits from vendors"
- "It uses deterministic tools for calculations - the AI never does math"
- "Let me show you how it handles a real scenario"

### The Scenario (30 seconds)
- "VendorA guarantees 99.9% uptime with 10% credit if they miss it"
- "We had a 78-minute outage on October 5th"
- "Vendor claimed 35 minutes were scheduled maintenance"
- "But they only posted the notice 20 hours before - the SLA requires 72 hours"

### Running the Demo (2 minutes)
- Run the replay: `python replay.py --run demo_replay.json --delay 0.5`
- Point out each step:
  1. Agent retrieves SLA clauses
  2. Calculates uptime (initially with maintenance excluded)
  3. Checks notice period - finds it's invalid
  4. Recalculates uptime without exclusion
  5. Files claim with evidence
  6. Vendor rejects (simulated)
  7. Agent files rebuttal with notice period evidence
  8. Vendor approves

### Dashboard Tour (30 seconds)
- Start the API: `uvicorn api:app --reload`
- Start the dashboard: `cd dashboard && npm run dev`
- Show the three panels:
  - Live agent trace (shows reasoning)
  - Claim ledger (shows status)
  - Approval inbox (for high-value claims)

### Results (30 seconds)
- "The agent successfully recovered a 10% credit"
- "It identified the invalid maintenance exclusion automatically"
- "The entire process took about 10 steps with no human intervention"
- "For high-value claims, it would pause for approval"

## Running the Full Stack

### Terminal 1: API Server
```bash
uvicorn api:app --reload
```

### Terminal 2: React Dashboard
```bash
cd dashboard
npm run dev
```

### Terminal 3: Run Demo
```bash
python replay.py --run demo_replay.json --delay 0.5
```

Then open http://localhost:3000 in your browser to see the live dashboard.

## Failure Mode

If the network fails or ASI:One is down during the demo:

1. **Switch to replay mode immediately**
   ```bash
   python replay.py --run demo_replay.json --delay 0.5
   ```

2. **The replay is deterministic** - it will run the same way every time

3. **No network required** - all data is local

## Testing the Tools

Run the unit tests to verify everything works:

```bash
python test_tools.py
```

Run the scenario tests:

```bash
python test_scenarios/run_scenarios.py
```

## Key Talking Points

1. **Deterministic Tools**: All math done by Python functions, never by AI
2. **Audit Trail**: Every decision logged to SQLite for compliance
3. **Approval Gate**: High-value claims require human approval
4. **Multi-Vendor**: Easy to add more vendors with different SLAs
5. **Evidence-Based**: Claims cite specific contract clauses and data points

## Performance Metrics

From our test scenarios:
- **Accuracy**: 100% (6/6 scenarios correct)
- **False Claims**: 0 (target achieved)
- **Automation**: 100% (no human intervention needed for standard claims)

## Next Steps (Optional)

If the demo goes well, we can:
- Add PDF parsing for real SLA documents
- Integrate with real Statuspage APIs
- Add more vendors with different rejection styles
- Build 30+ test scenarios for comprehensive validation
