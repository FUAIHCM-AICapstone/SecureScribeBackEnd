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
import { useRouter } from 'next/navigation';
import { MeResponse } from 'types/auth.type';

interface LoginFormProps {
  onRegister?: () => void;
  onForgotPassword?: () => void;
  onOtp?: (email: string) => void;
}

const LoginForm: React.FC<LoginFormProps> = (props) => {
  const { onRegister, onForgotPassword } = props;
  const { login } = useAuth();
  const dispatch = useDispatch();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [rememberMe, setRememberMe] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const t = useTranslations('AuthForm');
  const router = useRouter();

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
      const res = await authApi.login({ email, password });
      if (res && res.error_code === 0 && res.data) {
        // Set cookies for access_token and refresh_token
        document.cookie = `access_token=${res.data.access_token}; path=/;`;
        document.cookie = `refresh_token=${res.data.refresh_token}; path=/;`;
        login();
        // Dispatch Redux login action with user info
        dispatch(loginAction(res.data as MeResponse));
        showToast('success', t('loginSuccess'), 3000);
        setTimeout(() => {
          router.push('/dashboard');
        }, 1000);
      } else {
        setError(res?.message || t('loginFailed'));
      }
    } catch (err: any) {
      setError(err?.response?.data?.message || t('loginFailed'));
    }
    setLoading(false);
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
