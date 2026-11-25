export const MAX_EDGE = 1600;
export const MAX_BYTES = 1_500_000;

export function fitWithin(w: number, h: number, max = MAX_EDGE): { w: number; h: number } {
  const scale = Math.min(1, max / Math.max(w, h));
  return { w: Math.round(w * scale), h: Math.round(h * scale) };
}

/** Box [y0, x0, y1, x1] in 0–1 fractions -> absolute-position percentages, padded a little. */
export function boxStyle(box: number[], pad = 0.008): { top: string; left: string; width: string; height: string } {
  const [y0, x0, y1, x1] = box;
  const clamp = (v: number) => Math.min(1, Math.max(0, v));
  const t = clamp(y0 - pad), l = clamp(x0 - pad), b = clamp(y1 + pad), r = clamp(x1 + pad);
  const pct = (v: number) => `${(v * 100).toFixed(2)}%`;
  return { top: pct(t), left: pct(l), width: pct(r - l), height: pct(b - t) };
}

export type PreparedImage = { base64: string; mime: "image/jpeg"; url: string; bytes: number };

/** Downscale a photo in the browser: ≤1600 px long edge, JPEG, ≤1.5 MB. */
export async function prepareImage(file: Blob): Promise<PreparedImage> {
  const bmp = await createImageBitmap(file, { imageOrientation: "from-image" });
  const { w, h } = fitWithin(bmp.width, bmp.height);
  const canvas = document.createElement("canvas");
  canvas.width = w;
  canvas.height = h;
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("canvas unavailable");
  ctx.drawImage(bmp, 0, 0, w, h);
  bmp.close();
  let blob: Blob | null = null;
  for (const q of [0.85, 0.75, 0.65, 0.55]) {
    blob = await new Promise<Blob | null>((res) => canvas.toBlob(res, "image/jpeg", q));
    if (blob && blob.size <= MAX_BYTES) break;
  }
  if (!blob) throw new Error("encode failed");
  const base64 = await new Promise<string>((res, rej) => {
    const r = new FileReader();
    r.onload = () => res(String(r.result).split(",")[1] ?? "");
    r.onerror = () => rej(r.error);
    r.readAsDataURL(blob!);
  });
  return { base64, mime: "image/jpeg", url: URL.createObjectURL(blob), bytes: blob.size };
}
