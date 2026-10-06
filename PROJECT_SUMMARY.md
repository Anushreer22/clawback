# Clawback Project Summary

## Completed Phases

### Phase 1: Data Files ✅
- Created `sla_vendorA.json` with SLA terms (99.9% uptime, 10% credit, 72-hour notice requirement)
- Created `incidents.json` with demo incident (78-minute outage, 35-minute maintenance overlap, 20-hour notice)

### Phase 2: Deterministic Tools ✅
- Built `calculate_uptime()` - calculates uptime percentage and credit tier
- Built `get_clause()` - retrieves exact contract clause text
- Built `get_status_history()` - retrieves maintenance notice timestamps
- Built `check_notice_period()` - validates notice period compliance
- All tools tested with unit tests - 100% pass rate

### Phase 3: Vendor Agent ✅
- Built vendor agent with uagents framework
- Scripted behavior: rejects first claim, approves if rebuttal cites notice period correctly
- Test scripts for agent-to-agent messaging

### Phase 4: Clawback Agent Loop ✅
- Built main agent with ASI:One integration
- Tool calling with OpenAI-compatible API
- System prompt enforces rules: read clauses first, never do math, check notice periods
- Safety limit: max 10 steps per claim

### Phase 5: Agent Communication ⏸️
- Placeholder `file_claim()` tool created
- Full uagents Chat Protocol integration pending (requires both agents running)

### Phase 6: SQLite Logging ✅
- Database schema with events, claims, and approvals tables
- Every tool call and decision logged
- Audit trail for compliance and debugging

### Phase 7: Approval Gate ✅
- Configurable approval cap (default: $1000)
- Configurable confidence threshold (default: 0.7)
- Claims above cap or below confidence require human approval
- Approval inbox in dashboard

### Phase 8: Dashboard ✅
- FastAPI backend with polling endpoints
- React frontend with three panels:
  - Live agent trace (real-time tool calls and decisions)
  - Claim ledger (vendor, amount, status)
  - Approval inbox (approve/reject buttons)
- CORS enabled for cross-origin requests

### Phase 9: PDF Parsing & Statuspage ⏸️
- Marked as optional - not implemented for demo
- Can be added if demo path works well

### Phase 10: Test Scenarios ✅
- Created 6 test scenarios covering edge cases:
  - Short outage (no credit)
  - Long outage (credit eligible)
  - Valid maintenance exclusion
  - Invalid maintenance exclusion
  - Missing maintenance notice
  - Exact SLA threshold
- Scenario runner with performance reporting
- **Results**: 100% accuracy (6/6 correct), 0 false claims

### Phase 11: Replay Mode ✅
- Deterministic replay system for demo backup
- Pre-recorded demo scenario saved to JSON
- Network failure recovery: switch to replay mode
- Adjustable delay between steps for pacing

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
│   └── comms.py             # Agent communication (placeholder)
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
├── README.md                # Project documentation
├── DEMO_GUIDE.md            # Demo instructions
└── requirements.txt         # Python dependencies
```

## How to Run

### Quick Demo (Replay Mode)
```bash
python replay.py --run demo_replay.json --delay 0.5
```

### Interactive Demo
```bash
python run_demo.py
```

### Full Stack (Dashboard)
```bash
# Terminal 1: API
uvicorn api:app --reload

# Terminal 2: Dashboard
cd dashboard
npm run dev

# Terminal 3: Run demo
python replay.py --run demo_replay.json --delay 0.5
```

### Test Tools
```bash
python test_tools.py
```

### Test Scenarios
```bash
python test_scenarios/run_scenarios.py
```

## Key Features

1. **Deterministic Calculations**: All math done by Python functions, never by AI
2. **Audit Trail**: Every tool call and decision logged to SQLite
3. **Approval Gate**: High-value or low-confidence claims require human approval
4. **Live Dashboard**: Real-time monitoring of agent reasoning
5. **Replay Mode**: Deterministic demo runs for backup
6. **Multi-Vendor**: Easy to add more vendors with different SLAs
7. **Evidence-Based**: Claims cite specific contract clauses and data points

## Performance Metrics

- **Tool Test Accuracy**: 100% (all unit tests pass)
- **Scenario Accuracy**: 100% (6/6 scenarios correct)
- **False Claims**: 0 (target achieved)
- **Automation**: 100% (no human intervention for standard claims)

## Dependencies

- Python 3.8+
- FastAPI + Uvicorn (API server)
- React + Vite (dashboard)
- uagents (agent framework)
- OpenAI SDK (ASI:One integration)
- SQLite (database)

## Configuration

Environment variables in `.env`:
- `ASI_KEY`: ASI:One API key (for AI agent)
- `ASI_MODEL`: Model name (default: asi1-mini)
- `APPROVAL_CAP`: Approval threshold in dollars (default: 1000)
- `CONFIDENCE_THRESHOLD`: Minimum confidence for auto-approval (default: 0.7)

## Next Steps (Optional)

If demo is successful:
1. Complete Phase 5: Full uagents Chat Protocol integration
2. Phase 9: Add PDF parsing and real Statuspage integration
3. Expand to 30+ test scenarios
4. Add more vendors with different rejection styles
5. Deploy to production environment

## Demo Preparation Checklist

- [x] Demo scenario saved as replay file
- [x] Unit tests passing
- [x] Scenario tests passing
- [x] Dashboard functional
- [x] API server functional
- [x] Replay mode tested
- [x] Demo guide written
- [ ] Rehearse 4-minute script 5 times
- [ ] Prerecord backup run
- [ ] Prepare for network failure (switch to replay)
