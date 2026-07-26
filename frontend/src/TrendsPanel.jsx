import React, { useEffect, useState } from "react";
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import { MapContainer, TileLayer, CircleMarker, Popup } from "react-leaflet";
import "leaflet/dist/leaflet.css";

import { API_BASE } from "./config.js";

const CRIME_TYPE_COLORS = {
  Burglary: "#4F9DDE",
  Robbery: "#E0A458",
  Theft: "#3FB68B",
  Cybercrime: "#E5484D",
  Assault: "#9B7FD4",
};

const STATUS_COLORS = {
  Solved: "#3FB68B",
  Open: "#E0A458",
  "Under Investigation": "#4F9DDE",
};

const CHART_TEXT = "#8B98A5";
const CHART_GRID = "#232D38";

function ChartTooltip({ active, payload, label }) {
  if (!active || !payload || payload.length === 0) return null;
  return (
    <div className="chart-tooltip">
      <div className="chart-tooltip-label">{label}</div>
      <div className="chart-tooltip-value">{payload[0].value} cases</div>
    </div>
  );
}

export default function TrendsPanel() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(`${API_BASE}/api/trends/dashboard`);
        const json = await res.json();
        if (!res.ok) {
          setError(json.detail || "Request failed");
        } else {
          setData(json);
        }
      } catch (err) {
        setError(`Could not reach the backend: ${err.message}`);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) return <div className="network-scroll"><div className="thinking-text">Loading trends…</div></div>;
  if (error) return <div className="network-scroll"><div className="access-denied">{error}</div></div>;
  if (!data) return null;

  const mapCenter = data.hotspots.length > 0
    ? [data.hotspots[0].lat, data.hotspots[0].lng]
    : [14.5, 76.0];

  const maxHotspotCount = Math.max(...data.hotspots.map((h) => h.count), 1);

  return (
    <div className="network-scroll">
      <div className="trend-grid">
        <section className="network-section">
          <h2 className="section-title">Cases by Crime Type</h2>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={data.by_crime_type}>
              <CartesianGrid strokeDasharray="3 3" stroke={CHART_GRID} vertical={false} />
              <XAxis dataKey="crime_type" tick={{ fill: CHART_TEXT, fontSize: 11 }} axisLine={{ stroke: CHART_GRID }} tickLine={false} />
              <YAxis tick={{ fill: CHART_TEXT, fontSize: 11 }} axisLine={{ stroke: CHART_GRID }} tickLine={false} />
              <Tooltip content={<ChartTooltip />} cursor={{ fill: "rgba(79,157,222,0.06)" }} />
              <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                {data.by_crime_type.map((entry, i) => (
                  <Cell key={i} fill={CRIME_TYPE_COLORS[entry.crime_type] || "#566373"} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </section>

        <section className="network-section">
          <h2 className="section-title">Cases by District</h2>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={data.by_district} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke={CHART_GRID} horizontal={false} />
              <XAxis type="number" tick={{ fill: CHART_TEXT, fontSize: 11 }} axisLine={{ stroke: CHART_GRID }} tickLine={false} />
              <YAxis dataKey="district" type="category" tick={{ fill: CHART_TEXT, fontSize: 11 }} axisLine={{ stroke: CHART_GRID }} tickLine={false} width={80} />
              <Tooltip content={<ChartTooltip />} cursor={{ fill: "rgba(79,157,222,0.06)" }} />
              <Bar dataKey="count" fill="#4F9DDE" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </section>

        <section className="network-section">
          <h2 className="section-title">Monthly Timeline</h2>
          <ResponsiveContainer width="100%" height={240}>
            <LineChart data={data.monthly_timeline}>
              <CartesianGrid strokeDasharray="3 3" stroke={CHART_GRID} vertical={false} />
              <XAxis dataKey="month" tick={{ fill: CHART_TEXT, fontSize: 10 }} axisLine={{ stroke: CHART_GRID }} tickLine={false} />
              <YAxis tick={{ fill: CHART_TEXT, fontSize: 11 }} axisLine={{ stroke: CHART_GRID }} tickLine={false} />
              <Tooltip content={<ChartTooltip />} />
              <Line type="monotone" dataKey="count" stroke="#4F9DDE" strokeWidth={2} dot={{ r: 2, fill: "#4F9DDE" }} />
            </LineChart>
          </ResponsiveContainer>
        </section>

        <section className="network-section">
          <h2 className="section-title">Investigation Status</h2>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={data.by_status}>
              <CartesianGrid strokeDasharray="3 3" stroke={CHART_GRID} vertical={false} />
              <XAxis dataKey="investigation_status" tick={{ fill: CHART_TEXT, fontSize: 10 }} axisLine={{ stroke: CHART_GRID }} tickLine={false} />
              <YAxis tick={{ fill: CHART_TEXT, fontSize: 11 }} axisLine={{ stroke: CHART_GRID }} tickLine={false} />
              <Tooltip content={<ChartTooltip />} cursor={{ fill: "rgba(79,157,222,0.06)" }} />
              <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                {data.by_status.map((entry, i) => (
                  <Cell key={i} fill={STATUS_COLORS[entry.investigation_status] || "#566373"} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </section>
      </div>

      <section className="network-section">
        <h2 className="section-title">Hotspot Map</h2>
        <p className="section-subtitle">
          One marker per police station, sized by case count. Requires internet to load
          map tiles — if offline, use the district chart above as the hotspot view instead.
        </p>
        <div className="map-wrap">
          <MapContainer center={mapCenter} zoom={7} style={{ height: "100%", width: "100%" }}>
            <TileLayer
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              attribution='&copy; OpenStreetMap contributors'
            />
            {data.hotspots.map((h, i) => (
              <CircleMarker
                key={i}
                center={[h.lat, h.lng]}
                radius={6 + (h.count / maxHotspotCount) * 18}
                pathOptions={{ color: "#4F9DDE", fillColor: "#4F9DDE", fillOpacity: 0.45, weight: 1 }}
              >
                <Popup>
                  <strong>{h.police_station}</strong>, {h.district}
                  <br />
                  {h.count} cases
                </Popup>
              </CircleMarker>
            ))}
          </MapContainer>
        </div>
      </section>
    </div>
  );
}
