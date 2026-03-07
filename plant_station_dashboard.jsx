import React, { useEffect, useMemo, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { RefreshCw, Thermometer, Droplets, Sun, CloudRain, Wifi } from "lucide-react";
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

export default function PlantStationDashboard() {
  const [baseUrl, setBaseUrl] = useState("https://plant-postgres-1.onrender.com");
  const [apiKey, setApiKey] = useState("");
  const [deviceId, setDeviceId] = useState("esp32-plant-01");
  const [limit, setLimit] = useState(100);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [rows, setRows] = useState([]);

  const headers = useMemo(() => {
    const h = {};
    if (apiKey.trim()) h["X-Api-Key"] = apiKey.trim();
    return h;
  }, [apiKey]);

  const fetchData = async () => {
    setLoading(true);
    setError("");
    try {
      const url = `${baseUrl.replace(/\/$/, "")}/api/v1/readings?deviceId=${encodeURIComponent(deviceId)}&limit=${limit}`;
      const res = await fetch(url, { headers });
      if (!res.ok) {
        const text = await res.text();
        throw new Error(`HTTP ${res.status}: ${text}`);
      }
      const data = await res.json();
      const normalized = [...data]
        .reverse()
        .map((r) => ({
          ...r,
          timeLabel: new Date(r.ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }),
          dateLabel: new Date(r.ts).toLocaleString(),
        }));
      setRows(normalized);
    } catch (e) {
      setError(e.message || "Error carregant dades");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const latest = rows.length ? rows[rows.length - 1] : null;

  const statCards = [
    {
      title: "Temperatura",
      value: latest?.tempC != null ? `${latest.tempC.toFixed(1)} °C` : "--",
      icon: Thermometer,
    },
    {
      title: "Humitat aire",
      value: latest?.humAir != null ? `${Math.round(latest.humAir)} %` : "--",
      icon: Droplets,
    },
    {
      title: "Humitat sòl",
      value: latest?.soilPercent != null ? `${latest.soilPercent} %` : "--",
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
    <div className="min-h-screen bg-slate-50 p-6">
      <div className="mx-auto max-w-7xl space-y-6">
        <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Plant Station Dashboard</h1>
            <p className="text-sm text-slate-600">Visualització de lectures guardades a la teva API.</p>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="secondary">{rows.length} lectures</Badge>
            <Button onClick={fetchData} disabled={loading} className="gap-2">
              <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
              Actualitzar
            </Button>
          </div>
        </div>

        <Card className="rounded-2xl shadow-sm">
          <CardHeader>
            <CardTitle>Configuració</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-3 md:grid-cols-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">Base URL</label>
                <Input value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} placeholder="https://...onrender.com" />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">API Key</label>
                <Input value={apiKey} onChange={(e) => setApiKey(e.target.value)} placeholder="X-Api-Key" type="password" />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">deviceId</label>
                <Input value={deviceId} onChange={(e) => setDeviceId(e.target.value)} placeholder="esp32-plant-01" />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Límit lectures</label>
                <Input value={limit} onChange={(e) => setLimit(Number(e.target.value) || 100)} type="number" min={1} max={2000} />
              </div>
            </div>
            <div className="mt-4">
              <Button onClick={fetchData}>Carregar dades</Button>
            </div>
            {error ? <p className="mt-3 text-sm text-red-600">{error}</p> : null}
          </CardContent>
        </Card>

        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {statCards.map((card) => {
            const Icon = card.icon;
            return (
              <Card key={card.title} className="rounded-2xl shadow-sm">
                <CardContent className="flex items-center justify-between p-6">
                  <div>
                    <p className="text-sm text-slate-500">{card.title}</p>
                    <p className="mt-1 text-2xl font-semibold">{card.value}</p>
                  </div>
                  <div className="rounded-2xl bg-slate-100 p-3">
                    <Icon className="h-5 w-5 text-slate-700" />
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>

        <div className="grid gap-6 xl:grid-cols-2">
          <Card className="rounded-2xl shadow-sm">
            <CardHeader>
              <CardTitle>Temperatura i humitat aire</CardTitle>
            </CardHeader>
            <CardContent className="h-[340px]">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={rows}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="timeLabel" minTickGap={24} />
                  <YAxis />
                  <Tooltip labelFormatter={(_, payload) => payload?.[0]?.payload?.dateLabel ?? ""} />
                  <Legend />
                  <Line type="monotone" dataKey="tempC" name="Temp °C" strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="humAir" name="Hum %" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          <Card className="rounded-2xl shadow-sm">
            <CardHeader>
              <CardTitle>Humitat sòl</CardTitle>
            </CardHeader>
            <CardContent className="h-[340px]">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={rows}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="timeLabel" minTickGap={24} />
                  <YAxis domain={[0, 100]} />
                  <Tooltip labelFormatter={(_, payload) => payload?.[0]?.payload?.dateLabel ?? ""} />
                  <Legend />
                  <Line type="monotone" dataKey="soilPercent" name="Soil %" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          <Card className="rounded-2xl shadow-sm xl:col-span-2">
            <CardHeader>
              <CardTitle>Llum i qualitat WiFi</CardTitle>
            </CardHeader>
            <CardContent className="h-[340px]">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={rows}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="timeLabel" minTickGap={24} />
                  <YAxis yAxisId="left" />
                  <YAxis yAxisId="right" orientation="right" />
                  <Tooltip labelFormatter={(_, payload) => payload?.[0]?.payload?.dateLabel ?? ""} />
                  <Legend />
                  <Line yAxisId="left" type="monotone" dataKey="ldrRaw" name="LDR raw" strokeWidth={2} dot={false} />
                  <Line yAxisId="right" type="monotone" dataKey="rssi" name="RSSI" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </div>

        <Card className="rounded-2xl shadow-sm">
          <CardHeader>
            <CardTitle>Últimes lectures</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-slate-500">
                    <th className="px-3 py-2">Hora</th>
                    <th className="px-3 py-2">Temp</th>
                    <th className="px-3 py-2">Hum air</th>
                    <th className="px-3 py-2">Soil %</th>
                    <th className="px-3 py-2">LDR</th>
                    <th className="px-3 py-2">Pluja</th>
                    <th className="px-3 py-2">RSSI</th>
                  </tr>
                </thead>
                <tbody>
                  {[...rows].reverse().slice(0, 15).map((row) => (
                    <tr key={row.id} className="border-b last:border-0">
                      <td className="px-3 py-2">{row.dateLabel}</td>
                      <td className="px-3 py-2">{row.tempC ?? "--"}</td>
                      <td className="px-3 py-2">{row.humAir ?? "--"}</td>
                      <td className="px-3 py-2">{row.soilPercent ?? "--"}</td>
                      <td className="px-3 py-2">{row.ldrRaw ?? "--"}</td>
                      <td className="px-3 py-2">{row.rain ?? "--"}</td>
                      <td className="px-3 py-2">{row.rssi ?? "--"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
