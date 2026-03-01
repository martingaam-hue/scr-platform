export default function Loading() {
  return (
    <div className="space-y-6 p-6 animate-pulse">
      <div className="h-8 w-40 bg-neutral-200 rounded" />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="rounded-lg border border-neutral-200 bg-white p-6">
            <div className="h-5 w-32 bg-neutral-200 rounded mb-3" />
            <div className="h-3 w-full bg-neutral-100 rounded mb-2" />
            <div className="h-3 w-2/3 bg-neutral-100 rounded" />
          </div>
        ))}
      </div>
    </div>
  );
}

