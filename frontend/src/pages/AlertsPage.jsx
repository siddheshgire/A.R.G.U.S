import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  AlertTriangle, 
  Search, 
  Filter, 
  CheckCircle2, 
  Clock, 
  ShieldAlert, 
  ExternalLink, 
  RefreshCw,
  X,
  FileEdit,
  UserCheck
} from 'lucide-react';
import { listAlerts, updateAlert } from '../api/alerts';
import { useAuth } from '../context/AuthContext';

export default function AlertsPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filter state
  const [status, setStatus] = useState('');
  const [severity, setSeverity] = useState('');

  // Triage modal state
  const [selectedAlert, setSelectedAlert] = useState(null);
  const [modalStatus, setModalStatus] = useState('IN_REVIEW');
  const [modalNotes, setModalNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [modalError, setModalError] = useState(null);

  const canTriage = user?.role === 'ANALYST' || user?.role === 'ADMIN';

  const fetchAlerts = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const params = {
        status: status || undefined,
        severity: severity || undefined,
        limit: 50,
      };
      const res = await listAlerts(params);
      setAlerts(res.items || []);
    } catch (err) {
      console.error('Failed to load alerts:', err);
      setError(err.message || 'Failed to retrieve fraud alert queue.');
    } finally {
      setLoading(false);
    }
  }, [status, severity]);

  useEffect(() => {
    fetchAlerts();
  }, [fetchAlerts]);

  const handleOpenTriage = (alert) => {
    setSelectedAlert(alert);
    setModalStatus(alert.status || 'IN_REVIEW');
    setModalNotes(alert.resolution_notes || '');
    setModalError(null);
  };

  const handleCloseTriage = () => {
    setSelectedAlert(null);
    setModalNotes('');
    setModalError(null);
  };

  const handleSubmitTriage = async (e) => {
    e.preventDefault();
    if (!selectedAlert) return;

    try {
      setSubmitting(true);
      setModalError(null);
      await updateAlert(selectedAlert.id, {
        status: modalStatus,
        notes: modalNotes,
      });
      handleCloseTriage();
      fetchAlerts();
    } catch (err) {
      console.error('Failed to update alert:', err);
      setModalError(err.message || 'Failed to save triage update.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2.5">
            <AlertTriangle className="w-6 h-6 text-amber-400" />
            Fraud Alert Review & Disposition Queue
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Suspicious transaction triage queue. Alerts flagged by policy engine or model ensemble anomalies.
          </p>
        </div>

        <button
          onClick={fetchAlerts}
          disabled={loading}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-900 border border-slate-800 rounded-lg text-xs font-medium text-slate-300 hover:text-white hover:bg-slate-800 transition"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-primary-400' : ''}`} />
          Refresh Queue
        </button>
      </div>

      {/* Filter controls */}
      <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-4 shadow-md flex flex-wrap items-center gap-4">
        <div className="w-44">
          <label className="block text-[11px] font-medium text-slate-400 uppercase tracking-wider mb-1">Status</label>
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-white focus:border-primary-500 focus:outline-none"
          >
            <option value="">All Statuses</option>
            <option value="PENDING">PENDING</option>
            <option value="IN_REVIEW">IN_REVIEW</option>
            <option value="RESOLVED">RESOLVED</option>
          </select>
        </div>

        <div className="w-44">
          <label className="block text-[11px] font-medium text-slate-400 uppercase tracking-wider mb-1">Severity</label>
          <select
            value={severity}
            onChange={(e) => setSeverity(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-white focus:border-primary-500 focus:outline-none"
          >
            <option value="">All Severities</option>
            <option value="CRITICAL">CRITICAL</option>
            <option value="HIGH">HIGH</option>
            <option value="MEDIUM">MEDIUM</option>
            <option value="LOW">LOW</option>
          </select>
        </div>

        <div className="ml-auto text-xs text-slate-400">
          Showing <span className="font-bold text-slate-200">{alerts.length}</span> active alert cases
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-lg bg-red-900/20 border border-red-500/30 text-red-300 text-xs flex items-center justify-between">
          <span>{error}</span>
          <button onClick={fetchAlerts} className="underline">Retry</button>
        </div>
      )}

      {/* Alerts Table */}
      <div className="bg-slate-900/70 border border-slate-800 rounded-xl overflow-hidden shadow-lg">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-slate-950/80 text-slate-400 font-medium border-b border-slate-800 uppercase tracking-wider">
              <tr>
                <th className="py-3 px-4">Alert ID</th>
                <th className="py-3 px-4">Timestamp</th>
                <th className="py-3 px-4">Severity</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Transaction ID</th>
                <th className="py-3 px-4">Notes / Rationale</th>
                <th className="py-3 px-4 text-right">Triage</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono">
              {loading ? (
                <tr>
                  <td colSpan="7" className="py-12 text-center text-slate-500 font-sans text-xs">
                    <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2 text-primary-400" />
                    Querying fraud review queue...
                  </td>
                </tr>
              ) : alerts.length === 0 ? (
                <tr>
                  <td colSpan="7" className="py-12 text-center text-slate-500 font-sans text-xs">
                    No alerts in this queue. All suspicious patterns triaged.
                  </td>
                </tr>
              ) : (
                alerts.map((alt) => (
                  <tr key={alt.id} className="hover:bg-slate-800/40 transition">
                    <td className="py-3 px-4 text-slate-400 font-medium">#{alt.id}</td>
                    <td className="py-3 px-4 text-slate-400 font-sans text-[11px] whitespace-nowrap">
                      {alt.created_at ? new Date(alt.created_at).toLocaleString() : 'N/A'}
                    </td>
                    <td className="py-3 px-4 font-sans">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold ${
                        alt.severity === 'CRITICAL' ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40' :
                        alt.severity === 'HIGH' ? 'bg-orange-500/20 text-orange-300 border border-orange-500/40' :
                        alt.severity === 'MEDIUM' ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40' :
                        'bg-blue-500/20 text-blue-300 border border-blue-500/40'
                      }`}>
                        {alt.severity}
                      </span>
                    </td>
                    <td className="py-3 px-4 font-sans">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold ${
                        alt.status === 'RESOLVED' ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40' :
                        alt.status === 'IN_REVIEW' ? 'bg-blue-500/20 text-blue-300 border border-blue-500/40' :
                        'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                      }`}>
                        {alt.status}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      {alt.transaction_id ? (
                        <button
                          onClick={() => navigate(`/transactions/${alt.transaction_id}`)}
                          className="text-primary-400 hover:underline inline-flex items-center gap-1"
                        >
                          Tx #{alt.transaction_id} <ExternalLink className="w-3 h-3" />
                        </button>
                      ) : (
                        <span className="text-slate-500">None</span>
                      )}
                    </td>
                    <td className="py-3 px-4 font-sans text-slate-400 text-xs max-w-xs truncate">
                      {alt.resolution_notes || alt.message || 'Awaiting investigation'}
                    </td>
                    <td className="py-3 px-4 text-right font-sans">
                      {canTriage ? (
                        <button
                          onClick={() => handleOpenTriage(alt)}
                          className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 text-[11px] font-medium rounded transition inline-flex items-center gap-1"
                        >
                          <FileEdit className="w-3 h-3 text-primary-400" /> Triage
                        </button>
                      ) : (
                        <span className="text-slate-500 text-[11px]">Read-Only</span>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Triage Modal */}
      {selectedAlert && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <UserCheck className="w-5 h-5 text-primary-400" />
                Disposition Alert #{selectedAlert.id}
              </h3>
              <button
                onClick={handleCloseTriage}
                className="text-slate-400 hover:text-white transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {modalError && (
              <div className="p-3 bg-red-900/20 border border-red-500/30 rounded text-red-300 text-xs">
                {modalError}
              </div>
            )}

            <form onSubmit={handleSubmitTriage} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Investigation Disposition Status
                </label>
                <select
                  value={modalStatus}
                  onChange={(e) => setModalStatus(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white focus:border-primary-500 focus:outline-none"
                >
                  <option value="PENDING">PENDING — Unreviewed</option>
                  <option value="IN_REVIEW">IN_REVIEW — Under Active Analyst Investigation</option>
                  <option value="RESOLVED">RESOLVED — Investigation Closed / Disposed</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Investigator Notes & Disposition Rationale
                </label>
                <textarea
                  rows={4}
                  required
                  value={modalNotes}
                  onChange={(e) => setModalNotes(e.target.value)}
                  placeholder="Record forensic observations, customer verification result, or false positive rationale..."
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-3 text-xs text-white focus:border-primary-500 focus:outline-none"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-800">
                <button
                  type="button"
                  onClick={handleCloseTriage}
                  className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium rounded-lg transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-1.5 bg-primary-600 hover:bg-primary-500 disabled:opacity-50 text-white text-xs font-semibold rounded-lg transition flex items-center gap-1.5"
                >
                  {submitting && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                  Submit Disposition
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
