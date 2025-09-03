'use client';

import { useTranslations } from 'next-intl';
import Image from 'next/image';
import Link from 'next/link';
import { useRef } from 'react';

export default function StackSection({ id }: { id: string }) {
  const t = useTranslations('HomePage.stack');
  const sectionRef = useRef<HTMLDivElement | null>(null);


  return (
    <section
      ref={sectionRef}
      id={id}
      className="relative pt-10 lg:pt-20 font-sans bg-white"
      style={{
        color: 'var(--text-color)',
        background: 'var(--background-color)',
      }}
    >
      <div className="max-w-full mx-auto px-4 lg:px-20 flex flex-col gap-5">
        {/* Title */}
        <h2
          className="text-2xl lg:text-3xl font-bold text-left tracking-tight"
          style={{ color: 'var(--text-color)' }}
        >
          {t('title')}
        </h2>

        {/* Top Section */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 lg:gap-12 items-center">
          {/* Left – Timeline */}
          <div className="relative space-y-8">
            {[0, 1, 2].map((idx) => (
              <div key={idx} className="flex items-start gap-6 group">
                {/* Timeline Marker */}
                <div className="relative flex-shrink-0">
                  <div
                    className="w-10 h-10 lg:w-12 lg:h-12 rounded-full flex items-center justify-center shadow-lg group-hover:scale-110 transition-transform duration-300 bg-[var(--primary-color)]"
                    style={{ color: 'var(--background-color)' }}
                  >
                    {idx + 1}
                  </div>
                  {idx < 2 && (
                    <div className="absolute top-10 lg:top-12 left-5 lg:left-6 w-0.5 h-16 bg-[var(--accent-color)]"></div>
                  )}
                </div>
                <div className="pt-2">
                  <div
                    className="font-semibold text-lg"
                    style={{ color: 'var(--text-color)' }}
                  >
                    {t(`timeline.${idx}.title`)}
                  </div>
                  <div
                    className="text-sm mt-1"
                    style={{ color: 'var(--muted-text-color)' }}
                  >
                    {t(`timeline.${idx}.desc`)}
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Center – Cat image */}
          <div className="flex justify-center">
            <div className="relative w-full max-w-[250px] aspect-square">
              <Image
                src="/images/cat.png"
                alt={t('catAlt')}
                fill
                className="object-contain hover:scale-105 transition-transform duration-300"
              />
            </div>
          </div>

          {/* Right – Benefits */}
          <div
            className="border rounded-xl p-8 shadow-lg hover:shadow-xl transition-shadow duration-300"
            style={{
              background: 'var(--card-bg)',
              borderColor: 'var(--border-color)',
              color: 'var(--muted-text-color)',
            }}
          >
            <div
              className="font-bold text-xl mb-6"
              style={{ color: 'var(--text-color)' }}
            >
              {t('benefits.title')}
            </div>
            <ul className="space-y-4 text-sm">
              {[0, 1, 2, 3].map((idx) => (
                <li key={idx} className="flex items-center gap-3">
                  <div className="w-5 h-5 min-w-5 min-h-5 rounded flex items-center justify-center bg-[var(--accent-color)]">
                    <svg
                      className="w-4 h-4"
                      style={{ color: 'var(--primary-color)' }}
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                      xmlns="http://www.w3.org/2000/svg"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth="2"
                        d="M5 13l4 4L19 7"
                      />
                    </svg>
                  </div>
                  <span>{t(`benefits.items.${idx}`)}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>

        <div
          className="relative w-screen left-1/2 right-1/2 -mx-[50vw] h-auto py-8 lg:py-16 bg-gradient-to-r from-[var(--primary-color)] to-[var(--secondary-color)] px-10"
          style={{ color: 'var(--background-color)' }}
        >
          <div className="max-w-7xl mx-auto px-4 lg:px-6 grid grid-cols-1 lg:grid-cols-2 gap-8 lg:gap-12 items-center relative">
            {/* Right – Text content */}
            <div className="flex flex-col justify-center space-y-6 order-1 lg:order-2">
              <Image
                src="/images/logos/logo.png"
                alt={t('miniCatAlt')}
                width={100}
                height={100}
                className="object-contain"
              />
              <div className="text-2xl lg:text-4xl font-extrabold leading-tight text-white">
                {t('bottom.title')}
              </div>
              <Link
                href="https://chromewebstore.google.com/detail/meowmo/eacneidbgomibehikolkflgompbohedi"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-block"
              >
                <Image
                  src="/images/chrome-store.png"
                  alt={t('chromeStoreAlt')}
                  width={523}
                  height={175}
                  className="w-full max-w-[260px] h-auto"
                />
              </Link>
              <div className="text-base text-white">
                <strong>{t('bottom.strong')}</strong> {t('bottom.desc')}
              </div>
            </div>

            {/* Left – Laptop Image */}
            <div className="relative w-full max-w-[600px] aspect-[4/3] mx-auto order-2 md:order-1">
              <Image
                src="/images/laptop2.png"
                alt={t('laptopAlt')}
                fill
                className="object-contain hover:scale-105 transition-transform duration-300"
              />
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
