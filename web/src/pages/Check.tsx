import { Camera, Check as CheckIcon, ImageUp, Keyboard, Plus, RotateCcw, Sparkles, Trash2, Users } from "lucide-react";
import { type ReactNode, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Gate } from "../components/Gate";
import { Hints } from "../components/Hints";
import { Practice } from "../components/Practice";
import { Badge, Banner, Button, MathText, RedUnderline, Skeleton, StatusIcon, statusLabel } from "../components/ui";
import { api, ApiError, type Health, type Line, type VerifyResult } from "../lib/api";
import { boxStyle, type PreparedImage, prepareImage } from "../lib/image";
import { hasAcceptedGate } from "../lib/storage";

type Sample = { id: string; title: string; problem: string; lines: string[]; image: string };
type Stage = "capture" | "reading" | "review" | "checking" | "results";

const newId = () => `l${Math.random().toString(36).slice(2, 10)}`;
const toLines = (xs: string[]): Line[] => xs.map((ascii) => ({ id: newId(), ascii }));

export default function Check() {
  const [params, setParams] = useSearchParams();
  const [gateOk, setGateOk] = useState(hasAcceptedGate);
  const [health, setHealth] = useState<Health | null>(null);
  const [samples, setSamples] = useState<Sample[]>([]);
  const [stage, setStage] = useState<Stage>("capture");
  const [mode, setMode] = useState<"photo" | "type">("photo");
  const [image, setImage] = useState<PreparedImage | null>(null);
  const [problem, setProblem] = useState("");
  const [lines, setLines] = useState<Line[]>([]);
  const [notes, setNotes] = useState<string | null>(null);
  const [result, setResult] = useState<VerifyResult | null>(null);
  const [checkedLines, setCheckedLines] = useState<Line[]>([]);
  const [error, setError] = useState<ApiError | null>(null);
  const [aiDown, setAiDown] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [lastMisconception, setLastMisconception] = useState<string | null>(null);
  const [announce, setAnnounce] = useState("");
  const top = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api.health().then(setHealth).catch(() => setHealth(null));
    fetch("/samples/samples.json").then((r) => r.json()).then(setSamples).catch(() => setSamples([]));
  }, []);
  useEffect(() => {
    if (health && health.ai !== "ok") setAiDown(true);
  }, [health]);
  useEffect(() => {
    top.current?.scrollIntoView({ block: "start" });
  }, [stage]);

  const reset = () => {
    if (image) URL.revokeObjectURL(image.url);
    setImage(null);
    setLines([]);
    setProblem("");
    setResult(null);
    setError(null);
    setNotice(null);
    setNotes(null);
    setLastMisconception(null);
    setStage("capture");
  };

  const runVerify = useCallback(
    async (ls: Line[], prob: string) => {
      setError(null);
      setStage((s) => (s === "results" ? s : "checking"));
      try {
        const r = await api.verify(ls, prob);
        setResult(r);
        setCheckedLines(ls);
        setLines(ls);
        setStage("results");
        const m = r.misconception;
        if (m) setLastMisconception((prev) => prev ?? m.id); // practise the first mistake found
        const idx = ls.findIndex((l) => l.id === r.first_error_id);
        setAnnounce(
          idx >= 0
            ? `Line ${idx + 1} has an error${r.misconception ? `: ${r.misconception.name}` : ""}.`
            : r.final_correct
              ? `All ${ls.length} steps verified.`
              : "Every step so far follows from the one before.",
        );
      } catch (e) {
        setError(e as ApiError);
        setStage((s) => (s === "checking" ? (image ? "review" : "capture") : s));
      }
    },
    [image],
  );

  const readImage = useCallback(
    async (blob: Blob, sample?: Sample) => {
      setError(null);
      setNotice(null);
      let prepared: PreparedImage;
      try {
        prepared = await prepareImage(blob);
      } catch {
        setError(new ApiError(415, "image_invalid", "That file couldn't be opened as an image. Try a JPG or PNG."));
        return;
      }
      setImage(prepared);
      setStage("reading");
      try {
        const t = await api.transcribe(prepared.base64, prepared.mime);
        setLines(t.lines.map((l) => ({ ...l, id: newId(), orig: l.ascii })));
        setProblem(t.problem ?? "");
        setNotes(t.notes);
        setStage("review");
      } catch (e) {
        const err = e as ApiError;
        if (err.code === "ai_unavailable") setAiDown(true);
        if (sample && (err.code === "ai_unavailable" || err.code === "ai_bad_output" || err.code === "network" || err.code === "rate_limited")) {
          // Honest fallback: use the sample's typed lines, and say so.
          setLines(toLines(sample.lines));
          setProblem(sample.problem.replace(/^Solve\s+/, ""));
          setNotice("Handwriting reading is unavailable, so Redline loaded the typed version of this sample. The math check is the same.");
          setStage("review");
          return;
        }
        setError(err);
        setImage(null);
        URL.revokeObjectURL(prepared.url);
        setStage("capture");
        if (err.code === "ai_unavailable") setMode("type");
      }
    },
    [],
  );

  const loadSample = useCallback(
    async (s: Sample) => {
      try {
        const blob = await (await fetch(s.image)).blob();
        await readImage(blob, s);
      } catch {
        setError(new ApiError(0, "network", "Couldn't load the sample. Check your connection."));
      }
    },
    [readImage],
  );

  // ?sample=id deep link (from the landing page)
  useEffect(() => {
    const id = params.get("sample");
    const s = samples.find((x) => x.id === id);
    if (gateOk && s && stage === "capture") {
      setParams({}, { replace: true });
      loadSample(s);
    }
  }, [gateOk, samples, params, stage, loadSample, setParams]);

  return (
    <div ref={top} className="mx-auto max-w-6xl scroll-mt-20 px-4 pb-20 pt-8 sm:px-6 sm:pt-10">
      {!gateOk && <Gate onAccept={() => setGateOk(true)} />}
      <p aria-live="polite" className="sr-only">
        {announce}
      </p>
      <Progress stage={stage} hasImage={!!image} />

      {error && (
        <div className="mt-6">
          <Banner tone="error" action={stage !== "capture" ? undefined : <Button size="sm" variant="secondary" onClick={() => setMode("type")}>Type steps instead</Button>}>
            {error.message}
          </Banner>
        </div>
      )}
      {aiDown && stage !== "results" && (
        <div className="mt-4">
          <Banner tone="warn">
            AI reading is unavailable right now. Redline can still check typed steps and give built-in hints.
          </Banner>
        </div>
      )}

      {stage === "capture" && (
        <Capture
          mode={mode}
          setMode={setMode}
          samples={samples}
          disabled={!gateOk}
          onFile={(f) => readImage(f)}
          onSample={loadSample}
          onTyped={(prob, ls) => {
            setProblem(prob);
            runVerify(toLines(ls), prob);
          }}
        />
      )}
      {(stage === "reading" || stage === "checking") && <Working image={image} stage={stage} />}
      {stage === "review" && (
        <Review
          image={image}
          problem={problem}
          setProblem={setProblem}
          lines={lines}
          setLines={setLines}
          notes={notes}
          notice={notice}
          onBack={reset}
          onConfirm={() => runVerify(lines.filter((l) => l.ascii.trim()), problem)}
        />
      )}
      {stage === "results" && result && (
        <Results
          image={image}
          problem={problem}
          lines={checkedLines}
          result={result}
          health={health}
          aiDown={aiDown || result.offline}
          lastMisconception={lastMisconception}
          onRecheck={(ls) => runVerify(ls, problem)}
          onRestart={reset}
          onEditAll={() => setStage("review")}
          error={error}
        />
      )}
    </div>
  );
}

