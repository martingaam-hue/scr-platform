"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { useState, type ReactNode } from "react";
import * as Sentry from "@sentry/nextjs";

function handleMutationError(error: unknown) {
  const err = error as { response?: { data?: { message?: string } }; message?: string };
  const message = err?.response?.data?.message ?? err?.message ?? "An error occurred";
  // TODO: replace with toast once a toast library is added (e.g. sonner)
  console.error("[API Mutation Error]", message, error);
  Sentry.captureException(error);
}

export function QueryProvider({ children }: { children: ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60 * 1000,
            gcTime: 5 * 60 * 1000,
            retry: 1,
            refetchOnWindowFocus: false,
          },
          mutations: {
            onError: handleMutationError,
          },
        },
      })
  );

  return (
    <QueryClientProvider client={queryClient}>
      {children}
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  );
}
