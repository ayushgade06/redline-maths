import { Lightbulb, X } from "lucide-react";
import { useState } from "react";
import { api, ApiError, type Hint, type Line } from "../lib/api";
import { HINT_LABELS, nextHintLevel } from "../lib/hints";
import { load, save } from "../lib/storage";
import { Badge, Banner, Button, GuardChip, MathText, RichText } from "./ui";

const LANGS = { en: "English", hi: "हिन्दी", mr: "मराठी", es: "Español" } as const;
type Lang = keyof typeof LANGS;

export function Hints({ lines, problem, errorLineId, misconceptionId }: { lines: Line[]; problem: string; errorLineId: string; misconceptionId: string }) {
  const [hints, setHints] = useState<Partial<Record<1 | 2 | 3, Hint>>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lang, setLang] = useState<Lang>(() => (load("redline.lang") as Lang) in LANGS ? (load("redline.lang") as Lang) : "en");
  const next = nextHintLevel(hints);

  const reveal = async () => {
    if (!next) return;
    setBusy(true);
    setError(null);
    try {
      const h = await api.hint({ lines, problem, error_line_id: errorLineId, misconception_id: misconceptionId, level: next, lang });
      setHints((prev) => ({ ...prev, [next]: h }));
    } catch (e) {
      setError((e as ApiError).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <section aria-labelledby="hints-title" className="rounded-2xl border border-rule bg-sheet p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 id="hints-title" className="flex items-center gap-2 font-display text-xl font-semibold">
          <Lightbulb className="size-5 text-amber" aria-hidden /> Hints
        </h2>
        <label className="flex items-center gap-2 text-sm text-ink-2">
          Language
          <select
            value={lang}
            onChange={(e) => {
              setLang(e.target.value as Lang);
              save("redline.lang", e.target.value);
            }}
            className="h-9 rounded-md border border-ink/20 bg-paper px-2 text-sm text-ink"
          >
            {Object.entries(LANGS).map(([k, v]) => (
              <option key={k} value={k}>
                {v}
              </option>
            ))}
          </select>
        </label>
      </div>
      <p className="mt-1 text-sm text-ink-2">Each hint gives a little more. None of them will give you the answer.</p>

      <ol className="mt-4 space-y-3">
        {([1, 2, 3] as const).map((lvl) => {
          const h = hints[lvl];
          if (!h) return null;
          return (
            <li key={lvl} className="fade-in rounded-xl border border-amber/25 bg-paper p-4">
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-sm font-medium">
                  {lvl}. {HINT_LABELS[lvl]}
                </span>
                <GuardChip regenerated={h.guard.regenerated} />
                {h.source === "template" && <Badge tone="muted">Built-in hint</Badge>}
              </div>
              <p className="mt-2 text-[15px] leading-relaxed" lang={lang}>
                <RichText text={h.text} />
              </p>
              {h.example && (
                <div className="mt-3 grid gap-2 rounded-lg border border-rule bg-sheet p-3 text-[15px]">
                  <p className="text-xs text-ink-3">A different problem with the same trap</p>
                  <p>
                    <MathText ascii={h.example.problem} />
                  </p>
                  <p className="flex items-center gap-2">
                    <span className="grid size-5 place-items-center rounded-full bg-red-soft text-red">
                      <X className="size-3" strokeWidth={3} aria-label="Wrong" />
                    </span>
                    <MathText ascii={h.example.wrong} />
                  </p>
                  <p className="flex items-center gap-2">
                    <span className="grid size-5 place-items-center rounded-full bg-green-soft text-green" aria-label="Right">
                      ✓
                    </span>
                    <MathText ascii={h.example.right} />
                  </p>
                </div>
              )}
            </li>
          );
        })}
      </ol>
      {error && (
        <div className="mt-3">
          <Banner tone="error">{error}</Banner>
        </div>
      )}
      {next ? (
        <Button className="mt-4" variant={next === 1 ? "primary" : "secondary"} loading={busy} onClick={reveal}>
          {next === 1 ? "Get a nudge" : HINT_LABELS[next]}
        </Button>
      ) : (
        <p className="mt-4 text-sm text-ink-2">That's every hint. Now try fixing the line yourself — Redline will re-check it.</p>
      )}
    </section>
  );
}