function Progress({ stage, hasImage }: { stage: Stage; hasImage: boolean }) {
  const steps = hasImage ? ["Add your work", "Confirm the reading", "Results"] : ["Add your work", "Results"];
  const at = stage === "capture" ? 0 : stage === "reading" || stage === "review" ? 1 : hasImage ? 2 : 1;
  return (
    <ol className="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm" aria-label="Progress">
      {steps.map((s, i) => (
        <li key={s} className="flex items-center gap-2">
          <span
            aria-current={i === at ? "step" : undefined}
            className={`inline-flex items-center gap-2 ${i === at ? "font-medium text-ink" : i < at ? "text-ink-2" : "text-ink-3"}`}
          >
            <span className={`grid size-5 place-items-center rounded-full text-[11px] tabular-nums ${i <= at ? "bg-ink text-paper" : "border border-ink/25"}`}>
              {i < at ? <CheckIcon className="size-3" strokeWidth={3} aria-hidden /> : i + 1}
            </span>
            {s}
          </span>
          {i < steps.length - 1 && <span aria-hidden className="h-px w-6 bg-ink/20" />}
        </li>
      ))}
    </ol>
  );
}

// ---------------- capture ----------------

function Capture(props: {
  mode: "photo" | "type";
  setMode: (m: "photo" | "type") => void;
  samples: Sample[];
  disabled: boolean;
  onFile: (f: File) => void;
  onSample: (s: Sample) => void;
  onTyped: (problem: string, lines: string[]) => void;
}) {
  const { mode, setMode } = props;
  return (
    <section className="mt-8 grid gap-10 lg:grid-cols-[1.4fr_1fr]">
      <div>
        <h1 className="font-display text-3xl font-semibold sm:text-4xl">Check your work</h1>
        <p className="mt-2 text-ink-2">Add the steps you wrote. Redline will find the first line that doesn't follow.</p>
        <div role="tablist" aria-label="Input method" className="mt-6 inline-flex rounded-lg border border-rule bg-sheet p-1">
          {(
            [
              ["photo", "Photo", <Camera key="c" className="size-4" aria-hidden />],
              ["type", "Type steps", <Keyboard key="k" className="size-4" aria-hidden />],
            ] as const
          ).map(([m, label, icon]) => (
            <button
              key={m}
              role="tab"
              type="button"
              aria-selected={mode === m}
              onClick={() => setMode(m)}
              className={`inline-flex h-9 items-center gap-2 rounded-md px-3.5 text-sm font-medium transition-colors ${mode === m ? "bg-ink text-paper" : "text-ink-2 hover:text-ink"}`}
            >
              {icon}
              {label}
            </button>
          ))}
        </div>
        <div className="mt-5">{mode === "photo" ? <Dropzone {...props} /> : <Typed onSubmit={props.onTyped} disabled={props.disabled} />}</div>
      </div>
      <aside className="space-y-8">
        <div>
          <h2 className="font-display text-xl font-semibold">Try a sample</h2>
          <p className="mt-1 text-sm text-ink-2">Each one has a different mistake. Samples go through the full live pipeline.</p>
          <ul className="mt-4 space-y-2">
            {props.samples.map((s) => (
              <li key={s.id}>
                <button
                  type="button"
                  disabled={props.disabled}
                  onClick={() => props.onSample(s)}
                  className="group flex w-full items-center gap-3 rounded-xl border border-rule bg-sheet p-2.5 text-left transition-colors hover:border-ink/35 disabled:opacity-50"
                >
                  <img src={s.image} alt="" className="h-14 w-20 shrink-0 rounded-md border border-rule object-cover object-top" />
                  <span className="min-w-0">
                    <span className="block text-sm font-medium">{s.title}</span>
                    <span className="block truncate text-sm text-ink-2">
                      <MathText ascii={s.problem.replace(/^Solve\s+/, "")} />
                    </span>
                  </span>
                </button>
              </li>
            ))}
            {!props.samples.length && <Skeleton className="h-20 w-full" />}
          </ul>
          <p className="mt-2 text-xs text-ink-3">Sample sheets are rendered in a handwriting font, not photographed.</p>
        </div>
        <div>
          <h2 className="font-display text-xl font-semibold">For a good reading</h2>
          <ul className="mt-2 list-disc space-y-1.5 pl-5 text-sm text-ink-2">
            <li>Write one step per line.</li>
            <li>Use one letter for the unknown, like x.</li>
            <li>Shoot from above in good light; crop out other work.</li>
            <li>Leave out your name and personal details.</li>
          </ul>
        </div>
      </aside>
    </section>
  );
}

