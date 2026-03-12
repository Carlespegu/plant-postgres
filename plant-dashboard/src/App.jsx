import React, { useEffect, useMemo, useState } from "react";
import {
  RefreshCw,
  Thermometer,
  Droplets,
  Sun,
  CloudRain,
  Wifi,
  Cpu,
  Database,
} from "lucide-react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";

const STORAGE_KEY = "plant-station-dashboard-config";

function Panel({ title, children }) {
  return (
    <div
      style={{
        background: "#fff",
        borderRadius: 16,
        padding: 20,
        boxShadow: "0 1px 8px rgba(0,0,0,0.06)",
      }}
    >
      {title && <h3 style={{ marginTop: 0 }}>{title}</h3>}
      {children}
    </div>
  );
}

function StatCard({ title, value, Icon }) {
  return (
    <div
      style={{
        background: "#fff",
        borderRadius: 16,
        padding: 20,
        boxShadow: "0 1px 8px rgba(0,0,0,0.06)",
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
      }}
    >
      <div>
        <div style={{ fontSize: 14, color: "#64748b" }}>{title}</div>
        <div style={{ fontSize: 24, fontWeight: 700, marginTop: 8 }}>{value}</div>
      </div>
      <div
        style={{
          background: "#f1f5f9",
          borderRadius: 16,
          padding: 12,
        }}
      >
        <Icon size={20} />
      </div>
    </div>
  );
}

