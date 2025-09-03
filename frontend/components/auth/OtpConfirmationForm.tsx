'use client';

import React from 'react';
import { Button, Input } from 'antd';
import { AiOutlineCheckCircle, AiOutlineSync } from 'react-icons/ai';
import authApi from '@/services/api/auth';

interface OtpConfirmationFormProps {
  email: string;
  onSubmit: (otp: string, email: string) => Promise<void>;
  isLoading?: boolean;
  resendOTP?: () => Promise<void>;
  purpose: 'registration' | 'passwordReset' | 'login';
}

const OtpConfirmationForm: React.FC<OtpConfirmationFormProps> = ({
  email,
  onSubmit,
  isLoading = false,
  purpose,
}) => {
  // OTP state
  const [otp, setOtp] = React.useState<string[]>(Array(6).fill(''));
  const [otpError, setOtpError] = React.useState<string | null>(null);
  const inputRefs = React.useRef<(HTMLInputElement | null)[]>([]);
  const [isSubmitting, setIsSubmitting] = React.useState(false);
  const [isResending, setIsResending] = React.useState(false);
  const [resendCooldown, setResendCooldown] = React.useState(0);
  const [canResend, setCanResend] = React.useState(true);

  const isProcessing = isLoading || isSubmitting;

  // OTP validation
  const validateOtp = (otpArr: string[]) => {
    const otpValue = otpArr.join('');
    if (otpValue.length !== 6 || !/^[0-9]{6}$/.test(otpValue)) {
      setOtpError('Mã OTP phải gồm 6 chữ số.');
      return { isValid: false };
    }
    setOtpError(null);
    return { isValid: true };
  };

  const handleDigitInput = (index: number, value: string) => {
    if (!/^[0-9]?$/.test(value)) return;
    const newOtp = [...otp];
    newOtp[index] = value;
    setOtp(newOtp);
    if (value && index < 5) {
      inputRefs.current[index + 1]?.focus?.();
    }
  };

  // Handle key down (backspace, arrow)
  const handleKeyDown = (
    index: number,
    e: React.KeyboardEvent<HTMLInputElement>,
  ) => {
    if (e.key === 'Backspace' && !otp[index] && index > 0) {
      inputRefs.current[index - 1]?.focus?.();
    }
    if (e.key === 'ArrowLeft' && index > 0) {
      inputRefs.current[index - 1]?.focus?.();
    }
    if (e.key === 'ArrowRight' && index < 5) {
      inputRefs.current[index + 1]?.focus?.();
    }
  };

  // Handle paste
  const handlePaste = (e: React.ClipboardEvent<HTMLInputElement>) => {
    const paste = e.clipboardData.getData('text').slice(0, 6);
    if (/^[0-9]{6}$/.test(paste)) {
      setOtp(paste.split(''));
      inputRefs.current[5]?.focus?.();
    }
    e.preventDefault();
  };

  // Resend OTP cooldown logic
  React.useEffect(() => {
    let timer: NodeJS.Timeout;
    if (isResending) {
      setCanResend(false);
      setResendCooldown(30);
      timer = setInterval(() => {
        setResendCooldown((prev) => {
          if (prev <= 1) {
            setCanResend(true);
            setIsResending(false);
            clearInterval(timer);
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    }
    return () => clearInterval(timer);
  }, [isResending]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const validationResult = validateOtp(otp);
    if (!validationResult.isValid) {
      return;
    }
    try {
      setIsSubmitting(true);
      await onSubmit(otp.join(''), email);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleResendClick = async () => {
    if (!canResend) return;
    setIsResending(true);
    try {
      // Call API to resend OTP (email verification)
      await authApi.requestEmailVerification({ email });
    } catch (error) {
      console.error('Failed to resend OTP:', error);
      setIsResending(false);
      setCanResend(true);
    }
  };

  // Purpose-specific title and description
  const getPurposeText = () => {
    switch (purpose) {
      case 'registration':
        return {
          title: 'Xác thực email đăng ký',
          description:
            'Vui lòng nhập mã OTP được gửi đến email của bạn để hoàn tất quá trình đăng ký.',
        };
      case 'passwordReset':
        return {
          title: 'Xác thực đặt lại mật khẩu',
          description:
            'Vui lòng nhập mã OTP được gửi đến email của bạn để tiếp tục quá trình đặt lại mật khẩu.',
        };
      default:
        return {
          title: 'Xác thực OTP',
          description: 'Vui lòng nhập mã OTP được gửi đến email của bạn.',
        };
    }
  };

  const purposeText = getPurposeText();

  return (
    <div className="w-full">
      <div className="text-center mb-6">
        <h2 className="text-2xl font-bold mb-2">{purposeText.title}</h2>
        <p className="text-gray-600 mb-4">{purposeText.description}</p>
        <p className="text-sm text-gray-500">
          Mã xác thực đã được gửi đến:{' '}
          <span className="font-medium text-primary-600">{email}</span>
        </p>
      </div>
      <form onSubmit={handleSubmit} className="space-y-5 w-full">
        <div className="flex justify-between gap-2 mb-1">
          {Array.from({ length: 6 }).map((_, index) => (
            <Input
              key={index}
              type="text"
              ref={(el) => {
                // AntD Input exposes the native input via el?.input
                inputRefs.current[index] = el?.input || null;
              }}
              value={otp[index] || ''}
              onChange={(e) => handleDigitInput(index, e.target.value)}
              onKeyDown={(e) => handleKeyDown(index, e)}
              onPaste={index === 0 ? handlePaste : undefined}
              maxLength={1}
              inputMode="numeric"
              autoComplete="one-time-code"
              size="large"
              className="text-center font-bold"
              style={{ width: 48, height: 56, padding: 0 }}
            />
          ))}
        </div>
        <input type="hidden" name="otp" value={otp.join('')} />
        {otpError && (
          <div className="text-red-500 text-sm mt-1 text-left">{otpError}</div>
        )}
        <Button
          type="primary"
          htmlType="submit"
          loading={isProcessing}
          icon={!isProcessing ? <AiOutlineCheckCircle /> : undefined}
          block
          size="large"
          style={{
            borderRadius: 6,
            background: 'var(--primary-color)',
            border: 'none',
          }}
          disabled={isProcessing || otp.join('').length < 6}
        >
          Xác Nhận
        </Button>
      </form>
      <div className="text-center mt-6 flex flex-col gap-4">
        <span className="text-sm text-gray-600">Chưa nhận được mã OTP?</span>
        <Button
          type="default"
          icon={<AiOutlineSync />}
          onClick={handleResendClick}
          disabled={isResending || !canResend}
          loading={isResending}
          style={{ borderRadius: 6 }}
        >
          {canResend ? 'Gửi lại mã OTP' : `Gửi lại sau (${resendCooldown}s)`}
        </Button>
      </div>
    </div>
  );
};

export default OtpConfirmationForm;