function Dropzone({ onFile, disabled }: { onFile: (f: File) => void; disabled: boolean }) {
  const [over, setOver] = useState(false);
  const input = useRef<HTMLInputElement>(null);
  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setOver(true);
      }}
      onDragLeave={() => setOver(false)}
      onDrop={(e) => {
        e.preventDefault();
        setOver(false);
        const f = e.dataTransfer.files?.[0];
        if (f && !disabled) onFile(f);
      }}
      className={`quad flex min-h-72 flex-col items-center justify-center rounded-2xl border-2 border-dashed px-6 py-10 text-center transition-colors ${over ? "border-ink/60" : "border-ink/20"}`}
    >
      <ImageUp className="size-8 text-ink-3" aria-hidden />
      <p className="mt-3 font-display text-xl font-semibold">Photograph or upload your working</p>
      <p className="mt-1 text-sm text-ink-2">JPG or PNG. Drag a file here on desktop.</p>
      <input
        ref={input}
        type="file"
        accept="image/*"
        capture="environment"
        className="sr-only"
        aria-label="Choose a photo of your working"
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) onFile(f);
          e.target.value = "";
        }}
      />
      <div className="mt-6 flex flex-wrap justify-center gap-3">
        <Button disabled={disabled} icon={<Camera className="size-4" aria-hidden />} onClick={() => input.current?.click()}>
          Take or choose a photo
        </Button>
      </div>
    </div>
  );
}

