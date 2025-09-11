// app/RootLayoutServer.tsx
import React from 'react';
import { getMessages } from 'next-intl/server';
import RootLayoutClient from './RootLayoutClient';
import { seoConfig } from 'config/seo';
import { Metadata } from 'next';

type Props = {
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
};

export async function generateMetadata(): Promise<Metadata> {
  return {
    title: 'SecureScribe',
    description: seoConfig.description,
    openGraph: {
      title: 'SecureScribe',
      description: seoConfig.openGraph.description,
      url: seoConfig.openGraph.url,
      type: seoConfig.openGraph.type as 'website',
      siteName: seoConfig.openGraph.site_name,
      images: seoConfig.openGraph.images,
      locale: seoConfig.openGraph.locale,
    },
    robots: seoConfig.advancedSEO?.metaRobots || 'index, follow',
    alternates: {
      canonical: seoConfig.canonical || seoConfig.url,
      languages: seoConfig.advancedSEO?.alternateLangs?.reduce(
        (acc, lang) => {
          acc[lang.hrefLang] = lang.href;
          return acc;
        },
        {} as Record<string, string>,
      ),
    },
    authors: [{ name: 'SecureScribe Meeting', url: seoConfig.url }],
    keywords: seoConfig.keywords,
    icons: {
      icon: '/images/logos/logo.png',
    },
    other: {
      contact: seoConfig.contact?.email,
      support: seoConfig.support?.email,
      region: seoConfig.product?.region,
      uiux: seoConfig.product?.uiux,
      pricing: seoConfig.product?.pricing,
      security: seoConfig.product?.security?.note,
    },
  };
}

export default async function RootLayoutServer(props: Props) {
  const { params } = props;
  const resolvedParams = await params;
  const locale = resolvedParams.locale;
  const messages = await getMessages({ locale });

  return (
    <RootLayoutClient locale={locale} messages={messages}>
      {props.children}
    </RootLayoutClient>
  );
}
