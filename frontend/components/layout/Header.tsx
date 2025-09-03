'use client';
import React, { useState } from 'react';
import Link from 'next/link';
import { useTranslations } from 'next-intl';
import ThemeToggle from './ThemeToggle';
import LanguageSwitcher from './LanguageSwitcher';
import { useRouter, usePathname } from 'next/navigation';
import Image from 'next/image';

const NAV_ITEMS = [
  { label: 'home', href: '#hero' },
  { label: 'features', href: '#features' },
  { label: 'techStack', href: '#stack' },
  { label: 'testimonials', href: '#testimonials' },
  { label: 'userGuide', href: '/guide/welcome' },
];


interface PrimaryButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  className?: string;
  children: React.ReactNode;
  leftIcon?: React.ReactNode;
}

const PrimaryButton: React.FC<PrimaryButtonProps> = ({
  children,
  className = '',
  leftIcon,
  ...props
}) => (
  <button
    className={`inline-flex items-center gap-2 bg-[var(--primary-color)] text-white px-5 py-2 rounded font-semibold transition hover:opacity-90 ${className}`}
    {...props}
  >
    {leftIcon && <span className="text-lg">{leftIcon}</span>}
    {children}
  </button>
);

const Header = () => {
  const t = useTranslations('Header.navigation');
  const [mobileOpen, setMobileOpen] = useState(false);
  const router = useRouter();
  const pathname = usePathname();

  const isLandingPage =
    pathname === '/' || /^\/[a-z]{2}(-[A-Z]{2})?$/.test(pathname);

  const handleStartNow = () => {
    router.push('/auth');
  };

  return (
    <>
      <header className="sticky top-0 left-0 right-0 z-50 bg-[var(--background-color)] shadow font-[var(--font-family-base)]">
        <div className="mx-auto flex items-center justify-between px-4 py-3">
          <Link
            href={isLandingPage ? '/dashboard' : '/'}
            className="flex items-center gap-2"
          >
            <Image
              src="/images/logos/logo2.png"
              alt="Logo"
              width={1000}
              height={1000}
              className="h-10 w-10 object-contain rounded-lg"
            />
            <span className="hidden md:block text-2xl font-bold text-[var(--text-color)] font-sofia">
              Meobeo.ai
            </span>
          </Link>
          <div className="w-[30%] md:w-[50%] justify-start">
            <nav className="hidden md:flex gap-8">
              {isLandingPage &&
                NAV_ITEMS.map((item) => (
                  <Link
                    key={item.label}
                    href={item.href}
                    className="text-[var(--muted-text-color)] hover:text-[var(--primary-color)] font-medium transition"
                  >
                    {t(item.label)}
                  </Link>
                ))}
            </nav>
          </div>
          <div className="flex items-center gap-3">
            <LanguageSwitcher />
            <ThemeToggle />
            {isLandingPage && (
              <PrimaryButton
                className="hidden md:inline-block"
                onClick={handleStartNow}
              >
                {t('startNow')}
              </PrimaryButton>
            )}
            <button
              className="md:hidden p-2 rounded hover:bg-[var(--surface-color)]"
              onClick={() => setMobileOpen((v) => !v)}
              aria-label="Toggle Navigation"
            >
              <svg
                className="w-6 h-6 text-[var(--text-color)]"
                fill="none"
                stroke="currentColor"
                strokeWidth={2}
                viewBox="0 0 24 24"
              >
                {mobileOpen ? (
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M6 18L18 6M6 6l12 12"
                  />
                ) : (
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M4 6h16M4 12h16M4 18h16"
                  />
                )}
              </svg>
            </button>
          </div>
        </div>
        {mobileOpen && (
          <nav className="md:hidden bg-[var(--background-color)] px-4 pb-4">
            <ul className="flex flex-col gap-4">
              {isLandingPage &&
                NAV_ITEMS.map((item) => (
                  <li key={item.label}>
                    <Link
                      href={item.href}
                      className="block text-[var(--muted-text-color)] hover:text-[var(--primary-color)] font-medium py-2"
                      onClick={() => setMobileOpen(false)}
                    >
                      {t(item.label)}
                    </Link>
                  </li>
                ))}
              {isLandingPage && (
                <li>
                  <PrimaryButton
                    className="w-full"
                    onClick={() => {
                      setMobileOpen(false);
                      handleStartNow();
                    }}
                  >
                    {t('startNow')}
                  </PrimaryButton>
                </li>
              )}
            </ul>
          </nav>
        )}
      </header>
    </>
  );
};

export default Header;
