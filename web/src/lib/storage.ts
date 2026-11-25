// Browser storage can be missing or throw (private mode, blocked site data); the app
// must work without it, so the gate falls back to in-memory state for this session.

const GATE_KEY = "redline.gate.v1";
let memoryGate = false;

export function hasAcceptedGate(store: Pick<Storage, "getItem"> | undefined = safeLocal()): boolean {
  if (memoryGate) return true;
  try {
    return store?.getItem(GATE_KEY) === "1";
  } catch {
    return false;
  }
}

export function acceptGate(store: Pick<Storage, "setItem"> | undefined = safeLocal()): void {
  memoryGate = true;
  try {
    store?.setItem(GATE_KEY, "1");
  } catch {
    /* in-memory only */
  }
}

export function resetGateMemory() {
  memoryGate = false;
}

function safeLocal(): Storage | undefined {
  try {
    return typeof localStorage === "undefined" ? undefined : localStorage;
  } catch {
    return undefined;
  }
}

export function load(key: string): string | null {
  try {
    return safeLocal()?.getItem(key) ?? null;
  } catch {
    return null;
  }
}

export function save(key: string, value: string): void {
  try {
    safeLocal()?.setItem(key, value);
  } catch {
    /* ignore */
  }
}
