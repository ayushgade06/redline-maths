import { beforeEach, describe, expect, it } from "vitest";
import { api, ApiError, toApiError } from "./api";
import { nextHintLevel } from "./hints";
import { boxStyle, fitWithin } from "./image";
import { asciiToLatex } from "./math";
import { acceptGate, hasAcceptedGate, resetGateMemory } from "./storage";

describe("asciiToLatex", () => {
  it.each([
    ["2(x-3)=10", "2(x-3)=10"],
    ["x^2 = 9", "x^{2}=9"],
    ["x/3 + 1/2 = 5/6", "\\frac{x}{3}+\\frac{1}{2}=\\frac{5}{6}"],
    ["sqrt(x+1) = 3", "\\sqrt{x+1}=3"],
    ["(x+1)/4 = 2", "\\frac{x+1}{4}=2"],
    ["x = 3 or x = -3", "x=3\\quad\\text{or}\\quad x=-3"],
    ["x = ±4", "x=\\pm 4"],
    ["2*3", "2\\cdot 3"],
  ])("%s", (src, out) => expect(asciiToLatex(src)).toBe(out));

  it("never throws on junk", () => {
    expect(() => asciiToLatex(")))((( ^^ //")).not.toThrow();
  });
});

describe("image utils", () => {
  it("fits a 12 MP photo inside 1600 px", () => {
    expect(fitWithin(4000, 3000)).toEqual({ w: 1600, h: 1200 });
    expect(fitWithin(3000, 4000)).toEqual({ w: 1200, h: 1600 });
    expect(fitWithin(800, 600)).toEqual({ w: 800, h: 600 });
  });

  it("scales fractional boxes to padded percentages, clamped", () => {
    expect(boxStyle([0.2, 0.1, 0.3, 0.5], 0)).toEqual({ top: "20.00%", left: "10.00%", width: "40.00%", height: "10.00%" });
    const s = boxStyle([0, 0, 1, 1]);
    expect(s.top).toBe("0.00%");
    expect(s.width).toBe("100.00%");
  });
});

describe("gate storage", () => {
  beforeEach(() => resetGateMemory());

  it("persists acceptance when storage works", () => {
    const m = new Map<string, string>();
    const store = { getItem: (k: string) => m.get(k) ?? null, setItem: (k: string, v: string) => void m.set(k, v) };
    expect(hasAcceptedGate(store)).toBe(false);
    acceptGate(store);
    resetGateMemory();
    expect(hasAcceptedGate(store)).toBe(true);
  });

  it("falls back to memory when storage throws", () => {
    const broken = {
      getItem: () => { throw new Error("blocked"); },
      setItem: () => { throw new Error("blocked"); },
    };
    expect(hasAcceptedGate(broken)).toBe(false);
    acceptGate(broken);
    expect(hasAcceptedGate(broken)).toBe(true);
  });
});

describe("api error mapping", () => {
  it("uses the engine's error shape", async () => {
    const res = new Response(JSON.stringify({ error: { code: "unsupported_scope", message: "found x, y" } }), { status: 422 });
    const e = await toApiError(res);
    expect(e).toBeInstanceOf(ApiError);
    expect([e.status, e.code, e.message]).toEqual([422, "unsupported_scope", "found x, y"]);
  });

  it("maps non-JSON 5xx to a friendly server error", async () => {
    const e = await toApiError(new Response("<html>bad gateway</html>", { status: 502 }));
    expect(e.code).toBe("server");
    expect(e.message).toMatch(/our side/);
  });

  it("maps network failures", async () => {
    const failing = (() => Promise.reject(new TypeError("Failed to fetch"))) as unknown as typeof fetch;
    await expect(api.call("/health", undefined, failing)).rejects.toMatchObject({ code: "network", status: 0 });
  });

  it("returns parsed JSON on success", async () => {
    const ok = (() => Promise.resolve(new Response(JSON.stringify({ status: "ok" })))) as unknown as typeof fetch;
    await expect(api.call("/health", undefined, ok)).resolves.toEqual({ status: "ok" });
  });
});

describe("hint ladder", () => {
  it("unlocks levels in order and stops at 3", () => {
    expect(nextHintLevel({})).toBe(1);
    expect(nextHintLevel({ 1: true })).toBe(2);
    expect(nextHintLevel({ 1: true, 2: true })).toBe(3);
    expect(nextHintLevel({ 1: true, 2: true, 3: true })).toBe(null);
    expect(nextHintLevel({ 2: true })).toBe(1);
  });
});
