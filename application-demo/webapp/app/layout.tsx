import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'LamiSema — Nepali PDF Extraction',
  description: 'Structured information extraction for Nepali and multilingual PDFs',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}
