import { createNavigation } from 'next-intl/navigation';
export const locales = ['en', 'vi'];

export const { Link, redirect, usePathname, useRouter, getPathname } =
  createNavigation();
