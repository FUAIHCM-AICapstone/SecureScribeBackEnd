'use client';
import React, { useState } from 'react';
import Image from 'next/image';
import { usePathname, useRouter } from '@/i18n/navigation';
import { useLocale, useTranslations } from 'next-intl';
import { FiChevronDown } from 'react-icons/fi';

// Assumes public directory contains /vietnam.png and /united-kingdom.png

const languages = [
  {
    code: 'en',
    name: 'English',
    flagSrc: '/images/icons/united-kingdom.png',
    flagAlt: 'United Kingdom Flag',
  },
  {
    code: 'vi',
    name: 'Tiếng Việt',
    flagSrc: '/images/icons/vietnam.png',
    flagAlt: 'Vietnam Flag',
  },
];

const LanguageSwitcher = () => {
  const locale = useLocale();
  const router = useRouter();
  const pathname = usePathname();
  const t = useTranslations('LanguageSwitcher');

  const [open, setOpen] = useState(false);

  const currentLanguage =
    languages.find((lang) => lang.code === locale) || languages[0];

  const handleLanguageChange = (language: (typeof languages)[0]) => {
    setOpen(false);
    const normalizedPath = pathname.replace(/^\/(en|vi)/, '') || '/';
    router.push(normalizedPath, { locale: language.code });
  };

  return (
    <div className="relative">
      <button
        className="flex items-center gap-2 px-3 py-2 rounded-[var(--border-radius)] bg-[var(--background-color)] text-[var(--muted-text-color)] hover:bg-[var(--surface-color)] transition font-[var(--font-family-base)] border border-[var(--border-color)]"
        onClick={() => setOpen((v) => !v)}
        aria-label={t('selectLanguage', { current: currentLanguage.name })}
        type="button"
      >
        <Image
          src={currentLanguage.flagSrc}
          alt={currentLanguage.flagAlt}
          width={20}
          height={20}
          className="rounded-sm"
          priority
        />
        <span className="uppercase">{currentLanguage.code}</span>
        <FiChevronDown className="w-4 h-4" />
      </button>
      {open && (
        <div className="absolute right-0 mt-2 w-40 bg-[var(--background-color)] rounded-[var(--border-radius)] shadow-lg z-10 border border-[var(--border-color)]">
          {languages.map((language) => (
            <button
              key={language.code}
              onClick={() => handleLanguageChange(language)}
              className="flex items-center w-full px-4 py-2 hover:bg-[var(--surface-color)] transition text-[var(--text-color)] font-[var(--font-family-base)]"
              type="button"
            >
              <Image
                src={language.flagSrc}
                alt={language.flagAlt}
                width={20}
                height={20}
                className="rounded-sm"
                priority
              />
              <span className="ml-2">{language.name}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

export default LanguageSwitcher;
