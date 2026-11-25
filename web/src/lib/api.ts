const BASE = (import.meta.env?.VITE_ENGINE_URL as string | undefined)?.replace(/\/$/, "") ?? "";

export type Line = {
  id: string;
  ascii: string;
  box?: number[] | null;
  confidence?: "high" | "medium" | "low";
  parse_ok?: boolean;
  parse_error?: string;
  /** What the handwriting reader returned, to flag lines edited since the photo. */
  orig?: string;
};

export type Transcription = { problem: string | null; variable: string; lines: Line[]; notes: string | null };

export type LineStatus =
  | "start" | "valid" | "invalid" | "lost_solution" | "gained_solution" | "unreadable" | "undetermined" | "segment_break";

export type Misconception = {
  id: string;
  name: string;
  description: string;
  concept: string;
  evidence: "verified" | "ai_hypothesis";
  rationale: string | null;
  focus: string | null;
  practice: boolean;
};

export type VerifyResult = {
  variable: string;
  lines: { id: string; status: LineStatus; detail: string }[];
  first_error_id: string | null;
  final_correct: boolean | null;
  misconception: Misconception | null;
  scope_ok: boolean;
  offline: boolean;
};

export type Hint = {
  text: string;
  level: 1 | 2 | 3;
  source: "ai" | "template";
  guard: { passed: boolean; regenerated: boolean };
  example: { problem: string; wrong: string; right: string; note: string } | null;
};

export type PracticeProblem = { template_id: string; params: Record<string, number>; prompt_ascii: string };
export type Health = { status: string; version: string; model: string; ai: "ok" | "disabled"; db: "ok" | "disabled" | "error" };
export type ClassSummary = {
  name: string;
  total: number;
  window_days: number;
  counts: { misconception_id: string; name: string; count: number }[];
  suggestions: { misconception_id: string; name: string; concept: string }[];
};

export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string) {
    super(message);
  }
}

const FRIENDLY: Record<string, string> = {
  network: "Can't reach Redline right now. Check your connection and try again.",
  rate_limited: "That's a lot of checks in a minute — wait a moment and try again.",
  ai_unavailable: "Handwriting reading is unavailable right now. You can type your steps instead.",
  ai_bad_output: "Couldn't read that photo. Try a clearer photo or type your steps.",
  image_invalid: "Use a JPG or PNG photo under 4 MB.",
  unsupported_scope: "Redline checks single-variable algebra (one letter, like x).",
  server: "Something went wrong on our side. Try again in a moment.",
};

export async function toApiError(res: Response | null, err?: unknown): Promise<ApiError> {
  if (!res) return new ApiError(0, "network", FRIENDLY.network + (err ? "" : ""));
  let code = res.status >= 500 ? "server" : "error";
  let message = "";
  try {
    const body = await res.json();
    code = body?.error?.code ?? code;
    message = body?.error?.message ?? "";
  } catch {
    /* non-JSON error page */
  }
  return new ApiError(res.status, code, message || FRIENDLY[code] || FRIENDLY.server);
}

async function call<T>(path: string, body?: unknown, fetcher: typeof fetch = fetch): Promise<T> {
  let res: Response;
  try {
    res = await fetcher(`${BASE}/api${path}`, {
      method: body === undefined ? "GET" : "POST",
      headers: body === undefined ? undefined : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch (e) {
    throw await toApiError(null, e);
  }
  if (!res.ok) throw await toApiError(res);
  return (await res.json()) as T;
}

export const api = {
  call,
  health: () => call<Health>("/health"),
  transcribe: (image_base64: string, mime: string) => call<Transcription>("/transcribe", { image_base64, mime }),
  verify: (lines: Line[], problem?: string | null) =>
    call<VerifyResult>("/verify", { problem: problem || null, lines: lines.map(({ id, ascii }) => ({ id, ascii })) }),
  hint: (b: { lines: Line[]; problem?: string | null; error_line_id: string; misconception_id: string; level: number; lang: string }) =>
    call<Hint>("/hint", { ...b, problem: b.problem || null, lines: b.lines.map(({ id, ascii }) => ({ id, ascii })) }),
  practice: (misconception_id: string, count = 2) =>
    call<{ problems: PracticeProblem[] }>("/practice/generate", { misconception_id, count }),
  checkPractice: (template_id: string, prompt_ascii: string, answer_ascii: string) =>
    call<{ correct: boolean; feedback_code: string; message?: string }>("/practice/check", { template_id, prompt_ascii, answer_ascii }),
  createClass: (name: string) => call<{ code: string; dashboard_path: string }>("/class", { name }),
  shareEvent: (code: string, misconception_id: string) => call<{ ok: true }>(`/class/${encodeURIComponent(code)}/events`, { misconception_id }),
  classSummary: (code: string) => call<ClassSummary>(`/class/${encodeURIComponent(code)}/summary`),
};
