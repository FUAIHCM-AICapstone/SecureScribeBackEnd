'use client';
import { ThemeProvider } from 'next-themes';
import { AuthProvider } from '../context/AuthContext';
import { WebSocketProvider } from '../context/WebSocketContext';
import { ReactQueryProvider } from '../context/ReactQueryProvider';

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider
      attribute="class"
      defaultTheme="system"
      enableSystem
      storageKey="theme"
      disableTransitionOnChange
    >
      <ReactQueryProvider>
        <AuthProvider>
          <WebSocketProvider>
            {children}
          </WebSocketProvider>
        </AuthProvider>
      </ReactQueryProvider>
    </ThemeProvider>
  );
}
