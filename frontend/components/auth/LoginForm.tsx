'use client';

import React, { useEffect, useState } from 'react';
import { useAuth } from '@/context/AuthContext';
import { useDispatch } from 'react-redux';
import { login as loginAction } from '@/store/slices/authSlice';
import { showToast } from '@/hooks/useShowToast';
import authApi from '@/services/api/auth';
import { LockOutlined, LoginOutlined, MailOutlined } from '@ant-design/icons';
import { Button, Checkbox, Input } from 'antd';
import { useTranslations } from 'next-intl';
import { MeResponse } from '../../types/auth.type';
import Cookies from 'js-cookie';
import OAuthLoginButtons from './OAuthLoginButtons';
import { initializeApp } from 'firebase/app';
import { getAuth, signInWithEmailAndPassword, sendEmailVerification } from 'firebase/auth';

interface LoginFormProps {
  onRegister?: () => void;
  onForgotPassword?: () => void;
  onSuccess?: () => void;
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

const LoginForm: React.FC<LoginFormProps> = (props) => {
  const { onRegister, onForgotPassword, onSuccess } = props;
  const { login } = useAuth();
  const dispatch = useDispatch();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [rememberMe, setRememberMe] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const t = useTranslations('AuthForm');

  useEffect(() => {
    if (error) {
      showToast('error', error, 4000);
      const timer = setTimeout(() => setError(null), 4000);
      return () => clearTimeout(timer);
    }
  }, [error]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    if (!email) {
      setError(t('errorEmail'));
      setLoading(false);
      return;
    }
    if (!password) {
      setError(t('errorPassword'));
      setLoading(false);
      return;
    }

    try {
      // Firebase Authentication
      const app = initializeApp(firebaseConfig);
      const auth = getAuth(app);
      const userCredential = await signInWithEmailAndPassword(auth, email, password);
      const user = userCredential.user;

      // Check if email is verified
      if (!user.emailVerified) {
        // Send verification email
        await sendEmailVerification(user);
        setError(t('emailNotVerified'));
        setLoading(false);
        return;
      }

      // Get Firebase ID token
      const idToken = await user.getIdToken();

      // Call backend API with Firebase ID token
      const res = await authApi.firebaseLogin({ id_token: idToken });

      if (res && res.success && res.data) {
        // Set cookies for access_token and refresh_token
        Cookies.set('access_token', res.data.token.access_token, { expires: 7 });
        Cookies.set('refresh_token', res.data.token.refresh_token, { expires: 30 });

        // Call login with tokens and user data
        login(res.data.token, res.data.user);
        // Dispatch Redux login action with user info
        dispatch(loginAction({
          id: res.data.user.id,
          email: res.data.user.email,
          name: res.data.user.name,
          avatar_url: res.data.user.avatar_url
        } as MeResponse));
        onSuccess?.();
      } else {
        setError(res?.message || t('networkError'));
      }
    } catch (err: any) {
      console.error('Login error:', err);

      // Handle Firebase errors
      let errorMessage = t('networkError');
      if (err.code === 'auth/user-not-found') {
        errorMessage = t('userNotFound');
      } else if (err.code === 'auth/wrong-password') {
        errorMessage = t('wrongPassword');
      } else if (err.code === 'auth/invalid-email') {
        errorMessage = t('invalidEmail');
      } else if (err.code === 'auth/invalid-credential') {
        errorMessage = t('invalidCredentials');
      } else if (err.code === 'auth/user-disabled') {
        errorMessage = t('userDisabled');
      } else if (err.code === 'auth/too-many-requests') {
        errorMessage = t('tooManyRequests');
      } else if (err.code === 'auth/network-request-failed') {
        errorMessage = t('networkErrorConnection');
      } else if (err.response) {
        // Handle backend API errors
        const responseMessage = err.response.data?.message || err.response.data?.detail || '';

        // Check for specific token timing errors
        if (responseMessage.includes('Token used too early') ||
          responseMessage.includes('clock is set correctly') ||
          responseMessage.includes('Invalid Google token')) {
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
    // Chúng ta chỉ cần call onSuccess callback ở đây
    onSuccess?.();
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

        <div className="flex items-center justify-between text-[var(--text-color)]">
          <Checkbox
            checked={rememberMe}
            onChange={(e) => setRememberMe(e.target.checked)}
            disabled={loading}
            style={{ color: 'var(--text-color)' }}
          >
            {t('rememberMe')}
          </Checkbox>
          <button
            type="button"
            className="text-primary hover:underline text-sm font-medium"
            style={{
              color: 'var(--link-color)',
              background: 'none',
              border: 'none',
              padding: 0,
              cursor: 'pointer',
            }}
            onClick={onForgotPassword}
          >
            {t('forgotPassword')}
          </button>
        </div>

        <Button
          type="primary"
          htmlType="submit"
          loading={loading}
          icon={<LoginOutlined />}
          block
          size="large"
          style={{
            borderRadius: 6,
            background: 'var(--primary-color)',
            border: 'none',
          }}
        >
          {t('loginButton')}
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
            {t('noAccount')}{' '}
            <button
              type="button"
              className="text-primary hover:underline font-medium text-[var(--link-color)]"
              onClick={onRegister}
            >
              {t('registerNow')}
            </button>
          </span>
        </div>
      </form>
    </div>
  );
};

export default LoginForm;
