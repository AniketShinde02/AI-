import { ThemeTokens } from './ThemeSchema';
import { defaultTheme } from './default';
import { hermesTheme } from './hermes';
import { minimalTheme } from './minimal';
import { cyberpunkTheme } from './cyberpunk';
import { luxuryTheme } from './luxury';
import { jarvisTheme } from './jarvis';
import { animeTheme } from './anime';

// Map of all available themes
export const themeRegistry: Record<string, ThemeTokens> = {
  default: defaultTheme,
  hermes: hermesTheme,
  minimal: minimalTheme,
  cyberpunk: cyberpunkTheme,
  luxury: luxuryTheme,
  jarvis: jarvisTheme,
  anime: animeTheme,
};

// Helper to get a theme with a fallback to default
export function getTheme(id: string): ThemeTokens {
  return themeRegistry[id] || defaultTheme;
}

export function getAllThemes(): ThemeTokens[] {
  return Object.values(themeRegistry);
}
