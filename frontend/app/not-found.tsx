import NotFound from 'components/layout/NotFound';
import '@/styles/globals.css';
import { Metadata } from 'next';

export const metadata: Metadata = {
  title: '404 - Meobeo.ai',
  description:
    'Trang bạn tìm kiếm không tồn tại hoặc đã bị di chuyển. Quay lại trang chủ Meobeo.ai để tiếp tục sử dụng các tính năng ghi chú, transcript, quản lý task và lịch sử cuộc họp tự động.',
  robots: 'noindex, nofollow',
  openGraph: {
    title: '404 - Meobeo.ai',
    description: 'Trang bạn tìm kiếm không tồn tại hoặc đã bị di chuyển.',
    url: 'https://meobeo.ai/404',
    type: 'website',
    siteName: 'Meobeo.ai',
    images: [
      {
        url: 'https://meobeo.ai/images/background-features.jpg',
        width: 1200,
        height: 630,
        alt: 'Meobeo.ai - AI Note Taker',
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
