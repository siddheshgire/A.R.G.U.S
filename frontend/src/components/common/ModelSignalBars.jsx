import React from 'react';
import { Cpu, Network, Binary, GitFork } from 'lucide-react';

export function ModelSignalBars({ signals, contributions }) {
  const data = contributions || signals;
  if (!data) return null;

  const xgbVal = data.xgboost?.raw_probability ?? data.xgboost_score ?? 0;
  const aeVal = data.autoencoder?.raw_probability ?? data.autoencoder_score ?? 0;
  const isoVal = data.isolation_forest?.raw_probability ?? data.isolation_score ?? 0;
  const lrVal = data.logistic_regression?.raw_probability ?? data.logistic_score ?? 0;

  const models = [
    {
      name: 'Supervised XGBoost',
      weight: '50%',
      type: 'Model-estimated probability',
      value: xgbVal,
      icon: <GitFork size={16} color="#3B82F6" />,
      color: '#3B82F6',
    },
    {
      name: 'Unsupervised Deep Autoencoder',
      weight: '20%',
      type: 'Anomaly signal',
      value: aeVal,
      icon: <Network size={16} color="#06B6D4" />,
      color: '#06B6D4',
    },
    {
      name: 'Unsupervised Isolation Forest',
      weight: '15%',
      type: 'Anomaly signal',
      value: isoVal,
      icon: <Cpu size={16} color="#A855F7" />,
      color: '#A855F7',
    },
    {
      name: 'Supervised Logistic Regression',
      weight: '15%',
      type: 'Model-estimated probability',
      value: lrVal,
      icon: <Binary size={16} color="#10B981" />,
      color: '#10B981',
    },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.1rem' }}>
      {models.map((m) => {
        const pct = Math.min(100, Math.max(0, m.value * 100));
        return (
          <div key={m.name} style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.85rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                {m.icon}
                <span>{m.name}</span>
                <span
                  style={{
                    fontSize: '0.72rem',
                    background: 'rgba(255, 255, 255, 0.06)',
                    padding: '0.1rem 0.4rem',
                    borderRadius: '4px',
                    color: 'var(--text-muted)',
                  }}
                >
                  Weight {m.weight}
                </span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{m.type}</span>
                <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--text-primary)', minWidth: '52px', textAlign: 'right' }}>
                  {pct.toFixed(1)}%
                </span>
              </div>
            </div>

            {/* Progress Track */}
            <div
              style={{
                width: '100%',
                height: '8px',
                background: 'rgba(255, 255, 255, 0.08)',
                borderRadius: '9999px',
                overflow: 'hidden',
                position: 'relative',
              }}
            >
              <div
                style={{
                  width: `${pct}%`,
                  height: '100%',
                  background: m.color,
                  borderRadius: '9999px',
                  transition: 'width 800ms ease-out',
                  boxShadow: pct > 70 ? `0 0 8px ${m.color}` : 'none',
                }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}
export default ModelSignalBars;
