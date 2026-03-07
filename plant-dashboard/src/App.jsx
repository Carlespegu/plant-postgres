import React, { useEffect, useMemo, useState } from 'react';
import {
  CloudRain,
  Droplets,
  RefreshCw,
  Sun,
  Thermometer,
  Wifi,
  Sprout,
} from 'lucide-react';
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

function StatCard({ title, value, icon: Icon }) {
  return (
    <div className="card stat-card">
      <div>
        <div className="muted">{title}</div>
        <div className="stat-value">{value}</div>
      </div>
      <div className="icon-pill">
        <Icon size={20} />
      </div>
    </div>
  );
}

function ChartCard({ title, children }) {
  return (
    <div className="card chart-card">
      <div className="card-title">{title}</div>
      <div className="chart-wrap">{children}</div>
    </div>
  );
}

export default function App() {
  const [baseUrl, setBaseUrl] = useState('https://plant-postgres-1.onrender.com');
  const [apiKey, setApiKey] = useState('');
  const [deviceId, setDeviceId] = useState('esp32-plant-01');
  const [limit, setLimit] = useState(100);
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const headers = useMemo(() => {
    const h = {};
    if (apiKey.trim()) h['X-Api-Key'] = apiKey.trim();
    return h;
  }, [apiKey]);

  const fetchData = async () => {
    setLoading(true);
    setError('');
    try {
      const url = `${baseUrl.replace(/\/$/, '')}/api/v1/readings?deviceId=${encodeURIComponent(deviceId)}&limit=${limit}`;
      const response = await fetch(url, { headers });
      if (!response.ok) {
        const text = await response.text();
        throw new Error(`HTTP ${response.status}: ${text}`);
      }
      const data = await response.json();
      const normalized = [...data]
        .reverse()
        .map((item) => ({
          ...item,
          timeLabel: new Date(item.ts).toLocaleTimeString([], {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
          }),
          dateLabel: new Date(item.ts).toLocaleString(),
        }));
      setRows(normalized);
    } catch (err) {
      setError(err.message || 'Error carregant dades');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const latest = rows.length ? rows[rows.length - 1] : null;

  return (
    <div className="page">
      <div className="container">
        <div className="header-row">
          <div>
            <div className="title-row">
              <Sprout size={30} />
              <h1>Plant Station Dashboard</h1>
            </div>
            <p className="subtitle">Visualització de lectures guardades a la teva API.</p>
          </div>
          <div className="header-actions">
            <span className="badge">{rows.length} lectures</span>
            <button className="button primary" onClick={fetchData} disabled={loading}>
              <RefreshCw size={16} className={loading ? 'spin' : ''} />
              Actualitzar
            </button>
          </div>
        </div>

        <div className="card config-card">
          <div className="card-title">Configuració</div>
          <div className="config-grid">
            <label>
              <span>Base URL</span>
              <input value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} placeholder="https://...onrender.com" />
            </label>
            <label>
              <span>API Key</span>
              <input value={apiKey} onChange={(e) => setApiKey(e.target.value)} placeholder="X-Api-Key" type="password" />
            </label>
            <label>
              <span>deviceId</span>
              <input value={deviceId} onChange={(e) => setDeviceId(e.target.value)} placeholder="esp32-plant-01" />
            </label>
            <label>
              <span>Límit lectures</span>
              <input value={limit} onChange={(e) => setLimit(Number(e.target.value) || 100)} type="number" min={1} max={2000} />
            </label>
          </div>
          <div className="config-actions">
            <button className="button" onClick={fetchData} disabled={loading}>Carregar dades</button>
            {error ? <div className="error-text">{error}</div> : null}
          </div>
        </div>

        <div className="stats-grid">
          <StatCard title="Temperatura" value={latest?.tempC != null ? `${latest.tempC.toFixed(1)} °C` : '--'} icon={Thermometer} />
          <StatCard title="Humitat aire" value={latest?.humAir != null ? `${Math.round(latest.humAir)} %` : '--'} icon={Droplets} />
          <StatCard title="Humitat sòl" value={latest?.soilPercent != null ? `${latest.soilPercent} %` : '--'} icon={Droplets} />
          <StatCard title="Llum (raw)" value={latest?.ldrRaw != null ? `${latest.ldrRaw}` : '--'} icon={Sun} />
          <StatCard title="Pluja" value={latest?.rain ?? '--'} icon={CloudRain} />
          <StatCard title="RSSI" value={latest?.rssi != null ? `${latest.rssi} dBm` : '--'} icon={Wifi} />
        </div>

        <div className="charts-grid">
          <ChartCard title="Temperatura i humitat aire">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={rows}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="timeLabel" minTickGap={24} />
                <YAxis />
                <Tooltip labelFormatter={(_, payload) => payload?.[0]?.payload?.dateLabel ?? ''} />
                <Legend />
                <Line type="monotone" dataKey="tempC" name="Temp °C" stroke="#2563eb" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="humAir" name="Hum %" stroke="#16a34a" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </ChartCard>

          <ChartCard title="Humitat sòl">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={rows}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="timeLabel" minTickGap={24} />
                <YAxis domain={[0, 100]} />
                <Tooltip labelFormatter={(_, payload) => payload?.[0]?.payload?.dateLabel ?? ''} />
                <Legend />
                <Line type="monotone" dataKey="soilPercent" name="Soil %" stroke="#f59e0b" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </ChartCard>

          <ChartCard title="Llum i qualitat WiFi">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={rows}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="timeLabel" minTickGap={24} />
                <YAxis yAxisId="left" />
                <YAxis yAxisId="right" orientation="right" />
                <Tooltip labelFormatter={(_, payload) => payload?.[0]?.payload?.dateLabel ?? ''} />
                <Legend />
                <Line yAxisId="left" type="monotone" dataKey="ldrRaw" name="LDR raw" stroke="#7c3aed" strokeWidth={2} dot={false} />
                <Line yAxisId="right" type="monotone" dataKey="rssi" name="RSSI" stroke="#0f172a" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </ChartCard>
        </div>

        <div className="card table-card">
          <div className="card-title">Últimes lectures</div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Hora</th>
                  <th>Temp</th>
                  <th>Hum air</th>
                  <th>Soil %</th>
                  <th>LDR</th>
                  <th>Pluja</th>
                  <th>RSSI</th>
                </tr>
              </thead>
              <tbody>
                {[...rows].reverse().slice(0, 15).map((row) => (
                  <tr key={row.id}>
                    <td>{row.dateLabel}</td>
                    <td>{row.tempC ?? '--'}</td>
                    <td>{row.humAir ?? '--'}</td>
                    <td>{row.soilPercent ?? '--'}</td>
                    <td>{row.ldrRaw ?? '--'}</td>
                    <td>{row.rain ?? '--'}</td>
                    <td>{row.rssi ?? '--'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
