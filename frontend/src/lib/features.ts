import { useState, useEffect } from 'react';

/**
 * Feature Flag Configuration
 * In production, this would be fetched from a remote config service (Firebase/PostHog).
 * For now, we use a local constant that can be overridden by localStorage for testing.
 */
const DEFAULT_FEATURES = {
  'voice-streaming': true,
  'chat-history': false,
  'ai-suggestions': true,
  'debug-mode': process.env.NODE_ENV === 'development',
};

export type FeatureKey = keyof typeof DEFAULT_FEATURES;

export const useFeature = (key: FeatureKey): boolean => {
  const [isEnabled, setIsEnabled] = useState(DEFAULT_FEATURES[key]);

  useEffect(() => {
    // Check for localStorage override (e.g., ?feature-chat-history=true)
    const override = localStorage.getItem(`feature-${key}`);
    if (override !== null) {
      setIsEnabled(override === 'true');
    }
  }, [key]);

  return isEnabled;
};

/**
 * Manually toggle a feature for debugging
 */
export const toggleFeature = (key: FeatureKey, value: boolean) => {
  localStorage.setItem(`feature-${key}`, String(value));
  window.location.reload(); // Reload to apply changes across the SPA
};
