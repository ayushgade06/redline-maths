import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Skeleton } from "../components/ui";

type Metric = { label: string; value: number | null; n: number; target?: string; note?: string };
type Eval = {
  generated_at: string;
  synthetic: { n_cases: number; metrics: Metric[]; by_misconception: { id: string; name: string; n: number; correct: number }[] };
  photos: { date: string; n_photos: number; metrics: Metric[]; note: string } | null;
  hints: { date: string; n: number; metrics: Metric[] } | null;
  failures: { kind: string; lines: string[]; expected: string; got: string }[];
};

const PIPELINE = [
  { who: "AI", title: "Read", body: "Claude transcribes each handwritten line into a strict math grammar and marks roughly where it sits; Redline then snaps each box to the actual ink row in your photo." },
  { who: "You", title: "Confirm", body: "You fix any misread line. Redline won't judge text you didn't write." },
  { who: "Code", title: "Parse safely", body: "A whitelist parser turns each line into SymPy. Nothing reaches Python's eval unless it passes; length, exponent and number caps bound the work." },
  { who: "Code", title: "Prove", body: "For each pair of lines, SymPy compares their solution sets over the real numbers. Same set: valid. Smaller: a solution was lost. Different: the step is wrong." },
  { who: "Code", title: "Diagnose", body: "Ten misconceptions are rewrite rules. Redline applies each to the previous line; if one reproduces your line exactly, the diagnosis is verified. Only if none do does the AI offer a labelled hypothesis." },
  { who: "AI + code", title: "Coach", body: "Claude words three levels of hints from verified facts only — it is never given the answer. A code guard then scans each hint for answers or corrected lines; a leaking draft is rewritten once, then replaced by a built-in hint." },
];

function pct(v: number | null) {
  return v === null ? "—" : `${(v * 100).toFixed(v === 0 || v === 1 ? 0 : 1)}%`;
}

