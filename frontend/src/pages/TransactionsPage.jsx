import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  History, 
  Search, 
  Filter, 
  ChevronLeft, 
  ChevronRight, 
  RefreshCw, 
  ExternalLink,
  ShieldCheck,
  AlertCircle
} from 'lucide-react';
import { listTransactions } from '../api/transactions';
import DecisionBadge from '../components/common/DecisionBadge';
import { useAuth } from '../context/AuthContext';

export default function TransactionsPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [transactions, setTransactions] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filters and pagination state
  const [type, setType] = useState('');
  const [decision, setDecision] = useState('');
  const [minRisk, setMinRisk] = useState('');
  const [maxRisk, setMaxRisk] = useState('');
  const [page, setPage] = useState(0);
  const pageSize = 15;

  const fetchTransactions = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const params = {
        limit: pageSize,
        offset: page * pageSize,
        type: type || undefined,
        decision: decision || undefined,
        min_risk: minRisk !== '' ? parseFloat(minRisk) : undefined,
        max_risk: maxRisk !== '' ? parseFloat(maxRisk) : undefined,
      };

      const res = await listTransactions(params);
      setTransactions(res.items || []);
      setTotal(res.total || 0);
    } catch (err) {
      console.error('Failed to list transactions:', err);
      setError(err.message || 'Failed to retrieve transactions.');
    } finally {
      setLoading(false);
    }
  }, [page, type, decision, minRisk, maxRisk]);

  useEffect(() => {
    fetchTransactions();
  }, [fetchTransactions]);

  const handleApplyFilter = (e) => {
    e.preventDefault();
    setPage(0);
    fetchTransactions();
  };

  const handleClearFilter = () => {
    setType('');
    setDecision('');
    setMinRisk('');
    setMaxRisk('');
    setPage(0);
  };

  const totalPages = Math.ceil(total / pageSize);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2.5">
            <History className="w-6 h-6 text-primary-400" />
            Transaction Ledger & Telemetry
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Real-time inference history and risk assessments.
            {user?.role === 'USER' && (
              <span className="text-amber-400 ml-1">(Scoped View: Displaying transactions associated with your account)</span>
            )}
          </p>
        </div>

        <button
          onClick={fetchTransactions}
          disabled={loading}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-900 border border-slate-800 rounded-lg text-xs font-medium text-slate-300 hover:text-white hover:bg-slate-800 transition"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-primary-400' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Filter Bar */}
      <form onSubmit={handleApplyFilter} className="bg-slate-900/70 border border-slate-800 rounded-xl p-4 shadow-md flex flex-wrap items-end gap-3">
        <div className="flex-1 min-w-[140px]">
          <label className="block text-[11px] font-medium text-slate-400 uppercase tracking-wider mb-1">Type</label>
          <select
            value={type}
            onChange={(e) => { setType(e.target.value); setPage(0); }}
            className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-white focus:border-primary-500 focus:outline-none"
          >
            <option value="">All Types</option>
            <option value="TRANSFER">TRANSFER</option>
            <option value="CASH_OUT">CASH_OUT</option>
            <option value="PAYMENT">PAYMENT</option>
            <option value="CASH_IN">CASH_IN</option>
            <option value="DEBIT">DEBIT</option>
          </select>
        </div>

        <div className="flex-1 min-w-[140px]">
          <label className="block text-[11px] font-medium text-slate-400 uppercase tracking-wider mb-1">Decision</label>
          <select
            value={decision}
            onChange={(e) => { setDecision(e.target.value); setPage(0); }}
            className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-white focus:border-primary-500 focus:outline-none"
          >
            <option value="">All Decisions</option>
            <option value="APPROVE">APPROVE (&lt; 40)</option>
            <option value="REVIEW">REVIEW (40–69)</option>
            <option value="BLOCK">BLOCK (&ge; 70)</option>
          </select>
        </div>

        <div className="w-24">
          <label className="block text-[11px] font-medium text-slate-400 uppercase tracking-wider mb-1">Min Score</label>
          <input
            type="number"
            min="0"
            max="100"
            placeholder="0"
            value={minRisk}
            onChange={(e) => setMinRisk(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-white focus:border-primary-500 focus:outline-none font-mono"
          />
        </div>

        <div className="w-24">
          <label className="block text-[11px] font-medium text-slate-400 uppercase tracking-wider mb-1">Max Score</label>
          <input
            type="number"
            min="0"
            max="100"
            placeholder="100"
            value={maxRisk}
            onChange={(e) => setMaxRisk(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-white focus:border-primary-500 focus:outline-none font-mono"
          />
        </div>

        <div className="flex items-center gap-2">
          <button
            type="submit"
            className="px-3.5 py-1.5 bg-primary-600 hover:bg-primary-500 text-white text-xs font-medium rounded-lg transition"
          >
            Apply
          </button>
          <button
            type="button"
            onClick={handleClearFilter}
            className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium rounded-lg transition"
          >
            Reset
          </button>
        </div>
      </form>

      {/* Error state */}
      {error && (
        <div className="p-4 rounded-lg bg-red-900/20 border border-red-500/30 text-red-300 text-xs flex items-center justify-between">
          <span>{error}</span>
          <button onClick={fetchTransactions} className="underline">Retry</button>
        </div>
      )}

      {/* Table & Content */}
      <div className="bg-slate-900/70 border border-slate-800 rounded-xl overflow-hidden shadow-lg">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-slate-950/80 text-slate-400 font-medium border-b border-slate-800 uppercase tracking-wider">
              <tr>
                <th className="py-3 px-4">Timestamp</th>
                <th className="py-3 px-4">Tx ID</th>
                <th className="py-3 px-4">Type</th>
                <th className="py-3 px-4">Amount</th>
                <th className="py-3 px-4">Origin &rarr; Dest</th>
                <th className="py-3 px-4">Risk Score</th>
                <th className="py-3 px-4">Decision</th>
                <th className="py-3 px-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono">
              {loading ? (
                <tr>
                  <td colSpan="8" className="py-12 text-center text-slate-500 font-sans text-xs">
                    <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2 text-primary-400" />
                    Fetching transactions from PostgreSQL ledger...
                  </td>
                </tr>
              ) : transactions.length === 0 ? (
                <tr>
                  <td colSpan="8" className="py-12 text-center text-slate-500 font-sans text-xs">
                    No transactions found matching current filters.
                  </td>
                </tr>
              ) : (
                transactions.map((tx) => (
                  <tr key={tx.id} className="hover:bg-slate-800/40 transition">
                    <td className="py-3 px-4 text-slate-400 font-sans text-[11px] whitespace-nowrap">
                      {tx.timestamp ? new Date(tx.timestamp).toLocaleString() : 'N/A'}
                    </td>
                    <td 
                      className="py-3 px-4 text-primary-400 hover:underline cursor-pointer font-medium"
                      onClick={() => navigate(`/transactions/${tx.id}`)}
                    >
                      {tx.tx_id || tx.id}
                    </td>
                    <td className="py-3 px-4 font-sans font-medium text-white">{tx.type}</td>
                    <td className="py-3 px-4 font-bold text-slate-100">
                      ${Number(tx.amount).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                    </td>
                    <td className="py-3 px-4 text-slate-400 text-[11px]">
                      <span>{tx.name_orig || 'N/A'}</span>
                      <span className="text-slate-600 mx-1">&rarr;</span>
                      <span>{tx.name_dest || 'N/A'}</span>
                    </td>
                    <td className="py-3 px-4 font-bold">
                      {tx.risk_score !== undefined && tx.risk_score !== null ? (
                        <span className={tx.risk_score >= 70 ? 'text-rose-400' : tx.risk_score >= 40 ? 'text-amber-400' : 'text-emerald-400'}>
                          {Number(tx.risk_score).toFixed(1)}
                        </span>
                      ) : (
                        <span className="text-slate-500 font-sans text-[11px]">Non-evaluated</span>
                      )}
                    </td>
                    <td className="py-3 px-4">
                      <DecisionBadge decision={tx.decision} />
                    </td>
                    <td className="py-3 px-4 text-right">
                      <button
                        onClick={() => navigate(`/transactions/${tx.id}`)}
                        className="inline-flex items-center gap-1 text-[11px] font-sans text-slate-300 hover:text-white px-2.5 py-1 bg-slate-800 hover:bg-slate-700 rounded transition"
                      >
                        Inspect <ExternalLink className="w-3 h-3 text-slate-400" />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Server-Side Pagination Footer */}
        <div className="p-3.5 bg-slate-950/70 border-t border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-slate-400">
          <div>
            Showing <span className="font-semibold text-slate-200">{transactions.length > 0 ? page * pageSize + 1 : 0}</span> to{' '}
            <span className="font-semibold text-slate-200">{Math.min((page + 1) * pageSize, total)}</span> of{' '}
            <span className="font-semibold text-slate-200">{total}</span> total transactions
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={page === 0 || loading}
              className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 disabled:opacity-40 disabled:cursor-not-allowed text-white flex items-center gap-1 transition"
            >
              <ChevronLeft className="w-3.5 h-3.5" /> Previous
            </button>
            <span className="px-2 font-mono text-[11px] text-slate-300">
              Page {page + 1} of {totalPages || 1}
            </span>
            <button
              onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
              disabled={page >= totalPages - 1 || loading}
              className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 disabled:opacity-40 disabled:cursor-not-allowed text-white flex items-center gap-1 transition"
            >
              Next <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
