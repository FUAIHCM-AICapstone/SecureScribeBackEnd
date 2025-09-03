// hooks/useTheme.ts
import { useState } from 'react';

export default function useTheme() {
  const [theme, setTheme] = useState('light');

  const toggleTheme = () =>
    setTheme((prev) => (prev === 'light' ? 'dark' : 'light'));

  return { theme, toggleTheme };
}
