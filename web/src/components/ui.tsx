import katex from "katex";
import { AlertTriangle, Check, CircleHelp, Info, Loader2, ShieldCheck, X } from "lucide-react";
import { type ButtonHTMLAttributes, type ReactNode, useMemo } from "react";
import type { LineStatus } from "../lib/api";
import { asciiToLatex, asciiToSpeech } from "../lib/math";

type Variant = "primary" | "secondary" | "ghost" | "quiet";

const VARIANTS: Record<Variant, string> = {
  primary:
    "bg-ink text-paper hover:bg-ink/88 active:translate-y-px shadow-[0_1px_0_rgba(0,0,0,.25),inset_0_1px_0_rgba(255,255,255,.12)]",
  secondary: "border border-ink/20 bg-sheet text-ink hover:border-ink/45 active:translate-y-px",
  ghost: "text-ink-2 hover:text-ink hover:bg-ink/5",
  quiet: "text-ink-2 underline decoration-ink/25 underline-offset-4 hover:decoration-ink hover:text-ink",
};

export function Button({
  variant = "primary",
  size = "md",
  loading,
  icon,
  children,
  className = "",
  disabled,
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; size?: "sm" | "md" | "lg"; loading?: boolean; icon?: ReactNode }) {
  const sizes = { sm: "h-9 px-3 text-sm gap-1.5", md: "h-11 px-4 text-[15px] gap-2", lg: "h-12 px-5 text-base gap-2" };
  return (
    <button
      {...rest}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={`inline-flex select-none items-center justify-center rounded-lg font-medium transition-[background,border,color,transform] duration-150 disabled:cursor-not-allowed disabled:opacity-45 ${variant === "quiet" ? "h-auto px-0" : sizes[size]} ${VARIANTS[variant]} ${className}`}
    >
      {loading ? <Loader2 className="size-4 animate-spin" aria-hidden /> : icon}
      {children}
    </button>
  );
}

export function MathText({ ascii, display = false, className = "" }: { ascii: string; display?: boolean; className?: string }) {
  const html = useMemo(
    () => katex.renderToString(asciiToLatex(ascii), { throwOnError: false, displayMode: display, output: "html" }),
    [ascii, display],
  );
  return <span role="img" aria-label={asciiToSpeech(ascii)} className={className} dangerouslySetInnerHTML={{ __html: html }} />;
}

