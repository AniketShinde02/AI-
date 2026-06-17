import { ThemeTokens } from './ThemeSchema';

export function applyTheme(theme: ThemeTokens) {
  if (typeof window === 'undefined') return;

  const root = document.documentElement;

  // Apply colors
  Object.entries(theme.colors).forEach(([key, value]) => {
    // Convert camelCase to kebab-case
    const cssVarName = `--${key.replace(/([a-z0-9]|(?=[A-Z]))([A-Z])/g, '$1-$2').toLowerCase()}`;
    root.style.setProperty(cssVarName, value);
  });

  // Apply typography
  root.style.setProperty('--font-base', theme.typography.fontFamilyBase);
  root.style.setProperty('--font-mono', theme.typography.fontFamilyMono);
  if (theme.typography.fontFamilyHeading) {
    root.style.setProperty('--font-heading', theme.typography.fontFamilyHeading);
  }

  // Apply layout
  root.style.setProperty('--radius', theme.layout.borderRadius);
  
  // Apply specific classes for density and effects to root for global styling hooks
  root.classList.remove('density-compact', 'density-comfortable', 'density-spacious');
  root.classList.add(`density-${theme.layout.density}`);

  if (theme.effects.glassmorphism) {
    root.classList.add('glass-effects-enabled');
  } else {
    root.classList.remove('glass-effects-enabled');
  }

  // Custom data attributes for use in components
  root.setAttribute('data-theme-id', theme.id);
  root.setAttribute('data-card-style', theme.effects.cardStyle);
  root.setAttribute('data-sidebar-style', theme.layout.sidebarStyle);

  // Apply background image if present
  if ((theme as any).backgroundImage) {
    root.style.setProperty('--global-bg-image', `url('${(theme as any).backgroundImage}')`);
    root.classList.add('has-custom-bg');
  } else {
    root.style.removeProperty('--global-bg-image');
    root.classList.remove('has-custom-bg');
  }
}
