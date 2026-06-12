"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState, useEffect, ReactNode } from "react";
import { ErrorBoundary } from "./ErrorBoundary";

function ErrorFallback({ error }: { error: Error }) {
  return (
    <div className="flex h-screen w-full flex-col items-center justify-center bg-neutral-950 p-6 text-center">
      <div className="max-w-md space-y-6">
        <div className="space-y-2">
          <h2 className="text-3xl font-bold text-white tracking-tight">System Interruption</h2>
          <p className="text-neutral-400 text-sm">
            Nexus encountered an unexpected state. Our core systems are still stable.
          </p>
        </div>
        <div className="text-left text-xs font-mono bg-neutral-900/50 border border-white/5 p-4 rounded-xl overflow-auto max-h-48 text-neutral-500">
          {error.message}
        </div>
        <button 
          onClick={() => window.location.reload()}
          className="w-full py-3 bg-white text-black rounded-xl font-semibold hover:bg-neutral-200 transition-all active:scale-[0.98]"
        >
          Recover Session
        </button>
      </div>
    </div>
  );
}

import { trpc } from "@/lib/trpc/client";
import { httpBatchLink } from "@trpc/client";

export function Providers({ children }: { children: ReactNode }) {
  useEffect(() => {
    if ("serviceWorker" in navigator) {
      window.addEventListener("load", () => {
        navigator.serviceWorker.register("/sw.js").then(
          (reg) => console.log("Nexus Core: SW registered", reg.scope),
          (err) => console.error("Nexus Core: SW registration failed", err)
        );
      });
    }
  }, []);

  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 5 * 60 * 1000,
            gcTime: 10 * 60 * 1000,
            retry: 1,
            refetchOnWindowFocus: false,
          },
        },
      })
  );

  const [trpcClient] = useState(() =>
    trpc.createClient({
      links: [
        httpBatchLink({
          url: "/api/trpc",
        }),
      ],
    })
  );

  return (
    <ErrorBoundary fallback={(error) => <ErrorFallback error={error} />}>
      <trpc.Provider client={trpcClient} queryClient={queryClient}>
        <QueryClientProvider client={queryClient}>
          {children}
        </QueryClientProvider>
      </trpc.Provider>
    </ErrorBoundary>
  );
}
