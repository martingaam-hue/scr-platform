export default function Loading() {
  return (
    <div className="max-w-3xl mx-auto py-8 px-4">
      <div className="h-8 w-48 bg-neutral-100 rounded animate-pulse mb-6" />
      <div className="rounded-xl border border-neutral-200 bg-white p-6 animate-pulse space-y-4">
        {[...Array(8)].map((_, i) => (
          <div key={i} className="h-10 bg-neutral-50 rounded" />
        ))}
      </div>
    </div>
  );
}
