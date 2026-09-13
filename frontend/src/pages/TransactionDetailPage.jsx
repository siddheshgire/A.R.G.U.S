import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  ArrowLeft, 
  ShieldAlert, 
  Clock, 
  Cpu, 
  Layers, 
  Database, 
  User, 
  FileText,
  AlertTriangle,
  ExternalLink,
  CheckCircle
} from 'lucide-react';
import { getTransactionDetail } from '../api/transactions';
import RiskGauge from '../components/common/RiskGauge';
import DecisionBadge from '../components/common/DecisionBadge';
import ModelSignalBars from '../components/common/ModelSignalBars';

export default function TransactionDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchDetail() {
      try {
        setLoading(true);
        setError(null);
        const res = await getTransactionDetail(id);
        setData(res);
      } catch (err) {
        console.error('Failed to load transaction detail:', err);
        setError(err.message || 'Transaction not found or unauthorized.');
      } finally {
        setLoading(false);
      }
    }
    fetchDetail();
  }, [id]);

  if (loading) {
    return (
      <div className="py-24 text-center text-slate-400 text-sm">
        <Cpu className="w-8 h-8 text-primary-400 animate-spin mx-auto mb-3" />
        Retrieving transaction records and model feature vectors...
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="max-w-xl mx-auto py-16 text-center space-y-4">
        <div className="p-4 bg-red-900/20 border border-red-500/30 rounded-xl text-red-300 text-sm">
          {error || 'Transaction records could not be found.'}
        </div>
        <button
          onClick={() => navigate('/transactions')}
          className="inline-flex items-center gap-1.5 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium rounded-lg transition"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Transaction Ledger
        </button>
      </div>
    );
  }

  const tx = data;
  const assessment = tx.assessment;
  const features = tx.engineered_features;
  const isEvaluated = assessment && assessment.decision !== 'NON_EVALUATED';

  // Format 18 features into human-readable list
  const featureList = features ? [
    { key: 'step', label: 'Temporal Step (Hours)', val: features.step },
    { key: 'type_CASH_OUT', label: 'Type: CASH_OUT Flag', val: features.type_CASH_OUT },
    { key: 'type_TRANSFER', label: 'Type: TRANSFER Flag', val: features.type_TRANSFER },
    { key: 'amount', label: 'Transaction Amount ($)', val: features.amount },
    { key: 'oldbalanceOrg', label: 'Origin Initial Balance ($)', val: features.oldbalanceOrg },
    { key: 'newbalanceOrig', label: 'Origin Post-Tx Balance ($)', val: features.newbalanceOrig },
    { key: 'oldbalanceDest', label: 'Destination Initial Balance ($)', val: features.oldbalanceDest },
    { key: 'newbalanceDest', label: 'Destination Post-Tx Balance ($)', val: features.newbalanceDest },
    { key: 'errorBalanceOrig', label: 'Origin Balance Accounting Discrepancy ($)', val: features.errorBalanceOrig },
    { key: 'errorBalanceDest', label: 'Dest Balance Accounting Discrepancy ($)', val: features.errorBalanceDest },
    { key: 'hour_of_day', label: 'Temporal Hour of Day [0–23]', val: features.hour_of_day },
    { key: 'day_of_week', label: 'Temporal Day of Week [0–6]', val: features.day_of_week },
    { key: 'orig_tx_count_1h', label: 'Origin 1h Rolling Frequency', val: features.orig_tx_count_1h },
    { key: 'orig_tx_amount_sum_1h', label: 'Origin 1h Cumulative Outflow ($)', val: features.orig_tx_amount_sum_1h },
    { key: 'dest_tx_count_1h', label: 'Dest 1h Rolling Inflow Frequency', val: features.dest_tx_count_1h },
    { key: 'dest_tx_amount_sum_1h', label: 'Dest 1h Cumulative Inflow ($)', val: features.dest_tx_amount_sum_1h },
    { key: 'orig_balance_drain_ratio', label: 'Origin Balance Drain Ratio [0–1]', val: features.orig_balance_drain_ratio },
    { key: 'dest_balance_surge_ratio', label: 'Dest Balance Surge Ratio', val: features.dest_balance_surge_ratio },
  ] : [];

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {/* Top navigation */}
      <div className="flex items-center justify-between">
        <button
          onClick={() => navigate(-1)}
          className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-white transition"
        >
          <ArrowLeft className="w-4 h-4" /> Back
        </button>
        <div className="text-xs text-slate-500 font-mono">
          Database ID: #{tx.id}
        </div>
      </div>

      {/* Hero assessment banner */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-6 shadow-xl relative overflow-hidden">
        <div className="flex flex-col md:flex-row items-center justify-between gap-6">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="text-xs font-mono text-slate-400">Transaction ID:</span>
              <span className="text-sm font-mono font-bold text-white bg-slate-950 px-2 py-0.5 rounded border border-slate-800">
                {tx.tx_id || tx.id}
              </span>
              <DecisionBadge decision={assessment?.decision || 'UNKNOWN'} />
            </div>
            <h1 className="text-2xl font-black text-white tracking-tight">
              ${Number(tx.amount).toLocaleString(undefined, { minimumFractionDigits: 2 })}
              <span className="text-sm font-medium text-slate-400 ml-2">via {tx.type}</span>
            </h1>
            <p className="text-xs text-slate-400 mt-1 flex items-center gap-3">
              <span>Channel: <strong className="text-slate-200">{tx.channel || 'WEB_SIMULATOR'}</strong></span>
              {tx.terminal_id && <span>Terminal: <strong className="text-slate-200">{tx.terminal_id}</strong></span>}
              <span>Logged: <strong className="text-slate-200">{tx.timestamp ? new Date(tx.timestamp).toLocaleString() : 'N/A'}</strong></span>
            </p>
          </div>

          {/* Continuous Risk Gauge */}
          {isEvaluated && assessment?.risk_score !== undefined && (
            <div className="flex items-center gap-4 bg-slate-950/60 p-4 rounded-xl border border-slate-800/80">
              <RiskGauge score={assessment.risk_score} size={150} />
            </div>
          )}
        </div>

        {/* Forensic Reasons if flagged */}
        {assessment?.reasons && assessment.reasons.length > 0 && (
          <div className="mt-6 pt-4 border-t border-slate-800/80">
            <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2 flex items-center gap-1.5">
              <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
              Forensic Risk Factors & Anomaly Indicators
            </h3>
            <ul className="grid grid-cols-1 md:grid-cols-2 gap-2">
              {assessment.reasons.map((r, i) => (
                <li key={i} className="text-xs text-slate-300 bg-slate-950/50 p-2 rounded border border-slate-800 flex items-start gap-2">
                  <span className="text-amber-400 mt-0.5">&bull;</span>
                  <span>{r}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Model Contributions breakdown */}
      {isEvaluated && assessment?.model_contributions && (
        <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-5 shadow-lg">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-slate-200 uppercase tracking-wider flex items-center gap-2">
              <Layers className="w-4 h-4 text-primary-400" />
              Multi-Model Ensemble Decomposition
            </h2>
            <span className="text-xs font-mono text-slate-400">
              Execution Time: {assessment.execution_time_ms ? `${assessment.execution_time_ms.toFixed(2)} ms` : 'N/A'}
            </span>
          </div>

          <ModelSignalBars contributions={assessment.model_contributions} />
        </div>
      )}

      {/* Account Balances and Ledger State */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Originator details */}
        <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-5 shadow-lg">
          <h2 className="text-sm font-semibold text-slate-200 uppercase tracking-wider mb-3 flex items-center gap-2">
            <User className="w-4 h-4 text-primary-400" /> Originator Account ({tx.name_orig || 'N/A'})
          </h2>
          <div className="space-y-2 text-xs font-mono">
            <div className="flex justify-between py-1.5 border-b border-slate-800">
              <span className="text-slate-400">Pre-Transaction Balance:</span>
              <span className="text-white">${Number(tx.oldbalance_org ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-slate-800">
              <span className="text-slate-400">Post-Transaction Balance:</span>
              <span className="text-white">${Number(tx.newbalance_orig ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
            </div>
            <div className="flex justify-between py-1.5 text-slate-400">
              <span>Debit Delta:</span>
              <span className="text-rose-400 font-bold">
                -${(Number(tx.oldbalance_org ?? 0) - Number(tx.newbalance_orig ?? 0)).toLocaleString(undefined, { minimumFractionDigits: 2 })}
              </span>
            </div>
          </div>
        </div>

        {/* Destination details */}
        <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-5 shadow-lg">
          <h2 className="text-sm font-semibold text-slate-200 uppercase tracking-wider mb-3 flex items-center gap-2">
            <User className="w-4 h-4 text-emerald-400" /> Destination Account ({tx.name_dest || 'N/A'})
          </h2>
          <div className="space-y-2 text-xs font-mono">
            <div className="flex justify-between py-1.5 border-b border-slate-800">
              <span className="text-slate-400">Pre-Transaction Balance:</span>
              <span className="text-white">${Number(tx.oldbalance_dest ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-slate-800">
              <span className="text-slate-400">Post-Transaction Balance:</span>
              <span className="text-white">${Number(tx.newbalance_dest ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
            </div>
            <div className="flex justify-between py-1.5 text-slate-400">
              <span>Credit Delta:</span>
              <span className="text-emerald-400 font-bold">
                +${(Number(tx.newbalance_dest ?? 0) - Number(tx.oldbalance_dest ?? 0)).toLocaleString(undefined, { minimumFractionDigits: 2 })}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Safe 18 Engineered Features Table */}
      <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-5 shadow-lg">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-sm font-semibold text-slate-200 uppercase tracking-wider flex items-center gap-2">
              <Database className="w-4 h-4 text-primary-400" />
              Engineered Model Features
            </h2>
            <p className="text-[11px] text-slate-400 mt-0.5">
              The 18 engineered features synthesized and passed into the ML/DL pipeline.
              <span className="text-emerald-400 ml-1 font-mono">Zero target leakage (isFraud/isFlaggedFraud strictly excluded).</span>
            </p>
          </div>
        </div>

        {features ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="bg-slate-950/80 text-slate-400 font-medium border-b border-slate-800 uppercase tracking-wider">
                <tr>
                  <th className="py-2.5 px-3">#</th>
                  <th className="py-2.5 px-3">Feature Key</th>
                  <th className="py-2.5 px-3">Feature Name / Description</th>
                  <th className="py-2.5 px-3 text-right">Evaluated Value</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono">
                {featureList.map((f, idx) => (
                  <tr key={f.key} className="hover:bg-slate-800/40">
                    <td className="py-2 px-3 text-slate-500 text-[11px]">{idx + 1}</td>
                    <td className="py-2 px-3 font-semibold text-primary-400">{f.key}</td>
                    <td className="py-2 px-3 font-sans text-slate-300">{f.label}</td>
                    <td className="py-2 px-3 text-right text-white font-bold">
                      {typeof f.val === 'number'
                        ? Number.isInteger(f.val)
                          ? f.val
                          : Number(f.val).toFixed(4)
                        : String(f.val ?? '0')}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="py-8 text-center text-xs text-slate-500 bg-slate-950/40 rounded-lg">
            Feature vector not stored or transaction is not an ML-evaluated type.
          </div>
        )}
      </div>
    </div>
  );
}
