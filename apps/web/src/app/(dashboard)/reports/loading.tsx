export default function Loading() {
  return (
    <div className="space-y-6 p-6 animate-pulse">
      <div className="flex justify-between items-center">
        <div className="h-8 w-48 bg-neutral-200 rounded" />
        <div className="h-10 w-32 bg-neutral-200 rounded" />
      </div>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="rounded-lg border border-neutral-200 bg-white p-4">
            <div className="h-3 w-20 bg-neutral-100 rounded mb-2" />
            <div className="h-7 w-16 bg-neutral-200 rounded" />
          </div>
        ))}
      </div>
      <div className="rounded-lg border border-neutral-200 bg-white overflow-hidden">
        <div className="border-b border-neutral-200 bg-neutral-50 px-6 py-3 flex gap-4">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-4 bg-neutral-200 rounded flex-1" />
          ))}
        </div>
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="border-b border-neutral-100 px-6 py-4 flex gap-4">
            {Array.from({ length: 5 }).map((_, j) => (
              <div key={j} className="h-3 bg-neutral-100 rounded flex-1" />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

