import { z } from 'zod';

// Zod schema for Nexus Themes
export const ThemeTokenSchema = z.object({
  id: z.string(),
  name: z.string(),
  description: z.string().optional(),
  backgroundImage: z.string().optional(),
  
  // Colors (CSS variables mapped to HSL or HEX)
  colors: z.object({
    background: z.string(),
    foreground: z.string(),
    primary: z.string(),
    primaryForeground: z.string(),
    secondary: z.string(),
    secondaryForeground: z.string(),
    accent: z.string(),
    accentForeground: z.string(),
    border: z.string(),
    card: z.string(),
    cardForeground: z.string(),
    muted: z.string(),
    mutedForeground: z.string(),
    glassBackground: z.string(),
    glassBorder: z.string(),
    cardBg: z.string().optional(),
    accentGlow: z.string().optional(),
    cyan: z.string().optional(),
  }),

  // Typography
  typography: z.object({
    fontFamilyBase: z.string(),
    fontFamilyMono: z.string(),
    fontFamilyHeading: z.string().optional(),
  }),

  // Layout & Density
  layout: z.object({
    density: z.enum(['compact', 'comfortable', 'spacious']),
    borderRadius: z.string(),
    sidebarStyle: z.enum(['floating', 'docked', 'minimal']),
    dashboardLayout: z.enum(['grid', 'masonry', 'fluid', 'terminal']),
  }),

  // Visual Effects
  effects: z.object({
    glassmorphism: z.boolean(),
    cardStyle: z.enum(['flat', 'elevated', 'bordered', 'neon']),
    motionScale: z.number().min(0).max(2).default(1), // 0 = no motion, 1 = normal, 2 = exaggerated
  }),

  // Nexus Orb styling
  orb: z.object({
    style: z.enum(['holographic', 'minimal', 'energy', 'wireframe', 'liquid', 'cyberpunk']),
    primaryColor: z.string(),
    secondaryColor: z.string(),
    glowIntensity: z.number().min(0).max(1).default(0.5),
  }),
});

export type ThemeTokens = z.infer<typeof ThemeTokenSchema>;