function Typed({ onSubmit, disabled }: { onSubmit: (problem: string, lines: string[]) => void; disabled: boolean }) {
  const [problem, setProblem] = useState("");
  const [text, setText] = useState("");
  const ls = useMemo(() => text.split("\n").map((s) => s.trim()).filter(Boolean), [text]);
  return (
    <form
      className="space-y-4"
      onSubmit={(e) => {
        e.preventDefault();
        if (ls.length) onSubmit(problem.trim(), ls.slice(0, 20));
      }}
    >
      <label className="block">
        <span className="text-sm font-medium">Problem (optional)</span>
        <input
          value={problem}
          onChange={(e) => setProblem(e.target.value)}
          maxLength={120}
          placeholder="5 - 2(x - 3) = 1"
          className="mt-1.5 h-11 w-full rounded-lg border border-ink/20 bg-sheet px-3 font-mono text-[15px] placeholder:text-ink-3 focus:border-ink/50"
        />
      </label>
      <div className="grid gap-4 md:grid-cols-2">
        <label className="block">
          <span className="text-sm font-medium">Your steps, one per line</span>
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={8}
            spellCheck={false}
            placeholder={"5 - 2(x - 3) = 1\n5 - 2x - 6 = 1\n-2x - 1 = 1\n-2x = 2\nx = -1"}
            className="mt-1.5 w-full rounded-lg border border-ink/20 bg-sheet px-3 py-2.5 font-mono text-[15px] leading-7 placeholder:text-ink-3 focus:border-ink/50"
          />
          <span className="mt-1 block text-xs text-ink-3">Use ^ for powers, sqrt() for roots, and "or" between answers.</span>
        </label>
        <div aria-label="Preview" className="quad min-h-48 rounded-lg border border-rule p-4">
          <p className="text-xs text-ink-3">Preview</p>
          <ol className="mt-2 space-y-2">
            {ls.map((l, i) => (
              <li key={i} className="flex items-baseline gap-3">
                <span className="w-4 text-right text-xs tabular-nums text-ink-3">{i + 1}</span>
                <MathText ascii={l} />
              </li>
            ))}
          </ol>
        </div>
      </div>
      <Button type="submit" disabled={disabled || !ls.length}>
        Check my steps
      </Button>
    </form>
  );
}

// ---------------- reading / review ----------------

function Working({ image, stage }: { image: PreparedImage | null; stage: Stage }) {
  return (
    <section className="mt-8 grid gap-8 md:grid-cols-2" aria-busy>
      {image && <img src={image.url} alt="Your working" className="max-h-[70vh] w-full rounded-2xl border border-rule object-contain" />}
      <div className="space-y-4">
        <p className="font-display text-2xl font-semibold">{stage === "reading" ? "Reading your handwriting…" : "Checking your steps…"}</p>
        <p className="text-sm text-ink-2">
          {stage === "reading" ? "Usually takes a few seconds. Nothing is stored." : "The math engine is comparing each line with the one before."}
        </p>
        <div className="space-y-3 pt-2">
          {["w-4/5", "w-2/3", "w-3/4", "w-1/2"].map((w) => (
            <Skeleton key={w} className={`h-9 ${w}`} />
          ))}
        </div>
      </div>
    </section>
  );
}

function PhotoWithBoxes({ image, lines, children }: { image: PreparedImage; lines: Line[]; children?: (l: Line, i: number) => ReactNode }) {
  return (
    <div className="relative overflow-hidden rounded-2xl border border-rule bg-sheet">
      <img src={image.url} alt="Your working, with each line outlined" className="block w-full" />
      {lines.map((l, i) => (l.box ? <div key={l.id} className="absolute" style={boxStyle(l.box)}>{children?.(l, i)}</div> : null))}
    </div>
  );
}

