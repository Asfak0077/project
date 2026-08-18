import type { Metadata } from "next";
import { Plus_Jakarta_Sans, Inter } from "next/font/google";
import Script from "next/script";
import "./globals.css";

const plusJakarta = Plus_Jakarta_Sans({
  subsets: ["latin"],
  variable: "--font-heading",
  weight: ["400", "500", "600", "700", "800"],
  display: "swap",
});

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
  weight: ["400", "500", "600", "700"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "VersusAI — Smart Hardware Comparison & AI Spec Engine",
  description:
    "Compare laptops, smartphones, and tech hardware with verified zero-hallucination RAG AI datasheets and live performance benchmarks.",
  keywords: ["product comparison", "laptop finder", "AI spec comparison", "tech specs", "RAG engine"],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="light scroll-smooth">
      <head>
        <Script
          src="https://accounts.google.com/gsi/client"
          strategy="beforeInteractive"
        />
      </head>
      <body
        className={`${plusJakarta.variable} ${inter.variable} font-sans text-slate-900 bg-[#F8FAFC] min-h-screen antialiased selection:bg-blue-600 selection:text-white`}
      >
        {children}
      </body>
    </html>
  );
}
