import React from 'react';
import { useTheme } from '@/themes/ThemeProvider';
import { DefaultLayout } from './DefaultLayout';
import { HermesLayout } from './HermesLayout';
import { JarvisLayout } from './JarvisLayout';
import { MinimalLayout } from './MinimalLayout';
import { CyberpunkLayout } from './CyberpunkLayout';
import { AnimeLayout } from './AnimeLayout';

export interface DashboardLayoutProps {
  orbNode: React.ReactNode;
  chatNode: React.ReactNode;
  logsNode: React.ReactNode;
  traceNode: React.ReactNode;
  inputNode: React.ReactNode;
  statusNode: React.ReactNode;
  telemetryNode: React.ReactNode;
}

export function DashboardLayoutRenderer(props: DashboardLayoutProps) {
  const { theme } = useTheme();

  switch (theme.id) {
    case 'hermes': return <HermesLayout {...props} />;
    case 'jarvis': return <JarvisLayout {...props} />;
    case 'minimal': return <MinimalLayout {...props} />;
    case 'luxury': return <MinimalLayout {...props} />; // Luxury uses the minimal spacious layout structure
    case 'cyberpunk': return <CyberpunkLayout {...props} />;
    case 'anime': return <AnimeLayout {...props} />;
    default: return <DefaultLayout {...props} />;
  }
}