function Review(props: {
  image: PreparedImage | null;
  problem: string;
  setProblem: (s: string) => void;
  lines: Line[];
  setLines: (ls: Line[]) => void;
  notes: string | null;
  notice: string | null;
  onBack: () => void;
  onConfirm: () => void;
}) {
  const { lines, setLines } = props;
  const update = (id: string, ascii: string) =>
    setLines(lines.map((l) => (l.id === id ? { ...l, ascii, parse_ok: undefined, parse_error: undefined, confidence: "high" } : l)));
  const flagged = lines.filter((l) => l.parse_ok === false || l.confidence === "low").length;
  return (
    <section className="mt-8 grid gap-8 lg:grid-cols-2">
      <div className="lg:sticky lg:top-24 lg:self-start">
        {props.image ? (
          <PhotoWithBoxes image={props.image} lines={lines}>
            {(l, i) => (
              <div className={`size-full rounded-md border-2 ${l.parse_ok === false || l.confidence === "low" ? "border-amber/80 bg-amber-soft" : "border-[#2f5fb3]/45"}`}>
                <span className="absolute -left-1 top-1/2 grid size-5 -translate-x-full -translate-y-1/2 place-items-center rounded-full bg-ink text-[11px] font-medium tabular-nums text-paper">
                  {i + 1}
                </span>
              </div>
            )}
          </PhotoWithBoxes>
        ) : (
          <Banner>{props.notice ?? "No photo for this check."}</Banner>
        )}
      </div>
      <div>
        <h1 className="font-display text-3xl font-semibold">Is this what you wrote?</h1>
        <p className="mt-2 text-ink-2">
          Fix anything that was misread before checking. Redline judges exactly what's here, so a misread line would blame you for
          something you didn't write.
        </p>
        {props.notice && props.image && <div className="mt-4"><Banner tone="warn">{props.notice}</Banner></div>}
        {flagged > 0 && (
          <div className="mt-4">
            <Banner tone="warn">
              {flagged === 1 ? "One line is" : `${flagged} lines are`} marked in amber: the reading was uncertain. Please check {flagged === 1 ? "it" : "them"}.
            </Banner>
          </div>
        )}
        <label className="mt-6 block">
          <span className="text-sm font-medium">Problem</span>
          <input
            value={props.problem}
            onChange={(e) => props.setProblem(e.target.value)}
            maxLength={120}
            placeholder="Optional — the equation you were asked to solve"
            className="mt-1.5 h-11 w-full rounded-lg border border-ink/20 bg-sheet px-3 font-mono text-[15px] focus:border-ink/50"
          />
        </label>
        <ol className="mt-5 space-y-3">
          {lines.map((l, i) => {
            const warn = l.parse_ok === false || l.confidence === "low";
            return (
              <li key={l.id} className={`rounded-xl border p-3 ${warn ? "border-amber/50 bg-amber-soft" : "border-rule bg-sheet"}`}>
                <div className="flex items-center gap-3">
                  <span className="grid size-6 shrink-0 place-items-center rounded-full bg-ink text-xs tabular-nums text-paper">{i + 1}</span>
                  <input
                    value={l.ascii}
                    onChange={(e) => update(l.id, e.target.value)}
                    aria-label={`Line ${i + 1}`}
                    maxLength={120}
                    spellCheck={false}
                    className="h-10 min-w-0 flex-1 rounded-md border border-ink/15 bg-paper px-2.5 font-mono text-[15px] focus:border-ink/50"
                  />
                  <button
                    type="button"
                    onClick={() => setLines(lines.filter((x) => x.id !== l.id))}
                    className="grid size-9 shrink-0 place-items-center rounded-md text-ink-3 hover:bg-ink/5 hover:text-red"
                    aria-label={`Remove line ${i + 1}`}
                  >
                    <Trash2 className="size-4" />
                  </button>
                </div>
                <div className="mt-2 flex flex-wrap items-baseline justify-between gap-2 pl-9">
                  <MathText ascii={l.ascii} />
                  {warn && <span className="text-xs text-amber">{l.parse_error ?? "Uncertain reading — check this line"}</span>}
                </div>
              </li>
            );
          })}
        </ol>
        <Button variant="ghost" size="sm" className="mt-3" icon={<Plus className="size-4" aria-hidden />} onClick={() => setLines([...lines, { id: newId(), ascii: "" }])}>
          Add a line
        </Button>
        {props.notes && <p className="mt-3 text-xs text-ink-3">Reader note: {props.notes}</p>}
        <div className="mt-8 flex flex-wrap items-center gap-3 border-t border-rule pt-6">
          <Button size="lg" onClick={props.onConfirm} disabled={!lines.some((l) => l.ascii.trim())}>
            Looks right — check my steps
          </Button>
          <Button variant="ghost" onClick={props.onBack}>
            Start over
          </Button>
        </div>
      </div>
    </section>
  );
}

// ---------------- results ----------------

