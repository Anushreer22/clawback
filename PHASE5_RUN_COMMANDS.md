# Phase 5: Exact Run Commands

## 1. Starting Vendor Agent Locally

```bash
cd C:\Users\ANUSHREE R\clawback
python agents/vendor_agent.py
```

**Expected Output:**
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8001
INFO:     Vendor agent started at agent1q...@https://127.0.0.1:8001
```

**Note:** Copy the agent address (e.g., `agent1q...@https://127.0.0.1:8001`) for the next step.

---

## 2. Starting Clawback Agent Locally

### Option A: Simulation Mode (Default)

```bash
cd C:\Users\ANUSHREE R\clawback
python agents/clawback_agent.py
```

**Note:** This uses simulation mode by default. No vendor agent required.

### Option B: Live Mode (Requires Vendor Agent Running)

```bash
cd C:\Users\ANUSHREE R\clawback
set DEMO_MODE=live
set VENDOR_AGENT_ADDRESS=agent1q...@https://127.0.0.1:8001
python agents/clawback_agent.py
```

**Replace `agent1q...@https://127.0.0.1:8001` with the actual address from Step 1.**

**Note:** Requires ASI_KEY to be set in .env file.

---

## 3. Running the Live Communication Demo

### Terminal 1: Start Vendor Agent

```bash
cd C:\Users\ANUSHREE R\clawback
python agents/vendor_agent.py
```

### Terminal 2: Start Clawback Agent in Live Mode

```bash
cd C:\Users\ANUSHREE R\clawback
set DEMO_MODE=live
set VENDOR_AGENT_ADDRESS=agent1q...@https://127.0.0.1:8001
python agents/clawback_agent.py
```

**Expected Flow:**
1. Clawback sends claim to Vendor
2. Vendor rejects claim (35 minutes maintenance)
3. Clawback receives rejection
4. ASI:One reasons about rejection
5. Clawback sends rebuttal with notice period evidence
6. Vendor approves claim

---

## 4. Registering/Deploying Vendor Agent on Agentverse

### Step 4.1: Install Agentverse CLI

```bash
pip install agentverse-cli
```

### Step 4.2: Login to Agentverse

```bash
agentverse login
```

**Follow the authentication prompts in your browser.**

### Step 4.3: Register the Agent

```bash
cd C:\Users\ANUSHREE R\clawback
agentverse register
```

**Expected Output:**
```
Agent registered successfully!
Agent address: agent1qxyz...@agentverse.ai
```

**Copy the agent address for configuration.**

### Step 4.4: Run Vendor Agent on Agentverse

```bash
cd C:\Users\ANUSHREE R\clawback
set AGENTVERSE_ENDPOINT=agentverse.ai
python agents/vendor_agent.py
```

---

## 5. Configuring VENDOR_AGENT_ADDRESS

### For Local Agent

```bash
set VENDOR_AGENT_ADDRESS=agent1q...@https://127.0.0.1:8001
```

### For Agentverse Agent

```bash
set VENDOR_AGENT_ADDRESS=agent1qxyz...@agentverse.ai
```

### For Testnet Agent

```bash
set VENDOR_AGENT_ADDRESS=agent1q...@testnet.agentverse.ai
```

### To Set Permanently in .env File

Edit `.env` and add:

```bash
VENDOR_AGENT_ADDRESS=agent1q...@https://127.0.0.1:8001
```

---

## 6. Running the Simulation Fallback

### Option A: Explicit Simulation Mode

```bash
cd C:\Users\ANUSHREE R\clawback
set DEMO_MODE=simulation
python agents/clawback_agent.py
```

### Option B: Default (No Environment Variable)

```bash
cd C:\Users\ANUSHREE R\clawback
python agents/clawback_agent.py
```

**Note:** If DEMO_MODE is not set, it defaults to `simulation`.

### Option C: Replay Mode (Deterministic)

```bash
cd C:\Users\ANUSHREE R\clawback
python replay.py --run demo_replay.json --delay 0.5
```

**Note:** Replay mode is completely independent of agent communication and works offline.

---

## 7. Testing

### Test Agent Communication

```bash
cd C:\Users\ANUSHREE R\clawback
python test_agent_communication.py
```

