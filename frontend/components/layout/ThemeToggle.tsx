'use client';
import React from 'react';
import { RiMoonFill, RiSunLine } from 'react-icons/ri';
import { useTranslations } from 'next-intl';
import { useTheme } from 'next-themes';

const ThemeToggle = () => {
  const t = useTranslations('ThemeToggle');
  const { resolvedTheme, setTheme } = useTheme();
  const [mounted, setMounted] = React.useState(false);
  React.useEffect(() => setMounted(true), []);

  if (!mounted) return null;
  return (
    <button
      aria-label={t('toggleTheme')}
      onClick={() => setTheme(resolvedTheme === 'dark' ? 'light' : 'dark')}
      className="p-2 rounded-[var(--border-radius)] bg-[var(--background-color)] text-[var(--muted-text-color)] hover:bg-[var(--surface-color)] transition border border-[var(--border-color)] font-[var(--font-family-base)]"
      type="button"
    >
      {resolvedTheme === 'light' ? (
        <RiMoonFill size={20} />
      ) : (
        <RiSunLine size={20} />
      )}
    </button>
  );
};

export default ThemeToggle;
