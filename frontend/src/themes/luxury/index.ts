import { ThemeTokens } from '../ThemeSchema';
import { defaultTheme } from '../default';

export const luxuryTheme: ThemeTokens = {
  ...defaultTheme,
  id: 'luxury',
  name: 'Luxury Dark',
  description: 'Elegant, high-contrast dark theme with gold accents and premium typography.',
  colors: {
    ...defaultTheme.colors,
    background: '#0a0a0a',
    foreground: '#ffffff',
    primary: '#d4af37', // Gold
    primaryForeground: '#0a0a0a',
    card: '#121212',
    cardForeground: '#ffffff',
    border: '#2a2a2a',
    muted: '#1a1a1a',
    mutedForeground: '#a0a0a0',
    glassBackground: 'rgba(18, 18, 18, 0.8)',
    glassBorder: 'rgba(212, 175, 55, 0.3)',
  },
  typography: {
    fontFamilyBase: 'var(--font-sans)',
    fontFamilyMono: 'var(--font-mono)',
    fontFamilyHeading: 'var(--font-serif)',
  },
  layout: {
    density: 'spacious',
    borderRadius: '0.25rem',
    sidebarStyle: 'docked',
    dashboardLayout: 'masonry',
  },
  effects: {
    glassmorphism: true,
    cardStyle: 'elevated',
    motionScale: 0.5,
  },
  orb: {
    style: 'holographic',
    primaryColor: '#d4af37',
    secondaryColor: '#ffffff',
    glowIntensity: 0.4,
  }
};
