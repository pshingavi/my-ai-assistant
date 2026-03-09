import type { Metadata } from 'next';
import { Toaster } from 'react-hot-toast';
import GlobalNav from '@/src/components/GlobalNav';
import './globals.css';

export const metadata: Metadata = {
  title: 'Zizi Byte — Learn in bytes. Think in leaps.',
  description:
    'Adaptive AI micro-learning platform that transforms dense course materials into personalized, analogy-driven learning experiences.',
  keywords: ['AI', 'learning', 'micro-learning', 'education', 'LMS'],
  icons: {
    icon: "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>⚡</text></svg>",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link
          rel="preconnect"
          href="https://fonts.gstatic.com"
          crossOrigin="anonymous"
        />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="antialiased" style={{ background: '#0a0a0f', color: '#f1f5f9' }}>
        <GlobalNav />
        {children}
        <Toaster
          position="bottom-right"
          toastOptions={{
            style: {
              background: '#13131a',
              color: '#f1f5f9',
              border: '1px solid rgba(139,92,246,0.3)',
              borderRadius: '10px',
              fontSize: '14px',
            },
            success: {
              iconTheme: {
                primary: '#8b5cf6',
                secondary: '#0a0a0f',
              },
            },
            error: {
              iconTheme: {
                primary: '#f87171',
                secondary: '#0a0a0f',
              },
            },
          }}
        />
      </body>
    </html>
  );
}
