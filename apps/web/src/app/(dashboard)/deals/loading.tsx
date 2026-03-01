export default function DealsLoading() {
  return (
    <div className="space-y-6 p-6 animate-pulse">
      <div className="flex justify-between items-center">
        <div className="h-8 w-48 bg-neutral-200 rounded" />
        <div className="flex gap-2">
          <div className="h-10 w-24 bg-neutral-200 rounded" />
          <div className="h-10 w-24 bg-neutral-200 rounded" />
          <div className="h-10 w-24 bg-neutral-200 rounded" />
        </div>
      </div>
      <div className="flex gap-2 border-b border-neutral-200 pb-2">
        <div className="h-8 w-28 bg-neutral-200 rounded" />
        <div className="h-8 w-28 bg-neutral-200 rounded" />
        <div className="h-8 w-28 bg-neutral-200 rounded" />
      </div>
      <div className="grid grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="space-y-3">
            <div className="h-6 w-32 bg-neutral-200 rounded" />
            {Array.from({ length: 3 }).map((_, j) => (
              <div key={j} className="h-24 w-full bg-neutral-200 rounded-lg" />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
