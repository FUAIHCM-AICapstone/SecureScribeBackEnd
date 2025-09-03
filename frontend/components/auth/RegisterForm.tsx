"use client";

import React from "react";
import authApi from '@/services/api/auth';

import { showToast } from '@/hooks/useShowToast';
import { UserOutlined, MailOutlined, LockOutlined, UserAddOutlined } from '@ant-design/icons';
import { Input, Button } from 'antd';
import { useTranslations } from 'next-intl';
import { SignupRequest, SignupResponseModel } from "types/auth.type";

interface RegisterFormProps {
  onSuccess?: (data: SignupResponseModel) => void;
  onLogin?: () => void;
  onOtp?: (email: string) => void;
}

const RegisterForm: React.FC<RegisterFormProps> = ({ onLogin, onOtp }) => {
  const [email, setEmail] = React.useState('');
  const [username, setUsername] = React.useState('');
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

  React.useEffect(() => {
    if (success) {
      showToast('success', success, 4000);
      const timer = setTimeout(() => setSuccess(null), 4000);
      return () => clearTimeout(timer);
    }
  }, [success]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username) {
      setError(t('errorUsername') || 'Vui lòng nhập tên đăng nhập.');
      return;
    }
    if (!email) {
      setError(t('errorEmail'));
      return;
    }
    if (!password) {
      setError(t('errorPassword'));
      return;
    }
    if (!confirmPassword || password !== confirmPassword) {
      setError(t('errorPassword'));
      return;
    }
    setLoading(true);
    try {
      const payload: SignupRequest = {
        email,
        username,
        password,
        confirm_password: confirmPassword,
        device_address: 'web',
      };
      const res = await authApi.signup(payload);
      if (res && res.error_code === 0) {
        setSuccess(t('registerSuccess'));
        setTimeout(() => {
          if (onOtp) onOtp(email);
        }, 1200);
      } else {
        setError(res?.message || 'Đăng ký thất bại');
      }
    } catch (err: any) {
      setError(err?.response?.data?.message || 'Đăng ký thất bại');
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
          prefix={<UserOutlined />}
          type="text"
          placeholder={t('usernamePlaceholder') || 'Tên đăng nhập'}
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          disabled={loading}
          size="large"
          style={inputStyle}
          className="custom-placeholder"
        />
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
