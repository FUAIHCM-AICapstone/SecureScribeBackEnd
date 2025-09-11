export const seoConfig = {
  title: 'SecureScribe', // <= 60 ký tự
  description:
    'SecureScribe giúp ghi chú, transcript, quản lý task và lịch sử cuộc họp tự động. Tiết kiệm 60% thời gian, bảo mật chuẩn quốc tế, tích hợp Google Meet, Zoom, Webex.', // 155-160 ký tự
  url: 'https://SecureScribe/',
  openGraph: {
    type: 'website',
    locale: 'vi_VN',
    url: 'https://SecureScribe/',
    title: 'SecureScribe',
    description:
      'SecureScribe giúp ghi chú, transcript, quản lý task và lịch sử cuộc họp tự động. Tiết kiệm 60% thời gian, bảo mật chuẩn quốc tế, tích hợp Google Meet, Zoom, Webex.',
    site_name: 'SecureScribe',
    images: [
      {
        url: 'https://SecureScribe/images/background-features.jpg',
        width: 1200,
        height: 630,
        alt: 'SecureScribe - AI Note Taker',
      },
    ],
  },
  favicon: '/images/logos/logo.png',
  canonical: 'https://SecureScribe/',
  keywords: [
    'AI Note Taker',
    'ghi chú cuộc họp tự động',
    'ghi âm meeting',
    'transcript tự động',
    'quản lý cuộc họp',
    'export meeting note',
    'tích hợp Google Calendar',
    'bảo mật dữ liệu',
    'SecureScribe',
  ],
  schema: {
    faq: true,
    product: true,
  },
  contact: {
    email: 'assistant.meowmo@gmail.com',
    support: 'email',
  },
  kpi: {
    target: 'Top 3 Google',
    organicTraffic: '+30%',
    timeOnPage: '>2 phút',
    bounceRate: '<50%',
    leads: 'Tăng chuyển đổi dùng thử',
    note: 'Theo dõi bằng Google Analytics, Search Console, Hotjar',
  },
  competitors: [
    {
      name: 'Fireflies.ai',
      strengths: 'Nhiều tích hợp, đa ngôn ngữ, nhận diện giọng nói tốt',
      weaknesses:
        'UI phức tạp, giá cao, chưa tối ưu cho người Việt, không hỗ trợ tốt tiếng Việt',
      url: 'https://fireflies.ai/',
    },
    {
      name: 'Otter.ai',
      strengths: 'Tự động hóa ghi chú, tích hợp Zoom',
      weaknesses: 'Chưa hỗ trợ tiếng Việt, giá cao',
      url: 'https://otter.ai/',
    },
  ],
  product: {
    name: 'SecureScribe',
    slogan: 'AI Note Taker cho doanh nghiệp Việt',
    features: [
      'Tự động ghi âm và ghi chú cuộc họp',
      'Tạo transcript chi tiết',
      'Theo dõi task và phân công công việc',
      'Lưu trữ lịch sử cuộc họp, tìm kiếm nhanh',
      'Export meeting note ra PDF',
      'Tích hợp Google Calendar, Google Meet, Zoom, Webex',
      'Bảo mật dữ liệu chuẩn quốc tế (mã hoá, tuân thủ GDPR)',
      'Giao diện thân thiện, nhiều thông tin, dễ sử dụng',
    ],
    painPoints: [
      'Lười ghi chú, dễ bỏ sót thông tin khi họp online',
      'Không có người take note chuyên nghiệp',
      'Ghi chú thủ công gây sao nhãng, mất tập trung',
      'Khó tìm lại lịch sử cuộc họp, task bị quên',
    ],
    targetUsers: [
      'Doanh nghiệp vừa và nhỏ (SME)',
      'Startup, đội nhóm công nghệ',
      'Nhân viên văn phòng, quản lý dự án',
      'Sinh viên, giáo viên, lớp học online',
    ],
    useCases: [
      'Họp dự án, họp nội bộ công ty',
      'Sales call, demo sản phẩm',
      'Lớp học trực tuyến, hội thảo',
    ],
    integrations: ['Google Meet', 'Zoom', 'Webex', 'Google Calendar'],
    security: {
      gdpr: true,
      encryption: 'AES-256',
      iso: false,
      note: 'Cam kết bảo mật dữ liệu, không chia sẻ với bên thứ ba',
    },
    cta: {
      text: 'Liên hệ dùng thử miễn phí',
      email: 'assistant.meowmo@gmail.com',
      button: 'Gửi email',
    },
    languages: ['vi', 'en'],
    region: 'Việt Nam, ưu tiên người Việt',
    uiux: 'Giao diện nhiều thông tin, thân thiện, dễ thao tác',
    demo: false,
    pricing: 'Miễn phí giai đoạn đầu, chưa có subscription',
    faq: true,
    schema: {
      faq: true,
      product: true,
      organization: true,
    },
  },
  advancedSEO: {
    metaRobots: 'index, follow',
    ogType: 'website',
    ogLocale: 'vi_VN',
    ogImage: 'https://SecureScribe/images/background-features.jpg',
    canonical: 'https://SecureScribe/',
    alternateLangs: [
      { hrefLang: 'vi', href: 'https://SecureScribe/' },
      { hrefLang: 'en', href: 'https://SecureScribe/en' },
    ],
    structuredData: true,
  },
  support: {
    email: 'assistant.meowmo@gmail.com',
    livechat: false,
    hotline: false,
    responseTime: 'Trong vòng 24h',
  },
  publish: {
    schedule: 'Xuất bản ngay khi hoàn thiện',
    updateFrequency: 'Cập nhật khi có tính năng mới',
  },
};
