import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Gurukul Voice Agent',
  description: 'Voice interface for the Gurukul agent',
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