**Expected Output:**
```
============================================================
AGENT-TO-AGENT COMMUNICATION TEST
============================================================

STEP 1: Send initial claim
------------------------------------------------------------
Status: rejected
[PASS] Initial claim rejected as expected

STEP 2: Send rebuttal with notice period evidence
------------------------------------------------------------
Status: approved
[PASS] Rebuttal approved as expected

ALL TESTS PASSED
```

### Test All Tools

```bash
cd C:\Users\ANUSHREE R\clawback
python test_tools.py
```

### Test Scenarios

```bash
cd C:\Users\ANUSHREE R\clawback
python test_scenarios/run_scenarios.py
```

### Test Replay Mode

```bash
cd C:\Users\ANUSHREE R\clawback
python replay.py --run demo_replay.json --delay 0.5
```

---

## 8. Full Stack (Dashboard + Agents)

### Terminal 1: API Server

```bash
cd C:\Users\ANUSHREE R\clawback
uvicorn api:app --reload
```

### Terminal 2: React Dashboard

```bash
cd C:\Users\ANUSHREE R\clawback\dashboard
npm run dev
```

### Terminal 3: Vendor Agent (for live mode)

```bash
cd C:\Users\ANUSHREE R\clawback
python agents/vendor_agent.py
```

### Terminal 4: Clawback Agent

```bash
cd C:\Users\ANUSHREE R\clawback
set DEMO_MODE=live
set VENDOR_AGENT_ADDRESS=agent1q...@https://127.0.0.1:8001
python agents/clawback_agent.py
```

**Then open http://localhost:3000 in your browser to see the live dashboard.**

---

## 9. Quick Reference

### Quick Demo (No Setup Required)

```bash
python replay.py --run demo_replay.json --delay 0.5
```

### Interactive Demo (Simulation Mode)

```bash
python run_demo.py
```

### Test Communication

```bash
python test_agent_communication.py
```

### Live Communication (Two Terminals)

**Terminal 1:**
```bash
python agents/vendor_agent.py
```

**Terminal 2:**
```bash
set DEMO_MODE=live
set VENDOR_AGENT_ADDRESS=agent1q...@https://127.0.0.1:8001
python agents/clawback_agent.py
```

---

## 10. Environment Variables Summary

| Variable | Required For | Default | Example |
|----------|--------------|---------|---------|
| `DEMO_MODE` | All | `simulation` | `live` or `simulation` |
| `VENDOR_AGENT_ADDRESS` | Live mode | (empty) | `agent1q...@https://127.0.0.1:8001` |
| `ASI_KEY` | Clawback Agent | (required) | `your_asi_api_key_here` |
| `ASI_MODEL` | Clawback Agent | `asi1-mini` | `asi1-mini` |
| `APPROVAL_CAP` | Approval Gate | `1000` | `1000` |
| `CONFIDENCE_THRESHOLD` | Approval Gate | `0.7` | `0.7` |

---

## 11. Troubleshooting Commands

### Check if Vendor Agent is Running

```bash
curl http://127.0.0.1:8001
```

### Check Environment Variables

```bash
echo %DEMO_MODE%
echo %VENDOR_AGENT_ADDRESS%
echo %ASI_KEY%
```

### Reset to Simulation Mode

```bash
set DEMO_MODE=simulation
set VENDOR_AGENT_ADDRESS=
```

### Clear Database (Start Fresh)

```bash
del clawback.db
python db.py
```

---

## 12. Windows vs Linux/Mac

### Windows (Current)
```bash
set DEMO_MODE=live
set VENDOR_AGENT_ADDRESS=agent1q...@https://127.0.0.1:8001
```

### Linux/Mac
```bash
export DEMO_MODE=live
export VENDOR_AGENT_ADDRESS=agent1q...@https://127.0.0.1:8001
```

---

## 13. Verification

After running any command, verify:

1. **Console Output:** Look for success messages or errors
2. **Database:** Check `clawback.db` was created/updated
3. **Dashboard:** If running, check http://localhost:3000
4. **Logs:** Check for `[AGENT_MESSAGE_SENT]` and `[VENDOR_RESPONSE]` messages

---

## 14. Clean Shutdown

To stop agents gracefully:

1. Press `Ctrl+C` in each terminal
2. Wait for shutdown messages
3. Close terminals

The database will persist across restarts.
