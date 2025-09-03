import React from 'react';
import ThemeToggle from '@/components/layout/ThemeToggle';
import Image from 'next/image';
import { useTranslations } from 'next-intl';


export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const t = useTranslations('AuthLayout');
  return (
    <div className="w-full h-screen flex flex-col lg:flex-row font-inter bg-[var(--background-color)] relative">
      {/* Left Panel: Gradient, Logo, Text, Acrylic Blur */}
      <div
        className="hidden lg:flex flex-col items-center justify-start lg:justify-center w-full lg:w-1/2 h-full py-10 px-6 lg:px-12 relative overflow-hidden"
        style={{ background: 'var(--auth-gradient)' }}
      >
        {/* Acrylic Blur Overlay */}
        <div className="absolute inset-0 z-0 backdrop-blur-lg bg-white/10 dark:bg-black/40 pointer-events-none" />
        <div className="relative z-10 flex flex-col items-center w-full">

          <div className="max-w-md w-full text-center mt-2">
            <p className="text-xs lg:text-sm text-white leading-relaxed mb-2">
              <span className="font-mono text-cyan-300 text-base lg:text-lg font-semibold">
                {t('welcomeTitle')}
              </span>
              <br />
              <span className="font-bold text-pink-300">
                {t('subtitle')}
              </span>
              <br />
              <span className="text-white font-normal">{t('tagline')}</span>
            </p>{' '}
          </div>
        </div>
      </div>
      {/* Right Panel: Background Image, Card, Form */}
      <div
        className="relative w-full lg:w-1/2 h-full flex items-center justify-center overflow-hidden"
        style={{
          background: 'url(/images/bg1.webp) center center / cover no-repeat',
        }}
      >
        {/* Overlay for better contrast */}
        <div className="absolute inset-0 bg-black bg-opacity-40 z-0 pointer-events-none" />
        {/* Card with Acrylic Effect */}
        <div className="relative z-10 w-full max-w-sm rounded-2xl shadow-2xl px-8 py-10 flex flex-col items-center backdrop-blur-lg border border-[var(--border-color)] bg-[var(--auth-card-bg)]">
          {/* Avatar */}
          <Image
            src="/images/logos/logo2.png"
            alt={t('mascotAlt')}
            width={256}
            height={256}
            className="rounded-full object-cover w-20"
            priority
          />
          <div className="text-center mb-6">
            <span className="block text-lg font-mono font-semibold">
              {t('mascotLabel')}
            </span>
          </div>
          {/* Children: Login Form */}
          {children}

          {/* Footer */}
          <div className="w-full text-center mt-6">
            <span className="text-xs text-[var(--text-color)]">{t('copyright', { year: new Date().getFullYear() })}</span>
          </div>
        </div>
      </div>
      <div className="absolute bottom-10 right-10 z-20">
        <ThemeToggle />
      </div>
    </div>
  );
}
