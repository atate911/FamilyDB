// The AI model page (settings/model.html, web/models_page.py). The page is a form that works without
// this script: each row is one dropdown of every model, and costs are the saved ones. The script
// swaps that dropdown for a company and a model, and lays the cost of whatever is chosen, before it
// is saved, over the rows, the company cards and the charts. It does no pricing of its own: each
// model's cost for each of the last 30 days arrives with the page, and this only adds and subtracts.
// Nothing is sent until the form's own Save.
(function () {
  "use strict";

  const root = document.getElementById("mp");
  if (!root) return;
  const D = JSON.parse(root.dataset.models);
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
  const DAYS = D.days.length;
  const OTHER = "__other";
  const SAME = "@same";
  const OFF = "@off";
  const J = D.uses;
  const by = Object.fromEntries(J.map((j) => [j.id, j]));
  const C = Object.fromEntries(D.companies.map((c) => [c.id, c]));
  const zeros = () => new Array(DAYS).fill(0);

  const esc = (t) =>
    String(t).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
  const money = (v) => (v === 0 ? "$0.00" : v < 0.005 ? "<$0.01" : "$" + v.toFixed(2));
  const delta = (v) => (v >= 0 ? "+" : "−") + "$" + Math.abs(v).toFixed(2);
  const kfmt = (n) => (n >= 10000 ? Math.round(n / 1000) + "k" : n >= 1000 ? (n / 1000).toFixed(1) + "k" : String(Math.round(n)));
  const sum = (a) => a.reduce((x, y) => x + y, 0);

  const fsel = (id) => $(`select[name="choice_${id}"]`);
  const vsel = (id) => $(`select[data-setting="vendor"][data-job="${id}"]`);
  const msel = (id) => $(`select[data-setting="model"][data-job="${id}"]`);
  const oinp = (id) => $(`input[name="other_${id}"]`);
  const box = (setting, company) => $(`[data-setting="${setting}"][data-vendor="${company}"]`);

  // ---- companies: one can answer when it has a key and is let to
  const avail = (id) => {
    if (!C[id].haskey) return { ok: false, reason: "no key" };
    const allow = box("allow", id);
    return allow && !allow.checked ? { ok: false, reason: "off" } : { ok: true, reason: "" };
  };
  const mayStand = (id) => avail(id).ok && !!box("standin-co", id) && box("standin-co", id).checked;
  // The first other company, in the order they are asked, that may stand in and can do this use.
  const standFor = (j, id) => D.order.map((slug) => C[slug]).find((x) => x && x.id !== id && j.vendors.includes(x.id) && mayStand(x.id));

  // ---- choices. A use's choice is "" (its default) or "same:<use>", "off", "<company>:<model>".
  const optOf = (j, e) => j.opts.find((o) => o.c + ":" + o.n === e);
  const companyOf = (e) => (e && e !== "off" && !e.startsWith("same:") ? e.slice(0, e.indexOf(":")) : null);
  const modelName = (e) => e.slice(e.indexOf(":") + 1);

  // What each dropdown holds now: what was saved, or what was typed before a complaint (or that the
  // browser kept across a reload), which is then an unsaved change.
  const raw = Object.fromEntries(J.map((j) => [j.id, fsel(j.id).value]));
  const savedMap = Object.fromEntries(J.map((j) => [j.id, j.stored]));
  const lastShown = {};

  function dflt(j, map, seen) {
    if (j.default.startsWith("same:") || j.default === "off") return j.default;
    if (j.anchor && !seen.includes(j.id) && Object.keys(j.by_company).length) {
      const a = eff(by[j.anchor], map, [...seen, j.id]);
      const co = companyOf(a);
      if (co && j.by_company[co]) return j.by_company[co];
    }
    return j.default;
  }
  const shown = (j, map, seen) => (map[j.id] !== "" ? map[j.id] : dflt(j, map, seen || []));
  function eff(j, map, seen) {
    seen = seen || [];
    if (seen.includes(j.id)) return "off";
    const c = shown(j, map, seen);
    return c.startsWith("same:") ? eff(by[c.slice(5)], map, [...seen, j.id]) : c;
  }
  const typed = (id) => (oinp(id) ? oinp(id).value.trim() : "");
  const monthOf = (j, e) => {
    if (e === "off") return 0;
    const o = optOf(j, e);
    return o ? o.m : j.unlisted;
  };
  const daysOf = (j, e) => {
    if (e === "off") return zeros();
    const o = optOf(j, e);
    if (o) return o.d && o.d.length ? o.d : zeros();
    const total = sum(j.calls) || 1; // a model nobody priced: the month, spread as the calls fell
    return j.calls.map((c) => (j.unlisted * c) / total);
  };
  const nameOf = (j, e) => {
    if (e === "off") return "off";
    const o = optOf(j, e);
    return o ? o.l : e.endsWith(":" + OTHER) ? typed(j.id) || "another model" : modelName(e);
  };
  const tierOf = (j, e) => {
    if (!e || e === "off") return "everyday";
    const o = optOf(j, e);
    return o ? o.tn : "everyday";
  };

  // ---- the two dropdowns that stand in for the one
  function fillVendors(j) {
    const v = vsel(j.id);
    v.replaceChildren();
    if (j.hassame) v.append(new Option("", SAME));
    j.vendors.forEach((id) => v.append(new Option("", id)));
    if (j.hasoff) v.append(new Option("Off", OFF));
  }
  function fillModels(j, vendor, chosen) {
    const m = msel(j.id);
    m.replaceChildren();
    if (vendor === SAME) {
      m.append(new Option("", "__follow"));
      m.disabled = true;
      return;
    }
    if (vendor === OFF) {
      m.append(new Option("—", "__off"));
      m.disabled = true;
      return;
    }
    m.disabled = false;
    j.opts.filter((o) => o.c === vendor).forEach((o) => m.append(new Option(o.l + (o.note ? " · " + o.note : ""), o.n)));
    m.append(new Option("Other…", OTHER));
    if (chosen) m.value = chosen;
  }
  function showPair(j, c) {
    if (c.startsWith("same:")) {
      vsel(j.id).value = SAME;
      fillModels(j, SAME);
    } else if (c === "off") {
      vsel(j.id).value = OFF;
      fillModels(j, OFF);
    } else {
      const co = companyOf(c);
      vsel(j.id).value = co;
      const listed = optOf(j, c);
      fillModels(j, co, listed ? modelName(c) : OTHER);
      if (!listed && !c.endsWith(":" + OTHER) && oinp(j.id) && !oinp(j.id).value) oinp(j.id).value = modelName(c);
    }
  }
  const readPair = (j) => {
    const v = vsel(j.id).value;
    if (v === SAME) return "same:" + j.anchor;
    if (v === OFF) return "off";
    return v + ":" + msel(j.id).value;
  };
  // Keep the strength when the company changes: the same level of the new company's lineup.
  function onVendor(j) {
    const v = vsel(j.id).value;
    if (v === SAME || v === OFF) {
      fillModels(j, v);
      return;
    }
    const row = j.lineup[v] || {};
    const first = j.opts.find((o) => o.c === v);
    fillModels(j, v, row[tierOf(j, lastShown[j.id])] || row.everyday || (first && first.n));
  }
  // The pair says what is chosen: store it, as "" when it is exactly the default.
  function commit(j) {
    const c = readPair(j);
    raw[j.id] = c === dflt(j, raw, []) ? "" : c;
    mirror(j);
  }
  // The dropdown a browser without the script posts holds the same choice, so Save sends it.
  function mirror(j) {
    const f = fsel(j.id);
    const value = raw[j.id];
    if (!$$("option", f).some((o) => o.value === value)) f.append(new Option(value, value));
    f.value = value;
  }
  function setRaw(j, c) {
    raw[j.id] = c === dflt(j, raw, []) ? "" : c;
    mirror(j);
  }

  // ---- charts
  function bars(series, ghost, w, h, ymax) {
    const step = w / series.length;
    const bw = step * 0.7;
    let s = `<svg class="mp-chart" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none" aria-hidden="true">`;
    (ghost || []).forEach((g, i) => {
      if (g > 0) {
        const gh = Math.max((g / ymax) * h, 0.8);
        s += `<rect class="mp-ghost" x="${(i * step).toFixed(2)}" y="${(h - gh).toFixed(2)}" width="${bw.toFixed(2)}" height="${gh.toFixed(2)}"/>`;
      }
    });
    series.forEach((v, i) => {
      if (v > 0) {
        const bh = Math.max((v / ymax) * h, 0.8);
        s += `<rect class="mp-day${i === series.length - 1 ? " mp-day--today" : ""}" x="${(i * step).toFixed(2)}" y="${(h - bh).toFixed(2)}" width="${bw.toFixed(2)}" height="${bh.toFixed(2)}"/>`;
      }
    });
    return s + "</svg>";
  }
  const hits = (kind, job) => {
    let s = '<div class="mp-hits">';
    for (let i = 0; i < DAYS; i++) s += `<div class="mp-hit" data-kind="${kind}" data-job="${esc(job || "")}" data-i="${i}"></div>`;
    return s + "</div>";
  };
  const plot = (series, ghost, w, h, ymax, kind, job) =>
    `<div class="mp-plot" tabindex="0" role="group" aria-label="${kind === "total" ? "Cost a day, last 30 days" : "Cost a day for this use"}. Use the left and right arrow keys to read each day." data-cur="${DAYS - 1}">${bars(series, ghost, w, h, ymax)}${hits(kind, job)}</div>`;

  // ---- one tooltip, built from the numbers the charts use
  const tip = document.createElement("div");
  tip.id = "mp-tip";
  tip.setAttribute("role", "tooltip");
  document.body.appendChild(tip);
  function tipHtml(kind, jid, i) {
    const S = state();
    const head = `<b>${esc(D.days[i])}${i === DAYS - 1 ? ' <span class="muted">· today, so far</span>' : ""}</b>`;
    if (kind === "job") {
      const j = by[jid];
      const c = j.calls[i];
      if (!c) return head + '<span class="muted">No calls</span>';
      const now = S.sav[jid][i];
      const cur = S.cur[jid][i];
      const rows = [["Calls", c]];
      if (j.hearing) rows.push(["Audio", ((c * 20) / 60).toFixed(1) + " min"]);
      else {
        rows.push(["Tokens in", `${kfmt(j.tin[i])}${j.tin[i] ? ` (${Math.round((j.tcached[i] / j.tin[i]) * 100)}% cached)` : ""}`], ["Tokens out", kfmt(j.tout[i])]);
        if (j.tsearch[i]) rows.push(["Searches", j.tsearch[i]]);
      }
      rows.push(["Cost", money(now)]);
      if (Math.abs(cur - now) > 1e-9) rows.push(["With the change", `${money(cur)} (${delta(cur - now)})`]);
      rows.push(["A call", now / c >= 0.005 ? money(now / c) : ((now / c) * 100).toFixed(2) + "¢"]);
      return head + "<dl>" + rows.map((r) => `<dt>${r[0]}</dt><dd class="fig">${esc(r[1])}</dd>`).join("") + "</dl>";
    }
    const rows = J.filter((j) => j.calls[i]).sort((a, b) => S.sav[b.id][i] - S.sav[a.id][i]);
    if (!rows.length) return head + '<span class="muted">No calls</span>';
    const changed = S.any;
    let t = `<table><thead><tr><td></td><td>calls</td><td>cost</td>${changed ? "<td>with changes</td>" : ""}</tr></thead><tbody>`;
    rows.forEach((j) => {
      const d = S.cur[j.id][i] !== S.sav[j.id][i];
      t += `<tr><th scope="row">${esc(j.name)}</th><td class="fig">${j.calls[i]}</td><td class="fig">${money(S.sav[j.id][i])}</td>${changed ? `<td class="fig">${d ? money(S.cur[j.id][i]) : "·"}</td>` : ""}</tr>`;
    });
    const total = (f) => sum(rows.map(f));
    return head + t + `</tbody><tfoot><tr><th scope="row">Day</th><td class="fig">${total((j) => j.calls[i])}</td><td class="fig">${money(total((j) => S.sav[j.id][i]))}</td>${changed ? `<td class="fig">${money(total((j) => S.cur[j.id][i]))}</td>` : ""}</tr></tfoot></table>`;
  }
  function showTip(el) {
    tip.innerHTML = tipHtml(el.dataset.kind, el.dataset.job, +el.dataset.i);
    tip.style.display = "block";
    const r = el.getBoundingClientRect();
    const t = tip.getBoundingClientRect();
    let x = r.left + r.width / 2 - t.width / 2;
    x = Math.max(8, Math.min(x, innerWidth - t.width - 8));
    let y = r.top - t.height - 8;
    if (y < 8) y = r.bottom + 8;
    tip.style.left = x + "px";
    tip.style.top = y + "px";
  }
  const hitAt = (p, i) => p.querySelectorAll(".mp-hit")[i];
  document.addEventListener("mouseover", (e) => {
    const h = e.target.closest && e.target.closest(".mp-hit");
    if (h) showTip(h);
  });
  document.addEventListener("mouseout", (e) => {
    if (e.target.closest && e.target.closest(".mp-hit")) tip.style.display = "none";
  });
  document.addEventListener("keydown", (e) => {
    const p = e.target.classList && e.target.classList.contains("mp-plot") ? e.target : null;
    if (!p || !["ArrowLeft", "ArrowRight"].includes(e.key)) return;
    e.preventDefault();
    const i = Math.max(0, Math.min(DAYS - 1, +p.dataset.cur + (e.key === "ArrowRight" ? 1 : -1)));
    p.dataset.cur = i;
    showTip(hitAt(p, i));
  });
  document.addEventListener("focusin", (e) => {
    if (e.target.classList && e.target.classList.contains("mp-plot")) showTip(hitAt(e.target, +e.target.dataset.cur));
  });
  document.addEventListener("focusout", () => {
    tip.style.display = "none";
  });

  // ---- what is saved, what the form says now
  const genericControls = () => $$("[data-setting]").filter((c) => !["choice", "vendor", "model", "another"].includes(c.dataset.setting));
  const dirtyOther = (c) => (c.type === "checkbox" ? c.checked !== (c.dataset.saved === "1") : c.value !== c.dataset.saved);

  function state() {
    const cur = {};
    const sav = {};
    const curM = {};
    const savM = {};
    J.forEach((j) => {
      const es = eff(j, savedMap);
      const ec = eff(j, raw);
      savM[j.id] = monthOf(j, es);
      curM[j.id] = monthOf(j, ec);
      sav[j.id] = daysOf(j, es);
      cur[j.id] = daysOf(j, ec);
    });
    const tot = (m, i) => sum(J.map((j) => m[j.id][i]));
    const explicit = J.filter((j) => raw[j.id] !== savedMap[j.id] || (raw[j.id].endsWith(":" + OTHER) && typed(j.id)));
    const followers = J.filter((j) => raw[j.id] === savedMap[j.id] && eff(j, raw) !== eff(j, savedMap));
    return {
      cur, sav, curM, savM,
      totS: sum(Object.values(savM)),
      totC: sum(Object.values(curM)),
      day: (i) => tot(sav, i),
      dayC: (i) => tot(cur, i),
      explicit, followers,
      others: genericControls().filter(dirtyOther),
      any: J.some((j) => eff(j, raw) !== eff(j, savedMap)),
    };
  }

  function notes(j, S) {
    const e = eff(j, raw);
    const nb = $(`[data-note="${j.id}"]`);
    const part = (n) => $(`[data-n="${n}"]`, nb);
    const set = (n, text) => {
      const el = part(n);
      el.hidden = !text;
      el.textContent = text || "";
    };
    set("off", e === "off" && eff(j, savedMap) !== "off" ? j.offnote : "");
    const v = companyOf(e);
    let warn = "";
    if (v && !avail(v).ok) {
      const stand = standFor(j, v);
      warn = `${C[v].name} ${avail(v).reason === "no key" ? "has no key" : "is turned off"}, so ${stand ? stand.name + " answers instead until that changes" : "nothing can answer this until that changes"}.`;
    }
    set("warn", warn);
    if (warn && v && !avail(v).ok && avail(v).reason === "no key") {
      const a = document.createElement("a");
      a.href = C[v].added ? `#company-${v}` : `#k-${v}`;
      a.textContent = " Add a key";
      part("warn").append(a);
    }
    const chatCo = companyOf(eff(by.chat, raw));
    set("priv", j.family && v && j.id !== "chat" && chatCo && v !== chatCo ? `Sends the family’s words and what she remembers to ${C[v].name} as well as ${C[chatCo].name}.` : "");
    const other = raw[j.id].endsWith(":" + OTHER);
    part("other").hidden = !other;
    nb.hidden = $$("[data-n]", nb).every((x) => x.hidden);
    [vsel(j.id), msel(j.id)].forEach((s) => s.classList.toggle("is-unavail", !!(v && !avail(v).ok)));
  }

  let flash = "";
  function render() {
    // A use left at its default follows the others it follows: show where it stands now.
    J.forEach((j) => {
      if (raw[j.id] === "") showPair(j, dflt(j, raw, []));
    });
    const S = state();
    J.forEach((j) => {
      const c = shown(j, raw);
      lastShown[j.id] = c;
      const ms = msel(j.id);
      if (c.startsWith("same:")) {
        const target = by[c.slice(5)];
        ms.options[0].textContent = nameOf(target, eff(target, raw));
      }
      if (!ms.disabled) {
        const d = dflt(j, raw, []);
        $$("option", ms).forEach((op) => {
          const o = optOf(j, vsel(j.id).value + ":" + op.value);
          if (o) op.textContent = o.l + (o.note ? " · " + o.note : "") + (o.c + ":" + o.n === d && ms.value !== o.n ? " · default" : "");
        });
      }
      const ud = $(`[data-usedefault="${j.id}"]`);
      if (ud) ud.hidden = raw[j.id] === "";
      const cell = $(`[data-cost="${j.id}"]`);
      const changed = eff(j, savedMap) !== eff(j, raw);
      $("#row-" + j.id).classList.toggle("is-changed", changed);
      cell.innerHTML = `<b class="fig">${eff(j, raw) === "off" ? "off" : money(S.curM[j.id])}</b>` + (changed ? `<span class="mp-delta fig">${delta(S.curM[j.id] - S.savM[j.id])}</span>` : "");
      const goes = $(`[data-goes="${j.id}"]`);
      if (goes) {
        const co = companyOf(eff(j, raw));
        goes.textContent = co ? C[co].name : "nobody";
      }
      const st = $(`[data-standin="${j.id}"]`);
      if (st) {
        const co = companyOf(eff(j, raw));
        const stand = co && standFor(j, co);
        st.textContent = !co ? "Not used." : stand ? `${stand.name} stands in, at the same strength.` : "No other company may stand in, so a message waits and is tried again.";
      }
      notes(j, S);
    });
    // each company: how many uses it answers, and what that costs a month
    D.companies.forEach((c) => {
      const mine = J.filter((x) => companyOf(eff(x, raw)) === c.id);
      const cost = sum(mine.map((x) => S.curM[x.id]));
      const st = avail(c.id);
      const li = $(`.mp-co[data-vendor="${c.id}"]`);
      const el = $(`[data-use="${c.id}"]`);
      const limBox = box("limit", c.id);
      const lim = limBox ? parseFloat(limBox.value) || 0 : 0;
      li.classList.toggle("mp-co--none", !st.ok);
      $(".mp-co__dot", li).classList.toggle("mp-co__dot--ok", st.ok);
      const over = st.ok && lim > 0 && c.spent + cost > lim;
      el.classList.toggle("mp-co__over", over);
      el.textContent = !st.ok
        ? st.reason + (mine.length ? ` · chosen for ${mine.length}` : "")
        : over
          ? `over its ${money(lim)} limit: ${money(c.spent)} spent, ${money(cost)} a month`
          : mine.length
            ? `${mine.length} of ${J.length} · ${money(cost)}/mo`
            : mayStand(c.id)
              ? "stands in"
              : "not used";
    });
    // the company in each dropdown says when it cannot answer
    J.forEach((x) =>
      $$("option", vsel(x.id)).forEach((op) => {
        if (C[op.value]) {
          const st = avail(op.value);
          op.textContent = C[op.value].name + (st.ok ? "" : " · " + st.reason);
          op.classList.toggle("mp-unavail", !st.ok);
        } else if (op.value === SAME) op.textContent = "Same as " + by[x.anchor].short;
      })
    );
    header(S);
    J.forEach((j) => panel(j, S));
    bar(S);
    presetLabels();
  }

  function header(S) {
    const days = Array.from({ length: DAYS }, (_, i) => i);
    const ymax = Math.max(...days.map((i) => Math.max(S.day(i), S.dayC(i))), 0.01);
    const real = J.some((j) => !j.typical);
    const ghost = S.any ? days.map(S.dayC) : null;
    $("#head-chart").innerHTML = real
      ? `<div class="mp-chart__y fig" aria-hidden="true">${money(ymax)}</div>${S.any ? '<p class="mp-chart__key"><span><i class="mp-sw"></i>each day</span><span><i class="mp-sw mp-sw--ghost"></i>with the changes</span></p>' : ""}` + plot(days.map(S.day), ghost, 600, 56, ymax, "total", "") + `<div class="mp-chart__x"><span>${esc(D.days[0])}</span><span>today, so far</span></div>`
      : "";
    $("#t-lede").innerHTML = `<span class="mp-k">${real ? "A month at today’s choices" : "A typical month at today’s choices"}</span><span class="mp-figs"><b class="fig mp-big">${money(S.totS)}</b>${S.any ? ` <span class="mp-to" aria-hidden="true">→</span><span class="sr"> becomes </span><b class="fig mp-big">${money(S.totC)}</b> <span class="small muted">with your changes</span>` : ""}</span>`;
    if (!real) return;
    const top = J.slice().sort((x, y) => S.savM[y.id] - S.savM[x.id])[0];
    const share = S.totS ? S.savM[top.id] / S.totS : 0;
    const lead = share >= 0.4 ? `${esc(top.name)} was ${share >= 0.7 ? "most" : "about half"} of it. ` : "";
    const dS = days.map(S.day);
    const dC = days.map(S.dayC);
    const peak = Math.max(...(S.any ? dC : dS));
    const limit = D.limit ? ` ${Math.round((peak / D.limit) * 100)}% of the <span class="fig">${money(D.limit)}</span> daily limit.` : "";
    $("#t-facts").innerHTML = `${lead}Busiest day <span class="fig">${money(Math.max(...dS))}</span>${S.any ? ` → <span class="fig">${money(Math.max(...dC))}</span>` : ""}.${limit}`;
  }

  function panel(j, S) {
    const cur = S.cur[j.id];
    const sav = S.sav[j.id];
    const changed = eff(j, savedMap) !== eff(j, raw);
    const chart = $(`[data-chart="${j.id}"]`);
    if (sum(j.calls) === 0) chart.innerHTML = '<p class="small muted">No calls in the last 30 days.</p>';
    else {
      const ym = Math.max(...cur, ...sav, 0.0001);
      chart.innerHTML = `<div class="mp-chart__y fig" aria-hidden="true">${money(ym)}</div>` + plot(sav, changed ? cur : null, 300, 68, ym, "job", j.id) + `<div class="mp-chart__x"><span>${esc(D.days[0])}</span><span>today</span></div>`;
    }
    const es = eff(j, savedMap);
    const en = eff(j, raw);
    $$(`[data-compare="${j.id}"] tr[data-model]`).forEach((tr) => {
      const m = tr.dataset.model;
      const o = optOf(j, m);
      tr.classList.toggle("is-now", m === es && !changed);
      tr.classList.toggle("is-new", changed && m === en);
      tr.classList.toggle("is-unavail", !avail(o.c).ok);
      $("[data-vs]", tr).textContent = m === es ? "now" : delta(o.m - monthOf(j, es));
    });
  }

  function bar(S) {
    const parts = S.explicit.map((j) => `${j.name} → ${nameOf(j, eff(j, raw))}`);
    const labels = { effort: "thinking", cap: "monthly cap", extra: "a setting", lineup: "everyday, better and best", allow: "let it answer", "standin-co": "may stand in", limit: "monthly limit", watch: "daily check" };
    S.others.forEach((c) => {
      const who = c.dataset.job ? by[c.dataset.job].name + " " : c.dataset.vendor ? C[c.dataset.vendor].name + " " : "";
      parts.push(who + (labels[c.dataset.setting] || "changed"));
    });
    const n = parts.length;
    const more = parts.length > 2 ? ` · +${parts.length - 2} more` : "";
    const f = S.followers.length === 1 ? ` · ${S.followers[0].name} follows` : S.followers.length ? ` · ${S.followers.length} more follow` : "";
    const msg = $("#save-msg");
    if (n) msg.innerHTML = `<b>Unsaved:</b> ${parts.slice(0, 2).map(esc).join(" · ")}${esc(more)}<span class="muted">${esc(f)}</span>`;
    else msg.textContent = flash || "Nothing changes until you save.";
    $("#save").disabled = !n;
    $("#revert").disabled = !n;
  }

  // ---- presets and "use for everything" only fill the form; nothing saves until Save
  const PRESET_NAMES = { thrifty: "Thrifty", balanced: "Balanced, the defaults", quality: "Quality first" };
  function presetMap(name) {
    const spec = D.presets[name] || {};
    const map = {};
    J.forEach((j) => {
      const want = spec[j.id];
      if (want === undefined) map[j.id] = "";
      else if (want === "off") map[j.id] = j.hasoff ? "off" : "";
      else {
        const co = companyOf(eff(j, raw));
        const model = co && (j.lineup[co] || {})[want];
        map[j.id] = model ? co + ":" + model : "";
      }
    });
    return map;
  }
  function presetLabels() {
    const picker = $("#preset");
    if (!picker) return;
    Array.from(picker.options).forEach((op) => {
      if (!PRESET_NAMES[op.value]) return;
      const map = presetMap(op.value);
      const total = sum(J.map((j) => monthOf(j, eff(j, map))));
      op.textContent = `${PRESET_NAMES[op.value]} · ≈${money(total)} a month`;
    });
  }
  function applyPreset(name) {
    const map = presetMap(name);
    J.forEach((j) => {
      setRaw(j, map[j.id]);
      showPair(j, shown(j, raw));
    });
  }
  function useForAll(v) {
    const kept = [];
    J.forEach((j) => {
      const c = shown(j, raw);
      if (c.startsWith("same:") || c === "off") return;
      if (!j.vendors.includes(v)) {
        kept.push(j.name.toLowerCase());
        return;
      }
      const row = j.lineup[v] || {};
      const model = row[tierOf(j, c)] || row.everyday;
      if (model) {
        setRaw(j, v + ":" + model);
        showPair(j, shown(j, raw));
      }
    });
    $(`[data-usedmsg="${v}"]`).textContent = `Filled the table with ${C[v].name}’s models at the same strength${kept.length ? `; ${kept.join(", ")} stays (${C[v].name} can’t do it)` : ""}. Nothing saves until Save.`;
  }

  // ---- behaviour
  root.addEventListener("change", (e) => {
    const c = e.target;
    if (c.id === "preset") {
      if (c.value) applyPreset(c.value);
      c.value = "";
      flash = "";
      render();
      return;
    }
    if (c.classList && c.classList.contains("mp-open")) {
      c.setAttribute("aria-expanded", c.checked);
      return;
    }
    const kind = c.dataset && c.dataset.setting;
    if (kind === "vendor") {
      onVendor(by[c.dataset.job]);
      commit(by[c.dataset.job]);
    } else if (kind === "model") {
      commit(by[c.dataset.job]);
      if (c.value === OTHER && oinp(c.dataset.job)) oinp(c.dataset.job).focus();
    }
    flash = "";
    render();
  });
  root.addEventListener("input", (e) => {
    // A dropdown or a tick reports with "change" as well, once its choice is made: only typing here.
    if (e.target.matches && e.target.matches('input[data-setting]:not([type="checkbox"])')) {
      flash = "";
      render();
    }
  });
  document.addEventListener("click", (e) => {
    const t = e.target.closest ? e.target : e.target.parentElement;
    const all = t.closest("[data-useall]");
    if (all) {
      useForAll(all.dataset.useall);
      flash = "";
      render();
      return;
    }
    const d = t.closest("[data-usedefault]");
    if (d) {
      const j = by[d.dataset.usedefault];
      raw[j.id] = "";
      mirror(j);
      flash = "";
      render();
      return;
    }
    // A link to something inside a closed fold opens the fold first.
    const a = t.closest('a[href^="#"]');
    if (!a || a.getAttribute("href").length < 2) return;
    const target = document.getElementById(a.getAttribute("href").slice(1));
    const fold = target && target.closest("details");
    if (fold) {
      fold.open = true;
      setTimeout(() => target.focus && target.focus(), 0);
    }
  });
  $("#revert").addEventListener("click", () => {
    J.forEach((j) => {
      raw[j.id] = savedMap[j.id];
      mirror(j);
      if (oinp(j.id)) oinp(j.id).value = "";
    });
    genericControls().forEach((c) => {
      if (c.type === "checkbox") c.checked = c.dataset.saved === "1";
      else c.value = c.dataset.saved;
    });
    flash = "";
    render();
  });

  // ---- start: the saved state
  root.classList.add("mp-js");
  $$(".mp-row__vendor, .mp-row__model, .mp-preset, [data-useall]").forEach((el) => {
    el.hidden = false;
  });
  $("#revert").hidden = false;
  J.forEach((j) => {
    fillVendors(j);
    mirror(j);
    showPair(j, shown(j, raw));
    lastShown[j.id] = shown(j, raw);
  });
  $$(".mp-open").forEach((c) => c.setAttribute("aria-expanded", c.checked));
  render();
})();
