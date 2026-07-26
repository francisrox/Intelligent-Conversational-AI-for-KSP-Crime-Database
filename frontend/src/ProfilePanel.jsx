import React, { useState } from "react";

const API_BASE = "http://localhost:8000";

const TIER_STYLES = {
  High: { bg: "rgba(229,72,77,0.15)", fg: "#E5484D", border: "rgba(229,72,77,0.4)" },
  Medium: { bg: "rgba(224,164,88,0.15)", fg: "#E0A458", border: "rgba(224,164,88,0.4)" },
  Low: { bg: "rgba(63,182,139,0.15)", fg: "#3FB68B", border: "rgba(63,182,139,0.4)" },
};

const STATUS_STYLES = {
  Solved: { bg: "rgba(63,182,139,0.15)", fg: "#3FB68B", border: "rgba(63,182,139,0.4)" },
  Open: { bg: "rgba(224,164,88,0.15)", fg: "#E0A458", border: "rgba(224,164,88,0.4)" },
  "Under Investigation": { bg: "rgba(79,157,222,0.15)", fg: "#4F9DDE", border: "rgba(79,157,222,0.4)" },
};

function Pill({ text, styleMap }) {
  const style = styleMap[text] || { bg: "rgba(139,152,165,0.15)", fg: "#8B98A5", border: "rgba(139,152,165,0.4)" };
  return (
    <span className="status-pill" style={{ background: style.bg, color: style.fg, borderColor: style.border }}>
      {text}
    </span>
  );
}

export default function ProfilePanel() {
  const [accusedId, setAccusedId] = useState("");
  const [profile, setProfile] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  async function lookup() {
    if (!accusedId.trim()) return;
    setLoading(true);
    setError(null);
    setProfile(null);
    try {
      const res = await fetch(`${API_BASE}/api/profile/${accusedId.trim()}`);
      const data = await res.json();
      if (!res.ok) {
        setError(data.detail || "Request failed");
      } else {
        setProfile(data);
      }
    } catch (err) {
      setError(`Could not reach the backend: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }

  const tierStyle = profile ? TIER_STYLES[profile.risk_tier] : null;

  return (
    <div className="network-scroll">
      <section className="network-section">
        <h2 className="section-title">Offender Profile Lookup</h2>
        <p className="section-subtitle">
          Risk score is a transparent weighted formula, not a black-box model — every
          point is traceable to a specific fact below.
        </p>
        <div className="lookup-bar">
          <input
            className="input-box lookup-input"
            placeholder="Accused ID (e.g. 57, 72, 184)"
            value={accusedId}
            onChange={(e) => setAccusedId(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && lookup()}
          />
          <button className="send-button" onClick={lookup} disabled={loading}>
            {loading ? "…" : "Look up"}
          </button>
        </div>
        {error && <div className="access-denied">{error}</div>}
      </section>

      {profile && (
        <>
          <section className="network-section profile-header">
            <div className="profile-identity">
              <div className="profile-name">{profile.name}</div>
              <div className="profile-meta">
                {profile.age} yrs · {profile.gender} · Accused #{profile.accused_id}
              </div>
              <div className="profile-badges">
                {profile.gang_affiliated && <span className="badge badge--danger">Gang affiliated</span>}
                {profile.flagged_repeat_offender && <span className="badge badge--warning">Repeat offender</span>}
              </div>
            </div>
            <div
              className="risk-gauge"
              style={{ background: tierStyle.bg, color: tierStyle.fg, borderColor: tierStyle.border }}
            >
              <div className="risk-score-number">{profile.risk_score}</div>
              <div className="risk-score-label">/ 100 · {profile.risk_tier} risk</div>
            </div>
          </section>

          <section className="network-section">
            <h2 className="section-title">Conclusion → Evidence → Confidence</h2>
            <p className="section-subtitle">
              This is the explainability habit (Module 9) applied to the risk score above — every
              contributing factor, its raw value, and exactly how many points it added.
            </p>
            <div className="breakdown-table">
              {profile.risk_breakdown.map((row, i) => (
                <div key={i} className="breakdown-row">
                  <div className="breakdown-factor">
                    <div className="breakdown-factor-name">{row.factor}</div>
                    <div className="breakdown-factor-explanation">{row.explanation}</div>
                  </div>
                  <div className="breakdown-raw">{String(row.raw_value)}</div>
                  <div className="breakdown-points">
                    <div className="breakdown-bar-track">
                      <div
                        className="breakdown-bar-fill"
                        style={{ width: `${(row.points / row.max_points) * 100}%` }}
                      />
                    </div>
                    <div className="breakdown-points-text">
                      {row.points} / {row.max_points}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </section>

          <section className="network-section">
            <h2 className="section-title">
              Linked Cases <span className="row-count-badge">{profile.case_count}</span>
            </h2>
            <div className="data-table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>FIR No</th>
                    <th>Crime Type</th>
                    <th>Date</th>
                    <th>District</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {profile.cases.map((c) => (
                    <tr key={c.crime_id}>
                      <td>{c.fir_no}</td>
                      <td>{c.crime_type}</td>
                      <td>{c.crime_date}</td>
                      <td>{c.district}</td>
                      <td>
                        <Pill text={c.investigation_status} styleMap={STATUS_STYLES} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </>
      )}
    </div>
  );
}
