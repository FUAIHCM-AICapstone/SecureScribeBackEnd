import { toast } from 'sonner';

type ToastType = 'success' | 'error' | 'warning' | 'info';

const showToast = (
  type: ToastType,
  description: string,
  duration: number = 3000,
) => {
  console.log('[showToast]', { type, description, duration });
  // Detect language from path: /vi/... or /en/...
  let lang: 'vi' | 'en' = 'en';
  if (typeof window !== 'undefined') {
    const pathLocale = window.location.pathname.split('/')[1];
    if (pathLocale === 'vi' || pathLocale === 'en') {
      lang = pathLocale as 'vi' | 'en';
    }
  }
  const titles: Record<'vi' | 'en', Record<ToastType, string>> = {
    vi: {
      success: 'Thành công',
      error: 'Lỗi',
      warning: 'Cảnh báo',
      info: 'Thông báo',
    },
    en: {
      success: 'Success',
      error: 'Error',
      warning: 'Warning',
      info: 'Info',
    },
  };

  const toastMessage = titles[lang][type];

  switch (type) {
    case 'success':
      toast.success(toastMessage, { duration, description });
      break;
    case 'error':
      toast.error(toastMessage, { duration, description });
      break;
    case 'warning':
      toast.warning(toastMessage, { duration, description });
      break;
    case 'info':
      toast.info(toastMessage, { duration, description });
      break;
    default:
      toast(toastMessage, { duration, description });
  }
};

export { showToast };
