import { useState, useEffect, useMemo } from 'react'
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

// Configurable API base URL with fallback to local development URL
const API_BASE = (import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000').replace(/\/$/, '')

type EventCategory =
  | 'tool_call'
  | 'tool_result'
  | 'vendor_rejection'
  | 'vendor_approval'
  | 'reasoning_rebuttal'
  | 'agent_action'

function classifyEvent(event: Event): {
  category: EventCategory
  label: string
  badgeClass: string
} {
  const type = (event.type || '').toLowerCase()
  const outputStatus = (event.output?.status || '').toLowerCase()
  const inputMsg = (
    event.input?.payload?.message ||
    event.input?.arguments?.claim_message ||
    event.input?.message ||
    ''
  ).toLowerCase()

  if (outputStatus === 'approved') {
    return {
      category: 'vendor_approval',
      label: 'Vendor Approval',
      badgeClass: 'badge-approval',
    }
  }

  if (outputStatus === 'rejected') {
    return {
      category: 'vendor_rejection',
      label: 'Vendor Rejection',
      badgeClass: 'badge-rejection',
    }
  }

  if (
    inputMsg.includes('rebuttal') ||
    inputMsg.includes('dispute') ||
    inputMsg.includes('notice period') ||
    inputMsg.includes('insufficient') ||
    type.includes('rebuttal') ||
    type.includes('reasoning')
  ) {
    return {
      category: 'reasoning_rebuttal',
      label: 'Reasoning / Rebuttal',
      badgeClass: 'badge-rebuttal',
    }
  }

  if (type === 'tool_call') {
    const tool = event.input?.tool || 'Tool'
    return {
      category: 'tool_call',
      label: `Tool Call: ${tool}`,
      badgeClass: 'badge-tool-call',
    }
  }

  if (type.includes('result')) {
    return {
      category: 'tool_result',
      label: 'Tool Result',
      badgeClass: 'badge-tool-result',
    }
  }

  return {
    category: 'agent_action',
    label: event.type === 'AGENT_MESSAGE_SENT' ? 'Agent Message' : 'Agent Action',
    badgeClass: 'badge-action',
  }
}

function App() {
  const [events, setEvents] = useState<Event[]>([])
  const [claims, setClaims] = useState<Claim[]>([])
  const [approvals, setApprovals] = useState<Approval[]>([])
  const [selectedClaim, setSelectedClaim] = useState<string | null>(null)
  const [expandedEvents, setExpandedEvents] = useState<Record<number, boolean>>({})
  const [isPolling, setIsPolling] = useState(true)
  const [lastSync, setLastSync] = useState<Date | null>(null)
  const [actionLoading, setActionLoading] = useState<number | null>(null)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  // Poll for real backend data approximately every 1 second
  useEffect(() => {
    let isMounted = true
    let activeController: AbortController | null = null

    const fetchData = async () => {
      activeController = new AbortController()
      try {
        const claimParam = selectedClaim ? `?claim_id=${encodeURIComponent(selectedClaim)}&limit=100` : '?limit=100'
        const [eventsRes, claimsRes, approvalsRes] = await Promise.all([
          fetch(`${API_BASE}/api/events${claimParam}`, { signal: activeController.signal }),
          fetch(`${API_BASE}/api/claims`, { signal: activeController.signal }),
          fetch(`${API_BASE}/api/approvals?status=pending`, { signal: activeController.signal }),
        ])

        if (!eventsRes.ok || !claimsRes.ok || !approvalsRes.ok) {
          throw new Error('Failed to fetch data from API')
        }

        const eventsData = await eventsRes.json()
        const claimsData = await claimsRes.json()
        const approvalsData = await approvalsRes.json()

        if (isMounted) {
          setEvents(eventsData.events || [])
          setClaims(claimsData.claims || [])
          setApprovals(approvalsData.approvals || [])
          setLastSync(new Date())
          setErrorMsg(null)
        }
      } catch (err: any) {
        if (err.name === 'AbortError') return
        if (isMounted) {
          setErrorMsg(`Connecting to backend at ${API_BASE}...`)
        }
      }
    }

    fetchData()
    let interval: ReturnType<typeof setInterval> | null = null
    if (isPolling) {
      interval = setInterval(fetchData, 1000)
    }

    return () => {
      isMounted = false
      if (activeController) {
        activeController.abort()
      }
      if (interval) clearInterval(interval)
    }
  }, [selectedClaim, isPolling])

  const toggleExpandEvent = (id: number) => {
    setExpandedEvents(prev => ({ ...prev, [id]: !prev[id] }))
  }

  const handleApprovalAction = async (approvalId: number, status: 'approved' | 'rejected') => {
    setActionLoading(approvalId)
    try {
      const res = await fetch(`${API_BASE}/api/approvals/${approvalId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          approval_id: approvalId,
          status,
          reviewed_by: 'admin',
        }),
      })

      if (!res.ok) {
        throw new Error(`Failed to update approval (${res.status})`)
      }

      // Immediately refresh approvals and claims
      const [appRes, claimsRes] = await Promise.all([
        fetch(`${API_BASE}/api/approvals?status=pending`),
        fetch(`${API_BASE}/api/claims`),
      ])
      const appData = await appRes.json()
      const claimsData = await claimsRes.json()
      setApprovals(appData.approvals || [])
      setClaims(claimsData.claims || [])
    } catch (err: any) {
      alert(`Error updating approval: ${err.message}`)
    } finally {
      setActionLoading(null)
    }
  }

  // Calculate ledger summary metrics
  const ledgerMetrics = useMemo(() => {
    const totalClaims = claims.length
    let totalRecovered = 0
    let totalClaimed = 0

    for (const c of claims) {
      const amt = c.amount ?? 100.0
      totalClaimed += amt
      if (c.status === 'approved' || c.status === 'completed') {
        totalRecovered += amt
      }
    }

    return { totalClaims, totalClaimed, totalRecovered }
  }, [claims])

  return (
    <div className="app">
      <header className="header">
        <div className="header-content">
          <div>
            <h1>Clawback Autonomous SLA Recovery</h1>
            <p>Real-time Agent Trace, Claim Ledger & Approval Inbox</p>
          </div>
          <div className="header-meta">
            <span className="api-badge" title={`API: ${API_BASE}`}>
              API: {API_BASE}
            </span>
            <div className="sync-status">
              <span className={`status-indicator ${errorMsg ? 'offline' : 'online'}`} />
              <span>{errorMsg ? 'Disconnected' : 'Live Syncing (1s)'}</span>
            </div>
            <button
              className="toggle-poll-btn"
              onClick={() => setIsPolling(prev => !prev)}
            >
              {isPolling ? 'Pause Polling' : 'Resume Polling'}
            </button>
          </div>
        </div>
        {lastSync && (
          <div className="last-synced">
            Last updated: {lastSync.toLocaleTimeString()}
          </div>
        )}
      </header>

      {errorMsg && (
        <div className="api-error-banner">
          <span>{errorMsg}</span>
        </div>
      )}

      <main className="dashboard">
        {/* PANEL 1: LIVE AGENT TRACE */}
        <section className="panel trace-panel">
          <div className="panel-header">
            <div>
              <h2>Live Agent Trace</h2>
              <span className="panel-subtitle">
                Tool execution, multi-agent dialogues, rebuttals & decisions
              </span>
            </div>
            <span className="count-badge">{events.length}</span>
          </div>

          <div className="panel-controls">
            <label htmlFor="claim-filter">Filter by Claim:</label>
            <select
              id="claim-filter"
              value={selectedClaim || ''}
              onChange={(e) => setSelectedClaim(e.target.value || null)}
            >
              <option value="">All Claims ({events.length} events)</option>
              {claims.map(claim => (
                <option key={claim.claim_id} value={claim.claim_id}>
                  {claim.claim_id} ({claim.vendor})
                </option>
              ))}
            </select>
          </div>

          <div className="events-list">
            {events.length === 0 ? (
              <div className="empty">
                <p>No events recorded yet.</p>
                <small>Trigger a live or simulation run to watch real-time execution.</small>
              </div>
            ) : (
              events.map(event => {
                const { category, label, badgeClass } = classifyEvent(event)
                const isExpanded = !!expandedEvents[event.id]

                return (
                  <article key={event.id} className={`event-item event-${category}`}>
                    <div className="event-header">
                      <div className="badge-row">
                        <span className={`event-badge ${badgeClass}`}>{label}</span>
                        {event.claim_id && (
                          <span className="event-claim-tag">{event.claim_id}</span>
                        )}
                        {event.step_number !== null && (
                          <span className="event-step">Step {event.step_number}</span>
                        )}
                      </div>
                      <time className="event-time">
                        {new Date(event.timestamp).toLocaleTimeString()}
                      </time>
                    </div>

                    {/* Formatted Content by Category */}
                    <div className="event-body">
                      {category === 'tool_call' && event.input?.arguments && (
                        <div className="tool-call-info">
                          <span className="info-label">Arguments:</span>
                          <div className="kv-grid">
                            {Object.entries(event.input.arguments).map(([k, v]) => (
                              <div key={k} className="kv-item">
                                <span className="kv-key">{k}:</span>
                                <span className="kv-val">
                                  {typeof v === 'object' ? JSON.stringify(v) : String(v)}
                                </span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {category === 'vendor_rejection' && event.output && (
                        <div className="rejection-box">
                          <strong>Rejection Notice:</strong>
                          <p className="rejection-reason">{event.output.reason}</p>
                          <div className="meta-tag-row">
                            <span className="meta-tag">Requires Rebuttal: Yes</span>
                            <span className="meta-tag">Mode: {event.output.mode || 'live'}</span>
                          </div>
                        </div>
                      )}

                      {category === 'vendor_approval' && event.output && (
                        <div className="approval-box">
                          <strong>Claim Approved:</strong>
                          <p className="approval-reason">{event.output.reason}</p>
                          <div className="meta-tag-row">
                            <span className="meta-tag success">Status: Approved</span>
                            <span className="meta-tag">Mode: {event.output.mode || 'live'}</span>
                          </div>
                        </div>
                      )}

                      {category === 'reasoning_rebuttal' && (
                        <div className="rebuttal-box">
                          <strong>Evidence-Based Rebuttal:</strong>
                          <p className="rebuttal-text">
                            {event.input?.payload?.message ||
                              event.input?.arguments?.claim_message ||
                              event.input?.message ||
                              'Rebuttal message sent.'}
                          </p>
                        </div>
                      )}

                      {category === 'agent_action' && event.input?.payload?.message && (
                        <div className="action-box">
                          <strong>Message Payload:</strong>
                          <p className="action-text">{event.input.payload.message}</p>
                        </div>
                      )}

                      {/* Tool Result summary if tool_call has output */}
                      {category === 'tool_call' && event.output && (
                        <div className="tool-output-preview">
                          <span className="info-label">Tool Result:</span>
                          <pre className="code-snippet">
                            {JSON.stringify(event.output, null, 2)}
                          </pre>
                        </div>
                      )}
                    </div>

                    {/* Expandable Raw JSON */}
                    <div className="event-footer">
                      <button
                        type="button"
                        className="btn-link"
                        onClick={() => toggleExpandEvent(event.id)}
                      >
                        {isExpanded ? 'Hide Raw JSON ▲' : 'View Raw JSON ▼'}
                      </button>
                      {isExpanded && (
                        <pre className="raw-json-block">
                          {JSON.stringify(
                            { input: event.input, output: event.output },
                            null,
                            2
                          )}
                        </pre>
                      )}
                    </div>
                  </article>
                )
              })
            )}
          </div>
        </section>

        {/* PANEL 2: CLAIM LEDGER */}
        <section className="panel ledger-panel">
          <div className="panel-header">
            <div>
              <h2>Claim Ledger</h2>
              <span className="panel-subtitle">Audit log of submitted claims & recovered credits</span>
            </div>
            <span className="count-badge">{claims.length}</span>
          </div>

          <div className="ledger-metrics-bar">
            <div className="metric-box">
              <span className="metric-label">Total Claims</span>
              <span className="metric-val">{ledgerMetrics.totalClaims}</span>
            </div>
            <div className="metric-box">
              <span className="metric-label">Claimed Value</span>
              <span className="metric-val">${ledgerMetrics.totalClaimed.toFixed(2)}</span>
            </div>
            <div className="metric-box highlight">
              <span className="metric-label">Recovered</span>
              <span className="metric-val">${ledgerMetrics.totalRecovered.toFixed(2)}</span>
            </div>
          </div>

          <div className="claims-list">
            {claims.length === 0 ? (
              <div className="empty">
                <p>No claims recorded in database.</p>
                <small>Run a claim scenario to populate ledger records.</small>
              </div>
            ) : (
              claims.map(claim => {
                const claimAmt = claim.amount !== null ? claim.amount : 100.0
                const isRecovered = claim.status === 'approved' || claim.status === 'completed'
                const recoveredAmt = isRecovered ? claimAmt : 0.0

                return (
                  <div key={claim.id} className="claim-item">
                    <div className="claim-header">
                      <div>
                        <span className="claim-id">{claim.claim_id}</span>
                        <span className="claim-vendor">Vendor: {claim.vendor}</span>
                      </div>
                      <span className={`claim-status status-${claim.status.toLowerCase()}`}>
                        {claim.status}
                      </span>
                    </div>

                    <div className="claim-grid">
                      <div className="grid-cell">
                        <span className="cell-label">Incident ID</span>
                        <span className="cell-val">{claim.incident_id || 'INC-2026-001'}</span>
                      </div>
                      <div className="grid-cell">
                        <span className="cell-label">Claim Amount</span>
                        <span className="cell-val font-mono">${claimAmt.toFixed(2)}</span>
                      </div>
                      <div className="grid-cell highlight-cell">
                        <span className="cell-label">Recovered Amount</span>
                        <span className={`cell-val font-mono ${isRecovered ? 'text-success' : 'text-muted'}`}>
                          ${recoveredAmt.toFixed(2)}
                        </span>
                      </div>
                    </div>

                    <div className="claim-footer">
                      <span className="claim-date">
                        Created: {new Date(claim.created_at).toLocaleString()}
                      </span>
                      {claim.updated_at && (
                        <span className="claim-date">
                          Updated: {new Date(claim.updated_at).toLocaleTimeString()}
                        </span>
                      )}
                    </div>
                  </div>
                )
              })
            )}
          </div>
        </section>

        {/* PANEL 3: APPROVAL INBOX */}
        <section className="panel approvals-panel">
          <div className="panel-header">
            <div>
              <h2>Approval Inbox</h2>
              <span className="panel-subtitle">Human-in-the-loop governance for low-confidence or high-value claims</span>
            </div>
            <span className={`count-badge ${approvals.length > 0 ? 'badge-alert' : ''}`}>
              {approvals.length}
            </span>
          </div>

          <div className="approvals-list">
            {approvals.length === 0 ? (
              <div className="empty">
                <div className="check-icon">✓</div>
                <p>Approval Inbox is clear.</p>
                <small>Claims exceeding the cap ($1,000) or under confidence threshold (&lt;70%) appear here.</small>
              </div>
            ) : (
              approvals.map(approval => {
                const confPercent = Math.round(approval.confidence * 100)
                const isUnderThreshold = approval.confidence < 0.7
                const isLoading = actionLoading === approval.id

                return (
                  <div key={approval.id} className="approval-item">
                    <div className="approval-header">
                      <div>
                        <span className="approval-claim">{approval.claim_id}</span>
                        <span className="approval-tag">Requires Human Signoff</span>
                      </div>
                      <span className="approval-value">${approval.claim_value.toFixed(2)}</span>
                    </div>

                    <div className="approval-details">
                      <div className="confidence-meter">
                        <div className="meter-header">
                          <span className="meter-label">Model Confidence</span>
                          <span className={`meter-score ${isUnderThreshold ? 'low-conf' : 'good-conf'}`}>
                            {confPercent}%
                          </span>
                        </div>
                        <div className="meter-bar-bg">
                          <div
                            className={`meter-bar-fill ${isUnderThreshold ? 'low' : 'good'}`}
                            style={{ width: `${confPercent}%` }}
                          />
                        </div>
                      </div>

                      <div className="approval-reason-box">
                        <span className="reason-label">Trigger Reason:</span>
                        <p className="reason-text">{approval.reason}</p>
                      </div>

                      <div className="approval-timestamp">
                        Submitted: {new Date(approval.created_at).toLocaleString()}
                      </div>
                    </div>

                    <div className="approval-actions">
                      <button
                        type="button"
                        className="btn btn-approve"
                        disabled={isLoading}
                        onClick={() => handleApprovalAction(approval.id, 'approved')}
                      >
                        {isLoading ? 'Processing...' : '✓ Approve Credit'}
                      </button>
                      <button
                        type="button"
                        className="btn btn-reject"
                        disabled={isLoading}
                        onClick={() => handleApprovalAction(approval.id, 'rejected')}
                      >
                        {isLoading ? 'Processing...' : '✕ Reject Claim'}
                      </button>
                    </div>
                  </div>
                )
              })
            )}
          </div>
        </section>
      </main>
    </div>
  )
}

export default App
