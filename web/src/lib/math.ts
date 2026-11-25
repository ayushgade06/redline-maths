// Redline ASCII grammar -> LaTeX for KaTeX display. Display only: the engine's
// safe parser is the authority on what a line means.

type Tok = { t: "num" | "var" | "op" | "lp" | "rp" | "word"; v: string };

function tokenize(src: string): Tok[] {
  const s = src
    .replace(/[−–—]/g, "-")
    .replace(/[×·]/g, "*")
    .replace(/÷/g, "/")
    .replace(/\*\*/g, "^")
    .replace(/²/g, "^2")
    .replace(/³/g, "^3")
    .replace(/√/g, "sqrt")
    .replace(/\+-|±/g, "±");
  const out: Tok[] = [];
  let i = 0;
  while (i < s.length) {
    const c = s[i];
    if (/\s/.test(c)) { i++; continue; }
    const num = /^\d+(\.\d+)?/.exec(s.slice(i));
    if (num) { out.push({ t: "num", v: num[0] }); i += num[0].length; continue; }
    const word = /^(sqrt|or)\b/i.exec(s.slice(i));
    if (word) { out.push({ t: "word", v: word[0].toLowerCase() }); i += word[0].length; continue; }
    if (/[a-zA-Z]/.test(c)) { out.push({ t: "var", v: c }); i++; continue; }
    if (c === "(") out.push({ t: "lp", v: c });
    else if (c === ")") out.push({ t: "rp", v: c });
    else out.push({ t: "op", v: c });
    i++;
  }
  return out;
}

// Parse into nested groups: each group is a list of tokens or sub-groups.
type Node = Tok | { group: Node[] };

function group(toks: Tok[]): Node[] {
  const stack: Node[][] = [[]];
  for (const tk of toks) {
    if (tk.t === "lp") stack.push([]);
    else if (tk.t === "rp" && stack.length > 1) {
      const g = stack.pop()!;
      stack[stack.length - 1].push({ group: g });
    } else stack[stack.length - 1].push(tk);
  }
  while (stack.length > 1) {
    const g = stack.pop()!;
    stack[stack.length - 1].push({ group: g });
  }
  return stack[0];
}

const isGroup = (n: Node): n is { group: Node[] } => "group" in n;

function atom(n: Node, paren = true): string {
  if (isGroup(n)) return paren ? `(${render(n.group)})` : render(n.group);
  return n.v;
}

function render(nodes: Node[]): string {
  const parts: string[] = [];
  for (let i = 0; i < nodes.length; i++) {
    const n = nodes[i];
    if (!isGroup(n) && n.t === "word" && n.v === "sqrt") {
      const arg = nodes[i + 1];
      parts.push(`\\sqrt{${arg ? atom(arg, false) : ""}}`);
      i++;
      continue;
    }
    if (!isGroup(n) && n.t === "word" && n.v === "or") { parts.push("\\quad\\text{or}\\quad "); continue; }
    if (!isGroup(n) && n.t === "op") {
      const next = nodes[i + 1];
      if (n.v === "^" && next) { parts.push(`^{${atom(next, false)}}`); i++; continue; }
      if (n.v === "/" && next && parts.length) {
        const num = parts.pop()!;
        const den = atom(next, false);
        parts.push(`\\frac{${num.replace(/^\((.*)\)$/, "$1")}}{${den}}`);
        i++;
        continue;
      }
      if (n.v === "*") {
        const prev = nodes[i - 1];
        const bothNum = prev && next && !isGroup(prev) && !isGroup(next) && prev.t === "num" && next.t === "num";
        parts.push(bothNum ? "\\cdot " : "");
        continue;
      }
      parts.push(n.v === "±" ? "\\pm " : n.v === "," ? ",\\ " : n.v);
      continue;
    }
    parts.push(atom(n));
  }
  return parts.join("");
}

export function asciiToLatex(src: string): string {
  try {
    return render(group(tokenize(src)));
  } catch {
    return src.replace(/[\\{}]/g, "");
  }
}

// Speakable label for screen readers.
export function asciiToSpeech(src: string): string {
  return src
    .replace(/sqrt/g, " square root of ")
    .replace(/\^2/g, " squared")
    .replace(/\^(\d+)/g, " to the power $1")
    .replace(/-/g, " minus ")
    .replace(/\+/g, " plus ")
    .replace(/=/g, " equals ")
    .replace(/\//g, " over ")
    .replace(/\s+/g, " ")
    .trim();
}
