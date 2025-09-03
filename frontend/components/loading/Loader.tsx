'use client';

import React, { useEffect, useState } from 'react';
import { useTheme } from 'next-themes';
import { FiLoader } from 'react-icons/fi';
import { motion, AnimatePresence } from 'framer-motion';

interface LoaderProps {
  fallbackMessage?: string;
}

const Loader: React.FC<LoaderProps> = ({ fallbackMessage = 'Loading...' }) => {
  const { resolvedTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const overlayVariants = {
    hidden: { opacity: 0 },
    visible: { opacity: 1 },
    exit: { opacity: 0 }
  };

  const spinnerVariants = {
    animate: { rotate: 360 },
  };

  if (!mounted || resolvedTheme === undefined) {
    return (
      <AnimatePresence>
        <motion.div
          className="fixed inset-0 flex flex-col items-center justify-center bg-white dark:bg-[#1a1a1a] z-50"
          variants={overlayVariants}
          initial="hidden"
          animate="visible"
          exit="exit"
          transition={{ duration: 0.3 }}
        >
          <motion.div
            className="p-4 rounded-full bg-gray-100 dark:bg-[#2a2a2a] shadow-lg"
            variants={spinnerVariants}
            animate="animate"
            transition={{ repeat: Infinity, ease: 'linear', duration: 1 }}
          >
            <FiLoader className="w-8 h-8 text-gray-500 dark:text-gray-400" />
          </motion.div>
          <p className="mt-3 text-sm text-gray-600 dark:text-gray-300">
            {fallbackMessage}
          </p>
        </motion.div>
      </AnimatePresence>
    );
  }

  return null;
};

export default Loader;
