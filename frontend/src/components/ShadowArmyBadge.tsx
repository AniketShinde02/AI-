'use client';

import React from 'react';

interface AgentTierData {
  tier: string;
  provider: string;
  model: string;
  themePrimary: string;
  themeAccent: string;
}

interface ShadowArmyBadgeProps {
  activeAgentTier: AgentTierData | null;
}

const TIER_ICONS: Record<string, string> = {
  'grand marshal':   '⚔️',
  'generals':        '⚡',
  'knights':         '🛡️',
  'eyes':            '👁️',
  'shadow soldiers': '🌑',
  'infantry':        '⚙️',
};

const TIER_DESCRIPTIONS: Record<string, string> = {
  'grand marshal':   'Heavy Planning',
  'generals':        'Browser Execution',
  'knights':         'Fast Routing / Chat',
  'eyes':            'Vision / Multimodal',
  'shadow soldiers': 'Background Tasks',
  'infantry':        'Offline Fallback',
};

export function ShadowArmyBadge({ activeAgentTier }: ShadowArmyBadgeProps) {
  const [visible, setVisible] = React.useState(false);
  const [fadeOut, setFadeOut] = React.useState(false);
  const timerRef = React.useRef<ReturnType<typeof setTimeout> | null>(null);

  React.useEffect(() => {
    if (!activeAgentTier) return;

    // Show badge, reset any pending hide
    if (timerRef.current) clearTimeout(timerRef.current);
    setFadeOut(false);
    setVisible(true);

    // Auto-fade after 4 seconds
    timerRef.current = setTimeout(() => {
      setFadeOut(true);
      timerRef.current = setTimeout(() => setVisible(false), 600);
    }, 4000);

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [activeAgentTier]);

  if (!activeAgentTier || !visible) return null;

  const tierKey   = activeAgentTier.tier.toLowerCase();
  const icon      = TIER_ICONS[tierKey]      ?? '🤖';
  const desc      = TIER_DESCRIPTIONS[tierKey] ?? activeAgentTier.tier;
  const accent    = activeAgentTier.themeAccent;
  const primary   = activeAgentTier.themePrimary;
  const shortModel = activeAgentTier.model.split('/').pop() ?? activeAgentTier.model;

  return (
    <div
      style={{
        position: 'fixed',
        bottom: '24px',
        right: '24px',
        zIndex: 9999,
        display: 'flex',
        alignItems: 'center',
        gap: '10px',
        padding: '10px 16px',
        borderRadius: '12px',
        background: `${primary}e6`,
        border: `1px solid ${accent}55`,
        boxShadow: `0 0 18px ${accent}44, 0 4px 24px rgba(0,0,0,0.6)`,
        backdropFilter: 'blur(12px)',
        color: '#fff',
        fontFamily: 'var(--font-mono, monospace)',
        fontSize: '12px',
        letterSpacing: '0.04em',
        transition: 'opacity 0.6s ease',
        opacity: fadeOut ? 0 : 1,
        pointerEvents: 'none',
        userSelect: 'none',
      }}
      aria-live="polite"
      aria-label={`Active agent: ${activeAgentTier.tier}`}
    >
      {/* Animated pulse dot */}
      <div style={{ position: 'relative', width: '8px', height: '8px', flexShrink: 0 }}>
        <div
          style={{
            position: 'absolute',
            inset: 0,
            borderRadius: '50%',
            background: accent,
            animation: 'shadow-army-pulse 1.4s ease-in-out infinite',
          }}
        />
      </div>

      {/* Icon + Tier Name */}
      <div style={{ display: 'flex', flexDirection: 'column', lineHeight: 1.3 }}>
        <span style={{ color: accent, fontWeight: 700, fontSize: '11px', textTransform: 'uppercase' }}>
          {icon} {activeAgentTier.tier}
        </span>
        <span style={{ color: 'rgba(255,255,255,0.55)', fontSize: '10px' }}>
          {desc} · {activeAgentTier.provider}
        </span>
        <span style={{ color: 'rgba(255,255,255,0.35)', fontSize: '9px', marginTop: '1px' }}>
          {shortModel}
        </span>
      </div>

      <style>{`
        @keyframes shadow-army-pulse {
          0%, 100% { transform: scale(1); opacity: 1; box-shadow: 0 0 0 0 ${accent}88; }
          50%       { transform: scale(1.4); opacity: 0.7; box-shadow: 0 0 0 5px ${accent}00; }
        }
      `}</style>
    </div>
  );
}
