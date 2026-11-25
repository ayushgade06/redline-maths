export default function Privacy() {
  return (
    <article className="mx-auto max-w-2xl px-4 py-12 sm:px-6">
      <h1 className="font-display text-4xl font-semibold">Privacy</h1>
      <div className="mt-6 space-y-5 text-[15px] leading-relaxed text-ink-2">
        <p>Redline is for learners aged 18 and over. It has no accounts and sets no tracking cookies.</p>
        <h2 className="pt-2 font-display text-xl font-semibold text-ink">Photos</h2>
        <p>
          When you upload a photo, your browser shrinks it and sends it to the Redline engine, which forwards it to Anthropic's Claude API to
          read the handwriting. The engine processes the image in memory and never writes it to disk or a database. Anthropic handles API
          inputs under its own commercial terms and privacy policy. Don't include names or personal details in the photo.
        </p>
        <h2 className="pt-2 font-display text-xl font-semibold text-ink">Your steps</h2>
        <p>
          The lines you check are sent to the engine to be verified, and — only when an AI explanation is needed — to the Claude API. They are
          not stored. Server logs record the route, status and timing of each request, never images or line content.
        </p>
        <h2 className="pt-2 font-display text-xl font-semibold text-ink">Class mode</h2>
        <p>
          If you choose to share a mistake with a class, Redline stores the class code, the misconception type and the time. Nothing else.
        </p>
        <h2 className="pt-2 font-display text-xl font-semibold text-ink">In your browser</h2>
        <p>Redline remembers that you passed the 18+ notice, your hint language and your theme in local storage. Clear site data to remove them.</p>
      </div>
    </article>
  );
}
