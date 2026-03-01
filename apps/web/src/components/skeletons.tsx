export function PageHeaderSkeleton() {
  return (
    <div className="mb-6 animate-pulse">
      <div className="h-8 w-48 rounded bg-neutral-200 mb-2" />
      <div className="h-4 w-80 rounded bg-neutral-100" />
    </div>
  );
}

export function StatsBarSkeleton({ count = 4 }: { count?: number }) {
  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6 animate-pulse">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="rounded-lg border border-neutral-200 bg-white p-4">
          <div className="h-3 w-20 rounded bg-neutral-100 mb-2" />
          <div className="h-7 w-16 rounded bg-neutral-200" />
        </div>
      ))}
    </div>
  );
}

export function CardGridSkeleton({ count = 6 }: { count?: number }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 animate-pulse">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="rounded-lg border border-neutral-200 bg-white p-6">
          <div className="h-4 w-3/4 rounded bg-neutral-200 mb-3" />
          <div className="h-3 w-full rounded bg-neutral-100 mb-2" />
          <div className="h-3 w-2/3 rounded bg-neutral-100 mb-4" />
          <div className="flex gap-2">
            <div className="h-6 w-16 rounded-full bg-neutral-200" />
            <div className="h-6 w-16 rounded-full bg-neutral-200" />
          </div>
        </div>
      ))}
    </div>
  );
}

export function TableSkeleton({ rows = 8, cols = 5 }: { rows?: number; cols?: number }) {
  return (
    <div className="animate-pulse rounded-lg border border-neutral-200 bg-white overflow-hidden">
      <div className="border-b border-neutral-200 bg-neutral-50 px-6 py-3 flex gap-4">
        {Array.from({ length: cols }).map((_, i) => (
          <div key={i} className="h-4 rounded bg-neutral-200 flex-1" />
        ))}
      </div>
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="border-b border-neutral-100 px-6 py-4 flex gap-4">
          {Array.from({ length: cols }).map((_, j) => (
            <div key={j} className="h-3 rounded bg-neutral-100 flex-1" />
          ))}
        </div>
      ))}
    </div>
  );
}

export function DetailPageSkeleton() {
  return (
    <div className="animate-pulse space-y-6">
      <div className="flex items-center gap-4">
        <div className="h-10 w-10 rounded-full bg-neutral-200" />
        <div>
          <div className="h-6 w-64 rounded bg-neutral-200 mb-1" />
          <div className="h-4 w-40 rounded bg-neutral-100" />
        </div>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-4">
          <div className="rounded-lg border border-neutral-200 bg-white p-6">
            <div className="h-5 w-40 rounded bg-neutral-200 mb-4" />
            <div className="space-y-2">
              <div className="h-3 w-full rounded bg-neutral-100" />
              <div className="h-3 w-full rounded bg-neutral-100" />
              <div className="h-3 w-3/4 rounded bg-neutral-100" />
            </div>
          </div>
          <div className="rounded-lg border border-neutral-200 bg-white p-6">
            <div className="h-5 w-32 rounded bg-neutral-200 mb-4" />
            <div className="h-48 w-full rounded bg-neutral-100" />
          </div>
        </div>
        <div className="space-y-4">
          <div className="rounded-lg border border-neutral-200 bg-white p-6">
            <div className="h-5 w-24 rounded bg-neutral-200 mb-4" />
            <div className="space-y-3">
              {Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="flex justify-between">
                  <div className="h-3 w-20 rounded bg-neutral-100" />
                  <div className="h-3 w-16 rounded bg-neutral-200" />
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export function ChartSkeleton() {
  return (
    <div className="animate-pulse rounded-lg border border-neutral-200 bg-white p-6">
      <div className="h-5 w-40 rounded bg-neutral-200 mb-4" />
      <div className="h-64 w-full rounded bg-neutral-100" />
    </div>
  );
}

export function FormSkeleton() {
  return (
    <div className="animate-pulse rounded-lg border border-neutral-200 bg-white p-6 space-y-6 max-w-2xl">
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i}>
          <div className="h-4 w-24 rounded bg-neutral-200 mb-2" />
          <div className="h-10 w-full rounded bg-neutral-100" />
        </div>
      ))}
      <div className="h-10 w-32 rounded bg-neutral-200" />
    </div>
  );
}
