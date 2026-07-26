import React, { useState } from "react";

const API_BASE = "http://localhost:8000";

const STATUS_STYLES = {
  Solved: { bg: "rgba(63,182,139,0.15)", fg: "#3FB68B", border: "rgba(63,182,139,0.4)" },
  Open: { bg: "rgba(224,164,88,0.15)", fg: "#E0A458", border: "rgba(224,164,88,0.4)" },
  "Under Investigation": { bg: "rgba(79,157,222,0.15)", fg: "#4F9DDE", border: "rgba(79,157,222,0.4)" },
};

function StatusPill({ status }) {
  const style = STATUS_STYLES[status] || { bg: "rgba(139,152,165,0.15)", fg: "#8B98A5", border: "rgba(139,152,165,0.4)" };
  return (
    <span className="status-pill" style={{ background: style.bg, color: style.fg, borderColor: style.border }}>
      {status}
    </span>
  );
}

/** The LLM is prompted to return "SUMMARY:" and "LEADS:" sections, but small
 * local models don't always follow formatting exactly — fall back to showing
 * the raw text rather than silently dropping content if parsing fails. */
function splitAnalysis(analysis) {
  const leadsIndex = analysis.search(/LEADS\s*:/i);
  if (leadsIndex === -1) {
    return { summary: analysis, leads: null };
  }
  const summaryPart = analysis.slice(0, leadsIndex).replace(/SUMMARY\s*:/i, "").trim();
  const leadsPart = analysis.slice(leadsIndex).replace(/LEADS\s*:/i, "").trim();
  return { summary: summaryPart, leads: leadsPart };
}

export default function InvestigatePanel({ token }) {
  const [crimeId, setCrimeId] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  async function investigate() {
    if (!crimeId.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await fetch(`${API_BASE}/api/investigate/case/${crimeId.trim()}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data.detail || "Request failed");
      } else {
        setResult(data);
      }
    } catch (err) {
      setError(`Could not reach the backend: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }

  const parsed = result ? splitAnalysis(result.analysis) : null;

  return (
    <div className="network-scroll">
      <section className="network-section">
        <h2 className="section-title">Case Investigation</h2>
        <p className="section-subtitle">
          Auto-generated summary, investigative leads, and similar past cases for one FIR.
          Requires being signed in.
        </p>
        <div className="lookup-bar">
          <input
            className="input-box lookup-input"
            placeholder="Crime ID (e.g. 98, 733)"
            value={crimeId}
            onChange={(e) => setCrimeId(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && investigate()}
          />
          <button className="send-button" onClick={investigate} disabled={loading}>
            {loading ? "…" : "Investigate"}
          </button>
        </div>
        {loading && <div className="thinking-indicator" style={{ marginTop: 8 }}>
          <span className="dot" /><span className="dot" /><span className="dot" />
          <span className="thinking-text">Generating case summary and searching for similar cases…</span>
        </div>}
        {error && <div className="access-denied">{error}</div>}
      </section>

      {result && (
        <>
          <section className="network-section">
            <div className="case-header">
              <div>
                <div className="case-fir">{result.case.fir_no}</div>
                <div className="case-meta">
                  {result.case.crime_type} ({result.case.ipc_sections}) · {result.case.police_station}, {result.case.district} · {result.case.crime_date}
                </div>
              </div>
              <StatusPill status={result.case.status} />
            </div>
            <p className="case-description">{result.case.description}</p>
            <div className="case-people">
              <div>
                <span className="sidebar-label">Accused</span>
                <div className="case-people-list">
                  {result.case.accused.length > 0
                    ? result.case.accused.map((a, i) => (
                        <span key={i} className="chip chip--static">
                          {a.name}{a.repeat_offender ? " (repeat offender)" : ""}
                        </span>
                      ))
                    : <span className="text-faint">None on record</span>}
                </div>
              </div>
              <div>
                <span className="sidebar-label">Victims</span>
                <div className="case-people-list">
                  {result.case.victims.length > 0
                    ? result.case.victims.map((v, i) => <span key={i} className="chip chip--static">{v}</span>)
                    : <span className="text-faint">None on record</span>}
                </div>
              </div>
            </div>
          </section>

          <section className="network-section">
            <h2 className="section-title">Summary & Investigative Leads</h2>
            <p className="summary-text">{parsed.summary}</p>
            {parsed.leads && (
              <>
                <div className="sidebar-label" style={{ marginTop: 12, marginBottom: 6 }}>Leads</div>
                <p className="summary-text">{parsed.leads}</p>
              </>
            )}
          </section>

          <section className="network-section">
            <h2 className="section-title">
              Similar Past Cases <span className="row-count-badge">{result.similar_cases.length}</span>
            </h2>
            {result.similar_cases.length === 0 ? (
              <div className="empty-state-title">No embeddings found — run build_embeddings.py first.</div>
            ) : (
              <div className="similar-case-list">
                {result.similar_cases.map((c) => (
                  <div key={c.crime_id} className="similar-case-row">
                    <div className="similar-case-info">
                      <div>
                        <strong>{c.fir_no}</strong> — {c.crime_type} · {c.police_station}, {c.district}
                      </div>
                      <StatusPill status={c.investigation_status} />
                    </div>
                    <div className="similarity-bar-track">
                      <div className="similarity-bar-fill" style={{ width: `${c.similarity * 100}%` }} />
                    </div>
                    <div className="similarity-score">{(c.similarity * 100).toFixed(1)}% similar</div>
                  </div>
                ))}
              </div>
            )}
          </section>
        </>
      )}
    </div>
  );
}
