import React, { useState, useEffect } from 'react';
import { useParams, useLocation, useNavigate, Link } from 'react-router-dom';
import { getTransactionDetail } from '../api/transactions';
import { RiskGauge } from '../components/common/RiskGauge';
import { DecisionBadge } from '../components/common/DecisionBadge';
import { ModelSignalBars } from '../components/common/ModelSignalBars';
import { ArrowLeft, FileText, Send, CheckCircle, AlertTriangle, ShieldAlert } from 'lucide-react';

export function AssessmentResultPage() {
  const { id } = useParams();
  const location = useLocation();
  const navigate = useNavigate();

  const [assessment, setAssessment] = useState(location.state?.assessment || null);
  const [loading, setLoading] = useState(!assessment);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function loadDetails() {
      if (!assessment && id) {
        try {
          const detail = await getTransactionDetail(id);
          if (detail.risk_assessment && detail.decision) {
            setAssessment({
              transaction_id: detail.tx_id,
              risk_score: detail.risk_assessment.final_risk_score,
              decision: detail.decision.policy_decision,
              reasons: detail.decision.reasons || [],
              model_signals: {
                xgboost_score: detail.risk_assessment.xgboost_signal,
                logistic_score: detail.risk_assessment.logistic_signal,
                isolation_score: detail.risk_assessment.isolation_signal,
                autoencoder_score: detail.risk_assessment.autoencoder_signal,
              },
            });
          } else {
            setError('Transaction has not been evaluated with a risk assessment record.');
          }
        } catch (err) {
          setError(err.detail || 'Failed to retrieve assessment results.');
        } finally {
          setLoading(false);
        }
      }
    }
    loadDetails();
  }, [id, assessment]);

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '4rem 0', color: 'var(--text-secondary)' }}>
        Retrieving Risk Engine evaluation records...
      </div>
    );
  }

  if (error || !assessment) {
    return (
      <div className="card" style={{ textAlign: 'center', padding: '3rem 2rem' }}>
        <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--color-block)' }}>
          Assessment Record Unavailable
        </h2>
        <p style={{ color: 'var(--text-secondary)', marginTop: '0.5rem' }}>{error || 'Transaction ID not found.'}</p>
        <Link to="/simulator" className="btn btn-secondary" style={{ marginTop: '1.5rem', display: 'inline-flex' }}>
          <ArrowLeft size={16} />
          Return to Simulator
        </Link>
      </div>
    );
  }

  const { risk_score, decision, model_signals, reasons, transaction_id } = assessment;

  let policyDescription = 'Transaction verified as standard commercial activity.';
  if (decision === 'BLOCK') {
    policyDescription = 'High risk detected. Immediate rejection enforced by rule policy.';
  } else if (decision === 'REVIEW') {
    policyDescription = 'Borderline anomalies detected. Routed to Fraud Analyst review queue.';
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Top Navigation & Status */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
        <button onClick={() => navigate('/simulator')} className="btn btn-secondary btn-sm">
          <ArrowLeft size={14} />
          <span>New Simulation</span>
        </button>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <span style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
            Transaction ID: <code style={{ color: 'var(--text-primary)' }}>{String(transaction_id || id).slice(0, 16)}...</code>
          </span>
          <DecisionBadge decision={decision} size="large" />
        </div>
      </div>

      {/* Main Grid: Gauge & Signals */}
      <div className="grid-2">
        {/* Left Column: Overall Risk Gauge */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', textAlign: 'center', padding: '2rem 1.5rem' }}>
          <span style={{ fontSize: '0.82rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-secondary)', marginBottom: '1rem' }}>
            Ensemble Risk Engine Verdict
          </span>

          <RiskGauge score={risk_score} size={230} />

          <div style={{ marginTop: '1rem', padding: '0.75rem 1.25rem', borderRadius: 'var(--radius-md)', background: 'rgba(255,255,255,0.03)', border: '1px solid var(--border-subtle)', width: '100%', maxWidth: '340px' }}>
            <div style={{ fontSize: '0.88rem', fontWeight: 700, color: 'var(--text-primary)' }}>
              Action: {decision}
            </div>
            <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>
              {policyDescription}
            </div>
          </div>
        </div>

        {/* Right Column: Model Signal Breakdown */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
            <div>
              <h2 style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                Model Signal Decomposition
              </h2>
              <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                Decomposed signals from the 4 underlying ML/DL estimators
              </p>
            </div>
          </div>

          <ModelSignalBars signals={model_signals} />
        </div>
      </div>

      {/* Explainable Reasons Card */}
      <div className="card">
        <h3 style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <FileText size={18} color="var(--color-primary)" />
          Explainable Diagnostic Reasons
        </h3>

        {reasons && reasons.length > 0 ? (
          <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '0.6rem', paddingLeft: 0 }}>
            {reasons.map((reason, idx) => (
              <li
                key={idx}
                style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '0.65rem',
                  fontSize: '0.88rem',
                  color: 'var(--text-primary)',
                  padding: '0.6rem 0.85rem',
                  borderRadius: 'var(--radius-md)',
                  background: 'rgba(255, 255, 255, 0.03)',
                  border: '1px solid var(--border-subtle)',
                }}
              >
                <span style={{ color: 'var(--color-cyan)', fontWeight: 700, marginTop: '2px' }}>•</span>
                <span>{reason}</span>
              </li>
            ))}
          </ul>
        ) : (
          <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
            No anomaly flags triggered. Transaction exhibits standard parameters.
          </div>
        )}

        {/* Footer Actions */}
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '1.5rem', borderTop: '1px solid var(--border-subtle)', paddingTop: '1.25rem' }}>
          <Link to={`/transactions/${transaction_id || id}`} className="btn btn-secondary btn-sm">
            <FileText size={14} />
            <span>View Engineered Features</span>
          </Link>
          <Link to="/transactions" className="btn btn-secondary btn-sm">
            <span>Transaction History</span>
          </Link>
          <Link to="/simulator" className="btn btn-primary btn-sm">
            <Send size={14} />
            <span>Simulate Another</span>
          </Link>
        </div>
      </div>
    </div>
  );
}

export default AssessmentResultPage;

