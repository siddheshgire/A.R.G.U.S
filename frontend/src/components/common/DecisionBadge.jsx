import React from 'react';
import { CheckCircle2, AlertTriangle, ShieldAlert } from 'lucide-react';

export function DecisionBadge({ decision, size = 'normal' }) {
  if (!decision) return null;

  const upper = decision.toUpperCase();

  let badgeClass = 'badge-neutral';
  let icon = null;
  const iconSize = size === 'large' ? 18 : 14;

  if (upper === 'APPROVE') {
    badgeClass = 'badge-approve';
    icon = <CheckCircle2 size={iconSize} />;
  } else if (upper === 'REVIEW') {
    badgeClass = 'badge-review';
    icon = <AlertTriangle size={iconSize} />;
  } else if (upper === 'BLOCK') {
    badgeClass = 'badge-block';
    icon = <ShieldAlert size={iconSize} />;
  }

  const style = size === 'large' ? { padding: '0.4rem 1rem', fontSize: '0.95rem' } : {};

  return (
    <span className={`badge ${badgeClass}`} style={style}>
      {icon}
      {upper}
    </span>
  );
}

export default DecisionBadge;
