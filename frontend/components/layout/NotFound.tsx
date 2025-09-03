'use client';

import React from 'react';
import { useRouter } from 'next/navigation';
import { IoArrowBack, IoHome } from 'react-icons/io5';
import LightRays from '../animations/LightRays';
import FuzzyText from '../animations/FuzzyText';

const NotFoundPage = () => {
  const router = useRouter();

  const handleGoBack = () => {
    router.push('/');
  };

  const handleGoHome = () => {
    router.push('/dashboard');
  };

  return (
    <div className="relative min-h-screen w-full bg-black overflow-hidden flex flex-col items-center justify-center">
      {/* Light rays background */}
      <div className="absolute inset-0 z-10">
        <LightRays
          raysOrigin="top-center"
          raysColor="#7c3aed"
          raysSpeed={1.5}
          lightSpread={2}
          rayLength={10}
          followMouse={false}
          mouseInfluence={0}
          noiseAmount={0}
          distortion={0}
          className="custom-rays"
        />
      </div>

      {/* Main content */}
      <div className="flex flex-col items-center justify-center gap-8 z-10">
        <FuzzyText baseIntensity={0.4} enableHover={true}>
          404
        </FuzzyText>
        <FuzzyText baseIntensity={0.4} enableHover={false}>
          Not Found
        </FuzzyText>
        <div className="flex gap-6 mt-6">
          <button
            onClick={handleGoBack}
            className="flex items-center gap-2 rounded-full bg-white p-5 shadow hover:bg-gray-200 transition cursor-pointer"
            aria-label="Go Back"
          >
            <IoArrowBack className="text-black text-3xl" />
            <span className="font-semibold text-black hidden sm:inline">Quay lại</span>
          </button>
          <button
            onClick={handleGoHome}
            className="flex items-center gap-2 rounded-full bg-white p-5 shadow hover:bg-gray-200 transition cursor-pointer"
            aria-label="Go Home"
          >
            <IoHome className="text-black text-3xl" />
            <span className="font-semibold text-black hidden sm:inline">Trang chủ</span>
          </button>
        </div>
      </div>
    </div>
  );
};

export default NotFoundPage;
