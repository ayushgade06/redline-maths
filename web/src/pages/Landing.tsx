import { Camera, ShieldCheck } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { Button, MathText, RedUnderline, StatusIcon } from "../components/ui";

// Real output for the bundled sample (engine run on samples/negative-bracket.jpg).
const SHEET = [
  { ascii: "5 - 2(x - 3) = 1", status: "start" as const },
  { ascii: "5 - 2x - 6 = 1", status: "invalid" as const },
  { ascii: "-2x - 1 = 1", status: "valid" as const },
  { ascii: "-2x = 2", status: "valid" as const },
  { ascii: "x = -1", status: "valid" as const },
];

function Sheet() {
  return (
    <figure className="quad relative rounded-2xl border border-rule p-5 shadow-[0_1px_0_var(--c-rule),0_24px_48px_-28px_rgba(40,30,10,.35)] sm:p-7">
      <figcaption className="mb-4 text-sm text-ink-3">Solve for x</figcaption>
      <ol className="space-y-3.5">
        {SHEET.map((l, i) => (
          <li key={i} className="grid grid-cols-[1.5rem_1fr_auto] items-center gap-3">
            <span className="text-right text-xs tabular-nums text-ink-3">{i + 1}</span>
            <span className={`relative w-fit text-lg ${l.status === "invalid" ? "text-ink" : "text-ink/85"}`}>
              <MathText ascii={l.ascii} />
              {l.status === "invalid" && <RedUnderline className="absolute -bottom-2.5 left-0 h-3 w-full" />}
            </span>
            {l.status !== "start" && <StatusIcon status={l.status} size="sm" />}
          </li>
        ))}
      </ol>
      <div className="mt-6 rounded-xl border border-red/25 bg-sheet/90 p-4">
        <p className="flex items-center gap-1.5 text-xs font-medium text-green">
          <ShieldCheck className="size-3.5" aria-hidden /> Verified diagnosis
        </p>
        <p className="mt-1.5 font-display text-lg leading-snug">Line 2: the −2 was applied to only the first term in the bracket.</p>
        <p className="mt-2 text-sm text-ink-2">
          Nudge: look at how <MathText ascii="-2(x - 3)" /> was expanded. Check the sign of each term that came out of the bracket.
        </p>
      </div>
    </figure>
  );
}

const STEPS = [
  { title: "Read", body: "Claude reads your handwriting line by line and marks where each line sits on the photo. You confirm it read you right." },
  { title: "Prove", body: "A symbolic math engine (SymPy) checks that each line keeps exactly the same solutions as the one before. The AI never decides what's correct." },
  { title: "Name", body: "Ten known misconceptions are written as code. If one reproduces your line exactly, you get a verified diagnosis — not a guess." },
  { title: "Coach", body: "Three hints, from a nudge to a worked example with different numbers. Each one is checked by code so it can't contain your answer." },
];

export default function Landing() {
  const nav = useNavigate();
  return (
    <>
      <section className="mx-auto grid max-w-6xl items-center gap-12 px-4 pb-16 pt-12 sm:px-6 md:grid-cols-[1.05fr_1fr] md:pt-20 lg:gap-16">
        <div>
          <h1 className="font-display text-[2.6rem] font-semibold leading-[1.04] sm:text-6xl">
            Finds the line where your math went wrong.
            <span className="mt-2 block text-ink-2">Won't give you the answer.</span>
          </h1>
          <p className="mt-6 max-w-[34rem] text-lg leading-relaxed text-ink-2">
            Photograph your worked algebra. Redline proves which step broke, names the mistake behind it, and coaches you until you
            fix it yourself.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Button size="lg" icon={<Camera className="size-4" aria-hidden />} onClick={() => nav("/check")}>
              Check my work
            </Button>
            <Button size="lg" variant="secondary" onClick={() => nav("/check?sample=negative-bracket")}>
              Try a sample
            </Button>
          </div>
          <p className="mt-5 text-sm text-ink-3">Single-variable algebra: linear equations, brackets, fractions and quadratics.</p>
        </div>
        <Sheet />
      </section>

      <section className="border-t border-rule">
        <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
          <h2 className="max-w-xl font-display text-3xl font-semibold leading-tight">The AI reads and explains. The math engine judges.</h2>
          <ol className="mt-10 grid gap-x-10 gap-y-8 sm:grid-cols-2 lg:grid-cols-4">
            {STEPS.map((s, i) => (
              <li key={s.title} className="border-t-2 border-ink pt-4">
                <p className="text-sm tabular-nums text-ink-3">Step {i + 1}</p>
                <h3 className="mt-1 font-display text-xl font-semibold">{s.title}</h3>
                <p className="mt-2 text-[15px] leading-relaxed text-ink-2">{s.body}</p>
              </li>
            ))}
          </ol>
          <Link to="/how-it-works" className="mt-10 inline-block text-[15px] text-ink underline decoration-ink/30 underline-offset-4 hover:decoration-ink">
            See the architecture and accuracy numbers
          </Link>
        </div>
      </section>

      <section className="border-t border-rule bg-sheet">
        <div className="mx-auto grid max-w-6xl gap-10 px-4 py-16 sm:px-6 md:grid-cols-[1fr_1.2fr]">
          <figure className="font-display text-2xl leading-snug sm:text-[1.7rem]">
            Students who practised with unrestricted GPT-4 scored 17% lower on the exam without it than students who never had it.
            <figcaption className="mt-4 font-sans text-sm text-ink-3">
              Finding from Bastani et al., <cite>Generative AI without guardrails can harm learning</cite>, PNAS 2025 — a field experiment
              with about 1,000 high-school students.
            </figcaption>
          </figure>
          <div className="space-y-4 text-[15px] leading-relaxed text-ink-2">
            <p>
              Answer apps hand over the full solution, so the struggle that builds skill disappears. Redline is the opposite: it is
              precise about <em>where</em> your reasoning broke and deliberately unhelpful about the answer.
            </p>
            <p>
              That refusal is enforced in code. The engine never sends the correct answer to your browser or to the AI, and every
              hint is scanned for answers before you see it.
            </p>
            <Button variant="secondary" onClick={() => nav("/check?sample=square-root")}>
              Try the square-root sample
            </Button>
          </div>
        </div>
      </section>
    </>
  );
}