function Results(props: {
  image: PreparedImage | null;
  problem: string;
  lines: Line[];
  result: VerifyResult;
  health: Health | null;
  aiDown: boolean;
  lastMisconception: string | null;
  error: ApiError | null;
  onRecheck: (ls: Line[]) => Promise<void>;
  onRestart: () => void;
  onEditAll: () => void;
}) {
  const { lines, result } = props;
  const status = useMemo(() => new Map(result.lines.map((l) => [l.id, l])), [result]);
  const errIdx = lines.findIndex((l) => l.id === result.first_error_id);
  const errLine = errIdx >= 0 ? lines[errIdx] : null;
  const allGood = errIdx < 0 && result.final_correct === true;
  const unreadable = lines.filter((l) => status.get(l.id)?.status === "unreadable");
  const extraneous = errLine && status.get(errLine.id)?.detail === "keeps_extraneous";

  return (
    <section className="mt-8 grid gap-8 lg:grid-cols-[1fr_1.05fr]">
      <div className="lg:sticky lg:top-24 lg:self-start">
        {props.image && lines.some((l) => l.box) ? (
          <PhotoWithBoxes image={props.image} lines={lines}>
            {(l) => {
              const st = status.get(l.id)?.status;
              if (l.id === result.first_error_id)
                return (
                  <>
                    <div className="size-full rounded-md border-2 border-red bg-red-soft" />
                    <RedUnderline className="absolute -bottom-3 left-0 h-3.5 w-full" />
                  </>
                );
              if (l.orig !== undefined && l.orig !== l.ascii)
                return (
                  <span className="absolute -right-1 top-1/2 -translate-y-1/2 translate-x-full rounded bg-amber-soft px-1.5 py-0.5 text-[11px] font-medium text-amber">
                    edited
                  </span>
                );
              if (!st || st === "start" || st === "segment_break") return null;
              return (
                <span className="absolute -right-1 top-1/2 -translate-y-1/2 translate-x-full">
                  <StatusIcon status={st} size="sm" />
                </span>
              );
            }}
          </PhotoWithBoxes>
        ) : (
          <div className="quad rounded-2xl border border-rule p-5 sm:p-7">
            {props.problem && <p className="mb-4 text-sm text-ink-3">Problem: <MathText ascii={props.problem} /></p>}
            <ol className="space-y-4">
              {lines.map((l, i) => {
                const st = status.get(l.id)?.status ?? "start";
                return (
                  <li key={l.id} className="grid grid-cols-[1.5rem_1fr_auto] items-center gap-3">
                    <span className="text-right text-xs tabular-nums text-ink-3">{i + 1}</span>
                    <span className="relative w-fit text-lg">
                      <MathText ascii={l.ascii} />
                      {l.id === result.first_error_id && <RedUnderline className="absolute -bottom-2.5 left-0 h-3 w-full" />}
                    </span>
                    {st !== "start" && st !== "segment_break" && <StatusIcon status={st} size="sm" />}
                  </li>
                );
              })}
            </ol>
          </div>
        )}
        <div className="mt-4 flex flex-wrap gap-2">
          <Button variant="secondary" size="sm" onClick={props.onEditAll}>
            Edit lines
          </Button>
          <Button variant="ghost" size="sm" icon={<RotateCcw className="size-4" aria-hidden />} onClick={props.onRestart}>
            Check different work
          </Button>
        </div>
      </div>

      <div className="min-w-0 space-y-6">
        <Verdict result={result} errIdx={errIdx} total={lines.length} extraneous={!!extraneous} />
        {props.error && <Banner tone="error">{props.error.message}</Banner>}
        {!result.scope_ok && (
          <Banner tone="warn">This looks beyond Redline's scope (degree above 4). Results may be incomplete.</Banner>
        )}
        {unreadable.length > 0 && (
          <Banner tone="warn">
            Redline couldn't read line {unreadable.map((l) => lines.indexOf(l) + 1).join(", ")}, so it skipped {unreadable.length === 1 ? "it" : "them"}. Fix the line below to include it.
          </Banner>
        )}
        {props.aiDown && (
          <Banner tone="warn">AI explanations are unavailable right now. Verification still works, and hints come from Redline's built-in library.</Banner>
        )}

        <StepList lines={lines} result={result} status={status} onRecheck={props.onRecheck} />

        {errLine && (
          <>
            <MisconceptionCard result={result} />
            <Hints
              key={`${errLine.id}:${errLine.ascii}:${result.misconception?.id}`}
              lines={lines}
              problem={props.problem}
              errorLineId={errLine.id}
              misconceptionId={result.misconception?.id ?? "OTHER"}
            />
            {props.health?.db === "ok" && result.misconception && <ShareToClass misconceptionId={result.misconception.id} />}
          </>
        )}
        {allGood && props.lastMisconception && <Practice misconceptionId={props.lastMisconception} />}
      </div>
    </section>
  );
}

