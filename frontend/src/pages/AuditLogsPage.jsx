import React, { useState, useEffect, useCallback } from 'react';
import { 
  FileText, 
  Search, 
  Filter, 
  RefreshCw, 
  Shield, 
  ChevronLeft, 
  ChevronRight,
  Code,
  X
} from 'lucide-react';
import { getAuditLogs } from '../api/admin';

export default function AuditLogsPage() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [eventType, setEventType] = useState('');
  const [page, setPage] = useState(0);
  const [selectedMeta, setSelectedMeta] = useState(null);
  const pageSize = 20;

  const fetchLogs = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const params = {
        limit: pageSize,
        offset: page * pageSize,
        event_type: eventType || undefined,
      };
      const res = await getAuditLogs(params);
      setLogs(res.items || []);
    } catch (err) {
      console.error('Failed to load audit logs:', err);
      setError(err.message || 'Failed to retrieve security event history.');
    } finally {
      setLoading(false);
    }
  }, [page, eventType]);

  useEffect(() => {
    fetchLogs();
  }, [fetchLogs]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2.5">
            <Shield className="w-6 h-6 text-primary-400" />
            Audit Log Explorer — Security Event History
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Historical record of system access, transaction assessments, policy updates, and administrative overrides.
          </p>
        </div>

        <button
          onClick={fetchLogs}
          disabled={loading}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-900 border border-slate-800 rounded-lg text-xs font-medium text-slate-300 hover:text-white hover:bg-slate-800 transition"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-primary-400' : ''}`} />
          Refresh Logs
        </button>
      </div>

      {/* Filter */}
      <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-4 shadow-md flex items-center gap-4">
        <div className="w-64">
          <label className="block text-[11px] font-medium text-slate-400 uppercase tracking-wider mb-1">Event Filter</label>
          <input
            type="text"
            placeholder="e.g. LOGIN, ASSESSMENT, TAMPER"
            value={eventType}
            onChange={(e) => { setEventType(e.target.value); setPage(0); }}
            className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-white focus:border-primary-500 focus:outline-none"
          />
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-lg bg-red-900/20 border border-red-500/30 text-red-300 text-xs flex items-center justify-between">
          <span>{error}</span>
          <button onClick={fetchLogs} className="underline">Retry</button>
        </div>
      )}

      {/* Logs Table */}
      <div className="bg-slate-900/70 border border-slate-800 rounded-xl overflow-hidden shadow-lg">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-slate-950/80 text-slate-400 font-medium border-b border-slate-800 uppercase tracking-wider">
              <tr>
                <th className="py-3 px-4">Timestamp</th>
                <th className="py-3 px-4">Event Type</th>
                <th className="py-3 px-4">Actor</th>
                <th className="py-3 px-4">Action</th>
                <th className="py-3 px-4">Target Resource</th>
                <th className="py-3 px-4">Client IP</th>
                <th className="py-3 px-4 text-right">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono">
              {loading ? (
                <tr>
                  <td colSpan="7" className="py-12 text-center text-slate-500 font-sans text-xs">
                    <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2 text-primary-400" />
                    Querying audit event history...
                  </td>
                </tr>
              ) : logs.length === 0 ? (
                <tr>
                  <td colSpan="7" className="py-12 text-center text-slate-500 font-sans text-xs">
                    No security events recorded matching criteria.
                  </td>
                </tr>
              ) : (
                logs.map((log) => (
                  <tr key={log.id} className="hover:bg-slate-800/40 transition">
                    <td className="py-3 px-4 text-slate-400 font-sans text-[11px] whitespace-nowrap">
                      {log.timestamp ? new Date(log.timestamp).toLocaleString() : 'N/A'}
                    </td>
                    <td className="py-3 px-4">
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-primary-500/20 text-primary-300 border border-primary-500/30">
                        {log.event_type}
                      </span>
                    </td>
                    <td className="py-3 px-4 font-sans text-slate-300 font-medium">
                      {log.actor_username || (log.user_id ? `User #${log.user_id}` : 'System')}
                    </td>
                    <td className="py-3 px-4 font-sans text-slate-300">
                      {log.action || log.event_type}
                    </td>
                    <td className="py-3 px-4 text-slate-400 text-[11px]">
                      {log.resource || log.target || '--'}
                    </td>
                    <td className="py-3 px-4 text-slate-400 text-[11px]">
                      {log.ip_address || '127.0.0.1'}
                    </td>
                    <td className="py-3 px-4 text-right font-sans">
                      {log.metadata ? (
                        <button
                          onClick={() => setSelectedMeta(log)}
                          className="px-2 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 text-[11px] rounded transition inline-flex items-center gap-1"
                        >
                          <Code className="w-3 h-3 text-primary-400" /> View
                        </button>
                      ) : (
                        <span className="text-slate-600 text-[11px]">--</span>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        <div className="p-3.5 bg-slate-950/70 border-t border-slate-800 flex items-center justify-between text-xs text-slate-400">
          <div>Page {page + 1}</div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={page === 0 || loading}
              className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 disabled:opacity-40 disabled:cursor-not-allowed text-white flex items-center gap-1 transition"
            >
              <ChevronLeft className="w-3.5 h-3.5" /> Previous
            </button>
            <button
              onClick={() => setPage((p) => p + 1)}
              disabled={logs.length < pageSize || loading}
              className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 disabled:opacity-40 disabled:cursor-not-allowed text-white flex items-center gap-1 transition"
            >
              Next <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* Metadata Modal */}
      {selectedMeta && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-lg w-full p-5 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-sm font-bold text-white font-mono flex items-center gap-2">
                <Code className="w-4 h-4 text-primary-400" />
                Audit Metadata: {selectedMeta.event_type} (#{selectedMeta.id})
              </h3>
              <button
                onClick={() => setSelectedMeta(null)}
                className="text-slate-400 hover:text-white transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <pre className="bg-slate-950 p-4 rounded-lg text-xs font-mono text-emerald-400 overflow-x-auto max-h-96 border border-slate-800">
              {typeof selectedMeta.metadata === 'string'
                ? selectedMeta.metadata
                : JSON.stringify(selectedMeta.metadata, null, 2)}
            </pre>
            <div className="flex justify-end">
              <button
                onClick={() => setSelectedMeta(null)}
                className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium rounded-lg transition"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
