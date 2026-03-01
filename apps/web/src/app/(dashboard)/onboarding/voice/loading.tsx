export default function Loading() {
  return (
    <div className="space-y-6 p-6 animate-pulse max-w-4xl">
      <div className="h-8 w-40 bg-neutral-200 rounded" />
      <div className="rounded-lg border border-neutral-200 bg-white p-6 space-y-6">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i}>
            <div className="h-4 w-24 bg-neutral-200 rounded mb-2" />
            <div className="h-10 w-full bg-neutral-100 rounded" />
          </div>
        ))}
        <div className="h-10 w-32 bg-neutral-200 rounded" />
      </div>
    </div>
  );
}
