/* eslint-disable @typescript-eslint/no-unused-vars */
// middleware.ts

import { NextResponse } from 'next/server';
import createMiddleware from 'next-intl/middleware';
import { locales } from './i18n/navigation';
import type { NextRequest } from 'next/server';

const intlMiddleware = createMiddleware({
  locales: locales,
  defaultLocale: 'vi',
});

export function middleware(request: NextRequest) {
  const { pathname, origin, searchParams } = request.nextUrl;
  const accessToken = request.cookies.get('access_token');

  // Block dashboard access if not logged in
  // if (/^\/(dashboard|vi\/dashboard|en\/dashboard)(\/|$)/.test(pathname)) {
  //   if (!accessToken) {
  //     const url = request.nextUrl.clone();
  //     url.pathname = '/auth';
  //     url.searchParams.set('toast', 'require_login');
  //     return NextResponse.redirect(url);
  //   }
  // }

  // Block /auth if already logged in
  // if (/^\/(auth|vi\/auth|en\/auth)(\/|$)/.test(pathname)) {
  //   if (accessToken) {
  //     const url = request.nextUrl.clone();
  //     url.pathname = '/dashboard/personal';
  //     url.searchParams.set('toast', 'already_logged_in');
  //     return NextResponse.redirect(url);
  //   }
  // }

  // Redirect /dashboard or /vi/dashboard or /en/dashboard to /dashboard/personal (with locale if present)
  // if (/^\/(dashboard|vi\/dashboard|en\/dashboard)$/.test(pathname)) {
  //   const base = pathname.startsWith('/vi')
  //     ? '/vi'
  //     : pathname.startsWith('/en')
  //       ? '/en'
  //       : '';
  //   const url = request.nextUrl.clone();
  //   url.pathname = `${base}/dashboard/personal`;
  //   return NextResponse.redirect(url);
  // }

  const response = intlMiddleware(request);
  // If the response is a NextResponse and the status is 404, rewrite to /not-found
  if (response?.status === 404) {
    return NextResponse.rewrite('/not-found');
  }
  return response;
}

export const config = {
  matcher: [
    '/',
    '/(vi|en)/:path*',
    '/((?!api|_next|_vercel|.*\\.|robots.txt).*)',
    '/not-found',
    '/(vi|en)/not-found',
  ],
};