/** Render hint text, typesetting `backtick` math spans with KaTeX. */
export function RichText({ text }: { text: string }) {
  const parts = text.split(/(`[^`]+`)/g);
  return (
    <>
      {parts.map((p, i) =>
        p.startsWith("`") && p.endsWith("`") && p.length > 2 ? <MathText key={i} ascii={p.slice(1, -1)} /> : <span key={i}>{p}</span>,
      )}
    </>
  );
}

const STATUS: Record<LineStatus, { label: string; tone: "ok" | "bad" | "warn" | "muted"; Icon: typeof Check }> = {
  start: { label: "Starting line", tone: "muted", Icon: Info },
  valid: { label: "Follows correctly", tone: "ok", Icon: Check },
  invalid: { label: "Doesn't follow", tone: "bad", Icon: X },
  lost_solution: { label: "Loses a solution", tone: "bad", Icon: X },
  gained_solution: { label: "May add a false solution", tone: "warn", Icon: AlertTriangle },
  unreadable: { label: "Couldn't read", tone: "warn", Icon: CircleHelp },
  undetermined: { label: "Couldn't verify automatically", tone: "muted", Icon: CircleHelp },
  segment_break: { label: "New part", tone: "muted", Icon: Info },
};

const TONE = {
  ok: "text-green bg-green-soft",
  bad: "text-red bg-red-soft",
  warn: "text-amber bg-amber-soft",
  muted: "text-ink-3 bg-ink/5",
};

export function statusLabel(s: LineStatus) {
  return STATUS[s].label;
}

export function StatusIcon({ status, size = "md" }: { status: LineStatus; size?: "sm" | "md" }) {
  const { tone, Icon, label } = STATUS[status];
  const dim = size === "sm" ? "size-5" : "size-6";
  return (
    <span className={`inline-grid shrink-0 place-items-center rounded-full ${dim} ${TONE[tone]}`} title={label}>
      <Icon className={size === "sm" ? "size-3" : "size-3.5"} strokeWidth={2.75} aria-hidden />
    </span>
  );
}

export function Badge({ tone, children, icon }: { tone: "ok" | "bad" | "warn" | "muted"; children: ReactNode; icon?: ReactNode }) {
  return (
    <span className={`inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-xs font-medium ${TONE[tone]}`}>
      {icon}
      {children}
    </span>
  );
}

export function GuardChip({ regenerated }: { regenerated: boolean }) {
  const tip = regenerated
    ? "A draft gave away part of the solution, so Redline rewrote it. This hint passed the check."
    : "Before you see a hint, code checks that it contains no answer, no corrected line and no solution value.";
  return (
    <span className="group relative inline-flex">
      <span tabIndex={0} aria-describedby={undefined} className="inline-flex cursor-help items-center gap-1 rounded-md bg-green-soft px-2 py-0.5 text-xs font-medium text-green">
        <ShieldCheck className="size-3.5" aria-hidden />
        Answer guard passed
        <span className="sr-only">. {tip}</span>
      </span>
      <span
        role="tooltip"
        className="pointer-events-none absolute bottom-full left-0 z-20 mb-2 w-64 rounded-lg bg-ink px-3 py-2 text-xs leading-relaxed text-paper opacity-0 shadow-lg transition-opacity group-focus-within:opacity-100 group-hover:opacity-100"
      >
        {tip}
      </span>
    </span>
  );
}

export function Banner({ tone = "info", children, action }: { tone?: "info" | "warn" | "error"; children: ReactNode; action?: ReactNode }) {
  const styles = {
    info: "border-ink/12 bg-sheet text-ink-2",
    warn: "border-amber/30 bg-amber-soft text-ink",
    error: "border-red/30 bg-red-soft text-ink",
  };
  const Icon = tone === "info" ? Info : AlertTriangle;
  return (
    <div role={tone === "error" ? "alert" : "status"} className={`flex flex-wrap items-start gap-3 rounded-xl border px-4 py-3 text-sm ${styles[tone]}`}>
      <Icon className={`mt-0.5 size-4 shrink-0 ${tone === "error" ? "text-red" : tone === "warn" ? "text-amber" : "text-ink-3"}`} aria-hidden />
      <div className="min-w-0 flex-1 leading-relaxed">{children}</div>
      {action}
    </div>
  );
}

export function Skeleton({ className = "" }: { className?: string }) {
  return <span aria-hidden className={`block animate-pulse rounded-md bg-ink/8 ${className}`} />;
}

/** The hand-drawn red underline, sized to its container. */
export function RedUnderline({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 200 14" preserveAspectRatio="none" className={className} aria-hidden>
      <path
        className="pen-stroke"
        pathLength={1}
        d="M2 9.5 C 40 4.5, 75 11.5, 110 7.5 S 170 4, 198 8.5"
        fill="none"
        stroke="var(--c-red)"
        strokeWidth="3.2"
        strokeLinecap="round"
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  );
}

export function Wordmark() {
  return (
    <span className="relative inline-block font-display text-[22px] font-semibold leading-none tracking-tight">
      Redline
      <svg viewBox="0 0 100 8" preserveAspectRatio="none" className="absolute -bottom-1.5 left-0 h-2 w-full" aria-hidden>
        <path d="M1 5 C 30 2.5, 60 6.5, 99 3.5" fill="none" stroke="var(--c-red)" strokeWidth="2.4" strokeLinecap="round" vectorEffect="non-scaling-stroke" />
      </svg>
    </span>
  );
}