function Verdict({ result, errIdx, total, extraneous }: { result: VerifyResult; errIdx: number; total: number; extraneous: boolean }) {
  if (errIdx >= 0)
    return (
      <div>
        <p className="text-sm font-medium text-red">Line {errIdx + 1}</p>
        <h1 className="mt-1 font-display text-3xl font-semibold leading-tight">
          {extraneous
            ? "Your final answer includes a value that doesn't solve the original equation."
            : result.lines[errIdx]?.status === "lost_solution"
              ? `Line ${errIdx + 1} loses a solution.`
              : `Line ${errIdx + 1} doesn't follow from the line before it.`}
        </h1>
        <p className="mt-2 text-ink-2">The math engine proved it; here's what likely happened and how to find it yourself.</p>
      </div>
    );
  if (result.final_correct)
    return (
      <div className="fade-in rounded-2xl border border-green/30 bg-green-soft p-5">
        <p className="flex items-center gap-2 text-sm font-medium text-green">
          <Sparkles className="size-4" aria-hidden /> Verified
        </p>
        <h1 className="mt-1 font-display text-3xl font-semibold">All {total} steps verified.</h1>
        <p className="mt-1 text-ink-2">Every line follows from the one before, and your answer solves the original equation.</p>
      </div>
    );
  return (
    <div>
      <h1 className="font-display text-3xl font-semibold">Every step so far follows.</h1>
      <p className="mt-2 text-ink-2">Keep going: add your next step below until the variable is on its own.</p>
    </div>
  );
}

function StepList({
  lines,
  result,
  status,
  onRecheck,
}: {
  lines: Line[];
  result: VerifyResult;
  status: Map<string, VerifyResult["lines"][number]>;
  onRecheck: (ls: Line[]) => Promise<void>;
}) {
  const [editing, setEditing] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [dropAfter, setDropAfter] = useState(true);
  const errIdx = lines.findIndex((l) => l.id === result.first_error_id);

  const submit = async (ls: Line[]) => {
    setBusy(true);
    await onRecheck(ls);
    setBusy(false);
    setEditing(null);
  };

  const editor = (onSave: () => void, label: string) => (
    <form
      className="mt-3 space-y-2"
      onSubmit={(e) => {
        e.preventDefault();
        if (draft.trim()) onSave();
      }}
    >
      <input
        autoFocus
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        maxLength={120}
        spellCheck={false}
        aria-label={label}
        className="h-11 w-full rounded-lg border border-ink/25 bg-paper px-3 font-mono text-[15px] focus:border-ink/60"
      />
      {draft.trim() && (
        <p className="text-sm text-ink-2">
          Preview: <MathText ascii={draft} />
        </p>
      )}
      {editing !== "__new" && lines.findIndex((l) => l.id === editing) < lines.length - 1 && (
        <label className="flex items-center gap-2 text-sm text-ink-2">
          <input type="checkbox" className="size-4 accent-[var(--c-ink)]" checked={dropAfter} onChange={(e) => setDropAfter(e.target.checked)} />
          Remove the lines below it — I'll redo them from here
        </label>
      )}
      <div className="flex gap-2">
        <Button size="sm" type="submit" loading={busy}>
          Re-check
        </Button>
        <Button size="sm" variant="ghost" type="button" onClick={() => setEditing(null)}>
          Cancel
        </Button>
      </div>
    </form>
  );

  return (
    <div>
      <h2 className="sr-only">Your steps</h2>
      <ol className="divide-y divide-rule overflow-hidden rounded-2xl border border-rule bg-sheet">
        {lines.map((l, i) => {
          const st = status.get(l.id);
          const isErr = l.id === result.first_error_id;
          return (
            <li key={l.id} className={`px-4 py-3.5 ${isErr ? "bg-red-soft" : ""}`}>
              <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                <span className="w-5 text-right text-xs tabular-nums text-ink-3">{i + 1}</span>
                <span className="min-w-0 flex-1 overflow-x-auto text-[17px]">
                  <MathText ascii={l.ascii} />
                </span>
                {st && (
                  <span className="inline-flex items-center gap-1.5 text-sm text-ink-2">
                    <StatusIcon status={st.status} size="sm" />
                    <span className={isErr ? "font-medium text-red" : ""}>{statusLabel(st.status)}</span>
                  </span>
                )}
                {(isErr || st?.status === "unreadable") && editing !== l.id && (
                  <Button
                    size="sm"
                    variant={isErr ? "primary" : "secondary"}
                    onClick={() => {
                      setDraft(l.ascii);
                      setEditing(l.id);
                    }}
                  >
                    Fix this line
                  </Button>
                )}
              </div>
              {st?.status === "gained_solution" && (
                <p className="ml-8 mt-1 text-sm text-amber">Squaring or multiplying by the variable can add values that don't work. Check your final answers.</p>
              )}
              {editing === l.id &&
                editor(
                  () =>
                    submit(
                      lines
                        .slice(0, dropAfter ? i + 1 : lines.length)
                        .map((x) => (x.id === l.id ? { ...x, ascii: draft.trim() } : x)),
                    ),
                  `New version of line ${i + 1}`,
                )}
            </li>
          );
        })}
      </ol>
      {errIdx >= 0 && errIdx < lines.length - 1 && (
        <p className="mt-2 text-sm text-ink-3">Lines after your fix may need updating too — Redline re-checks every line as written.</p>
      )}
      {editing === "__new" ? (
        <div className="mt-3 rounded-2xl border border-rule bg-sheet p-4">{editor(() => submit([...lines, { id: newId(), ascii: draft.trim() }]), "Next step")}</div>
      ) : (
        lines.length < 20 && (
          <Button
            variant="ghost"
            size="sm"
            className="mt-2"
            icon={<Plus className="size-4" aria-hidden />}
            onClick={() => {
              setDraft("");
              setEditing("__new");
            }}
          >
            Add next step
          </Button>
        )
      )}
    </div>
  );
}

