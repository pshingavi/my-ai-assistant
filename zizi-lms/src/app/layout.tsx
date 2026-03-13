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
      <body className="antialiased">
        <GlobalNav />
        {children}
        <Toaster
          position="bottom-right"
          toastOptions={{
            style: {
              background: '#ffffff',
              color: '#1e1b4b',
              border: '1px solid rgba(124,58,237,0.15)',
              borderRadius: '12px',
              fontSize: '14px',
              boxShadow: '0 4px 24px rgba(124,58,237,0.1)',
            },
            success: {
              iconTheme: { primary: '#7c3aed', secondary: '#ffffff' },
            },
            error: {
              iconTheme: { primary: '#dc2626', secondary: '#ffffff' },
            },
          }}
        />
      </body>
    </html>
  );
}
