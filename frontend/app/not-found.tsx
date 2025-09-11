import NotFound from 'components/layout/NotFound';
import '@/styles/globals.css';
import { Metadata } from 'next';

export const metadata: Metadata = {
  title: '404 - SecureScribe',
  description:
    'Trang bạn tìm kiếm không tồn tại hoặc đã bị di chuyển. Quay lại trang chủ SecureScribe để tiếp tục sử dụng các tính năng ghi chú, transcript, quản lý task và lịch sử cuộc họp tự động.',
  robots: 'noindex, nofollow',
  openGraph: {
    title: '404 - SecureScribe',
    description: 'Trang bạn tìm kiếm không tồn tại hoặc đã bị di chuyển.',
    url: 'https://SecureScribe/404',
    type: 'website',
    siteName: 'SecureScribe',
    images: [
      {
        url: 'https://SecureScribe/images/background-features.jpg',
        width: 1200,
        height: 630,
        alt: 'SecureScribe - AI Note Taker',
      },
    ],
    locale: 'vi_VN',
  },
  icons: {
    icon: '/images/logos/logo.png',
  },
};

export default function NotFoundPage() {
  return <NotFound />;
}
