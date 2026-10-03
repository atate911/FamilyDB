# Fold a stacked stylesheet: drop every declaration a later rule with the very same selector (in the
# same @media/@supports context) overrides, drop the rules that leave empty, keep only the last
# @keyframes of a name, and write it compactly. Order is never changed, so the cascade is the same.
import re, sys

def strip_comments(s):
    return re.sub(r"/\*.*?\*/", "", s, flags=re.S)

def parse(s, i=0, depth=0):
    """Return (items, i). item = ('rule', sel, [decl...]) | ('at', prelude, items) | ('raw', text)"""
    items = []
    n = len(s)
    buf = ""
    while i < n:
        c = s[i]
        if c in "\"'":
            j = i + 1
            while j < n and s[j] != c:
                if s[j] == "\\": j += 1
                j += 1
            buf += s[i:j + 1]; i = j + 1; continue
        if c == "{":
            pre = buf.strip(); buf = ""
            if pre.startswith("@") and re.match(r"@(media|supports|layer|container|scope|starting-style)\b", pre):
                sub, i = parse(s, i + 1, depth + 1)
                items.append(("at", pre, sub))
            else:
                # read a declaration block (may contain nested {} in rare cases: treat raw)
                j = i + 1; lvl = 1; start = j
                while j < n and lvl:
                    if s[j] in "\"'":
                        q = s[j]; j += 1
                        while j < n and s[j] != q:
                            if s[j] == "\\": j += 1
                            j += 1
                    elif s[j] == "{": lvl += 1
                    elif s[j] == "}": lvl -= 1
                    j += 1
                body = s[start:j - 1]
                if pre.startswith("@") or "{" in body:
                    items.append(("raw", pre, body))
                else:
                    items.append(("rule", pre, split_decls(body)))
                i = j
            continue
        if c == "}":
            return items, i + 1
        if c == ";" and buf.strip().startswith("@"):
            items.append(("stmt", buf.strip())); buf = ""; i += 1; continue
        buf += c; i += 1
    return items, i

def split_decls(body):
    out = []; cur = ""; par = 0; q = None
    for ch in body:
        if q:
            cur += ch
            if ch == q: q = None
            continue
        if ch in "\"'": q = ch; cur += ch; continue
        if ch == "(": par += 1
        if ch == ")": par -= 1
        if ch == ";" and par == 0:
            if cur.strip(): out.append(cur.strip())
            cur = ""; continue
        cur += ch
    if cur.strip(): out.append(cur.strip())
    res = []
    for d in out:
        if ":" not in d: continue
        p, v = d.split(":", 1)
        p = p.strip(); v = re.sub(r"\s+", " ", v.strip())
        imp = bool(re.search(r"!\s*important$", v))
        res.append([p, v, imp])
    return res

def norm_sel(sel):
    sel = re.sub(r"\s+", " ", sel.strip())
    sel = re.sub(r"\s*,\s*", ",", sel)
    sel = re.sub(r"\s*>\s*", ">", sel)
    return sel

def walk(items, ctx, rules):
    for it in items:
        if it[0] == "rule":
            rules.append((ctx, norm_sel(it[1]), it))
        elif it[0] == "at":
            walk(it[2], ctx + "|" + re.sub(r"\s+", " ", it[1]), rules)

def fold(items):
    rules = []
    walk(items, "", rules)
    seen = {}  # (ctx, sel) -> {prop: important}
    for ctx, sel, it in reversed(rules):
        key = (ctx, sel)
        later = seen.setdefault(key, {})
        kept = []
        for d in it[2]:
            p, v, imp = d
            if p in later and (later[p] or not imp):
                continue
            kept.append(d)
        # within the rule keep fallbacks; record props
        for p, v, imp in kept:
            later[p] = later.get(p, False) or imp
        it[2][:] = kept
    # keyframes: last of a name wins
    kf = {}
    def collect(items):
        for idx, it in enumerate(items):
            if it[0] == "raw" and it[1].startswith("@keyframes"):
                kf[it[1].split()[1]] = it
            elif it[0] == "at": collect(it[2])
    collect(items)
    def prune(items):
        out = []
        for it in items:
            if it[0] == "rule" and not it[2]: continue
            if it[0] == "raw" and it[1].startswith("@keyframes") and kf.get(it[1].split()[1]) is not it: continue
            if it[0] == "at":
                sub = prune(it[2])
                if not sub: continue
                it = ("at", it[1], sub)
            out.append(it)
        return out
    return prune(items)

def emit(items, ind=""):
    out = []
    for it in items:
        if it[0] == "rule":
            out.append(norm_sel(it[1]) + "{" + ";".join(p + ":" + v for p, v, _ in it[2]) + "}")
        elif it[0] == "at":
            out.append(re.sub(r"\s+", " ", it[1]) + "{\n" + emit(it[2]) + "\n}")
        elif it[0] == "raw":
            body = re.sub(r"\s+", " ", it[2]).strip()
            body = re.sub(r"\s*([{};])\s*", r"\1", body)
            out.append(re.sub(r"\s+", " ", it[1]) + "{" + body + "}")
        elif it[0] == "stmt":
            out.append(it[1] + ";")
    return "\n".join(out)

if __name__ == "__main__":
    src = strip_comments(open(sys.argv[1]).read())
    items, _ = parse(src)
    print(emit(fold(items)))

def alive_words(paths):
    import pathlib
    text = ""
    for p in paths:
        p = pathlib.Path(p)
        files = [p] if p.is_file() else [f for f in p.rglob("*") if f.suffix in (".html", ".js", ".py")]
        for f in files:
            text += f.read_text(errors="ignore") + "\n"
    words = set(re.findall(r"[A-Za-z_][A-Za-z0-9_-]*", text))
    prefixes = set(m for m in re.findall(r"([a-z][a-z0-9_]*-?)\{\{", text) if m)
    prefixes |= set(re.findall(r"([a-z][a-z0-9_]*-)'\s*~", text))
    return words, prefixes

def class_alive(c, words, prefixes):
    if c in words: return True
    return any(c.startswith(p) and len(p) >= 1 for p in prefixes)

def prune_dead(items, words, prefixes, log=None):
    out = []
    for it in items:
        if it[0] == "rule":
            parts = split_selectors(it[1])
            keep = [p for p in parts if all(class_alive(c, words, prefixes) for c in re.findall(r"\.([A-Za-z_][A-Za-z0-9_-]*)", strip_pseudo_args(p)))]
            if not keep:
                if log is not None: log.append(it[1])
                continue
            out.append(("rule", ",".join(keep), it[2]))
        elif it[0] == "at":
            sub = prune_dead(it[2], words, prefixes, log)
            if sub: out.append(("at", it[1], sub))
        else:
            out.append(it)
    return out

def strip_pseudo_args(sel):
    # classes inside :not(), :is(), :has(), :where() still matter for :is/:has; inside :not() a dead class means the rule still applies
    return re.sub(r":not\([^()]*(\([^()]*\)[^()]*)*\)", "", sel)

def split_selectors(sel):
    out, cur, depth = [], "", 0
    for ch in sel:
        if ch == "(": depth += 1
        if ch == ")": depth -= 1
        if ch == "," and depth == 0:
            out.append(cur.strip()); cur = ""; continue
        cur += ch
    if cur.strip(): out.append(cur.strip())
    return out
