import { useState, useEffect } from 'react'
import './App.css'

interface Event {
  id: number
  claim_id: string
  timestamp: string
  type: string
  input: any
  output: any
  step_number: number | null
}

interface Claim {
  id: number
  claim_id: string
  vendor: string
  incident_id: string | null
  status: string
  amount: number | null
  created_at: string
  updated_at: string
}

interface Approval {
  id: number
  claim_id: string
  claim_value: number
  confidence: number
  reason: string
  status: string
  created_at: string
  reviewed_at: string | null
  reviewed_by: string | null
}

const API_BASE = 'http://localhost:8000'

function App() {
  const [events, setEvents] = useState<Event[]>([])
  const [claims, setClaims] = useState<Claim[]>([])
  const [approvals, setApprovals] = useState<Approval[]>([])
  const [selectedClaim, setSelectedClaim] = useState<string | null>(null)

  // Poll for events every second
  useEffect(() => {
    const fetchData = async () => {
      try {
        const [eventsRes, claimsRes, approvalsRes] = await Promise.all([
          fetch(`${API_BASE}/api/events?claim_id=${selectedClaim || ''}&limit=50`),
          fetch(`${API_BASE}/api/claims`),
          fetch(`${API_BASE}/api/approvals?status=pending`)
        ])

        const eventsData = await eventsRes.json()
        const claimsData = await claimsRes.json()
        const approvalsData = await approvalsRes.json()

        setEvents(eventsData.events || [])
        setClaims(claimsData.claims || [])
        setApprovals(approvalsData.approvals || [])
      } catch (error) {
        console.error('Error fetching data:', error)
      }
    }

    fetchData()
    const interval = setInterval(fetchData, 1000)
    return () => clearInterval(interval)
  }, [selectedClaim])

  const handleApproval = async (approvalId: number, status: string) => {
    try {
      await fetch(`${API_BASE}/api/approvals/${approvalId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ approval_id: approvalId, status, reviewed_by: 'admin' })
      })
      // Refresh approvals
      const res = await fetch(`${API_BASE}/api/approvals?status=pending`)
      const data = await res.json()
      setApprovals(data.approvals || [])
    } catch (error) {
      console.error('Error updating approval:', error)
    }
  }

  return (
    <div className="app">
      <header className="header">
        <h1>Clawback Dashboard</h1>
        <p>SLA Credit Recovery Agent</p>
      </header>

      <div className="dashboard">
        {/* Panel 1: Live Agent Trace */}
        <div className="panel">
          <h2>Live Agent Trace</h2>
          <div className="panel-controls">
            <select
              value={selectedClaim || ''}
              onChange={(e) => setSelectedClaim(e.target.value || null)}
            >
              <option value="">All Claims</option>
              {claims.map(claim => (
                <option key={claim.claim_id} value={claim.claim_id}>
                  {claim.claim_id}
                </option>
              ))}
            </select>
          </div>
          <div className="events-list">
            {events.length === 0 ? (
              <p className="empty">No events yet</p>
            ) : (
              events.map(event => (
                <div key={event.id} className="event-item">
                  <div className="event-header">
                    <span className="event-type">{event.type}</span>
                    <span className="event-time">
                      {new Date(event.timestamp).toLocaleTimeString()}
                    </span>
                    {event.step_number !== null && (
                      <span className="event-step">Step {event.step_number}</span>
                    )}
                  </div>
                  {event.input && (
                    <div className="event-details">
                      <strong>Input:</strong>
                      <pre>{JSON.stringify(event.input, null, 2)}</pre>
                    </div>
                  )}
                  {event.output && (
                    <div className="event-details">
                      <strong>Output:</strong>
                      <pre>{JSON.stringify(event.output, null, 2)}</pre>
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        </div>

        {/* Panel 2: Claim Ledger */}
        <div className="panel">
          <h2>Claim Ledger</h2>
          <div className="claims-list">
            {claims.length === 0 ? (
              <p className="empty">No claims yet</p>
            ) : (
              claims.map(claim => (
                <div key={claim.id} className="claim-item">
                  <div className="claim-header">
                    <span className="claim-id">{claim.claim_id}</span>
                    <span className={`claim-status status-${claim.status}`}>
                      {claim.status}
                    </span>
                  </div>
                  <div className="claim-details">
                    <p><strong>Vendor:</strong> {claim.vendor}</p>
                    {claim.incident_id && <p><strong>Incident:</strong> {claim.incident_id}</p>}
                    {claim.amount !== null && <p><strong>Amount:</strong> ${claim.amount}</p>}
                    <p><strong>Created:</strong> {new Date(claim.created_at).toLocaleString()}</p>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Panel 3: Approval Inbox */}
        <div className="panel">
          <h2>Approval Inbox</h2>
          <div className="approvals-list">
            {approvals.length === 0 ? (
              <p className="empty">No pending approvals</p>
            ) : (
              approvals.map(approval => (
                <div key={approval.id} className="approval-item">
                  <div className="approval-header">
                    <span className="approval-claim">{approval.claim_id}</span>
                    <span className="approval-value">${approval.claim_value}</span>
                  </div>
                  <div className="approval-details">
                    <p><strong>Confidence:</strong> {(approval.confidence * 100).toFixed(0)}%</p>
                    <p><strong>Reason:</strong> {approval.reason}</p>
                    <p><strong>Created:</strong> {new Date(approval.created_at).toLocaleString()}</p>
                  </div>
                  <div className="approval-actions">
                    <button
                      className="btn btn-approve"
                      onClick={() => handleApproval(approval.id, 'approved')}
                    >
                      Approve
                    </button>
                    <button
                      className="btn btn-reject"
                      onClick={() => handleApproval(approval.id, 'rejected')}
                    >
                      Reject
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default App
