import { useState, useEffect } from 'react';

export function useDarkMode() {
  // Always start with false to ensure server/client consistency
  const [isDark, setIsDark] = useState(false);
  const [hasMounted, setHasMounted] = useState(false);

  useEffect(() => {
    // This runs only on the client after hydration
    setHasMounted(true);
    
    // Check if user has a saved preference
    const saved = localStorage.getItem('darkMode');
    if (saved) {
      setIsDark(JSON.parse(saved));
      return;
    }
    
    // Default to system preference
    const systemDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    setIsDark(systemDark);
  }, []);

  useEffect(() => {
    // Only apply changes after component has mounted
    if (!hasMounted) return;
    
    // Apply dark mode class to document
    if (isDark) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
    // Save preference
    localStorage.setItem('darkMode', JSON.stringify(isDark));
  }, [isDark, hasMounted]);

  const toggleDarkMode = () => setIsDark(!isDark);

  return { isDark, toggleDarkMode };
}