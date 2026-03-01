"use client";

import { useEffect } from "react";
import * as Sentry from "@sentry/nextjs";

export default function DashboardError({
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
    <div className="flex items-center justify-center h-96">
      <div className="text-center space-y-3 max-w-sm px-4">
        <div className="text-4xl">⚠️</div>
        <h2 className="text-xl font-semibold text-neutral-900">
          Something went wrong
        </h2>
        <p className="text-sm text-neutral-500">
          This section encountered an error. Our team has been notified.
        </p>
        {error.digest && (
          <p className="text-xs text-neutral-400 font-mono">
            Error ID: {error.digest}
          </p>
        )}
        <button
          onClick={reset}
          className="px-4 py-2 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700"
        >
          Try Again
        </button>
      </div>
    </div>
  );
}
