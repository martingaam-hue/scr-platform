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
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="rounded-lg border border-neutral-200 bg-white p-6">
          <div className="h-5 w-40 bg-neutral-200 rounded mb-4" />
          <div className="h-64 w-full bg-neutral-100 rounded" />
        </div>
        <div className="rounded-lg border border-neutral-200 bg-white p-6">
          <div className="h-5 w-40 bg-neutral-200 rounded mb-4" />
          <div className="h-64 w-full bg-neutral-100 rounded" />
        </div>
      </div>
    </div>
  );
}

