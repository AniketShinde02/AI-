import { ThemeTokens } from '../ThemeSchema';
import { defaultTheme } from '../default';

export const minimalTheme: ThemeTokens = {
  ...defaultTheme,
  id: 'minimal',
  name: 'Minimal SaaS',
  description: 'Clean, distraction-free interface with generous whitespace.',
  colors: {
    ...defaultTheme.colors,
    background: '#fafafa',
    foreground: '#171717',
    primary: '#171717',
    primaryForeground: '#fafafa',
    card: '#ffffff',
    cardForeground: '#171717',
    border: '#e5e5e5',
    muted: '#f5f5f5',
    mutedForeground: '#737373',
  },
  layout: {
    density: 'spacious',
    borderRadius: '0.75rem',
    sidebarStyle: 'docked',
    dashboardLayout: 'grid',
  },
  effects: {
    glassmorphism: false,
    cardStyle: 'flat',
    motionScale: 1,
  },
  orb: {
    style: 'minimal',
    primaryColor: '#171717',
    secondaryColor: '#a3a3a3',
    glowIntensity: 0.1,
  }
};
