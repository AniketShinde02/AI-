import type { Metadata } from "next";
import { Inter, Geist } from "next/font/google";
import "./globals.css";
import "../bones/registry";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Nexus AI - Voice Assistant",
  description: "Next Generation Voice-First AI Assistant",
};

import { Providers } from "@/components/Providers";
import { NexusStreamProvider } from "@/components/NexusStreamProvider";
import { NexusProvider } from "@/contexts/NexusContext";
import { cn } from "@/lib/utils";

const geist = Geist({subsets:['latin'],variable:'--font-sans'});


export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={cn("font-sans", geist.variable)}>
      <body className={`${inter.className} antialiased bg-neutral-950 text-white`} suppressHydrationWarning={true}>
        <Providers>
          <NexusStreamProvider>
            <NexusProvider>
              {children}
            </NexusProvider>
          </NexusStreamProvider>
        </Providers>
      </body>
    </html>
  );
}

