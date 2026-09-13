import React from 'react';

export function RiskGauge({ score = 0, size = 220 }) {
  const clampedScore = Math.max(0, Math.min(100, Number(score) || 0));

  // Determine color and status
  let strokeColor = '#10B981'; // Approve
  let glowColor = 'rgba(16, 185, 129, 0.25)';
  let verdictText = 'LOW RISK';

  if (clampedScore >= 70) {
    strokeColor = '#EF4444'; // Block
    glowColor = 'rgba(239, 68, 68, 0.35)';
    verdictText = 'HIGH RISK';
  } else if (clampedScore >= 40) {
    strokeColor = '#F59E0B'; // Review
    glowColor = 'rgba(245, 158, 11, 0.3)';
    verdictText = 'MEDIUM RISK';
  }

  // Circular gauge math (240 degree arc)
  const radius = 80;
  const circumference = 2 * Math.PI * radius;
  const arcLength = circumference * (240 / 360);
  const strokeDashoffset = arcLength - (arcLength * clampedScore) / 100;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', position: 'relative' }}>
      <svg width={size} height={size * 0.85} viewBox="0 0 200 170">
        <defs>
          <filter id="gauge-glow" x="-20%" y="-20%" width="140%" height="140%">
            <feDropShadow dx="0" dy="0" stdDeviation="4" floodColor={strokeColor} floodOpacity="0.5" />
          </filter>
        </defs>

        {/* Background Track Arc */}
        <circle
          cx="100"
          cy="105"
          r={radius}
          fill="none"
          stroke="#1E293B"
          strokeWidth="14"
          strokeDasharray={`${arcLength} ${circumference}`}
          strokeDashoffset="0"
          strokeLinecap="round"
          transform="rotate(150 100 105)"
        />

        {/* Progress Arc */}
        <circle
          cx="100"
          cy="105"
          r={radius}
          fill="none"
          stroke={strokeColor}
          strokeWidth="14"
          strokeDasharray={`${arcLength} ${circumference}`}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
          transform="rotate(150 100 105)"
          filter="url(#gauge-glow)"
          style={{ transition: 'stroke-dashoffset 800ms ease-out, stroke 300ms ease' }}
        />

        {/* Center Text */}
        <text x="100" y="95" textAnchor="middle" fill="#FFFFFF" fontSize="32" fontWeight="800" fontFamily="var(--font-mono)">
          {clampedScore.toFixed(1)}
        </text>
        <text x="100" y="116" textAnchor="middle" fill="#94A3B8" fontSize="11" fontWeight="600" letterSpacing="0.05em">
          OUT OF 100
        </text>
        <text x="100" y="142" textAnchor="middle" fill={strokeColor} fontSize="12" fontWeight="700" letterSpacing="0.08em">
          {verdictText}
        </text>
      </svg>

      {/* Threshold Reference Indicator */}
      <div style={{ display: 'flex', gap: '1rem', fontSize: '0.72rem', color: '#64748B', marginTop: '-0.5rem' }}>
        <span>&lt;40 Safe</span>
        <span>40–69 Review</span>
        <span>&ge;70 Block</span>
      </div>
    </div>
  );
}

export default RiskGauge;
