'use client';

import { useRef } from 'react';
import { useTranslations } from 'next-intl';
import FeatureCarousel from './FeatureCarousel';

export default function FeaturesSection({ id }: { id: string }) {
  const t = useTranslations('HomePage.features');
  const carouselRef = useRef<HTMLDivElement>(null);
  const sectionRef = useRef<HTMLDivElement | null>(null);

  const scroll = (dir: 'left' | 'right') => {
    if (!carouselRef.current) return;
    const container = carouselRef.current;
    const firstCard = container.children[0];
    const cardWidth =
      firstCard instanceof HTMLElement ? firstCard.offsetWidth : 400;
    const maxScroll = container.scrollWidth - container.clientWidth;
    const currentScroll = container.scrollLeft;
    if (dir === 'right') {
      if (currentScroll + cardWidth >= maxScroll - 10) {
        // Scroll to first card
        container.scrollTo({ left: 0, behavior: 'smooth' });
      } else {
        container.scrollBy({ left: cardWidth, behavior: 'smooth' });
      }
    } else {
      if (currentScroll - cardWidth <= 10) {
        // Scroll to last card
        container.scrollTo({ left: maxScroll, behavior: 'smooth' });
      } else {
        container.scrollBy({ left: -cardWidth, behavior: 'smooth' });
      }
    }
  };

  return (
    <section
      ref={sectionRef}
      id={id}
      className="relative pt-5 lg:pt-24 bg-[var(--background-color)] w-full px-5"
    >
      <div className="mx-auto w-full">
        <div className="flex flex-col md:flex-row md:justify-between">
          <div className="max-w-2xl xl:max-w-[40%] mx-auto md:mx-0 text-left mb-6 md:mb-0">
            <h2 className="text-5xl font-bold sm:text-4xl tracking-tight text-[var(--text-color)] mb-6">
              {t('title.prefix')}{' '}
              <span className="text-[var(--primary-color)]">
                {' '}
                {t('title.suffix')}
              </span>
            </h2>
          </div>
          <div className="flex justify-end gap-6">
            <button
              onClick={() => scroll('left')}
              className="bg-[var(--primary-color)] hover:bg-[var(--primary-color)] text-white rounded-full w-12 h-12 flex items-center justify-center shadow-lg z-30"
              aria-label="Scroll left"
            >
              <svg width="24" height="24" fill="none"
                viewBox="0 0 24 24">
                <path
                  d="M15 19l-7-7 7-7"
                  stroke="white"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </button>
            <button
              onClick={() => scroll('right')}
              className="bg-[var(--primary-color)] hover:bg-[var(--primary-color)] text-white rounded-full w-12 h-12 flex items-center justify-center shadow-lg z-30"
              aria-label="Scroll right"
            >
              <svg width="24" height="24" fill="none"
                viewBox="0 0 24 24">
                <path
                  d="M9 5l7 7-7 7"
                  stroke="white"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </button>
          </div>
        </div>
      </div>
      <FeatureCarousel carouselRef={carouselRef} />
    </section>
  );
}
