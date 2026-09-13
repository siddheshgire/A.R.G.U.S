import React from 'react';

export function MetricCard({ title, value, icon: Icon, subtitle, trendColor, badgeText, tone }) {
  const getToneColor = () => {
    if (trendColor) return trendColor;
    if (tone === 'danger') return '#EF4444';
    if (tone === 'warning') return '#F59E0B';
    if (tone === 'success') return '#10B981';
    return 'var(--color-primary)';
  };

  const activeColor = getToneColor();

  return (
    <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
          {title}
        </span>
        <div style={{ padding: '0.4rem', background: 'rgba(255, 255, 255, 0.05)', borderRadius: 'var(--radius-md)', color: activeColor }}>
          {React.isValidElement(Icon) ? Icon : Icon ? <Icon size={18} /> : null}
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.75rem' }}>
        <span style={{ fontSize: '1.85rem', fontWeight: 800, fontFamily: 'var(--font-mono)', color: 'var(--text-primary)' }}>
          {value !== undefined && value !== null ? value : '—'}
        </span>
        {badgeText && (
          <span style={{ fontSize: '0.75rem', fontWeight: 700, padding: '0.15rem 0.45rem', borderRadius: '4px', background: `${activeColor}22`, color: activeColor }}>
            {badgeText}
          </span>
        )}
      </div>

      {subtitle && (
        <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
          {subtitle}
        </span>
      )}
    </div>
  );
}

export default MetricCard;

