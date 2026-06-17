import { ThemeTokens } from '../ThemeSchema';
import { defaultTheme } from '../default';

export const animeTheme: ThemeTokens = {
  ...defaultTheme,
  id: 'anime',
  name: 'Anime Companion',
  description: 'Soft pastels and bubbly aesthetics for a friendly AI companion.',
  colors: {
    ...defaultTheme.colors,
    background: '#fff0f5', // Lavender blush
    foreground: '#4a4a4a',
    primary: '#ff69b4', // Hot pink
    primaryForeground: '#ffffff',
    card: '#ffffff',
    cardForeground: '#4a4a4a',
    border: '#ffb6c1',
    muted: '#ffe4e1',
    mutedForeground: '#ff69b4',
    glassBackground: 'rgba(255, 255, 255, 0.8)',
    glassBorder: 'rgba(255, 105, 180, 0.3)',
  },
  typography: {
    fontFamilyBase: 'var(--font-sans)',
    fontFamilyMono: 'var(--font-mono)',
  },
  layout: {
    density: 'spacious',
    borderRadius: '2rem',
    sidebarStyle: 'floating',
    dashboardLayout: 'masonry',
  },
  effects: {
    glassmorphism: true,
    cardStyle: 'elevated',
    motionScale: 1.2,
  },
  orb: {
    style: 'liquid',
    primaryColor: '#ff69b4',
    secondaryColor: '#87cefa', // Light sky blue
    glowIntensity: 0.3,
  }
};
