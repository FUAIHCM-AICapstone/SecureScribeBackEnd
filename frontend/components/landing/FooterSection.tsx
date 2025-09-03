'use client';
import React, { useRef } from 'react';
import { useTranslations } from 'next-intl';
import Link from 'next/link';

const FooterSection = ({ id }: { id: string }) => {
  const t = useTranslations('Footer');
  const footerRef = useRef<HTMLDivElement | null>(null);

  return (
    <footer
      ref={footerRef}
      id={id}
      className="w-full h-auto py-8 lg:py-16 bg-gradient-to-r from-[var(--primary-color)] to-[var(--secondary-color)] px-4 sm:px-6 lg:px-8"
      style={{ color: 'var(--background-color)' }}
    >
      <div className="flex flex-col items-center">
      <div className="flex flex-wrap justify-center gap-4 mb-4">
        <Link
        href="/privacy"
        className="text-white hover:text-[var(--muted-text-color)] transition-colors hover:underline"
        >
        {t('privacy')}
        </Link>
        <Link
        href="/terms-of-service"
        className="text-white hover:text-[var(--muted-text-color)] transition-colors hover:underline"
        >
        {t('terms')}
        </Link>
      </div>
      <p className="text-sm text-[var(--background-color)] text-center">
        © {new Date().getFullYear()} {t('title')} . {t('rights')}
      </p>
      </div>
    </footer>
  );
};

export default FooterSection;
