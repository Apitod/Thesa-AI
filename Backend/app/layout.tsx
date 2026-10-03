import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "NeoMakalah Web",
  description: "Generator makalah berbasis template UIN, Next.js 16 + Tailwind"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="id">
      <body>{children}</body>
    </html>
  );
}
