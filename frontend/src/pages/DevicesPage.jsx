import React, { useState, useEffect, useCallback } from 'react';
import { 
  Cpu, 
  ShieldCheck, 
  ShieldAlert, 
  Thermometer, 
  RefreshCw, 
  AlertOctagon, 
  RotateCcw,
  CheckCircle2,
  Clock,
  Wifi,
  WifiOff
} from 'lucide-react';
import { listDevices, resetDeviceTamper } from '../api/devices';
import { useAuth } from '../context/AuthContext';

export default function DevicesPage() {
  const { user } = useAuth();
  const [devices, setDevices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [resettingId, setResettingId] = useState(null);
  const [actionMessage, setActionMessage] = useState(null);

  const isAdmin = user?.role === 'ADMIN';

  const fetchDevices = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await listDevices({ limit: 50 });
      setDevices(res.items || []);
    } catch (err) {
      console.error('Failed to load edge terminals:', err);
      setError(err.message || 'Failed to retrieve IoT device registry.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDevices();
  }, [fetchDevices]);

  const handleResetTamper = async (deviceId) => {
    if (!window.confirm(`Are you sure you want to reset hardware tamper lockdown for terminal #${deviceId}?`)) {
      return;
    }

    try {
      setResettingId(deviceId);
      setActionMessage(null);
      const res = await resetDeviceTamper(deviceId);
      setActionMessage({ type: 'success', text: res.message || 'Tamper state reset successfully.' });
      fetchDevices();
    } catch (err) {
      console.error('Failed to reset device tamper:', err);
      setActionMessage({ type: 'error', text: err.message || 'Failed to reset device tamper.' });
    } finally {
      setResettingId(null);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2.5">
            <Cpu className="w-6 h-6 text-primary-400" />
            IoT Terminal Fleet Telemetry & Edge Security
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Real-time edge terminal status, hardware tamper states, and SoC temperature monitoring.
          </p>
        </div>

        <button
          onClick={fetchDevices}
          disabled={loading}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-900 border border-slate-800 rounded-lg text-xs font-medium text-slate-300 hover:text-white hover:bg-slate-800 transition"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-primary-400' : ''}`} />
          Refresh Fleet
        </button>
      </div>

      {actionMessage && (
        <div className={`p-4 rounded-lg text-xs flex items-center justify-between ${
          actionMessage.type === 'success' 
            ? 'bg-emerald-900/20 border border-emerald-500/30 text-emerald-300' 
            : 'bg-red-900/20 border border-red-500/30 text-red-300'
        }`}>
          <span>{actionMessage.text}</span>
          <button onClick={() => setActionMessage(null)} className="underline ml-4">Dismiss</button>
        </div>
      )}

      {error && (
        <div className="p-4 rounded-lg bg-red-900/20 border border-red-500/30 text-red-300 text-xs flex items-center justify-between">
          <span>{error}</span>
          <button onClick={fetchDevices} className="underline">Retry</button>
        </div>
      )}

      {/* Terminals Table */}
      <div className="bg-slate-900/70 border border-slate-800 rounded-xl overflow-hidden shadow-lg">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-slate-950/80 text-slate-400 font-medium border-b border-slate-800 uppercase tracking-wider">
              <tr>
                <th className="py-3 px-4">Terminal ID</th>
                <th className="py-3 px-4">Label / Location</th>
                <th className="py-3 px-4">Device Status</th>
                <th className="py-3 px-4">Tamper Status</th>
                <th className="py-3 px-4">SoC Temp</th>
                <th className="py-3 px-4">Firmware</th>
                <th className="py-3 px-4">Last Heartbeat</th>
                <th className="py-3 px-4 text-right">Security Control</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono">
              {loading ? (
                <tr>
                  <td colSpan="8" className="py-12 text-center text-slate-500 font-sans text-xs">
                    <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2 text-primary-400" />
                    Querying IoT terminal fleet registry...
                  </td>
                </tr>
              ) : devices.length === 0 ? (
                <tr>
                  <td colSpan="8" className="py-12 text-center text-slate-500 font-sans text-xs">
                    <div className="max-w-md mx-auto space-y-2">
                      <p className="font-semibold text-slate-400">No edge terminals registered.</p>
                      <p className="text-slate-500 text-[11px]">
                        To register an ESP32 edge terminal, provision a device via admin or execute the hardware simulator in <code className="text-slate-400 bg-slate-950 px-1 py-0.5 rounded">edge/simulator.py</code>.
                      </p>
                    </div>
                  </td>
                </tr>
              ) : (
                devices.map((dev) => {
                  const isTampered = dev.is_tampered || dev.status === 'TAMPERED';
                  const isActive = dev.status === 'ACTIVE';

                  return (
                    <tr key={dev.id} className="hover:bg-slate-800/40 transition">
                      <td className="py-3 px-4 text-primary-400 font-bold">
                        {dev.terminal_id || `TERM-${dev.id}`}
                      </td>
                      <td className="py-3 px-4 font-sans text-slate-300">
                        {dev.label || dev.description || 'Edge POS Terminal'}
                      </td>
                      <td className="py-3 px-4 font-sans">
                        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold ${
                          isActive 
                            ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40' 
                            : 'bg-slate-800 text-slate-400 border border-slate-700'
                        }`}>
                          {isActive ? <Wifi className="w-3 h-3 text-emerald-400" /> : <WifiOff className="w-3 h-3 text-slate-400" />}
                          {dev.status}
                        </span>
                      </td>
                      <td className="py-3 px-4 font-sans">
                        {isTampered ? (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold bg-rose-500/20 text-rose-300 border border-rose-500/40 animate-pulse">
                            <AlertOctagon className="w-3 h-3 text-rose-400" />
                            TAMPER LOCKDOWN
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                            <ShieldCheck className="w-3 h-3 text-emerald-400" />
                            SECURE
                          </span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-slate-300">
                        {dev.soc_temperature !== undefined && dev.soc_temperature !== null ? (
                          <span className="flex items-center gap-1">
                            <Thermometer className="w-3.5 h-3.5 text-slate-400" />
                            {Number(dev.soc_temperature).toFixed(1)} &deg;C
                          </span>
                        ) : (
                          <span className="text-slate-500">--</span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-slate-400 text-[11px]">
                        {dev.firmware_version || 'v1.0.0-esp32'}
                      </td>
                      <td className="py-3 px-4 text-slate-400 font-sans text-[11px] whitespace-nowrap">
                        {dev.last_heartbeat ? new Date(dev.last_heartbeat).toLocaleTimeString() : 'N/A'}
                      </td>
                      <td className="py-3 px-4 text-right font-sans">
                        {isAdmin ? (
                          <button
                            onClick={() => handleResetTamper(dev.id)}
                            disabled={resettingId === dev.id}
                            className={`px-2.5 py-1 text-[11px] font-medium rounded transition inline-flex items-center gap-1 ${
                              isTampered 
                                ? 'bg-rose-600 hover:bg-rose-500 text-white' 
                                : 'bg-slate-800 hover:bg-slate-700 text-slate-300'
                            }`}
                          >
                            <RotateCcw className={`w-3 h-3 ${resettingId === dev.id ? 'animate-spin' : ''}`} />
                            Reset Tamper
                          </button>
                        ) : (
                          <span className="text-slate-500 text-[11px]">Admin Only</span>
                        )}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
