export default function Loading() {
  return (
    <div className="space-y-6 p-6 animate-pulse">
      <div className="flex items-center gap-4">
        <div className="h-8 w-8 rounded-full bg-neutral-200" />
        <div className="h-7 w-56 bg-neutral-200 rounded" />
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-4">
          <div className="rounded-lg border border-neutral-200 bg-white p-6">
            <div className="h-5 w-40 bg-neutral-200 rounded mb-4" />
            <div className="space-y-2">
              <div className="h-3 w-full bg-neutral-100 rounded" />
              <div className="h-3 w-full bg-neutral-100 rounded" />
              <div className="h-3 w-3/4 bg-neutral-100 rounded" />
            </div>
          </div>
          <div className="rounded-lg border border-neutral-200 bg-white p-6">
            <div className="h-5 w-32 bg-neutral-200 rounded mb-4" />
            <div className="h-48 w-full bg-neutral-100 rounded" />
          </div>
        </div>
        <div className="rounded-lg border border-neutral-200 bg-white p-6">
          <div className="h-5 w-24 bg-neutral-200 rounded mb-4" />
          <div className="space-y-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="flex justify-between">
                <div className="h-3 w-20 bg-neutral-100 rounded" />
                <div className="h-3 w-16 bg-neutral-200 rounded" />
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

