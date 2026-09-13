import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { assessTransaction } from '../api/transactions';
import { Terminal, Send, Sparkles, AlertCircle, Info } from 'lucide-react';

export function SimulatorPage() {
  const navigate = useNavigate();

  const [step, setStep] = useState(646);
  const [type, setType] = useState('TRANSFER');
  const [amount, setAmount] = useState(399045.08);
  const [nameOrig, setNameOrig] = useState('C1234567890');
  const [nameDest, setNameDest] = useState('M9876543210');
  const [oldbalanceOrg, setOldbalanceOrg] = useState(10399045.08);
  const [newbalanceOrig, setNewbalanceOrig] = useState(10000000.0);
  const [oldbalanceDest, setOldbalanceDest] = useState(0.0);
  const [newbalanceDest, setNewbalanceDest] = useState(0.0);
  const [clientTxId, setClientTxId] = useState('');

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Presets ONLY pre-fill form input fields (Zero hardcoded decisions)
  const applyPreset = (presetName) => {
    setError(null);
    if (presetName === 'BENIGN') {
      setStep(646);
      setType('TRANSFER');
      setAmount(1200.0);
      setNameOrig('C1122334455');
      setNameDest('C9988776655');
      setOldbalanceOrg(50000.0);
      setNewbalanceOrig(48800.0);
      setOldbalanceDest(1000.0);
      setNewbalanceDest(2200.0);
      setClientTxId(`CLI-TX-${Date.now().toString().slice(-4)}`);
    } else if (presetName === 'DRAIN') {
      setStep(646);
      setType('TRANSFER');
      setAmount(399045.08);
      setNameOrig('C1234567890');
      setNameDest('M9876543210');
      setOldbalanceOrg(10399045.08);
      setNewbalanceOrig(10000000.0);
      setOldbalanceDest(0.0);
      setNewbalanceDest(0.0);
      setClientTxId(`CLI-TX-${Date.now().toString().slice(-4)}`);
    } else if (presetName === 'CASHOUT') {
      setStep(647);
      setType('CASH_OUT');
      setAmount(45000.0);
      setNameOrig('C5566778899');
      setNameDest('M3344556677');
      setOldbalanceOrg(60000.0);
      setNewbalanceOrig(15000.0);
      setOldbalanceDest(0.0);
      setNewbalanceDest(45000.0);
      setClientTxId(`CLI-TX-${Date.now().toString().slice(-4)}`);
    } else if (presetName === 'NON_MODELED') {
      setStep(646);
      setType('PAYMENT');
      setAmount(250.0);
      setNameOrig('C1234567890');
      setNameDest('M9876543210');
      setOldbalanceOrg(5000.0);
      setNewbalanceOrig(4750.0);
      setOldbalanceDest(0.0);
      setNewbalanceDest(250.0);
      setClientTxId(`CLI-TX-${Date.now().toString().slice(-4)}`);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    const payload = {
      step: Number(step),
      type: String(type),
      amount: Number(amount),
      nameOrig: String(nameOrig),
      nameDest: String(nameDest),
      oldbalanceOrg: Number(oldbalanceOrg),
      newbalanceOrig: Number(newbalanceOrig),
      oldbalanceDest: Number(oldbalanceDest),
      newbalanceDest: Number(newbalanceDest),
      client_tx_id: clientTxId.trim() || undefined,
    };

    try {
      const response = await assessTransaction(payload);
      navigate(`/simulator/result/${response.transaction_id}`, { state: { assessment: response, payload } });
    } catch (err) {
      setError(err.detail || 'Failed to assess transaction. Please verify your inputs.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Header Banner */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h1 style={{ fontSize: '1.6rem', fontWeight: 800, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <Terminal size={26} color="var(--color-primary)" />
            A.R.G.U.S. Transaction Simulator
          </h1>
          <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>
            Simulated payment terminal submitting synthetic PaySim movements directly to the AI Risk Engine.
          </p>
        </div>

        {/* Viva Presets Bar */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
          <span style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
            <Sparkles size={14} color="#F59E0B" />
            Quick Presets:
          </span>
          <button type="button" onClick={() => applyPreset('BENIGN')} className="btn btn-secondary btn-sm">
            Benign Transfer
          </button>
          <button type="button" onClick={() => applyPreset('DRAIN')} className="btn btn-secondary btn-sm" style={{ borderColor: 'rgba(239, 68, 68, 0.4)', color: '#FCA5A5' }}>
            Account Drain Attack
          </button>
          <button type="button" onClick={() => applyPreset('CASHOUT')} className="btn btn-secondary btn-sm" style={{ borderColor: 'rgba(245, 158, 11, 0.4)', color: '#FCD34D' }}>
            Borderline Cash-Out
          </button>
          <button type="button" onClick={() => applyPreset('NON_MODELED')} className="btn btn-secondary btn-sm">
            Payment (Non-Modeled)
          </button>
        </div>
      </div>

      {/* Boundary / Scope Disclosure Notice */}
      <div className="alert-banner alert-banner-info" style={{ marginBottom: 0 }}>
        <Info size={18} style={{ flexShrink: 0, marginTop: '2px' }} />
        <div>
          <strong>Operational Model Boundary:</strong> Machine learning risk scoring is strictly trained and validated on high-risk <code>TRANSFER</code> and <code>CASH_OUT</code> transaction categories. Submitting non-modeled categories will trigger controlled rejection.
        </div>
      </div>

      {error && (
        <div className="alert-banner alert-banner-danger" style={{ marginBottom: 0 }}>
          <AlertCircle size={18} style={{ flexShrink: 0, marginTop: '2px' }} />
          <div>
            <strong>Evaluation Alert:</strong> {error}
          </div>
        </div>
      )}

      {/* Simulator Form Card */}
      <div className="card">
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1.4rem' }}>
          <div className="grid-2">
            <div>
              <label style={{ display: 'block', fontSize: '0.82rem', fontWeight: 600, marginBottom: '0.4rem', color: 'var(--text-secondary)' }}>
                Simulation Step (Temporal Hour 1–744)
              </label>
              <input
                type="number"
                min="1"
                required
                className="input-field"
                value={step}
                onChange={(e) => setStep(e.target.value)}
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.82rem', fontWeight: 600, marginBottom: '0.4rem', color: 'var(--text-secondary)' }}>
                Transaction Category
              </label>
              <select className="input-field" value={type} onChange={(e) => setType(e.target.value)}>
                <option value="TRANSFER">TRANSFER (Model Supported)</option>
                <option value="CASH_OUT">CASH_OUT (Model Supported)</option>
                <option value="PAYMENT">PAYMENT (Non-Modeled / Rejection Test)</option>
                <option value="CASH_IN">CASH_IN (Non-Modeled / Rejection Test)</option>
                <option value="DEBIT">DEBIT (Non-Modeled / Rejection Test)</option>
              </select>
            </div>
          </div>

          <div className="grid-2">
            <div>
              <label style={{ display: 'block', fontSize: '0.82rem', fontWeight: 600, marginBottom: '0.4rem', color: 'var(--text-secondary)' }}>
                Transaction Amount (₹)
              </label>
              <input
                type="number"
                step="any"
                min="0"
                required
                className="input-field"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.82rem', fontWeight: 600, marginBottom: '0.4rem', color: 'var(--text-secondary)' }}>
                Simulated Client TX Sequence ID (Optional Idempotency)
              </label>
              <input
                type="text"
                className="input-field"
                placeholder="e.g. CLI-TX-9901"
                value={clientTxId}
                onChange={(e) => setClientTxId(e.target.value)}
              />
            </div>
          </div>

          {/* Origin Account Section */}
          <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: '1.25rem' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-muted)', letterSpacing: '0.05em' }}>
              Origin Customer Ledger (Sender)
            </span>
            <div className="grid-3" style={{ marginTop: '0.6rem' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.82rem', fontWeight: 600, marginBottom: '0.4rem', color: 'var(--text-secondary)' }}>
                  Origin Account ID
                </label>
                <input
                  type="text"
                  required
                  className="input-field"
                  value={nameOrig}
                  onChange={(e) => setNameOrig(e.target.value)}
                />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '0.82rem', fontWeight: 600, marginBottom: '0.4rem', color: 'var(--text-secondary)' }}>
                  Origin Pre-Balance (₹)
                </label>
                <input
                  type="number"
                  step="any"
                  min="0"
                  required
                  className="input-field"
                  value={oldbalanceOrg}
                  onChange={(e) => setOldbalanceOrg(e.target.value)}
                />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '0.82rem', fontWeight: 600, marginBottom: '0.4rem', color: 'var(--text-secondary)' }}>
                  Origin Post-Balance (₹)
                </label>
                <input
                  type="number"
                  step="any"
                  min="0"
                  required
                  className="input-field"
                  value={newbalanceOrig}
                  onChange={(e) => setNewbalanceOrig(e.target.value)}
                />
              </div>
            </div>
          </div>

          {/* Destination Account Section */}
          <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: '1.25rem' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-muted)', letterSpacing: '0.05em' }}>
              Destination Recipient Ledger (Receiver)
            </span>
            <div className="grid-3" style={{ marginTop: '0.6rem' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.82rem', fontWeight: 600, marginBottom: '0.4rem', color: 'var(--text-secondary)' }}>
                  Destination Account ID
                </label>
                <input
                  type="text"
                  required
                  className="input-field"
                  value={nameDest}
                  onChange={(e) => setNameDest(e.target.value)}
                />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '0.82rem', fontWeight: 600, marginBottom: '0.4rem', color: 'var(--text-secondary)' }}>
                  Destination Pre-Balance (₹)
                </label>
                <input
                  type="number"
                  step="any"
                  min="0"
                  required
                  className="input-field"
                  value={oldbalanceDest}
                  onChange={(e) => setOldbalanceDest(e.target.value)}
                />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '0.82rem', fontWeight: 600, marginBottom: '0.4rem', color: 'var(--text-secondary)' }}>
                  Destination Post-Balance (₹)
                </label>
                <input
                  type="number"
                  step="any"
                  min="0"
                  required
                  className="input-field"
                  value={newbalanceDest}
                  onChange={(e) => setNewbalanceDest(e.target.value)}
                />
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '1rem', marginTop: '0.5rem' }}>
            <button
              type="submit"
              disabled={loading}
              className="btn btn-primary"
              style={{ minWidth: '220px', height: '44px' }}
            >
              {loading ? (
                <span>Executing Inference...</span>
              ) : (
                <>
                  <Send size={16} />
                  <span>Analyze with Risk Engine</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default SimulatorPage;

