import { ThemeTokens } from '../ThemeSchema';
import { defaultTheme } from '../default';

export const cyberpunkTheme: ThemeTokens = {
  ...defaultTheme,
  id: 'cyberpunk',
  name: 'Neon Cyberpunk',
  description: 'High-energy, neon-infused dark mode with intense glowing effects.',
  colors: {
    ...defaultTheme.colors,
    background: '#050510',
    foreground: '#00ffff',
    primary: '#ff00ff',
    primaryForeground: '#050510',
    card: '#0a0a1a',
    cardForeground: '#00ffff',
    border: '#ff00ff',
    muted: '#111122',
    mutedForeground: '#008888',
    glassBackground: 'rgba(10, 10, 26, 0.8)',
    glassBorder: 'rgba(255, 0, 255, 0.5)',
  },
  layout: {
    density: 'comfortable',
    borderRadius: '0px',
    sidebarStyle: 'floating',
    dashboardLayout: 'fluid',
  },
  effects: {
    glassmorphism: true,
    cardStyle: 'neon',
    motionScale: 2,
  },
  orb: {
    style: 'energy',
    primaryColor: '#ff00ff',
    secondaryColor: '#00ffff',
    glowIntensity: 1.0,
  }
};
