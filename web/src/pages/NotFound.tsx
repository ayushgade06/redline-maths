import { Link } from "react-router-dom";
import { RedUnderline } from "../components/ui";

export default function NotFound() {
  return (
    <div className="mx-auto max-w-2xl px-4 py-20 sm:px-6">
      <h1 className="relative w-fit font-display text-5xl font-semibold">
        This page doesn't follow
        <RedUnderline className="absolute -bottom-3 left-0 h-4 w-full" />
      </h1>
      <p className="mt-8 text-lg text-ink-2">There's nothing at this address.</p>
      <Link to="/" className="mt-6 inline-block underline decoration-ink/30 underline-offset-4 hover:decoration-ink">
        Back to Redline
      </Link>
    </div>
  );
}
