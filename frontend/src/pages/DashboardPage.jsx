import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Activity, 
  ShieldAlert, 
  AlertTriangle, 
  Cpu, 
  TrendingUp, 
  RefreshCw, 
  ArrowRight,
  ShieldCheck,
  CheckCircle2,
  Clock
} from 'lucide-react';
import { getDashboardMetrics } from '../api/analytics';
import MetricCard from '../components/common/MetricCard';
import DecisionBadge from '../components/common/DecisionBadge';

export default function DashboardPage() {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [refreshInterval, setRefreshInterval] = useState(0); // 0 = off
  const [lastUpdated, setLastUpdated] = useState(null);

  const fetchMetrics = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await getDashboardMetrics();
      setData(res);
      setLastUpdated(new Date());
    } catch (err) {
      console.error('Failed to load dashboard metrics:', err);
      setError(err.message || 'Failed to load telemetry analytics.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchMetrics();
  }, [fetchMetrics]);

  useEffect(() => {
    if (!refreshInterval || refreshInterval <= 0) return;
    const timer = setInterval(() => {
      fetchMetrics();
    }, refreshInterval * 1000);
    return () => clearInterval(timer);
  }, [refreshInterval, fetchMetrics]);

  const metrics = data?.metrics || {};
  const total = metrics.total_transactions || 0;
  const approved = metrics.decisions_count?.APPROVE || 0;
  const review = metrics.decisions_count?.REVIEW || 0;
  const blocked = metrics.decisions_count?.BLOCK || 0;

  const approvePct = total > 0 ? ((approved / total) * 100).toFixed(1) : 0;
  const reviewPct = total > 0 ? ((review / total) * 100).toFixed(1) : 0;
  const blockPct = total > 0 ? ((blocked / total) * 100).toFixed(1) : 0;

  return (
    <div className="space-y-6">
      {/* Header bar */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2.5">
            <Activity className="w-6 h-6 text-primary-400" />
            Security & Risk Operations Center
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Real-time inference telemetry, decision distribution, and active fleet health.
          </p>
        </div>

        {/* Live Refresh Controls */}
        <div className="flex items-center gap-2 bg-slate-900/80 border border-slate-800 px-3 py-1.5 rounded-lg text-xs">
          <Clock className="w-3.5 h-3.5 text-slate-400" />
          <span className="text-slate-400">Auto-Refresh:</span>
          <div className="flex items-center space-x-1">
            {[
              { label: 'Off', val: 0 },
              { label: '15s', val: 15 },
              { label: '30s', val: 30 },
              { label: '60s', val: 60 }
            ].map(opt => (
              <button
                key={opt.val}
                onClick={() => setRefreshInterval(opt.val)}
                className={`px-2 py-0.5 rounded text-[11px] font-medium transition ${
                  refreshInterval === opt.val
                    ? 'bg-primary-600 text-white font-semibold'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
          <button
            onClick={fetchMetrics}
            disabled={loading}
            className="ml-2 text-slate-400 hover:text-white transition"
            title="Refresh now"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-primary-400' : ''}`} />
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-lg bg-red-900/20 border border-red-500/30 text-red-300 text-sm flex items-center justify-between">
          <span>{error}</span>
          <button onClick={fetchMetrics} className="underline text-xs ml-4">Retry</button>
        </div>
      )}

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Total Transactions"
          value={total.toLocaleString()}
          subtitle="Processed through pipeline"
          icon={Activity}
          tone="default"
        />
        <MetricCard
          title="Pending Alerts"
          value={metrics.pending_alerts_count ?? 0}
          subtitle="Awaiting analyst review"
          icon={AlertTriangle}
          tone={metrics.pending_alerts_count > 0 ? 'warning' : 'default'}
        />
        <MetricCard
          title="Blocked Decisions"
          value={blocked.toLocaleString()}
          subtitle={`High risk (score >= 70)`}
          icon={ShieldAlert}
          tone={blocked > 0 ? 'danger' : 'default'}
        />
        <MetricCard
          title="Active Terminals"
          value={metrics.active_devices_count ?? 0}
          subtitle="IoT edge devices connected"
          icon={Cpu}
          tone="success"
        />
      </div>

      {/* Analytics Breakdown & Distribution */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Decision Ratio Chart / Card */}
        <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-5 shadow-lg">
          <h2 className="text-sm font-semibold text-slate-200 uppercase tracking-wider mb-4 flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-primary-400" />
            Decision Distribution
          </h2>

          <div className="space-y-4">
            {/* Approved Bar */}
            <div>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-emerald-400 font-medium">APPROVE (Score &lt; 40)</span>
                <span className="text-slate-300 font-mono">{approved} ({approvePct}%)</span>
              </div>
              <div className="w-full bg-slate-800 h-2.5 rounded-full overflow-hidden">
                <div 
                  className="bg-emerald-500 h-full rounded-full transition-all duration-500"
                  style={{ width: `${approvePct}%` }}
                />
              </div>
            </div>

            {/* Review Bar */}
            <div>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-amber-400 font-medium">REVIEW (Score 40–69)</span>
                <span className="text-slate-300 font-mono">{review} ({reviewPct}%)</span>
              </div>
              <div className="w-full bg-slate-800 h-2.5 rounded-full overflow-hidden">
                <div 
                  className="bg-amber-500 h-full rounded-full transition-all duration-500"
                  style={{ width: `${reviewPct}%` }}
                />
              </div>
            </div>

            {/* Block Bar */}
            <div>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-rose-400 font-medium">BLOCK (Score &ge; 70)</span>
                <span className="text-slate-300 font-mono">{blocked} ({blockPct}%)</span>
              </div>
              <div className="w-full bg-slate-800 h-2.5 rounded-full overflow-hidden">
                <div 
                  className="bg-rose-500 h-full rounded-full transition-all duration-500"
                  style={{ width: `${blockPct}%` }}
                />
              </div>
            </div>
          </div>

          <div className="mt-6 pt-4 border-t border-slate-800/80 flex justify-between items-center text-xs">
            <span className="text-slate-400">Mean Pipeline Risk Score:</span>
            <span className="text-white font-mono font-bold text-sm">
              {metrics.average_risk_score !== undefined ? Number(metrics.average_risk_score).toFixed(2) : '0.00'} / 100
            </span>
          </div>
        </div>

        {/* Operational Quick Actions & Pipeline Summary */}
        <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-5 shadow-lg lg:col-span-2 flex flex-col justify-between">
          <div>
            <h2 className="text-sm font-semibold text-slate-200 uppercase tracking-wider mb-2 flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              Real-Time Inference Architecture
            </h2>
            <p className="text-xs text-slate-400 leading-relaxed">
              Inbound transactions are evaluated using 18 engineered features evaluated concurrently against 
              XGBoost (50%), Autoencoder Anomaly Score (20%), Isolation Forest (15%), and Calibrated Logistic Regression (15%). 
              Final governance is enforced via deterministic policy thresholds.
            </p>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-4">
              <div className="p-3 bg-slate-950/60 rounded-lg border border-slate-800/80">
                <p className="text-[11px] text-slate-400">Supervised</p>
                <p className="text-xs font-semibold text-slate-200 mt-0.5">XGBoost (50%)</p>
              </div>
              <div className="p-3 bg-slate-950/60 rounded-lg border border-slate-800/80">
                <p className="text-[11px] text-slate-400">Unsupervised</p>
                <p className="text-xs font-semibold text-slate-200 mt-0.5">Autoencoder (20%)</p>
              </div>
              <div className="p-3 bg-slate-950/60 rounded-lg border border-slate-800/80">
                <p className="text-[11px] text-slate-400">Density Outlier</p>
                <p className="text-xs font-semibold text-slate-200 mt-0.5">IsoForest (15%)</p>
              </div>
              <div className="p-3 bg-slate-950/60 rounded-lg border border-slate-800/80">
                <p className="text-[11px] text-slate-400">Linear Baseline</p>
                <p className="text-xs font-semibold text-slate-200 mt-0.5">LogReg (15%)</p>
              </div>
            </div>
          </div>

          <div className="mt-6 pt-4 border-t border-slate-800 flex flex-wrap items-center justify-between gap-3">
            <div className="text-[11px] text-slate-400">
              {lastUpdated ? `Telemetry synchronized: ${lastUpdated.toLocaleTimeString()}` : 'Connecting...'}
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => navigate('/simulator')}
                className="px-3 py-1.5 rounded-lg bg-primary-600 hover:bg-primary-500 text-white text-xs font-medium transition flex items-center gap-1.5 shadow-md shadow-primary-600/20"
              >
                Launch Simulator <ArrowRight className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => navigate('/alerts')}
                className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium transition flex items-center gap-1.5"
              >
                Review Alerts ({metrics.pending_alerts_count ?? 0})
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Recent High-Risk Transactions */}
      <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-5 shadow-lg">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-slate-200 uppercase tracking-wider flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 text-rose-400" />
            Recent High-Risk Activity & Suspicious Signals
          </h2>
          <button
            onClick={() => navigate('/transactions')}
            className="text-xs text-primary-400 hover:text-primary-300 font-medium flex items-center gap-1"
          >
            View All Transactions <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>

        {metrics.recent_high_risk_transactions && metrics.recent_high_risk_transactions.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="bg-slate-950/70 text-slate-400 font-medium border-b border-slate-800 uppercase tracking-wider">
                <tr>
                  <th className="py-2.5 px-3">Transaction ID</th>
                  <th className="py-2.5 px-3">Type</th>
                  <th className="py-2.5 px-3">Amount</th>
                  <th className="py-2.5 px-3">Risk Score</th>
                  <th className="py-2.5 px-3">Decision</th>
                  <th className="py-2.5 px-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono">
                {metrics.recent_high_risk_transactions.map((tx) => (
                  <tr key={tx.id} className="hover:bg-slate-800/40 transition">
                    <td className="py-2.5 px-3 text-primary-400 hover:underline cursor-pointer" onClick={() => navigate(`/transactions/${tx.id}`)}>
                      {tx.tx_id || tx.id}
                    </td>
                    <td className="py-2.5 px-3 font-sans">{tx.type}</td>
                    <td className="py-2.5 px-3 font-mono">${Number(tx.amount).toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
                    <td className="py-2.5 px-3 font-mono font-bold">
                      <span className={tx.risk_score >= 70 ? 'text-rose-400' : tx.risk_score >= 40 ? 'text-amber-400' : 'text-emerald-400'}>
                        {tx.risk_score !== undefined ? Number(tx.risk_score).toFixed(1) : 'N/A'}
                      </span>
                    </td>
                    <td className="py-2.5 px-3">
                      <DecisionBadge decision={tx.decision} />
                    </td>
                    <td className="py-2.5 px-3 text-right">
                      <button
                        onClick={() => navigate(`/transactions/${tx.id}`)}
                        className="text-[11px] font-sans text-slate-400 hover:text-white px-2 py-1 bg-slate-800 rounded hover:bg-slate-700 transition"
                      >
                        Details
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="py-8 text-center text-xs text-slate-500 bg-slate-950/40 rounded-lg border border-dashed border-slate-800">
            No high-risk transactions detected recently. System telemetry is within normal bounds.
          </div>
        )}
      </div>
    </div>
  );
}
