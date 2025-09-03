'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { showToast } from '@/hooks/useShowToast';
import LoginForm from './LoginForm';
import RegisterForm from './RegisterForm';
import ForgotPasswordForm from './ForgotPasswordForm';

const AuthWrapper: React.FC = () => {
  const [view, setView] = useState<'login' | 'register' | 'forgot' | 'emailVerification' | 'passwordReset'>('login');
  const [pendingEmail, setPendingEmail] = useState<string>('');
  const router = useRouter();
  const t = useTranslations('AuthForm');
  const tEmailVerification = useTranslations('EmailVerification');
  const tPasswordReset = useTranslations('PasswordReset');

  const handleAuthSuccess = () => {
    showToast('success', t('loginSuccess'), 3000);
    router.push('/dashboard');
  };

  if (view === 'register') {
    return (
      <RegisterForm
        onLogin={() => setView('login')}
        onEmailVerification={(email: string) => {
          setPendingEmail(email);
          setView('emailVerification');
        }}
      />
    );
  }

  if (view === 'forgot') {
    return (
      <ForgotPasswordForm
        onBackToLogin={() => setView('login')}
        onRegister={() => setView('register')}
        onPasswordReset={(email: string) => {
          setPendingEmail(email);
          setView('passwordReset');
        }}
      />
    );
  }

  if (view === 'emailVerification') {
    return (
      <div className="w-full max-w-xs mx-auto text-center">
        <h2 className="text-2xl font-bold mb-4">{tEmailVerification('title')}</h2>
        <p className="text-gray-600 mb-6">
          <span className="break-words inline-block max-w-full">
            {tEmailVerification('description')} <strong className="break-words">{pendingEmail}</strong>.
          </span>
          {tEmailVerification('instructions')}
        </p>
        <button
          onClick={() => setView('login')}
          className="w-full py-3 rounded-xl font-semibold text-white bg-[var(--primary-color)] hover:bg-[var(--accent-color)] transition mb-2"
        >
          {tEmailVerification('verifiedButton')}
        </button>
        <button
          onClick={() => setView('register')}
          className="w-full py-3 rounded-xl font-semibold text-gray-700 bg-gray-200 hover:bg-gray-300 transition"
        >
          {tEmailVerification('backToRegister')}
        </button>
      </div>
    );
  }

  if (view === 'passwordReset') {
    return (
      <div className="w-full max-w-xs mx-auto text-center">
        <h2 className="text-2xl font-bold mb-4">{tPasswordReset('title')}</h2>
        <p className="text-gray-600 mb-6">
          {tPasswordReset('description')} <strong>{pendingEmail}</strong>.
          {tPasswordReset('instructions')}
        </p>
        <button
          onClick={() => setView('login')}
          className="w-full py-3 rounded-xl font-semibold text-white bg-[var(--primary-color)] hover:bg-[var(--accent-color)] transition"
        >
          {tPasswordReset('backToLogin')}
        </button>
      </div>
    );
  }

  return (
    <LoginForm
      onRegister={() => setView('register')}
      onForgotPassword={() => setView('forgot')}
      onSuccess={handleAuthSuccess}
    />
  );
};

export default AuthWrapper;
