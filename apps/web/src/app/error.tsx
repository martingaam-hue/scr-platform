"use client";

import { useEffect } from "react";
import * as Sentry from "@sentry/nextjs";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    Sentry.captureException(error);
  }, [error]);

  return (
    <html>
      <body>
        <div className="flex min-h-screen items-center justify-center bg-neutral-50">
          <div className="text-center space-y-4 max-w-md px-4">
            <div className="text-6xl">⚠️</div>
            <h1 className="text-2xl font-bold text-neutral-900">
              Something went wrong
            </h1>
            <p className="text-neutral-500">
              An unexpected error occurred. Our team has been notified and is
              looking into it.
            </p>
            {error.digest && (
              <p className="text-xs text-neutral-400 font-mono">
                Error ID: {error.digest}
              </p>
            )}
            <button
              onClick={reset}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
            >
              Try Again
            </button>
          </div>
        </div>
      </body>
    </html>
  );
}
