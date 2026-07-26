import React, { useEffect, useState } from "react";
import GraphCanvas from "./GraphCanvas.jsx";

const API_BASE = "http://localhost:8000";

function hiddenConnectionsToGraph(connections) {
  const nodes = {};
  const edges = [];

  connections.forEach((c) => {
    const vId = `Vehicle:${c.vehicle_id}`;
    const a1 = `Accused:${c.accused_1_id}`;
    const a2 = `Accused:${c.accused_2_id}`;
    const c1 = `Crime:${c.crime_1_id}`;
    const c2 = `Crime:${c.crime_2_id}`;

    nodes[vId] = { data: { id: vId, type: "Vehicle", plate_no: c.plate_no } };
    nodes[a1] = { data: { id: a1, type: "Accused", name: c.accused_1_name } };
    nodes[a2] = { data: { id: a2, type: "Accused", name: c.accused_2_name } };
    nodes[c1] = { data: { id: c1, type: "Crime", fir_no: c.crime_1_fir } };
    nodes[c2] = { data: { id: c2, type: "Crime", fir_no: c.crime_2_fir } };

    edges.push({ data: { id: `${a1}-${c1}`, source: a1, target: c1, label: "ACCUSED_IN" } });
    edges.push({ data: { id: `${a2}-${c2}`, source: a2, target: c2, label: "ACCUSED_IN" } });
    edges.push({ data: { id: `${c1}-${vId}`, source: c1, target: vId, label: "INVOLVES_VEHICLE" } });
    edges.push({ data: { id: `${c2}-${vId}`, source: c2, target: vId, label: "INVOLVES_VEHICLE" } });
  });

  return { nodes: Object.values(nodes), edges };
}

export default function NetworkPanel({ token }) {
  const [connections, setConnections] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  const [accusedId, setAccusedId] = useState("");
  const [accusedGraph, setAccusedGraph] = useState(null);
  const [accusedError, setAccusedError] = useState(null);
  const [accusedLoading, setAccusedLoading] = useState(false);

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(`${API_BASE}/api/network/hidden-connections`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        const data = await res.json();
        if (!res.ok) {
          setError(data.detail || "Request failed");
        } else {
          setConnections(data.connections);
        }
      } catch (err) {
        setError(`Could not reach the backend: ${err.message}`);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [token]);

  async function lookupAccused() {
    if (!accusedId.trim()) return;
    setAccusedLoading(true);
    setAccusedError(null);
    setAccusedGraph(null);
    try {
      const res = await fetch(`${API_BASE}/api/network/accused/${accusedId.trim()}`);
      const data = await res.json();
      if (!res.ok) {
        setAccusedError(data.detail || "Request failed");
      } else if (!data.nodes || data.nodes.length === 0) {
        setAccusedError(`No accused found with ID ${accusedId}.`);
      } else {
        setAccusedGraph(data);
      }
    } catch (err) {
      setAccusedError(`Could not reach the backend: ${err.message}`);
    } finally {
      setAccusedLoading(false);
    }
  }

  const graph = connections ? hiddenConnectionsToGraph(connections) : null;

  return (
    <div className="network-scroll">
      <section className="network-section">
        <h2 className="section-title">Hidden Connections</h2>
        <p className="section-subtitle">
          Vehicles used in crimes by different accused, in different districts — the kind of
          connection a manual FIR-by-FIR search would very likely miss. Restricted to
          Investigator, Supervisor, and Admin roles.
        </p>

        {loading && <div className="thinking-text">Loading network…</div>}
        {error && <div className="access-denied">{error}</div>}

        {connections && connections.length === 0 && (
          <div className="empty-state-title">No hidden connections found in the current data.</div>
        )}

        {graph && graph.nodes.length > 0 && (
          <>
            <GraphCanvas nodes={graph.nodes} edges={graph.edges} />
            <div className="connection-list">
              {connections.slice(0, 12).map((c, i) => (
                <div key={i} className="connection-row">
                  Vehicle <span className="mono">{c.plate_no}</span> links{" "}
                  <strong>{c.accused_1_name}</strong> ({c.crime_1_district} · {c.crime_1_fir}) to{" "}
                  <strong>{c.accused_2_name}</strong> ({c.crime_2_district} · {c.crime_2_fir})
                </div>
              ))}
            </div>
          </>
        )}
      </section>

      <section className="network-section">
        <h2 className="section-title">Look up an accused's network</h2>
        <div className="lookup-bar">
          <input
            className="input-box lookup-input"
            placeholder="Accused ID (e.g. 184)"
            value={accusedId}
            onChange={(e) => setAccusedId(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && lookupAccused()}
          />
          <button className="send-button" onClick={lookupAccused} disabled={accusedLoading}>
            {accusedLoading ? "…" : "Look up"}
          </button>
        </div>
        {accusedError && <div className="access-denied">{accusedError}</div>}
        {accusedGraph && <GraphCanvas nodes={accusedGraph.nodes} edges={accusedGraph.edges} />}
      </section>
    </div>
  );
}
