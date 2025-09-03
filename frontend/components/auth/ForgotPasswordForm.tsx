'use client';

import React, { useState } from 'react';
import { Input } from 'antd';
import Button from '@/components/ui/Button';
import { MailOutlined, ArrowLeftOutlined } from '@ant-design/icons';
import { useTranslations } from 'next-intl';
import { showToast } from '@/hooks/useShowToast';
import { initializeApp } from 'firebase/app';
import { getAuth, sendPasswordResetEmail } from 'firebase/auth';

interface ForgotPasswordFormProps {
  onBackToLogin?: () => void;
  onRegister?: () => void;
  onPasswordReset?: (email: string) => void;
}

// Firebase configuration
const firebaseConfig = {
  apiKey: "AIzaSyDui5MKg4sB4eEcMjgjVXnw-u6bLm90D4E",
  authDomain: "scribe-c7f13.firebaseapp.com",
  projectId: "scribe-c7f13",
  storageBucket: "scribe-c7f13.firebasestorage.app",
  messagingSenderId: "970064337409",
  appId: "1:970064337409:web:ab8ecc361e352c5025be00",
  measurementId: "G-NH06MQQ2J3"
};

const ForgotPasswordForm: React.FC<ForgotPasswordFormProps> = (props) => {
  const { onBackToLogin, onRegister, onPasswordReset } = props;
  const t = useTranslations('ForgotPassword');
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) {
      setError(t('errorEmail'));
      return;
    }
    setLoading(true);
    try {
      // Firebase password reset
      const app = initializeApp(firebaseConfig);
      const auth = getAuth(app);
      await sendPasswordResetEmail(auth, email);

      setSuccess(t('successMessage'));
      showToast('success', t('successMessage'), 4000);

      if (onPasswordReset) onPasswordReset(email);
    } catch (err: any) {
      console.error('Password reset error:', err);

      // Handle Firebase errors
      let errorMessage = t('errorFailed');
      if (err.code === 'auth/user-not-found') {
        errorMessage = t('noAccountFound');
      } else if (err.code === 'auth/invalid-email') {
        errorMessage = t('errorEmail');
      } else if (err.code === 'auth/invalid-credential') {
        errorMessage = t('invalidCredentialsGeneral');
      } else if (err.code === 'auth/too-many-requests') {
        errorMessage = t('tooManyRequestsGeneral');
      } else if (err.code === 'auth/network-request-failed') {
        errorMessage = t('networkErrorConnection');
      } else if (err.message) {
        // Check for token timing errors (though less likely for password reset)
        if (err.message.includes('Token used too early') ||
          err.message.includes('clock is set correctly')) {
          errorMessage = t('tokenUsedTooEarly');
        } else if (err.message.includes('Invalid token') ||
          err.message.includes('Token expired')) {
          errorMessage = t('invalidToken');
        } else {
          errorMessage = err.message;
        }
      }

      setError(errorMessage);
      showToast('error', errorMessage, 4000);
    }
    setLoading(false);
  };

  return (
    <div className="w-full max-w-xs mx-auto">
      <h2 className="text-2xl font-bold mb-2 text-center">{t('title')}</h2>
      <p className="text-gray-600 mb-6 text-center">{t('description')}</p>
      {success ? (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4 mb-6 text-green-700 text-center">
          {success}
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-5">
          <Input
            prefix={<MailOutlined />}
            type="email"
            placeholder={t('emailPlaceholder')}
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            disabled={loading}
            size="large"
            className="custom-placeholder"
          />
          {error && <div className="text-red-500 text-sm">{error}</div>}
          <div className='flex flex-row gap-4 justify-between'>
            <Button
              type="submit"
              leftIcon={<MailOutlined />}
              className="w-full py-3 rounded-xl font-semibold text-white bg-[var(--primary-color)] hover:bg-[var(--accent-color)] transition mb-2 disabled:opacity-60"
              disabled={loading}
            >
              {t('sendRequest')}
            </Button>
            <Button
              type="button"
              leftIcon={<ArrowLeftOutlined />}
              onClick={onBackToLogin}
              className="w-full py-3 rounded-xl font-semibold text-white bg-gray-700 hover:bg-gray-600 transition mb-2 disabled:opacity-60"
            >
              {t('backToLogin')}
            </Button>
          </div>
        </form>
      )}
      <div className="text-center mt-6 flex flex-col gap-2 items-center">
        <button
          type="button"
          className="text-primary hover:underline font-medium text-[var(--link-color)]"
          onClick={onRegister}
          style={{
            background: 'none',
            border: 'none',
            padding: 0,
            cursor: 'pointer',
          }}
        >
          {t('registerNow')}
        </button>
      </div>
    </div>
  );
};

export default ForgotPasswordForm;