function MetricTable({ metrics, caption }: { metrics: Metric[]; caption: string }) {
  return (
    <div className="overflow-x-auto rounded-xl border border-rule">
      <table className="w-full min-w-[480px] text-left text-[15px]">
        <caption className="sr-only">{caption}</caption>
        <thead className="bg-sheet text-sm text-ink-2">
          <tr>
            <th className="px-4 py-2.5 font-medium">Measure</th>
            <th className="px-4 py-2.5 text-right font-medium">Result</th>
            <th className="px-4 py-2.5 text-right font-medium">Cases</th>
            <th className="px-4 py-2.5 font-medium">Target</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-rule">
          {metrics.map((m) => (
            <tr key={m.label}>
              <td className="px-4 py-2.5">
                {m.label}
                {m.note && <span className="block text-xs text-ink-3">{m.note}</span>}
              </td>
              <td className="px-4 py-2.5 text-right font-medium tabular-nums">{pct(m.value)}</td>
              <td className="px-4 py-2.5 text-right tabular-nums text-ink-2">{m.n}</td>
              <td className="px-4 py-2.5 text-sm text-ink-3">{m.target ?? ""}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function HowItWorks() {
  const [ev, setEv] = useState<Eval | null | "missing">(null);
  useEffect(() => {
    fetch("/eval.json")
      .then((r) => (r.ok ? r.json() : "missing"))
      .then(setEv)
      .catch(() => setEv("missing"));
  }, []);

  return (
    <article className="mx-auto max-w-4xl px-4 py-12 sm:px-6">
      <h1 className="font-display text-4xl font-semibold leading-tight sm:text-5xl">How Redline works</h1>
      <p className="mt-4 max-w-2xl text-lg leading-relaxed text-ink-2">
        The language model perceives and explains. A symbolic math engine judges. Code enforces the teaching rules. Correctness is never
        decided by the AI.
      </p>

      <section className="mt-12" aria-labelledby="pipe">
        <h2 id="pipe" className="font-display text-2xl font-semibold">The pipeline</h2>
        <ol className="mt-6 space-y-0">
          {PIPELINE.map((s, i) => (
            <li key={s.title} className="relative grid grid-cols-[2.5rem_1fr] gap-4 pb-7 last:pb-0">
              {i < PIPELINE.length - 1 && <span aria-hidden className="absolute left-[1.2rem] top-9 h-[calc(100%-2.25rem)] w-px bg-rule" />}
              <span className="grid size-10 place-items-center rounded-full border border-ink/20 bg-sheet text-sm font-medium tabular-nums">{i + 1}</span>
              <div className="pt-1.5">
                <h3 className="flex flex-wrap items-baseline gap-x-3 font-display text-xl font-semibold">
                  {s.title}
                  <span className={`font-sans text-xs font-medium ${s.who === "Code" ? "text-green" : s.who === "You" ? "text-ink-2" : "text-amber"}`}>
                    {s.who === "Code" ? "Deterministic code" : s.who === "You" ? "You" : s.who === "AI" ? "Claude" : "Claude, checked by code"}
                  </span>
                </h3>
                <p className="mt-1.5 max-w-2xl text-[15px] leading-relaxed text-ink-2">{s.body}</p>
              </div>
            </li>
          ))}
        </ol>
      </section>

      <section className="mt-16" aria-labelledby="eval">
        <h2 id="eval" className="font-display text-2xl font-semibold">Measured accuracy</h2>
        <p className="mt-2 max-w-2xl text-[15px] leading-relaxed text-ink-2">
          Numbers are produced by <code className="text-sm">eval/run.py</code> and published as measured, including failures.
        </p>
        {ev === null && <Skeleton className="mt-6 h-48 w-full" />}
        {ev === "missing" && <p className="mt-6 text-ink-2">The evaluation results haven't been published for this build.</p>}
        {ev && ev !== "missing" && (
          <div className="mt-6 space-y-10">
            <div>
              <h3 className="font-display text-lg font-semibold">Synthetic error set ({ev.synthetic.n_cases} worked solutions)</h3>
              <p className="mb-3 mt-1 text-sm text-ink-3">
                15 hand-written correct solutions, plus every applicable misconception injected at every step. Deterministic, re-run in CI.
              </p>
              <MetricTable metrics={ev.synthetic.metrics} caption="Synthetic evaluation" />
            </div>
            {ev.hints && (
              <div>
                <h3 className="font-display text-lg font-semibold">Hint answer leaks ({ev.hints.n} live generations, {ev.hints.date})</h3>
                <p className="mb-3 mt-1 text-sm text-ink-3">Leak = the hint contains the answer, an equivalent equation, or the corrected term.</p>
                <MetricTable metrics={ev.hints.metrics} caption="Hint leak evaluation" />
              </div>
            )}
            {ev.photos ? (
              <div>
                <h3 className="font-display text-lg font-semibold">Photos ({ev.photos.n_photos}, {ev.photos.date})</h3>
                <p className="mb-3 mt-1 text-sm text-ink-3">{ev.photos.note}</p>
                <MetricTable metrics={ev.photos.metrics} caption="Photo evaluation" />
              </div>
            ) : null}
            {ev.failures.length > 0 && (
              <div>
                <h3 className="font-display text-lg font-semibold">Where it fails</h3>
                <ul className="mt-3 space-y-2 text-sm text-ink-2">
                  {ev.failures.slice(0, 6).map((f, i) => (
                    <li key={i} className="rounded-lg border border-rule bg-sheet px-3 py-2">
                      <span className="font-mono text-xs">{f.lines.join("  →  ")}</span>
                      <span className="block">
                        {f.kind}: expected {f.expected}, got {f.got}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            <p className="text-xs text-ink-3">Generated {new Date(ev.generated_at).toLocaleString()}</p>
          </div>
        )}
      </section>

      <section className="mt-16 grid gap-10 md:grid-cols-2">
        <div>
          <h2 className="font-display text-2xl font-semibold">Limitations</h2>
          <ul className="mt-3 list-disc space-y-2 pl-5 text-[15px] leading-relaxed text-ink-2">
            <li>Single-variable algebra only: linear equations, brackets, fractions, quadratics, simple square roots. No inequalities, systems, calculus or word problems.</li>
            <li>Handwriting reading can misread characters — that's why you confirm the reading first.</li>
            <li>Ten misconceptions are executable. Others get an AI hypothesis, clearly labelled, or none.</li>
            <li>A step that combines several operations is judged as a whole: Redline says the step is wrong, but the named misconception is the simplest one that explains it.</li>
            <li>For adults (18+) only in this version.</li>
          </ul>
        </div>
        <div>
          <h2 className="font-display text-2xl font-semibold">Privacy and AI use</h2>
          <ul className="mt-3 list-disc space-y-2 pl-5 text-[15px] leading-relaxed text-ink-2">
            <li>Photos are sent to Anthropic's Claude API for reading, processed in memory and never stored by Redline.</li>
            <li>No accounts. Class mode stores only a class code, a misconception type and a time.</li>
            <li>In-product AI: Claude (Anthropic) reads handwriting, suggests labelled hypotheses and words hints.</li>
            <li>
              Built with help from Claude Code as a coding assistant. See the repository's AI disclosure and{" "}
              <Link to="/privacy" className="underline decoration-ink/30 underline-offset-2 hover:decoration-ink">privacy page</Link>.
            </li>
          </ul>
          <h2 className="mt-8 font-display text-2xl font-semibold">Credits</h2>
          <p className="mt-3 text-[15px] leading-relaxed text-ink-2">
            SymPy, FastAPI, Pydantic, React, Vite, Tailwind CSS, KaTeX, Lucide, Anthropic Claude API, Fraunces and Inter (Google Fonts), Caveat
            and Kalam (sample sheets). Executable-misconception idea after MalruleLib (arXiv 2601.03217).
          </p>
        </div>
      </section>
    </article>
  );
}
