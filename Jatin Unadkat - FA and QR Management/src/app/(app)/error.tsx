"use client";

export default function AppError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <div className="p-8">
      <div className="card p-6 max-w-lg space-y-3">
        <p className="pill bg-bad-soft text-bad">Something went wrong</p>
        <p className="text-sm">{error.message || "Unexpected error. Please try again."}</p>
        <button onClick={() => reset()} className="btn-secondary">Try again</button>
      </div>
    </div>
  );
}
