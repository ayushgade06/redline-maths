import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { acceptGate } from "../lib/storage";
import { Button } from "./ui";

/** One-time 18+ and data notice before anything is sent to the engine. */
export function Gate({ onAccept }: { onAccept: () => void }) {
  const ref = useRef<HTMLDialogElement>(null);
  const [adult, setAdult] = useState(false);
  const [data, setData] = useState(false);

  useEffect(() => {
    const d = ref.current;
    if (d && !d.open) d.showModal();
  }, []);

  return (
    <dialog
      ref={ref}
      aria-labelledby="gate-title"
      onCancel={(e) => e.preventDefault()}
      className="m-auto w-[min(100vw-32px,520px)] rounded-2xl border border-rule bg-sheet p-0 text-ink shadow-2xl"
    >
      <form
        method="dialog"
        className="p-6 sm:p-7"
        onSubmit={(e) => {
          e.preventDefault();
          acceptGate();
          ref.current?.close();
          onAccept();
        }}
      >
        <h2 id="gate-title" className="font-display text-2xl font-semibold">
          Before you check your work
        </h2>
        <p className="mt-3 text-[15px] leading-relaxed text-ink-2">
          Redline is built for learners aged 18 and over. Photos you upload are sent to Anthropic's Claude API to read the
          handwriting, then discarded — Redline never stores them. Leave names and personal details out of the photo.
        </p>
        <fieldset className="mt-5 space-y-3">
          <legend className="sr-only">Confirm to continue</legend>
          <label className="flex cursor-pointer items-start gap-3 rounded-lg border border-rule p-3 text-[15px] hover:border-ink/30">
            <input type="checkbox" className="mt-1 size-4 accent-[var(--c-ink)]" checked={adult} onChange={(e) => setAdult(e.target.checked)} />
            <span>I'm 18 or older.</span>
          </label>
          <label className="flex cursor-pointer items-start gap-3 rounded-lg border border-rule p-3 text-[15px] hover:border-ink/30">
            <input type="checkbox" className="mt-1 size-4 accent-[var(--c-ink)]" checked={data} onChange={(e) => setData(e.target.checked)} />
            <span>
              I understand my photo and steps are sent to an AI service to be read, and I won't include personal information.{" "}
              <Link to="/privacy" className="underline decoration-ink/30 underline-offset-2 hover:decoration-ink" target="_blank">
                Privacy details
              </Link>
            </span>
          </label>
        </fieldset>
        <div className="mt-6 flex flex-wrap items-center justify-between gap-3">
          <Link to="/" className="text-sm text-ink-2 underline decoration-ink/25 underline-offset-4 hover:text-ink">
            Not now
          </Link>
          <Button type="submit" disabled={!adult || !data}>
            Continue
          </Button>
        </div>
      </form>
    </dialog>
  );
}
