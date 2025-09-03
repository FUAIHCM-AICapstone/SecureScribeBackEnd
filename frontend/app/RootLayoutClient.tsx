/* eslint-disable @next/next/no-css-tags */
/* eslint-disable @next/next/no-page-custom-font */
// app/RootLayoutClient.tsx
'use client';
import React, { useEffect } from 'react';
import { NextIntlClientProvider } from 'next-intl';
import { ReactQueryProvider } from '@/context/ReactQueryProvider';
import { Provider } from 'react-redux';
import store from '@/store/index';
import 'antd/dist/reset.css';
import '@/styles/globals.css';
import { Providers } from './providers';
import Header from '@/components/layout/Header';
import { usePathname, useSearchParams } from 'next/navigation';
import { showToast } from '@/hooks/useShowToast';
import { Toaster } from 'sonner';
import { SidebarProvider } from '@/context/SidebarContext';
import ClientOnlyLayout from '@/components/layout/ClientOnly';

export default function RootLayoutClient({
  children,
  locale,
  messages,
}: {
  children: React.ReactNode;
  locale: string;
  messages: any;
}) {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const pathAfterLocale = pathname.split('/').slice(2).join('/');
  const hideHeader =
    pathAfterLocale.startsWith('auth') ||
    pathAfterLocale.startsWith('dashboard') ||
    pathAfterLocale.startsWith('email');

  useEffect(() => {
    const toastKey = searchParams.get('toast');
    if (toastKey) {
      // Manual key-value for translation
      const locale = pathname.split('/')[1];
      const toastMessages: Record<string, Record<string, string>> = {
        vi: {
          require_login: 'Vui lòng đăng nhập để tiếp tục',
          already_logged_in: 'Bạn đã đăng nhập rồi!',
        },
        en: {
          require_login: 'Please login to continue',
          already_logged_in: 'You already logged in',
        },
      };
      let message = toastKey;
      if (toastMessages[locale] && toastMessages[locale][toastKey]) {
        message = toastMessages[locale][toastKey];
      }
      showToast('info', message);
      // Remove 'toast' from URL without reloading
      const params = new URLSearchParams(window.location.search);
      params.delete('toast');
      const newUrl = `${window.location.pathname}${params.toString() ? `?${params.toString()}` : ''}${window.location.hash}`;
      window.history.replaceState({}, '', newUrl);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams, pathname]);

  return (
    <>
      <head>
        {/* Preload CSS để tránh FART */}
        <link
          rel="preload"
          href="https://fonts.googleapis.com/css2?family=Sofia&display=swap"
          as="style"
        />
        <link
          rel="preload"
          href="https://fonts.googleapis.com/css2?family=Afacad:ital,wght@0,400..700;1,400..700&family=Sofia&display=swap"
          as="style"
        />
      </head>
      <ClientOnlyLayout>
        <Providers>
          <Toaster richColors position="top-right" />
          <Provider store={store}>
            <ReactQueryProvider>
              <NextIntlClientProvider
                locale={locale}
                messages={messages}
                timeZone="Asia/Bangkok"
              >
                <SidebarProvider>
                  {!hideHeader && <Header />}
                  <main>{children}</main>
                </SidebarProvider>
              </NextIntlClientProvider>
            </ReactQueryProvider>
          </Provider>
        </Providers>
      </ClientOnlyLayout>
    </>
  );
}
