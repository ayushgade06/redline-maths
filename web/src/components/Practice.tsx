import { Check, X } from "lucide-react";
import { useEffect, useState } from "react";
import { api, ApiError, type PracticeProblem } from "../lib/api";
import { Banner, Button, MathText, Skeleton } from "./ui";

function Problem({ p, n }: { p: PracticeProblem; n: number }) {
  const [answer, setAnswer] = useState("");
  const [state, setState] = useState<{ ok: boolean; msg?: string } | null>(null);
  const [busy, setBusy] = useState(false);
  return (
    <li className="rounded-xl border border-rule bg-paper p-4">
      <p className="text-sm text-ink-3">Problem {n}</p>
      <p className="mt-1 text-lg">
        <MathText ascii={p.prompt_ascii} />
      </p>
      <form
        className="mt-3 flex flex-wrap items-center gap-2"
        onSubmit={async (e) => {
          e.preventDefault();
          if (!answer.trim()) return;
          setBusy(true);
          try {
            const r = await api.checkPractice(p.template_id, p.prompt_ascii, answer);
            setState({ ok: r.correct, msg: r.feedback_code === "unreadable" ? r.message : undefined });
          } catch (err) {
            setState({ ok: false, msg: (err as ApiError).message });
          } finally {
            setBusy(false);
          }
        }}
      >
        <input
          value={answer}
          onChange={(e) => {
            setAnswer(e.target.value);
            setState(null);
          }}
          placeholder="x = …"
          aria-label={`Your answer to problem ${n}`}
          maxLength={60}
          className="h-10 w-44 rounded-lg border border-ink/20 bg-sheet px-3 font-mono focus:border-ink/50"
        />
        <Button size="sm" type="submit" loading={busy} variant="secondary">
          Check answer
        </Button>
        {state && (
          <span role="status" className={`inline-flex items-center gap-1.5 text-sm font-medium ${state.ok ? "text-green" : "text-red"}`}>
            {state.ok ? <Check className="size-4" aria-hidden /> : <X className="size-4" aria-hidden />}
            {state.msg ?? (state.ok ? "Correct" : "Not yet — try again (two answers? write x = a or x = b)")}
          </span>
        )}
      </form>
    </li>
  );
}

export function Practice({ misconceptionId }: { misconceptionId: string }) {
  const [problems, setProblems] = useState<PracticeProblem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [round, setRound] = useState(0);
  useEffect(() => {
    setProblems(null);
    api
      .practice(misconceptionId, 2)
      .then((r) => setProblems(r.problems))
      .catch((e: ApiError) => setError(e.code === "unknown_misconception" ? null : e.message));
  }, [misconceptionId, round]);
  if (!problems && !error && round === 0 && misconceptionId === "OTHER") return null;
  return (
    <section aria-labelledby="practice-title" className="rounded-2xl border border-rule bg-sheet p-5">
      <h2 id="practice-title" className="font-display text-xl font-semibold">
        Practise this trap
      </h2>
      <p className="mt-1 text-sm text-ink-2">Two fresh problems built to catch the same mistake. Work them on paper, then enter your answer.</p>
      {error && <Banner tone="error">{error}</Banner>}
      <ol className="mt-4 space-y-3">
        {problems ? problems.map((p, i) => <Problem key={p.prompt_ascii} p={p} n={i + 1} />) : !error && <Skeleton className="h-24 w-full" />}
      </ol>
      <Button variant="ghost" size="sm" className="mt-3" onClick={() => setRound((r) => r + 1)}>
        New problems
      </Button>
    </section>
  );
}