function MisconceptionCard({ result }: { result: VerifyResult }) {
  const m = result.misconception;
  if (!m)
    return (
      <div className="rounded-2xl border border-rule bg-sheet p-5">
        <h2 className="font-display text-xl font-semibold">Redline couldn't name this mistake</h2>
        <p className="mt-1.5 text-[15px] leading-relaxed text-ink-2">
          The line is proven wrong, but it doesn't match one of the known misconceptions{result.offline ? " and the AI is offline" : ""}. Compare it
          with the line before, one operation at a time.
        </p>
      </div>
    );
  return (
    <div className="rounded-2xl border border-rule bg-sheet p-5">
      <div className="flex flex-wrap items-center gap-2">
        {m.evidence === "verified" ? (
          <Badge tone="ok">Verified diagnosis</Badge>
        ) : (
          <Badge tone="muted">AI hypothesis</Badge>
        )}
        <span className="text-xs text-ink-3">
          {m.evidence === "verified"
            ? "Redline reproduced your line by applying this mistake in code."
            : "No known pattern reproduced your line exactly, so this is the AI's best guess."}
        </span>
      </div>
      <h2 className="mt-3 font-display text-2xl font-semibold leading-snug">{m.name}</h2>
      <p className="mt-1.5 text-[15px] leading-relaxed text-ink-2">{m.evidence === "ai_hypothesis" && m.rationale ? m.rationale : m.description}</p>
      {m.focus && (
        <p className="mt-3 text-sm text-ink-2">
          Where to look: <MathText ascii={m.focus} />
        </p>
      )}
    </div>
  );
}

function ShareToClass({ misconceptionId }: { misconceptionId: string }) {
  const [code, setCode] = useState("");
  const [state, setState] = useState<"idle" | "busy" | "done" | "error">("idle");
  const [msg, setMsg] = useState("");
  if (state === "done")
    return (
      <p className="flex items-center gap-2 text-sm text-green">
        <CheckIcon className="size-4" aria-hidden /> Shared anonymously with class {code.toUpperCase()}.
      </p>
    );
  return (
    <details className="rounded-2xl border border-rule bg-sheet p-4">
      <summary className="flex cursor-pointer items-center gap-2 text-sm font-medium">
        <Users className="size-4" aria-hidden /> Share this mistake with my class (anonymous)
      </summary>
      <form
        className="mt-3 flex flex-wrap items-end gap-2"
        onSubmit={async (e) => {
          e.preventDefault();
          setState("busy");
          try {
            await api.shareEvent(code.trim().toUpperCase(), misconceptionId);
            setState("done");
          } catch (err) {
            setMsg((err as ApiError).code === "class_not_found" ? "No class with that code." : (err as ApiError).message);
            setState("error");
          }
        }}
      >
        <label className="block">
          <span className="text-xs text-ink-2">Class code</span>
          <input
            value={code}
            onChange={(e) => setCode(e.target.value)}
            maxLength={6}
            required
            pattern="[A-Za-z2-9]{6}"
            className="mt-1 block h-10 w-36 rounded-lg border border-ink/20 bg-paper px-3 font-mono uppercase tracking-widest"
          />
        </label>
        <Button size="sm" type="submit" loading={state === "busy"}>
          Share
        </Button>
        <p className="w-full text-xs text-ink-3">Only the mistake type is sent — no photo, no lines, no name.</p>
        {state === "error" && <p className="w-full text-sm text-red">{msg}</p>}
      </form>
    </details>
  );
}
