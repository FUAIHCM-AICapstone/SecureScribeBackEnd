import React from 'react';
import {
  HeroSection,
  FeaturesSection,
  StackSection,
} from '@/components/landing';
import TestimonialsSection from '@/components/landing/TestimonialsSection';
import FooterSection from '@/components/landing/FooterSection';
// import { getIntl } from '@/i18n/request';

export default async function HomePage() {
  // const intl = await getIntl(locale); // i18n ready
  return (
    <>
    <main className='overflow-x-hidden px-3 lg:px-32'>
      <HeroSection id="hero" />
      <FeaturesSection id="features" />
      <StackSection id="stack" />
      <TestimonialsSection id="testimonials" />
    </main>
    <FooterSection id="footer" />
    </>
  );
}
