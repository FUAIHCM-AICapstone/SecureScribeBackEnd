import React, { useRef } from 'react';
import Image from 'next/image';
import { useTranslations } from 'next-intl';

function useFeatureTranslations() {
  const t = useTranslations('HomePage.features.carousel.features');
  // next-intl does not support returning arrays directly, so we fallback to manual mapping
  return [0, 1, 2, 3].map((idx) => ({
    title: t(`${idx}.title`),
    subtitle: t(`${idx}.subtitle`),
    imageUrl: '/images/CarouselBackGround.png',
  }));
}

function FeatureCard({
  title,
  subtitle,
  imageUrl,
}: {
  title: string;
  subtitle: string;
  imageUrl: string;
}) {
  return (
    <div className="relative rounded-3xl overflow-hidden w-[450px] h-[500px] flex-shrink-0 snap-start">
      <Image
        src={imageUrl}
        alt={title}
        fill
        className="object-cover w-full h-full rounded-xl blur-sm"
        style={{ zIndex: 0 }}
      />
      <div className="absolute inset-0 z-10" />
      <div className="absolute top-10 left-10 z-20 p-6 flex flex-col h-full justify-start">
        <h3 className="text-white text-2xl font-bold mb-2">{title}</h3>
        <p className="text-white text-sm leading-snug max-w-xs">{subtitle}</p>
      </div>
    </div>
  );
}

export default function FeatureCarousel({
  carouselRef,
}: {
  carouselRef: React.RefObject<HTMLDivElement>;
}) {
  const features = useFeatureTranslations();
  const localRef = useRef<HTMLDivElement | null>(null);
  return (
    <div className="relative w-full py-8" ref={localRef}>
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
          {features.map((f, idx) => (
            <div
              key={idx}
              className="min-w-[400px] max-w-[600px] flex-shrink-0 snap-start"
              style={{ flex: '0 0 auto' }}
            >
              <FeatureCard {...f} />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
