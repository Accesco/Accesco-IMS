import { useState, useEffect, useCallback } from 'react';
import { getStoredTheme, setStoredTheme } from '../services/storage';

export type Theme = 'dark' | 'light';

export function useTheme(): {
  theme: Theme;
  toggleTheme: () => void;
  isDark: boolean;
} {
  const [theme, setTheme] = useState<Theme>(() => {
    return getStoredTheme() ?? 'dark';
  });

  // Apply theme class to document
  useEffect(() => {
    const root = document.documentElement;
    if (theme === 'dark') {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }
    setStoredTheme(theme);
  }, [theme]);

  const toggleTheme = useCallback(() => {
    setTheme((prev) => (prev === 'dark' ? 'light' : 'dark'));
  }, []);

  return { theme, toggleTheme, isDark: theme === 'dark' };
}
