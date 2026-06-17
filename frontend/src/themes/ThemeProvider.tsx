'use client';

import React, { createContext, useContext, useEffect, useState } from 'react';
import { ThemeTokens } from './ThemeSchema';
import { getTheme, getAllThemes } from './ThemeRegistry';
import { applyTheme } from './ThemeLoader';

interface ThemeContextType {
  theme: ThemeTokens;
  setThemeId: (id: string) => void;
  setCustomTheme: (theme: ThemeTokens, backgroundUrl?: string) => void;
  availableThemes: ThemeTokens[];
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [themeId, setThemeId] = useState<string>('default');
  const [theme, setTheme] = useState<ThemeTokens>(getTheme('default'));

  useEffect(() => {
    // Attempt to load saved theme from localStorage on mount
    const savedThemeId = localStorage.getItem('nexus-theme');
    const customThemeStr = localStorage.getItem('nexus-custom-theme');
    
    if (savedThemeId === 'custom' && customThemeStr) {
      try {
        const customTheme = JSON.parse(customThemeStr);
        setThemeId('custom');
        setTheme(customTheme);
        applyTheme(customTheme);
      } catch (e) {
        setThemeId('default');
      }
    } else if (savedThemeId) {
      setThemeId(savedThemeId);
    }
  }, []);

  useEffect(() => {
    if (themeId !== 'custom') {
      const newTheme = getTheme(themeId);
      setTheme(newTheme);
      applyTheme(newTheme);
      localStorage.setItem('nexus-theme', themeId);
    }
  }, [themeId]);

  const setCustomTheme = (newTheme: ThemeTokens, backgroundUrl?: string) => {
    // Inject background image if provided, otherwise preserve existing if not explicitly overridden
    const finalTheme = { ...newTheme };
    if (backgroundUrl) {
      finalTheme.backgroundImage = backgroundUrl;
    }
    
    setTheme(finalTheme);
    setThemeId('custom');
    applyTheme(finalTheme);
    localStorage.setItem('nexus-theme', 'custom');
    localStorage.setItem('nexus-custom-theme', JSON.stringify(finalTheme));
  };

  return (
    <ThemeContext.Provider value={{ theme, setThemeId, setCustomTheme, availableThemes: getAllThemes() }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (context === undefined) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
}
