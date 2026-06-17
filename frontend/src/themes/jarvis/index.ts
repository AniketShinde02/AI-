import { ThemeTokens } from '../ThemeSchema';
import { defaultTheme } from '../default';

export const jarvisTheme: ThemeTokens = {
  ...defaultTheme,
  id: 'jarvis',
  name: 'J.A.R.V.I.S Blue',
  description: 'Holographic blue interface reminiscent of popular sci-fi AI assistants.',
  colors: {
    ...defaultTheme.colors,
    background: '#020813',
    foreground: '#4db8ff',
    primary: '#0088ff',
    primaryForeground: '#ffffff',
    card: '#041024',
    cardForeground: '#4db8ff',
    border: '#003366',
    muted: '#030c1c',
    mutedForeground: '#0066cc',
    glassBackground: 'rgba(4, 16, 36, 0.6)',
    glassBorder: 'rgba(0, 136, 255, 0.4)',
  },
  layout: {
    density: 'comfortable',
    borderRadius: '1rem',
    sidebarStyle: 'floating',
    dashboardLayout: 'fluid',
  },
  effects: {
    glassmorphism: true,
    cardStyle: 'bordered',
    motionScale: 1.5,
  },
  orb: {
    style: 'holographic',
    primaryColor: '#0088ff',
    secondaryColor: '#ffffff',
    glowIntensity: 0.7,
  }
};
