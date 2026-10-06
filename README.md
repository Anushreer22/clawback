# Clawback - SLA Credit Recovery Agent

An automated agent system for recovering SLA credits from vendors when service level agreements are violated.

## Quick Start Demo

The fastest way to see it in action:

```bash
# Run the deterministic replay (no API key required)
python replay.py --run demo_replay.json --delay 0.5
```

Or run the interactive demo:

```bash
python run_demo.py
```

## Architecture

- **Clawback Agent**: Main agent powered by ASI:One that analyzes incidents, checks SLA terms, and files claims
- **Vendor Agent**: Scripted opponent (built with uagents) that responds to claims with realistic rejection/approval logic
- **Deterministic Tools**: Pure Python functions for calculations (no AI does math)
- **Dashboard**: FastAPI + React frontend for live monitoring and approval workflows

## Setup

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables (optional - only needed for AI agent):
```bash
cp .env.example .env
# Edit .env and add your ASI:One API key
```

3. Initialize the database:
```bash
python db.py
```

## Running the Components

### 1. Quick Demo (Replay Mode)
```bash
python replay.py --run demo_replay.json --delay 0.5
```

### 2. Interactive Demo
```bash
python run_demo.py
```

### 3. Test Deterministic Tools
```bash
python test_tools.py
```

### 4. Run Test Scenarios
```bash
python test_scenarios/run_scenarios.py
```

### 5. Run Vendor Agent
```bash
python agents/vendor_agent.py
```

### 6. Run Clawback Agent (with ASI:One - requires API key)
```bash
python agents/clawback_agent.py
```

### 7. Run Full Stack (Dashboard)
```bash
# Terminal 1: API
uvicorn api:app --reload

# Terminal 2: Dashboard
cd dashboard
npm install
npm run dev

# Terminal 3: Run demo
python replay.py --run demo_replay.json --delay 0.5
```

Then open http://localhost:3000 in your browser.

## Demo Scenario

The demo scenario involves:
- **Vendor**: VendorA
- **SLA**: 99.9% monthly uptime, 10% credit if below
- **Incident**: 78 minutes downtime on 2026-10-05
- **Maintenance**: 35 minutes overlapped a maintenance window
- **Notice**: Posted only 20 hours before (required: 72 hours)

The agent should:
1. Calculate actual uptime (99.8253% - below SLA)
2. Check notice period (invalid - only 20.25 hours vs required 72)
3. File claim citing invalid maintenance exclusion
4. Handle vendor rejection with evidence-based rebuttal
5. Get approval and recover credit

## Project Structure

```
clawback/
├── agents/
│   ├── clawback_agent.py    # Main ASI:One-powered agent
│   ├── vendor_agent.py      # Scripted vendor opponent
│   └── test_vendor*.py      # Vendor agent tests
├── tools/
│   ├── calculator.py        # Uptime calculations
│   ├── clauses.py           # SLA clause retrieval
│   ├── status.py            # Notice period validation
│   └── comms.py             # Agent communication
├── data/
│   ├── sla_vendorA.json     # Vendor SLA data
│   └── incidents.json       # Incident records
├── test_scenarios/
│   ├── scenario_*.json      # Test scenario files
│   ├── run_scenarios.py     # Scenario runner
│   └── results.json         # Test results
├── dashboard/
│   └── src/                 # React frontend
├── api.py                   # FastAPI backend
├── db.py                    # SQLite database
├── replay.py                # Replay mode for demos
├── run_demo.py              # Interactive demo runner
├── test_tools.py            # Tool unit tests
├── test_clawback.py         # Manual tool testing
├── README.md                # This file
├── DEMO_GUIDE.md            # Demo instructions
└── PROJECT_SUMMARY.md       # Detailed project summary
```

## Key Features

- **Deterministic Calculations**: All math done by Python functions, never by AI
- **Audit Trail**: Every tool call and decision logged to SQLite
- **Approval Gate**: High-value or low-confidence claims require human approval
- **Live Trace**: Real-time dashboard shows agent reasoning
- **Replay Mode**: Deterministic demo runs for backup
- **Multi-Vendor Support**: Easy to add more vendors with different SLAs

## Performance Metrics

- **Tool Test Accuracy**: 100% (all unit tests pass)
- **Scenario Accuracy**: 100% (6/6 scenarios correct)
- **False Claims**: 0 (target achieved)
- **Automation**: 100% (no human intervention for standard claims)

## Phase Status

- [x] Phase 1: Data files (SLA and incidents)
- [x] Phase 2: Deterministic tools with unit tests
- [x] Phase 3: Vendor agent with uagents
- [x] Phase 4: Clawback agent loop with ASI:One
- [ ] Phase 5: Agent-to-agent communication (Chat Protocol) - placeholder implemented
- [x] Phase 6: SQLite logging
- [x] Phase 7: Approval gate logic
- [x] Phase 8: FastAPI + React dashboard
- [ ] Phase 9: PDF parsing and real Statuspage (optional - not implemented)
- [x] Phase 10: Test scenarios and measurement
- [x] Phase 11: Replay mode and demo prep

## Documentation

- **DEMO_GUIDE.md**: Detailed instructions for running demos and the 4-minute demo script
- **PROJECT_SUMMARY.md**: Complete project summary with all phases and next steps

## Next Steps (Optional)

If the demo is successful:
1. Complete Phase 5: Full uagents Chat Protocol integration
2. Phase 9: Add PDF parsing and real Statuspage integration
3. Expand to 30+ test scenarios
4. Add more vendors with different rejection styles
5. Deploy to production environment
