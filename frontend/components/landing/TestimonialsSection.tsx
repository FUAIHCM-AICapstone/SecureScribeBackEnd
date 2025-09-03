'use client';
import { useTranslations } from 'next-intl';
import Image from 'next/image';
import React, { useRef } from 'react';
import { FaChevronLeft, FaChevronRight } from 'react-icons/fa';


function useTestimonialTranslations() {
  const t = useTranslations('HomePage.testimonials.items');
  return [0, 1, 2, 3].map((idx) => ({
    avatar: `/images/avatar${idx}.png`,
    name: t(`${idx}.name`),
    title: t(`${idx}.title`),
    review: t(`${idx}.review`),
  }));
}

function TestimonialCard({
  avatar,
  name,
  title,
  review,
}: {
  avatar: string;
  name: string;
  title: string;
  review: string;
}) {
  return (
    <div className="relative rounded-3xl overflow-hidden w-[400px] h-[300px] flex-shrink-0 snap-start bg-[var(--card-bg)] shadow-md border border-[var(--border-color)] p-6 flex flex-col items-start">
      <Image
        src={avatar}
        alt={name}
        width={1000}
        height={1000}
        className="rounded-full mb-4 w-24"
      />
      <h4 className="text-lg font-bold text-[var(--text-color)]">{name}</h4>
      <p className="text-sm text-[var(--muted-text-color)]">{title}</p>
      <div className="flex items-center my-2">
        {[...Array(5)].map((_, i) => (
          <span key={i} className="text-[var(--primary-color)] text-xl">
            ★
          </span>
        ))}
      </div>
      <p className="text-sm text-[var(--text-color)]">“{review}”</p>
    </div>
  );
}

function TestimonialsCarousel({
  carouselRef,
}: {
  carouselRef: React.RefObject<HTMLDivElement>;
}) {
  const testimonials = useTestimonialTranslations();
  return (
    <div className="relative w-full py-8">
      <div className="relative w-full px-0">
        <div
          ref={carouselRef}
          className="flex space-x-6 snap-x snap-mandatory pb-4 px-5 overflow-x-auto scrollbar-hide"
          style={{
            scrollSnapType: 'x mandatory',
            msOverflowStyle: 'none',
            scrollbarWidth: 'none',
          }}
        >
          {testimonials.map((t, idx) => (
            <div
              key={idx}
              className="min-w-[400px] max-w-[400px] h-[300px] flex-shrink-0 snap-start"
              style={{ flex: '0 0 auto' }}
            >
              <TestimonialCard {...t} />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

const TestimonialsSection = ({ id }: { id: string }) => {
  const t = useTranslations('HomePage.testimonials');
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
        container.scrollTo({ left: 0, behavior: 'smooth' });
      } else {
        container.scrollBy({ left: cardWidth, behavior: 'smooth' });
      }
    } else {
      if (currentScroll - cardWidth <= 10) {
        container.scrollTo({ left: maxScroll, behavior: 'smooth' });
      } else {
        container.scrollBy({ left: -cardWidth, behavior: 'smooth' });
      }
    }
  };

  const benefits = [0, 1, 2, 3].map((idx) => t(`benefits.${idx}`));

  return (
    <section
      ref={sectionRef}
      id={id}
      className="w-full py-16 px-4 bg-[var(--background-color)] text-[var(--text-color)] font-[var(--font-family-base)]"
    >
      <div className="flex items-center justify-between max-w-7xl mx-auto">
        <h2 className="text-4xl font-bold text-[var(--text-color)] font-sofia">
          {t('title')}
        </h2>
        <div>
          <Image
            src="/images/catTest.png"
            alt="Cat playing with yarn"
            width={1000}
            height={1000}
            className="w-16 h-16 md:w-24 md:h-24 lg:w-32 lg:h-32 object-contain"
          />
        </div>
      </div>

      <div className="relative w-full max-w-7xl mx-auto">
        <TestimonialsCarousel carouselRef={carouselRef} />
        <button
          onClick={() => scroll('left')}
          className="absolute left-[-100px] top-1/2 transform -translate-y-1/2 bg-[var(--primary-color)] text-white rounded-full w-10 h-10 flex items-center justify-center z-10 shadow"
          aria-label="Scroll left"
        >
          <FaChevronLeft size={24} />
        </button>
        <button
          onClick={() => scroll('right')}
          className="absolute right-[-100px] top-1/2 transform -translate-y-1/2 bg-[var(--primary-color)] text-white rounded-full w-10 h-10 flex items-center justify-center z-10 shadow"
          aria-label="Scroll right"
        >
          <FaChevronRight size={24} />
        </button>
      </div>

      <div className="mx-auto max-w-7xl grid grid-cols-1 gap-8 lg:grid-cols-2 items-center">
        {/* Text Column */}
        <div className="px-6 lg:px-0 lg:pr-16">
          <h2 className="text-4xl font-semibold text-[var(--text-color)] font-sofia mb-4">
            {t('ctaTitle')}
          </h2>
          <ul className="list-disc list-inside space-y-2 mb-6">
            {benefits.map((benefit, idx) => (
              <li key={idx} className="text-lg text-[var(--text-color)]">
                {benefit}
              </li>
            ))}
          </ul>
          <button className="inline-block bg-[var(--primary-color)] text-white px-6 py-3 rounded-lg hover:bg-[var(--link-hover-color)] transition-colors">
            {t('ctaButton')}
          </button>
        </div>

        {/* Image Column */}
        <div className="flex justify-center lg:justify-end px-6 lg:px-0">
          <Image
            src="/images/CatTablet.png"
            alt="Cat with tablet"
            className="max-h-[300px] w-auto"
            width={1000}
            height={1000}
          />
        </div>
      </div>
    </section>
  );
};

export default TestimonialsSection;
