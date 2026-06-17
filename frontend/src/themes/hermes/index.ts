import { ThemeTokens } from '../ThemeSchema';
import { defaultTheme } from '../default';

export const hermesTheme: ThemeTokens = {
  ...defaultTheme,
  id: 'hermes',
  name: 'Hermes Terminal',
  description: 'High-contrast, terminal-inspired theme optimized for text density.',
  colors: {
    ...defaultTheme.colors,
    background: '#0a0a0a',
    foreground: '#00ff00',
    primary: '#00ff00',
    primaryForeground: '#0a0a0a',
    card: '#111111',
    cardForeground: '#00ff00',
    border: '#222222',
    muted: '#1a1a1a',
    mutedForeground: '#008800',
  },
  typography: {
    fontFamilyBase: 'var(--font-mono)',
    fontFamilyMono: 'var(--font-mono)',
  },
  layout: {
    density: 'compact',
    borderRadius: '0px',
    sidebarStyle: 'minimal',
    dashboardLayout: 'terminal',
  },
  effects: {
    glassmorphism: false,
    cardStyle: 'bordered',
    motionScale: 0,
  },
  orb: {
    style: 'wireframe',
    primaryColor: '#00ff00',
    secondaryColor: '#004400',
    glowIntensity: 0.8,
  }
};
