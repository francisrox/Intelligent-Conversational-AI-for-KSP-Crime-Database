import React, { useEffect, useRef, useState } from "react";

const API_URL = "http://localhost:8000/api/chat/";

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

function DataTable({ rows }) {
  if (!rows || rows.length === 0) return null;
  const columns = Object.keys(rows[0]);
  return (
    <div className="data-table-wrap">
      <table className="data-table">
        <thead>
          <tr>
            {columns.map((col) => (
              <th key={col}>{col.replace(/_/g, " ")}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i}>
              {columns.map((col) => (
                <td key={col}>
                  {col === "investigation_status" ? <StatusPill status={row[col]} /> : String(row[col] ?? "—")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function EvidenceCard({ result }) {
  const [sqlOpen, setSqlOpen] = useState(false);

  if (result.error) {
    return (
      <div className="evidence-card evidence-card--error">
        <div className="evidence-header">
          <span className="evidence-label evidence-label--error">Query failed</span>
        </div>
        <p className="evidence-error-text">{result.error}</p>
        {result.sql && <pre className="sql-block">{result.sql}</pre>}
      </div>
    );
  }

  return (
    <div className="evidence-card">
      <div className="evidence-header">
        <span className="evidence-label">Conclusion</span>
        <span className="row-count-badge">
          {result.row_count} record{result.row_count === 1 ? "" : "s"}
        </span>
      </div>
      <p className="summary-text">{result.summary}</p>

      <button className="sql-toggle" onClick={() => setSqlOpen((v) => !v)}>
        {sqlOpen ? "▾" : "▸"} Show supporting query
      </button>
      {sqlOpen && <pre className="sql-block">{result.sql}</pre>}

      <DataTable rows={result.rows} />
    </div>
  );
}

export default function ChatPanel() {
  const [sessionId] = useState(() => crypto.randomUUID());
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, loading]);

  async function sendMessage() {
    const question = input.trim();
    if (!question || loading) return;

    setMessages((prev) => [...prev, { role: "user", content: question }]);
    setInput("");
    setLoading(true);

    try {
      const res = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId, message: question }),
      });
      const data = await res.json();
      setMessages((prev) => [...prev, { role: "assistant", result: data }]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", result: { error: `Could not reach the backend: ${err.message}` } },
      ]);
    } finally {
      setLoading(false);
    }
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }

  return (
    <>
      <div className="panel-topbar">
        <div className="session-chip">Session {sessionId.slice(0, 8)} · llama3.1:8b local</div>
        <div className="suggestion-row">
          <button className="chip" onClick={() => setInput("Show burglary cases in Whitefield")}>
            Burglary in Whitefield
          </button>
          <button className="chip" onClick={() => setInput("Which accused has the highest number of burglary cases?")}>
            Top burglary offender
          </button>
          <button className="chip" onClick={() => setInput("Which police station has the highest theft cases?")}>
            Top theft hotspot
          </button>
          <button className="chip" onClick={() => setInput("Only the solved ones")}>
            Only the solved ones
          </button>
        </div>
      </div>

      <div className="chat-scroll" ref={scrollRef}>
        {messages.length === 0 && (
          <div className="empty-state">
            <div className="empty-state-title">No queries yet</div>
            <p>Ask a question about the crime database in plain English. Follow-up questions carry context from the previous turn.</p>
          </div>
        )}

        {messages.map((m, i) =>
          m.role === "user" ? (
            <div key={i} className="message message--user">
              <div className="bubble bubble--user">{m.content}</div>
            </div>
          ) : (
            <div key={i} className="message message--assistant">
              <EvidenceCard result={m.result} />
            </div>
          )
        )}

        {loading && (
          <div className="message message--assistant">
            <div className="thinking-indicator">
              <span className="dot" />
              <span className="dot" />
              <span className="dot" />
              <span className="thinking-text">Generating query and analyzing results…</span>
            </div>
          </div>
        )}
      </div>

      <div className="input-bar">
        <textarea
          className="input-box"
          placeholder="Ask about crimes, accused, hotspots, or a follow-up question…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          rows={1}
          disabled={loading}
        />
        <button className="send-button" onClick={sendMessage} disabled={loading || !input.trim()}>
          {loading ? "…" : "Ask"}
        </button>
      </div>
    </>
  );
}
