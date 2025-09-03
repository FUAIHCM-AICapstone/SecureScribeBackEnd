
// app/layout.tsx
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning={true} className="bg-[var(--background-color)] text-[var(--text-color)]">
      <body style={{ fontFamily: 'var(--font-family-base)' }}>
        {children}
      </body>
    </html>
  );
}