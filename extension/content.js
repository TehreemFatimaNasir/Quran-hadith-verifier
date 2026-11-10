// Select Arabic / Urdu text on any page -> search it automatically
(() => {
    if (window.__qhvLoaded) return;
    window.__qhvLoaded = true;

    const SCRIPT_RE = /[؀-ۿݐ-ݿﭐ-﷿ﹰ-﻿]/;
    let enabled = false;
    let timer = null;
    let lastText = "";
    let host = null;
    let tab = "ur";

    const load = () => {
        try {
            chrome.storage.local.get({ autoSearch: false }, (v) => { enabled = !!v.autoSearch; if (!enabled) closePanel(); });
        } catch (_) {}
    };
    load();
    try {
        chrome.storage.onChanged.addListener((changes) => {
            if (changes.autoSearch) { enabled = !!changes.autoSearch.newValue; if (!enabled) closePanel(); }
        });
    } catch (_) {}

    function closePanel() {
        if (host) { host.remove(); host = null; }
        lastText = "";
    }

    function selectionInfo() {
        const sel = window.getSelection();
        if (!sel || sel.isCollapsed || !sel.rangeCount) return null;
        const text = sel.toString().replace(/\s+/g, " ").trim();
        if (text.length < 6 || !SCRIPT_RE.test(text)) return null;
        const rect = sel.getRangeAt(0).getBoundingClientRect();
        return { text, rect };
    }

    function onSelect(event) {
        if (!enabled) return;
        if (host && event && event.composedPath && event.composedPath().includes(host)) return;
        clearTimeout(timer);
        timer = setTimeout(() => {
            const info = selectionInfo();
            if (!info) return;
            if (info.text === lastText) return;
            lastText = info.text;
            run(info);
        }, 350);
    }

    document.addEventListener("mouseup", onSelect, true);
    document.addEventListener("keyup", (e) => { if (e.shiftKey || e.key.startsWith("Arrow")) onSelect(e); }, true);
    document.addEventListener("mousedown", (e) => {
        if (host && !e.composedPath().includes(host)) closePanel();
    }, true);
    document.addEventListener("keydown", (e) => { if (e.key === "Escape") closePanel(); }, true);

    // ---------- panel ----------
    const CSS = `
    :host { all: initial; }
    .card { font-family: "Segoe UI", Roboto, Arial, sans-serif; width: 340px; max-width: calc(100vw - 24px);
        background: #fff; color: #1d2e47; border-radius: 16px; border: 1px solid #d3deec; overflow: hidden;
        box-shadow: 0 18px 40px rgba(47,77,115,.28); direction: ltr; text-align: left; max-height: calc(100vh - 24px); overflow-y: auto; }
    .top { display:flex; align-items:center; justify-content:space-between; padding: 10px 14px; color:#fff;
        background: linear-gradient(135deg,#2f4d73,#5d82ad); font-size: 13px; font-weight: 600; }
    .top.hadith { background: linear-gradient(135deg,#6d3f7c,#9a65a8); }
    .top.none { background: linear-gradient(135deg,#6b7a90,#94a3b8); }
    .x { all: unset; cursor: pointer; font-size: 18px; line-height: 1; padding: 0 4px; opacity: .85; }
    .body { padding: 14px; }
    .ar { font-family: "Amiri","Scheherazade New","Noto Naskh Arabic","Traditional Arabic",serif; direction: rtl; text-align: center;
        font-size: 21px; line-height: 2.1; max-height: 150px; overflow: auto; background:#f3f6fb; border:1px solid #d3deec; border-radius: 12px; padding: 10px 12px; }
    .ref { margin-top: 12px; padding: 10px 12px; border-radius: 12px; border:1px solid #d3deec; background: linear-gradient(135deg,#eaf0f8,#f3eef8); font-size: 12px; color:#62758f; display:flex; justify-content:space-between; align-items:center; gap:10px; }
    .ref b { color:#1d2e47; font-size: 15px; background: linear-gradient(transparent 55%, #fde68a 55%); padding: 0 3px; }
    .num { font-size: 18px; }
    .verdict { margin-top: 10px; padding: 9px 12px; border-radius: 12px; font-size: 12.5px; line-height: 1.5; }
    .verdict.ok { background:#e6f6ee; color:#17623c; } .verdict.bad { background:#fdeeef; color:#a33344; } .verdict.warn { background:#fbf1f7; color:#7a3f66; }
    .tabs { display:flex; gap:6px; margin-top: 12px; background:#e7eef7; padding:4px; border-radius: 999px; }
    .tabs button { all: unset; flex:1; text-align:center; cursor:pointer; padding: 6px 0; border-radius: 999px; font-size: 12.5px; color:#2f4d73; }
    .tabs button.on { background: linear-gradient(135deg,#2f4d73,#5d82ad); color:#fff; }
    .tr { margin-top: 8px; padding: 10px 12px; border-radius: 12px; background:#f3f6fb; border:1px solid #d3deec; font-size: 13.5px; line-height: 1.6; max-height: 120px; overflow:auto; }
    .tr.ur { direction: rtl; text-align: right; font-family: "Noto Nastaliq Urdu","Jameel Noori Nastaleeq",serif; font-size: 16px; line-height: 2.3; }
    .muted { color:#62758f; font-size: 13px; line-height:1.6; }
    .spin { display:inline-block; width:14px; height:14px; border:2px solid #b48bc2; border-top-color:transparent; border-radius:50%; animation: s 1s linear infinite; vertical-align:-2px; margin-right:8px; }
    @keyframes s { to { transform: rotate(360deg); } }
    `;

    function place(rect) {
        const w = Math.min(340, window.innerWidth - 24);
        let left = rect.left + rect.width / 2 - w / 2;
        left = Math.max(12, Math.min(left, window.innerWidth - w - 12));
        let top = rect.bottom + 10;
        if (top + 260 > window.innerHeight && rect.top > 280) top = Math.max(12, rect.top - 270);
        host.style.cssText = `all:initial; position:fixed; z-index:2147483647; left:${left}px; top:${top}px;`;
    }

    function open(rect) {
        closePanel();
        lastText = lastText || "";
        host = document.createElement("div");
        host.attachShadow({ mode: "open" });
        document.documentElement.appendChild(host);
        place(rect);
        return host.shadowRoot;
    }

    function render(root, kind, title, bodyHtml) {
        root.innerHTML = `<style>${CSS}</style><div class="card"><div class="top ${kind}"><span>${title}</span><button class="x" aria-label="Close">×</button></div><div class="body">${bodyHtml}</div></div>`;
        root.querySelector(".x").addEventListener("click", closePanel);
        requestAnimationFrame(() => {
            if (!host) return;
            const h = host.getBoundingClientRect();
            const card = root.querySelector(".card").getBoundingClientRect();
            const overflow = h.top + card.height - (window.innerHeight - 12);
            if (overflow > 0) host.style.top = Math.max(12, h.top - overflow) + "px";
        });
    }

    const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

    function run({ text, rect }) {
        const root = open(rect);
        render(root, "", "Searching…", `<div class="muted"><span class="spin"></span>Searching the selected text</div>`);
        try {
            chrome.runtime.sendMessage({ type: "search-selection", text }, (res) => {
                if (chrome.runtime.lastError || !res) {
                    return render(root, "none", "Not available", `<div class="muted">Could not reach the extension. Reload the page and try again.</div>`);
                }
                if (!res.ok) {
                    return render(root, "none", "Server not reachable", `<div class="muted">Start the backend first (<b>uvicorn main:app --reload</b>) and try again.</div>`);
                }
                show(root, res.data);
            });
        } catch (_) {
            closePanel();
        }
    }

    function verdictHtml(r) {
        if (!r) return "";
        if (r.verdict === "verified") return `<div class="verdict ok">✓ <b>Verified.</b> The selected text matches <b>${esc(r.label)}</b> (${esc(r.score)}% match).</div>`;
        if (r.verdict === "mismatch") return `<div class="verdict bad">✗ <b>Does not match ${esc(r.label)}</b> (${esc(r.score)}% match). Check the reference or the text.</div>`;
        return `<div class="verdict warn">${esc(r.message || "Reference could not be checked.")}</div>`;
    }

    function show(root, data) {
        const hit = data.quran || data.hadith;
        const refCheck = verdictHtml(data.reference);
        if (!hit) {
            return render(root, "none", "No match found", `<div class="muted">${esc(data.error || "No sufficiently similar Quran verse or Hadith was found for this selection.")}</div>${refCheck}`);
        }
        const isQ = !!data.quran;
        const tr = hit.translations || {};
        tab = tr.ur ? "ur" : "en";
        const refHtml = isQ
            ? `<div><div>REFERENCE</div><b>Surah ${esc(hit.surah)}</b><div>Quran ${esc(hit.surahNumber)}:${esc(hit.ayah)}</div></div><div class="num"><div style="font-size:11px">AYAH</div><b class="num">${esc(hit.ayah)}</b></div>`
            : `<div><div>REFERENCE</div><b>${esc(hit.book)}</b><div>Hadith collection</div></div><div class="num"><div style="font-size:11px">HADITH NO.</div><b class="num">${esc(hit.hadithNumber)}</b></div>`;
        render(root, isQ ? "" : "hadith", isQ ? "Quran Verse" : "Hadith",
            `<div class="ar">${esc(hit.text)}</div>
             <div class="ref">${refHtml}</div>
             ${refCheck}
             <div class="tabs"><button data-t="ur">اردو</button><button data-t="en">English</button></div>
             <div class="tr"></div>`);
        const out = root.querySelector(".tr");
        const set = () => {
            root.querySelectorAll(".tabs button").forEach((b) => b.classList.toggle("on", b.dataset.t === tab));
            out.className = "tr" + (tab === "ur" ? " ur" : "");
            out.textContent = tr[tab] || "Translation not available.";
        };
        root.querySelectorAll(".tabs button").forEach((b) => b.addEventListener("click", () => { tab = b.dataset.t; set(); }));
        set();
    }
})();