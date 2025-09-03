'use client';

import React, { useRef } from 'react';
import { motion } from 'framer-motion';
import { useTranslations } from 'next-intl';
import Link from 'next/link';
import Image from 'next/image';
import { FaUserCircle } from 'react-icons/fa';

const HeroSection = ({ id }: { id: string }) => {
  const t = useTranslations('HomePage.hero');
  const sectionRef = useRef<HTMLDivElement | null>(null);

  interface FeatureCardProps {
    title: string;
    description: string;
    imageSrc: string;
    imageAlt: string;
    className?: string;
  }

  const FeatureCard = ({
    title,
    description,
    imageSrc,
    imageAlt,
    className = '',
  }: FeatureCardProps) => (
    <motion.div
      initial={{ opacity: 0, y: 40 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, amount: 0.5 }}
      transition={{ duration: 0.6, ease: 'easeOut' }}
      className={`flex items-center p-4 rounded-xl w-fit max-w-[400px] max-h-[150px] bg-white ${className}`}
      style={{
        color: 'var(--text-color)',
        filter: 'drop-shadow(0 4px 4px var(--primary-color, #ff9800))',
      }}
    >
      <div className="flex flex-col">
        <h3
          className="text-lg font-semibold"
          style={{ color: 'var(--primary-color)' }}
        >
          {title}
        </h3>
        <p className="text-sm" style={{ color: '#444' }}>
          {description}
        </p>
      </div>
      <div className="ml-4">
        <Image
          src={imageSrc}
          alt={imageAlt}
          width={2000}
          height={1500}
          style={{ objectFit: 'cover', objectPosition: 'center' }}
          className="w-[100%]"
        />
      </div>
    </motion.div>
  );

  return (
    <motion.section
      ref={sectionRef}
      id={id}
      className="min-h-screen flex flex-col lg:flex-row justify-center items-center py-20 lg:py-32 bg-[var(--background-color)] text-[var(--text-color)] font-[var(--font-family-base)] px-20 md:gap-y-10"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.8, ease: 'easeOut' }}
    >
      {/* Left content */}
      <motion.div
        className="lg:w-1/2 text-left space-y-6"
        initial={{ opacity: 0, x: -60 }}
        whileInView={{ opacity: 1, x: 0 }}
        viewport={{ once: true, amount: 0.5 }}
        transition={{ duration: 0.7, ease: 'easeOut' }}
      >
        <h1 className="text-5xl sm:text-7xl font-medium tracking-tight font-sofia">
          {t('welcome')}{' '}
          <span className="relative whitespace-nowrap text-[var(--primary-color)]">
            <svg
              aria-hidden="true"
              viewBox="0 0 418 42"
              className="absolute left-0 top-2/3 h-[0.58em] w-full fill-[var(--accent-color)] opacity-70"
              preserveAspectRatio="none"
            >
              <path d="M203.371.916c-26.013-2.078-76.686 1.963-124.73 9.946L67.3 12.749C35.421 18.062 18.2 21.766 6.004 25.934 1.244 27.561.828 27.778.874 28.61c.07 1.214.828 1.121 9.595-1.176 9.072-2.377 17.15-3.92 39.246-7.496C123.565 7.986 157.869 4.492 195.942 5.046c7.461.108 19.25 1.696 19.17 2.582-.107 1.183-7.874 4.31-25.75 10.366-21.992 7.45-35.43 12.534-36.701 13.884-2.173 2.308-.202 4.407 4.442 4.734 2.654.187 3.263.157 15.593-.78 35.401-2.686 57.944-3.488 88.365-3.143 46.327.526 75.721 2.23 130.788 7.584 19.787 1.924 20.814 1.98 24.557 1.332l.066-.011c1.201-.203 1.53-1.825.399-2.335-2.911-1.31-4.893-1.604-22.048-3.261-57.509-5.556-87.871-7.36-132.059-7.842-23.239-.254-33.617-.116-50.627.674-11.629.54-42.371 2.494-46.696 2.967-2.359.259 8.133-3.625 26.504-9.81 23.239-7.825 27.934-10.149 28.304-14.005.417-4.348-3.529-6-16.878-7.066Z" />
            </svg>
            <span className="relative">{t('title')}</span>
          </span>
        </h1>
        <p className="text-xl sm:text-2xl tracking-tight text-[var(--muted-text-color)]">
          {t('description')}
        </p>
        <div className="flex items-start flex-col space-x-4 space-y-8">
          <Link
            href="https://chromewebstore.google.com/detail/meowmo/eacneidbgomibehikolkflgompbohedi"
            className="inline-flex items-center text-white rounded-md hover:opacity-90 transition"
          >
            <Image
              src="/images/chrome-store.png"
              alt="Chrome Web Store"
              width={1000}
              height={800}
              style={{ objectFit: 'cover', objectPosition: 'center' }}
              className="w-[200px]"
            />
          </Link>
          <div className="flex items-center">
            <div className="flex -space-x-2">
              {Array.from({ length: 4 }).map((_, i) => (
                <FaUserCircle
                  key={i}
                  size={32}
                  className="text-gray-400 bg-white rounded-full border-2 border-white"
                />
              ))}
            </div>
            <span className="ml-3 text-sm font-medium">
              <span className="ml-1 text-gray-500">
                {t('users')} {t('userLabel')}
              </span>
            </span>
          </div>
        </div>
      </motion.div>

      {/* Right image with overlay cards */}
      <div className="lg:w-1/2 mt-[100px] md:mt-[50px] lg:ml-[100px] lg:mt-0 relative flex justify-center">
        <Image
          src="/images/laptop.png"
          alt="Laptop"
          width={1406}
          height={840}
          style={{ objectFit: 'cover', objectPosition: 'center' }}
          className="w-[600px]"
        />
        <div className="absolute top-0 left-1/4 transform -translate-x-1/2 -translate-y-1/2">
          <FeatureCard
            title={t('summaryCard.title')}
            description={t('summaryCard.description')}
            imageSrc="/images/summary-icon.png"
            imageAlt={t('summaryCard.imageAlt')}
          />
        </div>
        <div className="absolute bottom-0 right-1/4 transform translate-x-1/2 translate-y-1/2">
          <FeatureCard
            title={t('analyzeCard.title')}
            description={t('analyzeCard.description')}
            imageSrc="/images/analyze-icon.png"
            imageAlt={t('analyzeCard.imageAlt')}
          />
        </div>
      </div>
    </motion.section>
  );
};

export default HeroSection;
