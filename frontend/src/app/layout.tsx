import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import "../bones/registry";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Nexus AI - Voice Assistant",
  description: "Next Generation Voice-First AI Assistant",
};

import { Providers } from "@/components/Providers";
import { NexusStreamProvider } from "@/components/NexusStreamProvider";

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${inter.className} antialiased bg-neutral-950 text-white`} suppressHydrationWarning={true}>
        <Providers>
          <NexusStreamProvider>
            {children}
          </NexusStreamProvider>
        </Providers>
      </body>
    </html>
  );
}

