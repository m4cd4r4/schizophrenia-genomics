import type { Metadata } from "next";
import { Geist_Mono, DM_Sans, Instrument_Serif } from "next/font/google";
import "./globals.css";
import Providers from "./providers";
import AppShell from "@/components/layout/app-shell";

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
  display: "swap",
});

const dmSans = DM_Sans({
  variable: "--font-dm-sans",
  subsets: ["latin"],
  weight: ["300", "400", "500", "600"],
  display: "swap",
});

const instrumentSerif = Instrument_Serif({
  variable: "--font-instrument-serif",
  subsets: ["latin"],
  weight: "400",
  style: ["normal", "italic"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "SCZ Genomics",
  description: "Schizophrenia transcriptomics pipeline — 3 GEO datasets, 10-stage analysis, RAG query interface",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className={`${geistMono.variable} ${dmSans.variable} ${instrumentSerif.variable} antialiased`}>
        <Providers>
          <AppShell>{children}</AppShell>
        </Providers>
      </body>
    </html>
  );
}
