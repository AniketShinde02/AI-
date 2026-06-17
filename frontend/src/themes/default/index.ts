import { ThemeTokens } from '../ThemeSchema';

export const defaultTheme: ThemeTokens = {
  id: 'default',
  name: 'Nexus Default',
  description: 'The standard, clean interface for Nexus OS.',
  colors: {
    background: '#06060c',
    foreground: '#ffffff',
    primary: '#6137FF',
    primaryForeground: '#ffffff',
    secondary: 'rgba(97, 55, 255, 0.1)',
    secondaryForeground: '#ffffff',
    accent: '#6137FF',
    accentForeground: '#ffffff',
    border: 'rgba(97, 55, 255, 0.2)',
    card: '#06060c',
    cardForeground: '#ffffff',
    muted: 'rgba(255, 255, 255, 0.05)',
    mutedForeground: '#a1a1aa',
    glassBackground: 'rgba(6, 6, 12, 0.8)',
    glassBorder: 'rgba(97, 55, 255, 0.2)',
    cardBg: 'rgba(6, 6, 12, 0.8)',
    accentGlow: 'rgba(0, 255, 255, 0.15)',
    cyan: '#00FFFF',
  },
  typography: {
    fontFamilyBase: 'var(--font-sans)',
    fontFamilyMono: 'var(--font-mono)',
  },
  layout: {
    density: 'comfortable',
    borderRadius: '0',
    sidebarStyle: 'docked',
    dashboardLayout: 'grid',
  },
  effects: {
    glassmorphism: false,
    cardStyle: 'bordered',
    motionScale: 1,
  },
  orb: {
    style: 'cyberpunk',
    primaryColor: '#6137FF',
    secondaryColor: '#00FFFF',
    glowIntensity: 0.8,
  },
};
