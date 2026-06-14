import type { Metadata } from "next";
import { Inter, Geist, Quantico } from "next/font/google";
import "./globals.css";
import "../bones/registry";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Nexus AI - Voice Assistant",
  description: "Next Generation Voice-First AI Assistant",
};

import { Providers } from "@/components/Providers";
import { VoiceProvider } from "@/contexts/VoiceContext";
import { NexusStreamProvider } from "@/components/NexusStreamProvider";
import { NexusProvider } from "@/contexts/NexusContext";
import { cn } from "@/lib/utils";
import { TopNav } from "@/components/layout/TopNav";

const geist = Geist({subsets:['latin'],variable:'--font-sans'});
const quantico = Quantico({
  weight: ['400', '700'],
  subsets: ['latin'],
  variable: '--font-quantico',
});

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={cn("font-sans", geist.variable, quantico.variable)}>
      <body className={`${inter.className} antialiased bg-[#06060c] text-white`} suppressHydrationWarning={true}>
        <Providers>
          <VoiceProvider>
            <NexusStreamProvider>
              <NexusProvider>
                <div className="flex flex-col h-screen overflow-hidden max-w-[1800px] mx-auto w-full relative z-10">
                  <TopNav />
                  <div className="flex-1 overflow-hidden">
                    {children}
                  </div>
                </div>
              </NexusProvider>
            </NexusStreamProvider>
          </VoiceProvider>
        </Providers>
      </body>
    </html>
  );
}

