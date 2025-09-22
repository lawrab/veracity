import { useState, useEffect } from 'react';

export function useDarkMode() {
  const [isDark, setIsDark] = useState(false);

  useEffect(() => {
    // Check if user has a saved preference
    const saved = localStorage.getItem('darkMode');
    if (saved) {
      setIsDark(JSON.parse(saved));
    } else {
      // Default to system preference
      setIsDark(window.matchMedia('(prefers-color-scheme: dark)').matches);
    }
  }, []);

  useEffect(() => {
    // Apply dark mode class to document
    if (isDark) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
    // Save preference
    localStorage.setItem('darkMode', JSON.stringify(isDark));
  }, [isDark]);

  const toggleDarkMode = () => setIsDark(!isDark);

  return { isDark, toggleDarkMode };
}