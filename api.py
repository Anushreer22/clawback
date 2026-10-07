from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))
import db

app = FastAPI(title="Clawback API")

# Add CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event():
    db.init_db()


# Request/Response models
class ApprovalAction(BaseModel):
    approval_id: int
    status: str  # "approved" or "rejected"
    reviewed_by: Optional[str] = "admin"


@app.get("/")
def root():
    return {
        "name": "Clawback",
        "status": "running"
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


# Dashboard endpoints

@app.get("/api/events")
def get_events(claim_id: Optional[str] = None, limit: int = 100):
    """
    Get events for the live agent trace.
    Poll this endpoint every second for real-time updates.
    """
    try:
        events = db.get_events(claim_id=claim_id, limit=limit)
        return {"events": events}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/claims")
def get_claims(vendor: Optional[str] = None, status: Optional[str] = None):
    """
    Get claims for the claim ledger.
    """
    try:
        claims = db.get_claims(vendor=vendor, status=status)
        return {"claims": claims}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/approvals")
def get_approvals(status: str = "pending"):
    """
    Get approval requests for the approval inbox.
    """
    try:
        approvals = db.get_approvals(status=status)
        return {"approvals": approvals}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/approvals/{approval_id}")
def update_approval(approval_id: int, action: ApprovalAction):
    """
    Update an approval request (approve or reject).
    """
    try:
        success = db.update_approval(
            approval_id=approval_id,
            status=action.status,
            reviewed_by=action.reviewed_by
        )
        if not success:
            raise HTTPException(status_code=404, detail="Approval not found")
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/claims")
def create_claim(claim_id: str, vendor: str, incident_id: Optional[str] = None, amount: Optional[float] = None):
    """
    Create a new claim.
    """
    try:
        claim_db_id = db.create_claim(claim_id, vendor, incident_id, amount)
        return {"success": True, "id": claim_db_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    import os
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("api:app", host=host, port=port, reload=False)
