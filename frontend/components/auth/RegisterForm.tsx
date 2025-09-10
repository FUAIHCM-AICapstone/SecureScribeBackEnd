/* eslint-disable @typescript-eslint/no-unused-vars */
"use client";

import { showToast } from '@/hooks/useShowToast';
import { LockOutlined, MailOutlined, UserAddOutlined } from '@ant-design/icons';
import { Button, Input } from 'antd';
import { initializeApp } from 'firebase/app';
import { createUserWithEmailAndPassword, getAuth, sendEmailVerification } from 'firebase/auth';
import { useTranslations } from 'next-intl';
import React from "react";
import { SignupResponseModel } from "../../types/auth.type";
import OAuthLoginButtons from './OAuthLoginButtons';

interface RegisterFormProps {
  onSuccess?: (data: SignupResponseModel) => void;
  onLogin?: () => void;
  onEmailVerification?: (email: string) => void;
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

const RegisterForm: React.FC<RegisterFormProps> = ({ onLogin, onEmailVerification }) => {
  const [email, setEmail] = React.useState('');
  const [password, setPassword] = React.useState('');
  const [confirmPassword, setConfirmPassword] = React.useState('');
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [success, setSuccess] = React.useState<string | null>(null);
  const t = useTranslations('AuthForm');

  React.useEffect(() => {
    if (error) {
      showToast('error', error, 4000);
      const timer = setTimeout(() => setError(null), 4000);
      return () => clearTimeout(timer);
    }
  }, [error]);



  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) {
      setError(t('errorEmail'));
      return;
    }
    if (!password) {
      setError(t('errorPassword'));
      return;
    }
    if (!confirmPassword || password !== confirmPassword) {
      setError(t('errorConfirmPassword'));
      return;
    }

    setLoading(true);
    try {
      // Firebase Authentication
      const app = initializeApp(firebaseConfig);
      const auth = getAuth(app);
      const userCredential = await createUserWithEmailAndPassword(auth, email, password);
      const user = userCredential.user;

      // Send email verification
      await sendEmailVerification(user);

      setSuccess(t('registerSuccess'));

      setTimeout(() => {
        if (onEmailVerification) onEmailVerification(email);
      }, 1200);
    } catch (err: any) {
      console.error('Registration error:', err);

      // Handle Firebase errors
      let errorMessage = t('networkError');
      if (err.code === 'auth/email-already-in-use') {
        errorMessage = t('emailAlreadyInUse');
      } else if (err.code === 'auth/invalid-email') {
        errorMessage = t('invalidEmail');
      } else if (err.code === 'auth/invalid-credential') {
        errorMessage = t('invalidCredentialsGeneral');
      } else if (err.code === 'auth/weak-password') {
        errorMessage = t('weakPassword');
      } else if (err.code === 'auth/operation-not-allowed') {
        errorMessage = t('operationNotAllowed');
      } else if (err.code === 'auth/network-request-failed') {
        errorMessage = t('networkErrorConnection');
      } else if (err.response) {
        // Handle backend API errors (for future use)
        const responseMessage = err.response.data?.message || err.response.data?.detail || '';

        // Check for specific token timing errors
        if (responseMessage.includes('Token used too early') ||
          responseMessage.includes('clock is set correctly')) {
          errorMessage = t('tokenUsedTooEarly');
        } else if (responseMessage.includes('Invalid token') ||
          responseMessage.includes('Token expired')) {
          errorMessage = t('invalidToken');
        } else {
          errorMessage = responseMessage || t('networkError');
        }
      } else if (err.message) {
        // Check for Firebase token timing errors
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
    }
    setLoading(false);
  };

  const handleGoogleSuccess = () => {
    // FirebaseAuth component đã handle backend API call và error handling
    // Redirect to dashboard on successful registration
    window.location.href = '/dashboard';
  };

  const inputStyle = {
    background: 'var(--background-color)',
    color: 'var(--text-color)',
    borderColor: 'var(--border-color)',
  };

  return (
    <div className="w-full">
      <form onSubmit={handleSubmit} className="space-y-5 w-full">

        <Input
          prefix={<MailOutlined />}
          type="email"
          placeholder={t('emailPlaceholder')}
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          disabled={loading}
          size="large"
          style={inputStyle}
          className="custom-placeholder"
        />
        <Input.Password
          prefix={<LockOutlined />}
          placeholder={t('passwordPlaceholder')}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          disabled={loading}
          size="large"
          style={inputStyle}
          className="custom-placeholder"
        />
        <Input.Password
          prefix={<LockOutlined />}
          placeholder={t('confirmPasswordPlaceholder') || 'Xác nhận mật khẩu'}
          value={confirmPassword}
          onChange={(e) => setConfirmPassword(e.target.value)}
          disabled={loading}
          size="large"
          style={inputStyle}
          className="custom-placeholder"
        />
        <Button
          type="primary"
          htmlType="submit"
          loading={loading}
          icon={<UserAddOutlined />}
          block
          size="large"
          style={{
            borderRadius: 6,
            background: 'var(--primary-color)',
            border: 'none',
          }}
        >
          {t('registerNow')}
        </Button>

        {/* Separator */}
        <div className="flex items-center w-full my-4">
          <div className="flex-1 h-px bg-gray-300" />
          <span className="mx-3 text-sm text-gray-500">hoặc</span>
          <div className="flex-1 h-px bg-gray-300" />
        </div>

        {/* OAuth Login Buttons */}
        <div className="space-y-3">
          <OAuthLoginButtons onSuccess={handleGoogleSuccess} />
        </div>

        <div className="text-center mt-6">
          <span className="text-sm text-[var(--text-color)]">
            {t('haveAccount') || 'Đã có tài khoản?'}{' '}
            <button
              type="button"
              className="text-primary hover:underline font-medium text-[var(--link-color)]"
              onClick={onLogin}
            >
              {t('loginButton')}
            </button>
          </span>
        </div>
      </form>
    </div>
  );
};

export default RegisterForm;
