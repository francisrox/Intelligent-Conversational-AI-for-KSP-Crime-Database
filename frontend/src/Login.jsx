import React, { useState } from "react";

const API_BASE = "http://localhost:8000";

export default function Login({ onLogin }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data.detail || "Login failed");
      } else {
        onLogin(data);
      }
    } catch (err) {
      setError(`Could not reach the backend: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-shell">
      <form className="login-card" onSubmit={handleSubmit}>
        <div className="brand login-brand">
          <div className="brand-mark">KSP</div>
          <div className="brand-text">
            <div className="brand-title">Crime Intelligence</div>
            <div className="brand-subtitle">Conversational Console</div>
          </div>
        </div>

        <label className="login-label">Username</label>
        <input
          className="login-input"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          autoFocus
        />

        <label className="login-label">Password</label>
        <input
          className="login-input"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />

        {error && <div className="access-denied">{error}</div>}

        <button className="send-button login-submit" disabled={loading}>
          {loading ? "Signing in…" : "Sign in"}
        </button>

        <div className="login-hint">
          Demo accounts: admin/admin123 · investigator1/invest123 · analyst1/analyst123
        </div>
      </form>
    </div>
  );
}
