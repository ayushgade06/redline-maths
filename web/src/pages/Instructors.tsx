import { Copy } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Banner, Button } from "../components/ui";
import { api, ApiError, type Health } from "../lib/api";

export default function Instructors() {
  const nav = useNavigate();
  const [health, setHealth] = useState<Health | null>(null);
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [created, setCreated] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState("");
  const [copied, setCopied] = useState(false);
  useEffect(() => {
    api.health().then(setHealth).catch(() => setHealth(null));
  }, []);
  const disabled = health !== null && health.db !== "ok";

  return (
    <div className="mx-auto max-w-4xl px-4 py-12 sm:px-6">
      <h1 className="font-display text-4xl font-semibold leading-tight">See which mistakes your class shares</h1>
      <p className="mt-4 max-w-2xl text-lg leading-relaxed text-ink-2">
        Create a class code and give it to your students. When Redline names a mistake, they can choose to share it — anonymously. Your
        dashboard shows which misconceptions came up most in the last 14 days, so you know what to re-teach.
      </p>
      <p className="mt-3 max-w-2xl text-sm text-ink-3">
        Stored per share: class code, misconception type, time. Never names, photos or the student's lines.
      </p>
      {disabled && (
        <div className="mt-6">
          <Banner tone="warn">Class mode isn't enabled on this server (no database configured).</Banner>
        </div>
      )}

      <div className="mt-10 grid gap-8 md:grid-cols-2">
        <section className="rounded-2xl border border-rule bg-sheet p-6">
          <h2 className="font-display text-xl font-semibold">Create a class</h2>
          {created ? (
            <div className="mt-4">
              <p className="text-sm text-ink-2">Class code</p>
              <p className="mt-1 font-mono text-4xl font-semibold tracking-[0.2em]">{created}</p>
              <div className="mt-5 flex flex-wrap gap-2">
                <Button onClick={() => nav(`/class/${created}`)}>Open dashboard</Button>
                <Button
                  variant="secondary"
                  icon={<Copy className="size-4" aria-hidden />}
                  onClick={() => {
                    navigator.clipboard?.writeText(`${location.origin}/class/${created}`).then(() => setCopied(true), () => setCopied(false));
                  }}
                >
                  {copied ? "Link copied" : "Copy dashboard link"}
                </Button>
              </div>
              <p className="mt-3 text-xs text-ink-3">Bookmark the dashboard: anyone with the code can view the anonymous counts.</p>
            </div>
          ) : (
            <form
              className="mt-4 space-y-4"
              onSubmit={async (e) => {
                e.preventDefault();
                setBusy(true);
                setError(null);
                try {
                  setCreated((await api.createClass(name.trim())).code);
                } catch (err) {
                  setError((err as ApiError).message);
                } finally {
                  setBusy(false);
                }
              }}
            >
              <label className="block">
                <span className="text-sm font-medium">Class name</span>
                <input
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required
                  maxLength={80}
                  placeholder="College Algebra — Section B"
                  className="mt-1.5 h-11 w-full rounded-lg border border-ink/20 bg-paper px-3 focus:border-ink/50"
                />
              </label>
              {error && <Banner tone="error">{error}</Banner>}
              <Button type="submit" loading={busy} disabled={disabled || !name.trim()}>
                Create class code
              </Button>
            </form>
          )}
        </section>
        <section className="rounded-2xl border border-rule p-6">
          <h2 className="font-display text-xl font-semibold">Open a dashboard</h2>
          <form
            className="mt-4 flex flex-wrap items-end gap-2"
            onSubmit={(e) => {
              e.preventDefault();
              if (open.trim()) nav(`/class/${open.trim().toUpperCase()}`);
            }}
          >
            <label className="block">
              <span className="text-sm font-medium">Class code</span>
              <input
                value={open}
                onChange={(e) => setOpen(e.target.value)}
                maxLength={6}
                className="mt-1.5 block h-11 w-40 rounded-lg border border-ink/20 bg-sheet px-3 font-mono uppercase tracking-widest focus:border-ink/50"
              />
            </label>
            <Button type="submit" variant="secondary" disabled={disabled}>
              Open
            </Button>
          </form>
          <p className="mt-6 text-sm text-ink-2">
            Students share from the results screen after a check. <Link to="/how-it-works" className="underline decoration-ink/30 underline-offset-2">How diagnoses work</Link>
          </p>
        </section>
      </div>
    </div>
  );
}
