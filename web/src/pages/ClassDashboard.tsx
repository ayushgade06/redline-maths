import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Banner, Skeleton } from "../components/ui";
import { api, ApiError, type ClassSummary } from "../lib/api";

export default function ClassDashboard() {
  const { code = "" } = useParams();
  const [data, setData] = useState<ClassSummary | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [updated, setUpdated] = useState<Date | null>(null);

  useEffect(() => {
    let alive = true;
    const load = () =>
      api
        .classSummary(code)
        .then((d) => {
          if (!alive) return;
          setData(d);
          setError(null);
          setUpdated(new Date());
        })
        .catch((e: ApiError) => alive && setError(e));
    load();
    const t = setInterval(load, 30_000);
    return () => {
      alive = false;
      clearInterval(t);
    };
  }, [code]);

  if (error?.code === "class_not_found")
    return (
      <div className="mx-auto max-w-2xl px-4 py-16 sm:px-6">
        <h1 className="font-display text-3xl font-semibold">No class with code {code.toUpperCase()}</h1>
        <p className="mt-3 text-ink-2">Check the code, or create a new class.</p>
        <Link to="/instructors" className="mt-6 inline-block underline decoration-ink/30 underline-offset-4">
          Go to instructor tools
        </Link>
      </div>
    );

  const max = Math.max(1, ...(data?.counts.map((c) => c.count) ?? [1]));
  return (
    <div className="mx-auto max-w-4xl px-4 py-12 sm:px-6">
      <p className="font-mono text-sm tracking-widest text-ink-3">{code.toUpperCase()}</p>
      <h1 className="mt-1 font-display text-4xl font-semibold leading-tight">{data?.name ?? <Skeleton className="h-10 w-72" />}</h1>
      {error && (
        <div className="mt-6">
          <Banner tone="error">{error.message}</Banner>
        </div>
      )}
      {data && (
        <>
          <p className="mt-3 text-ink-2">
            <span className="font-semibold text-ink tabular-nums">{data.total}</span> shared {data.total === 1 ? "mistake" : "mistakes"} in the
            last {data.window_days} days. Refreshes every 30 seconds.
          </p>
          {data.total === 0 ? (
            <div className="quad mt-8 rounded-2xl border border-rule p-8 text-center">
              <p className="font-display text-xl font-semibold">No shares yet</p>
              <p className="mt-2 text-ink-2">
                Give students the code <span className="font-mono font-semibold">{code.toUpperCase()}</span>. After a check, they can share
                the mistake Redline found from the results screen.
              </p>
            </div>
          ) : (
            <div className="mt-10 grid gap-10 md:grid-cols-[1.4fr_1fr]">
              <section aria-labelledby="counts">
                <h2 id="counts" className="font-display text-xl font-semibold">Most common mistakes</h2>
                <ul className="mt-5 space-y-4">
                  {data.counts.map((c) => (
                    <li key={c.misconception_id}>
                      <div className="flex items-baseline justify-between gap-3 text-[15px]">
                        <span>{c.name}</span>
                        <span className="tabular-nums text-ink-2">{c.count}</span>
                      </div>
                      <div className="mt-1.5 h-2.5 rounded-full bg-ink/6" aria-hidden>
                        <div className="h-full rounded-full bg-ink" style={{ width: `${(c.count / max) * 100}%` }} />
                      </div>
                    </li>
                  ))}
                </ul>
              </section>
              <section aria-labelledby="reteach" className="rounded-2xl border border-rule bg-sheet p-5">
                <h2 id="reteach" className="font-display text-xl font-semibold">Worth re-teaching</h2>
                <ol className="mt-4 space-y-4">
                  {data.suggestions.map((s, i) => (
                    <li key={s.misconception_id} className="text-[15px]">
                      <p className="font-medium">
                        {i + 1}. {s.name}
                      </p>
                      <p className="mt-1 text-sm leading-relaxed text-ink-2">{s.concept}</p>
                    </li>
                  ))}
                </ol>
              </section>
            </div>
          )}
          <p className="mt-10 text-xs text-ink-3">
            Anonymous: no names, photos or student work are stored. {updated && `Updated ${updated.toLocaleTimeString()}.`}
          </p>
        </>
      )}
    </div>
  );
}
