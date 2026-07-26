import React, { useState } from "react";
import Login from "./Login.jsx";
import ChatPanel from "./ChatPanel.jsx";
import NetworkPanel from "./NetworkPanel.jsx";
import TrendsPanel from "./TrendsPanel.jsx";
import ProfilePanel from "./ProfilePanel.jsx";
import InvestigatePanel from "./InvestigatePanel.jsx";

function loadAuth() {
  try {
    const raw = localStorage.getItem("ksp_auth");
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export default function App() {
  const [auth, setAuth] = useState(loadAuth);
  const [tab, setTab] = useState("chat");

  function handleLogin(data) {
    localStorage.setItem("ksp_auth", JSON.stringify(data));
    setAuth(data);
  }

  function handleLogout() {
    localStorage.removeItem("ksp_auth");
    setAuth(null);
  }

  if (!auth) {
    return <Login onLogin={handleLogin} />;
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">KSP</div>
          <div className="brand-text">
            <div className="brand-title">Crime Intelligence</div>
            <div className="brand-subtitle">Conversational Console</div>
          </div>
        </div>

        <div className="sidebar-section">
          <div className="sidebar-label">Signed in as</div>
          <div className="sidebar-value">{auth.username}</div>
          <span className="role-pill">{auth.role}</span>
        </div>

        <nav className="tab-nav">
          <button
            className={`tab-button ${tab === "chat" ? "tab-button--active" : ""}`}
            onClick={() => setTab("chat")}
          >
            Conversational Query
          </button>
          <button
            className={`tab-button ${tab === "network" ? "tab-button--active" : ""}`}
            onClick={() => setTab("network")}
          >
            Network Analysis
          </button>
          <button
            className={`tab-button ${tab === "trends" ? "tab-button--active" : ""}`}
            onClick={() => setTab("trends")}
          >
            Trends & Hotspots
          </button>
          <button
            className={`tab-button ${tab === "profile" ? "tab-button--active" : ""}`}
            onClick={() => setTab("profile")}
          >
            Offender Profiles
          </button>
          <button
            className={`tab-button ${tab === "investigate" ? "tab-button--active" : ""}`}
            onClick={() => setTab("investigate")}
          >
            Case Investigation
          </button>
        </nav>

        <div className="sidebar-footer">
          <button className="logout-button" onClick={handleLogout}>
            Sign out
          </button>
        </div>
      </aside>

      <main className="main-panel">
        {tab === "chat" && <ChatPanel />}
        {tab === "network" && <NetworkPanel token={auth.access_token} />}
        {tab === "trends" && <TrendsPanel />}
        {tab === "profile" && <ProfilePanel />}
        {tab === "investigate" && <InvestigatePanel token={auth.access_token} />}
      </main>
    </div>
  );
}