export default function App() {
  const [baseUrl, setBaseUrl] = useState("https://plant-postgres-1.onrender.com");
  const [apiKey, setApiKey] = useState("");
  const [deviceId, setDeviceId] = useState("esp32-plant-01");
  const [limit, setLimit] = useState(100);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [rows, setRows] = useState([]);
  const [lastFetchAt, setLastFetchAt] = useState(null);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return;
      const saved = JSON.parse(raw);
      if (saved.baseUrl) setBaseUrl(saved.baseUrl);
      if (saved.apiKey) setApiKey(saved.apiKey);
      if (saved.deviceId) setDeviceId(saved.deviceId);
      if (saved.limit) setLimit(saved.limit);
    } catch {}
  }, []);

  useEffect(() => {
    try {
      localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({ baseUrl, apiKey, deviceId, limit })
      );
    } catch {}
  }, [baseUrl, apiKey, deviceId, limit]);

  const headers = useMemo(() => {
    const h = {};
    if (apiKey.trim()) h["X-Api-Key"] = apiKey.trim();
    return h;
  }, [apiKey]);

  const fetchData = async () => {
    setLoading(true);
    setError("");

    try {
      const cleanBaseUrl = baseUrl.replace(/\/$/, "");
      const url = `${cleanBaseUrl}/api/v1/readings?deviceId=${encodeURIComponent(deviceId)}&limit=${limit}`;

      const res = await fetch(url, { headers });

      if (!res.ok) {
        const text = await res.text();
        throw new Error(`HTTP ${res.status}: ${text}`);
      }

      const data = await res.json();

      const normalized = [...data].reverse().map((r) => ({
        ...r,
        timeLabel: new Date(r.ts).toLocaleTimeString(),
        dateLabel: new Date(r.ts).toLocaleString(),
      }));

      setRows(normalized);
      setLastFetchAt(new Date());
    } catch (e) {
      setError(e.message || "Error carregant dades");
      setRows([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const latest = rows.length ? rows[rows.length - 1] : null;

  const statCards = [
    {
      title: "Temperatura",
      value: latest?.tempC != null ? `${Number(latest.tempC).toFixed(1)} °C` : "--",
      icon: Thermometer,
    },
    {
      title: "Humitat aire",
      value: latest?.humAir != null ? `${Math.round(Number(latest.humAir))} %` : "--",
      icon: Droplets,
    },
    {
      title: "Humitat sòl",
      value: latest?.soilPercent != null ? `${Math.round(Number(latest.soilPercent))} %` : "--",
      icon: Droplets,
    },
    {
      title: "Llum (raw)",
      value: latest?.ldrRaw != null ? `${latest.ldrRaw}` : "--",
      icon: Sun,
    },
    {
      title: "Pluja",
      value: latest?.rain ?? "--",
      icon: CloudRain,
    },
    {
      title: "RSSI",
      value: latest?.rssi != null ? `${latest.rssi} dBm` : "--",
      icon: Wifi,
    },
  ];

  return (
    <div style={{ minHeight: "100vh", background: "#f8fafc", padding: 24, fontFamily: "Arial, sans-serif" }}>
      <div style={{ maxWidth: 1400, margin: "0 auto" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24, gap: 16, flexWrap: "wrap" }}>
          <div>
            <h1 style={{ margin: 0 }}>Plant Station Dashboard</h1>
            <p style={{ color: "#64748b" }}>Lectures de la teva API FastAPI + PostgreSQL</p>
          </div>

          <button
            onClick={fetchData}
            disabled={loading}
            style={{
              border: "none",
              background: "#2563eb",
              color: "white",
              padding: "10px 16px",
              borderRadius: 10,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: 8,
            }}
          >
            <RefreshCw size={16} />
            {loading ? "Actualitzant..." : "Actualitzar"}
          </button>
        </div>

        <Panel title="Configuració">
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: 12 }}>
            <div>
              <label>Base URL</label>
              <input style={{ width: "100%", padding: 10, marginTop: 6 }} value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} />
            </div>
            <div>
              <label>API Key</label>
              <input style={{ width: "100%", padding: 10, marginTop: 6 }} type="password" value={apiKey} onChange={(e) => setApiKey(e.target.value)} />
            </div>
            <div>
              <label>deviceId</label>
              <input style={{ width: "100%", padding: 10, marginTop: 6 }} value={deviceId} onChange={(e) => setDeviceId(e.target.value)} />
            </div>
            <div>
              <label>Limit</label>
              <input style={{ width: "100%", padding: 10, marginTop: 6 }} type="number" value={limit} onChange={(e) => setLimit(Number(e.target.value) || 100)} />
            </div>
          </div>

          <div style={{ marginTop: 16, color: error ? "#dc2626" : "#64748b" }}>
            {error
              ? error
              : lastFetchAt
              ? `Última actualització: ${lastFetchAt.toLocaleString()}`
              : "Encara no s'han carregat dades."}
          </div>
        </Panel>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: 16, marginTop: 24 }}>
          <StatCard title="Device" value={latest?.deviceId ?? deviceId ?? "--"} Icon={Cpu} />
          <StatCard title="Última lectura" value={latest?.dateLabel ?? "--"} Icon={Database} />
          {statCards.map((card) => (
            <StatCard key={card.title} title={card.title} value={card.value} Icon={card.icon} />
          ))}
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(420px, 1fr))", gap: 16, marginTop: 24 }}>
          <Panel title="Temperatura i humitat aire">
            <div style={{ height: 320 }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={rows}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="timeLabel" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Line type="monotone" dataKey="tempC" name="Temp °C" dot={false} />
                  <Line type="monotone" dataKey="humAir" name="Hum %" dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </Panel>

          <Panel title="Humitat sòl">
            <div style={{ height: 320 }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={rows}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="timeLabel" />
                  <YAxis domain={[0, 100]} />
                  <Tooltip />
                  <Legend />
                  <Line type="monotone" dataKey="soilPercent" name="Soil %" dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </Panel>
        </div>

        <div style={{ marginTop: 24 }}>
          <Panel title="Últimes lectures">
            {rows.length === 0 ? (
              <p>No hi ha dades.</p>
            ) : (
              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse" }}>
                  <thead>
                    <tr>
                      <th style={{ textAlign: "left", padding: 8 }}>Hora</th>
                      <th style={{ textAlign: "left", padding: 8 }}>Temp</th>
                      <th style={{ textAlign: "left", padding: 8 }}>Hum air</th>
                      <th style={{ textAlign: "left", padding: 8 }}>Soil %</th>
                      <th style={{ textAlign: "left", padding: 8 }}>LDR</th>
                      <th style={{ textAlign: "left", padding: 8 }}>Pluja</th>
                      <th style={{ textAlign: "left", padding: 8 }}>RSSI</th>
                    </tr>
                  </thead>
                  <tbody>
                    {[...rows].reverse().slice(0, 15).map((row) => (
                      <tr key={row.id} style={{ borderTop: "1px solid #e2e8f0" }}>
                        <td style={{ padding: 8 }}>{row.dateLabel}</td>
                        <td style={{ padding: 8 }}>{row.tempC ?? "--"}</td>
                        <td style={{ padding: 8 }}>{row.humAir ?? "--"}</td>
                        <td style={{ padding: 8 }}>{row.soilPercent ?? "--"}</td>
                        <td style={{ padding: 8 }}>{row.ldrRaw ?? "--"}</td>
                        <td style={{ padding: 8 }}>{row.rain ?? "--"}</td>
                        <td style={{ padding: 8 }}>{row.rssi ?? "--"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Panel>
        </div>
      </div>
    </div>
  );
}