import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Providers } from "@/lib/providers";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
});

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 5,
  interactiveWidget: "resizes-content",
  themeColor: "#0891B2",
};

export const metadata: Metadata = {
  title: {
    default: "DentalOS",
    template: "%s | DentalOS",
  },
  description: "Software dental para clínicas en Latinoamérica",
  keywords: ["dental", "software", "clínica", "odontología", "Colombia", "LATAM"],
  authors: [{ name: "DentalOS" }],
  manifest: "/manifest.json",
  icons: {
    icon: [
      { url: "/favicon.svg", type: "image/svg+xml" },
      { url: "/icons/icon-192.png", type: "image/png", sizes: "192x192" },
    ],
    apple: "/icons/icon-192.png",
  },
  robots: {
    index: false, // SaaS app — do not index dashboard pages
    follow: false,
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="es-419" suppressHydrationWarning>
      <body className={inter.variable}>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
