/* ============================================================================
   SITE CONFIG: the only block you need to edit.
   Fill in a value, save, push. Nothing else on the page has to change.
   ============================================================================ */
window.PTG_CONFIG = {
  /* "prelaunch" shows the first-readers email form.
     "available" swaps it for buy buttons built from BUY_LINKS below. */
  STATUS: "prelaunch",

  /* One canonical product URL per format. Leave a format empty to hide its
     button. Use full https:// product URLs, never a.co share links. */
  BUY_LINKS: {
    hardcover: "",
    paperback: "",
    ebook: "",
    audiobook: "",
    direct: ""
  },

  /* The sign-up endpoint: the Google Apps Script web app that writes each
     sign-up to the private sheet "The Path to Greatness · First Readers".
     Paste the Web app URL (it ends in /exec). Setup steps:
     automation/pathtogreatness-signups/README.md in ImaginariumOzone.
     Empty = the form falls back to opening the visitor's own mail app. */
  FORM_ENDPOINT: "",

  /* Google Analytics 4 measurement ID (G-XXXXXXXXXX). Empty = no analytics
     script is loaded at all. */
  GA4_MEASUREMENT_ID: "",

  CONTACT_EMAIL: "eatmediatv@gmail.com"
};
/* ========================== end of config block ============================ */

(function () {
  "use strict";
  var cfg = window.PTG_CONFIG || {};
  var doc = document, root = doc.documentElement;
  var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var SITE = "https://eatmediatv.com/pathtogreatness/";

  /* A1: the inline head script hides reveal targets and closed gates only while this file is running */
  root.classList.add("js");
  /* each part of the page runs on its own, so one failure cannot take the others down */
  function mod(name, fn) { try { fn(); } catch (e) { if (window.console && console.error) console.error("ptg " + name, e); } }
  function plain(o) { return !!o && typeof o === "object" && !Array.isArray(o); }
  function mq(q) { return window.matchMedia ? window.matchMedia(q) : { matches: false }; }

  function $(sel, ctx) { return (ctx || doc).querySelector(sel); }
  function $$(sel, ctx) { return Array.prototype.slice.call((ctx || doc).querySelectorAll(sel)); }
  function isUrl(v) { return typeof v === "string" && /^https:\/\/[^\s"'<>]+$/.test(v); }
  function pad(n) { return (n < 10 ? "0" : "") + n; }
  function todayISO() { var d = new Date(); return d.getFullYear() + "-" + pad(d.getMonth() + 1) + "-" + pad(d.getDate()); }
  function niceDate(iso) {
    var m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso || "");
    if (!m) return "";
    var d = new Date(+m[1], +m[2] - 1, +m[3]);
    try { return d.toLocaleDateString(undefined, { year: "numeric", month: "long", day: "numeric" }); }
    catch (e) { return iso; }
  }

  /* ---- storage: every read and write is guarded; the page works without it */
  var store = {
    get: function (key, fallback) {
      try { var raw = localStorage.getItem("ptg.v1." + key); return raw === null ? fallback : JSON.parse(raw); }
      catch (e) { return fallback; }
    },
    set: function (key, value) {
      try { localStorage.setItem("ptg.v1." + key, JSON.stringify(value)); return true; }
      catch (e) { return false; }
    },
    del: function (key) { try { localStorage.removeItem("ptg.v1." + key); } catch (e) { /* ignore */ } }
  };

  /* ---- print one part of the page (the pledge, the notebook) instead of all of it */
  function printOnly(cls) {
    var body = doc.body;
    function done() { body.classList.remove(cls); window.removeEventListener("afterprint", done); }
    body.classList.add(cls);
    window.addEventListener("afterprint", done);
    window.print();
    setTimeout(done, 60000);
  }

  /* ---- toast */
  var toastEl = $("#toast"), toastTimer = 0;
  function toast(msg, ms) {
    if (!toastEl) return;
    toastEl.textContent = msg;
    toastEl.classList.add("is-on");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { toastEl.classList.remove("is-on"); }, ms || 1900);
  }

  /* ---- analytics: loads only when an ID is configured */
  function track(name, params) {
    if (typeof window.gtag === "function") window.gtag("event", name, params || {});
  }
  if (/^G-[A-Z0-9]{4,}$/.test(cfg.GA4_MEASUREMENT_ID || "")) {
    var ga = doc.createElement("script");
    ga.async = true;
    ga.src = "https://www.googletagmanager.com/gtag/js?id=" + cfg.GA4_MEASUREMENT_ID;
    doc.head.appendChild(ga);
    window.dataLayer = window.dataLayer || [];
    window.gtag = function () { window.dataLayer.push(arguments); };
    window.gtag("js", new Date());
    window.gtag("config", cfg.GA4_MEASUREMENT_ID);
  }
  doc.addEventListener("click", function (ev) {
    var a = ev.target.closest && ev.target.closest("[data-cta]");
    if (a) track("cta_click", { placement: a.getAttribute("data-cta") });
  });

  /* ==========================================================================
     Header: stuck state, reading progress, mobile menu, current section
     ========================================================================== */
  mod("header", function () {
    var head = $("#head"), bar = $("#progress"), nav = $("#nav"), btn = $("#menu-btn"), dock = $("#dock"), climb = $("#dock-climb");
    if (!head) return;
    var ticking = false;
    function update() {
      ticking = false;
      var y = window.scrollY || 0;
      head.classList.toggle("is-stuck", y > 24);
      var max = Math.max(1, doc.documentElement.scrollHeight - window.innerHeight);
      var prog = "scaleX(" + Math.min(1, y / max).toFixed(4) + ")";
      if (bar) bar.style.transform = prog;
      if (climb) climb.style.transform = prog;
      if (dock) {
        var vh = window.innerHeight, get = $("#get"), nearEnd = get && get.getBoundingClientRect().top < vh * 0.9;
        var sac = $("#sacred"), sr = sac && sac.getBoundingClientRect(), still = !!sr && sr.top < vh * 0.7 && sr.bottom > vh * 0.3;
        /* an inline ask on screen already offers the same button: one is enough */
        var asked = $$(".ask:not([hidden]), .reader__acts").some(function (el) { var r = el.getBoundingClientRect(); return r.height > 0 && r.top < vh && r.bottom > 0; });
        var on = y > vh * 0.85 && !nearEnd && !still && !asked;
        dock.classList.toggle("is-on", on);
        doc.body.classList.toggle("dock-on", on);
      }
    }
    window.addEventListener("scroll", function () { if (!ticking) { ticking = true; requestAnimationFrame(update); } }, { passive: true });
    window.addEventListener("resize", update);
    doc.addEventListener("ptg:ask", function () { requestAnimationFrame(update); });
    update();

    var behind = [$("main"), $(".foot"), dock, $(".brand", head)];
    function setMenu(open) {
      if (nav.classList.contains("is-open") === open) return;
      nav.classList.toggle("is-open", open);
      head.classList.toggle("menu-open", open);
      btn.setAttribute("aria-expanded", String(open));
      btn.setAttribute("aria-label", open ? "Close menu" : "Open menu");
      var icon = $("path", btn); if (icon) icon.setAttribute("d", open ? "M6 6l12 12M18 6 6 18" : "M3 7h18M3 12h18M3 17h18");
      doc.body.style.overflow = open ? "hidden" : "";
      behind.forEach(function (el) { if (el) el.inert = open; });
      if (open) { var first = $("a", nav); if (first) first.focus(); }
    }
    if (btn && nav) {
      btn.addEventListener("click", function () { setMenu(!nav.classList.contains("is-open")); });
      nav.addEventListener("click", function (ev) { if (ev.target === nav || ev.target.closest("a")) setMenu(false); });
      nav.addEventListener("keydown", function (ev) {
        if (ev.key !== "Tab" || !nav.classList.contains("is-open")) return;
        var f = $$("a,button", nav), first = f[0], last = f[f.length - 1];
        if (ev.shiftKey && doc.activeElement === first) { ev.preventDefault(); last.focus(); }
        else if (!ev.shiftKey && doc.activeElement === last) { ev.preventDefault(); first.focus(); }
      });
      doc.addEventListener("keydown", function (ev) {
        if (ev.key === "Escape" && nav.classList.contains("is-open")) { setMenu(false); btn.focus(); }
      });
      window.addEventListener("resize", function () { if (!mq("(max-width: 66.25em)").matches) setMenu(false); });
    }

    if ("IntersectionObserver" in window) {
      var links = {};
      $$("a[href^='#']", nav).forEach(function (a) { links[a.getAttribute("href").slice(1)] = a; });
      var io = new IntersectionObserver(function (entries) {
        entries.forEach(function (en) {
          if (!en.isIntersecting) return;
          Object.keys(links).forEach(function (id) {
            if (id === en.target.id) links[id].setAttribute("aria-current", "true"); else links[id].removeAttribute("aria-current");
          });
        });
      }, { rootMargin: "-45% 0px -50% 0px" });
      Object.keys(links).forEach(function (id) { var s = doc.getElementById(id); if (s && !links[id].classList.contains("btn")) io.observe(s); });
    }
  });

  /* ==========================================================================
     Reveal on scroll. Content is visible by default; this only adds motion.
     ========================================================================== */
  mod("reveal", function () {
    var items = $$(".rv, .rv-list");
    if (reduce || !("IntersectionObserver" in window)) { items.forEach(function (el) { el.classList.add("is-in"); }); return; }
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) { if (en.isIntersecting) { en.target.classList.add("is-in"); io.unobserve(en.target); } });
    }, { rootMargin: "0px 0px -8% 0px", threshold: 0.05 });
    items.forEach(function (el) { io.observe(el); });
    /* never leave anything hidden if the observer is slow to fire */
    setTimeout(function () { items.forEach(function (el) { if (el.getBoundingClientRect().top < window.innerHeight) el.classList.add("is-in"); }); }, 1200);
  });

  /* ==========================================================================
     Hero: the mountain at blue hour, engraved once, then the route is walked.
     Virtual canvas 1500 x 790; the summit is at (966,119).
     ========================================================================== */
  mod("heroArt", function () {
    var canvas = $("#ascent-art"), over = $("#ascent-route"), mast = $(".mast"), glowEl = $(".mast__glow");
    if (!canvas || !canvas.getContext) return;
    var ctx = canvas.getContext("2d");
    if (!ctx) return;
    var base = canvas, bctx = ctx;
    var octx = over && over.getContext ? over.getContext("2d") : null;
    if (!octx) { over = canvas; octx = ctx; }
    var seed = 1791, g = bctx, view = { scale: 1, tx: 0, ty: 0, dpr: 1 };

    function random() { seed = (Math.imul(1664525, seed) + 1013904223) >>> 0; return seed / 4294967296; }
    function line(pts, color, weight) {
      g.beginPath();
      for (var i = 0; i < pts.length; i++) { if (!i) g.moveTo(pts[i][0], pts[i][1]); else g.lineTo(pts[i][0], pts[i][1]); }
      g.strokeStyle = color; g.lineWidth = weight; g.stroke();
    }
    function yAt(profile, x) {
      for (var k = 1; k < profile.length; k++) {
        if (x <= profile[k][0]) { var a = profile[k - 1], b = profile[k], t = (x - a[0]) / (b[0] - a[0]); return a[1] + (b[1] - a[1]) * t; }
      }
      return profile[profile.length - 1][1];
    }
    function rough(a, b, c, depth) {
      if (!depth) return [a, b];
      var dx = b[0] - a[0], dy = b[1] - a[1], len = Math.hypot(dx, dy) || 1;
      var off = (random() - 0.48) * len * c;
      var mid = [(a[0] + b[0]) / 2 - off * dy / len, (a[1] + b[1]) / 2 + off * dx / len];
      return rough(a, mid, c * 0.82, depth - 1).slice(0, -1).concat(rough(mid, b, c * 0.82, depth - 1));
    }
    function ridge(profile, top, bottom, roughness, rim) {
      var sky = [];
      for (var i = 1; i < profile.length; i++) sky = sky.concat(rough(profile[i - 1], profile[i], roughness, 4).slice(0, -1));
      sky.push(profile[profile.length - 1]);
      var gr = g.createLinearGradient(0, 95, 0, 805);
      gr.addColorStop(0, top); gr.addColorStop(1, bottom);
      g.beginPath(); g.moveTo(sky[0][0], 1400);
      for (var j = 0; j < sky.length; j++) g.lineTo(sky[j][0], sky[j][1]);
      g.lineTo(sky[sky.length - 1][0], 1400); g.closePath(); g.fillStyle = gr; g.fill();
      if (rim) line(sky, rim, 1.1);
    }
    function face(poly, light, dark, dir, contrast) {
      var ys = poly.map(function (p) { return p[1]; }), xs = poly.map(function (p) { return p[0]; });
      var lo = Math.min.apply(null, ys), hi = Math.max.apply(null, ys), left = Math.min.apply(null, xs), right = Math.max.apply(null, xs);
      g.save(); g.beginPath();
      for (var i = 0; i < poly.length; i++) { if (!i) g.moveTo(poly[i][0], poly[i][1]); else g.lineTo(poly[i][0], poly[i][1]); }
      g.closePath(); g.clip();
      var gr = g.createLinearGradient(0, lo, 0, hi + 35);
      gr.addColorStop(0, light); gr.addColorStop(1, dark);
      g.fillStyle = gr; g.fillRect(left - 1, lo - 1, right - left + 3, hi - lo + 3);
      for (var x = left - 670; x < right + 670; x += 2.8 + random() * 2.8) {
        var slope = dir * (0.34 + random() * 0.35), pts = [[x, lo - 10]];
        for (var y = lo + 1; y < hi + 25; y += 7 + random() * 11) {
          var warp = 3 * Math.sin(y / 24 + x / 33) + 1.7 * Math.sin(y / 6 + x / 22);
          pts.push([x + slope * (y - lo) + warp + (random() - 0.5) * 3, y]);
        }
        var alpha = (0.035 + random() * 0.3) * contrast;
        line(pts, random() > 0.36 ? "rgba(214,223,238," + alpha.toFixed(3) + ")" : "rgba(8,11,17," + (alpha + 0.1).toFixed(3) + ")", 0.5 + random() * 1.25);
      }
      for (var n = 0; n < (hi - lo) * 1.2; n++) {
        var sx = left + random() * (right - left), sy = lo + random() * (hi - lo), l = 3 + random() * 11;
        line([[sx, sy], [sx + dir * l * 0.75, sy + l]], "rgba(226,232,243,.2)", 0.8);
      }
      g.restore();
    }
    function pine(x, y, size, color) {
      g.strokeStyle = color; g.lineWidth = Math.max(0.65, size * 0.052); g.beginPath();
      g.moveTo(x, y); g.lineTo(x, y - size);
      for (var k = 1; k < 8; k++) {
        var d = size * k / 9, spread = size * 0.23 * k / 8;
        g.moveTo(x, y - size + d * 0.72); g.lineTo(x - spread, y - size + d);
        g.moveTo(x, y - size + d * 0.72); g.lineTo(x + spread * 0.85, y - size + d * 0.98);
      }
      g.stroke();
    }
    function mist(y, h, alpha) {
      var gr = g.createLinearGradient(0, y - h, 0, y + h);
      gr.addColorStop(0, "rgba(150,163,186,0)"); gr.addColorStop(0.5, "rgba(150,163,186," + alpha + ")"); gr.addColorStop(1, "rgba(150,163,186,0)");
      g.fillStyle = gr; g.fillRect(-900, y - h, 3500, h * 2);
    }

    /* base camp, twelve levels, the summit */
    var route = [[754, 620], [778, 590], [813, 564], [801, 548], [824, 531], [861, 508], [866, 488], [898, 464], [886, 447], [901, 424], [923, 409], [931, 382], [943, 356], [930, 341], [942, 313], [955, 298], [948, 278], [964, 254], [960, 232], [973, 203], [965, 179], [973, 156], [966, 123]];
    var segs = [], total = 0;
    for (var r = 1; r < route.length; r++) { var dd = Math.hypot(route[r][0] - route[r - 1][0], route[r][1] - route[r - 1][1]); segs.push(dd); total += dd; }
    function upTo(t) {
      var want = t * total, pts = [route[0]];
      for (var i = 0; i < segs.length; i++) {
        if (want >= segs[i]) { pts.push(route[i + 1]); want -= segs[i]; }
        else { var k = want / segs[i]; pts.push([route[i][0] + (route[i + 1][0] - route[i][0]) * k, route[i][1] + (route[i + 1][1] - route[i][1]) * k]); break; }
      }
      return pts;
    }
    function at(t) { var p = upTo(t); return p[p.length - 1]; }

    function setView(c, w, h) {
      var small = w < 780, dpr = Math.min(window.devicePixelRatio || 1, small ? 1.5 : 1.75);
      c.width = Math.round(w * dpr); c.height = Math.round(h * dpr);
      var scale = Math.max(w / 1500, h / 790);
      if (small) {
        /* phones: the whole route, base camp to summit, sits above the title */
        scale = Math.max(w / 1500, Math.min(w / 520, h * 0.42 / 520));
        view = { dpr: dpr, scale: scale, tx: w * 0.56 - 862 * scale, ty: 70 - 104 * scale };
      } else {
        view = { dpr: dpr, scale: scale, tx: (w - 1500 * scale) * 0.62, ty: (h - 790 * scale) * 0.42 };
      }
    }
    function useView(c2d) { c2d.setTransform(view.dpr * view.scale, 0, 0, view.dpr * view.scale, view.dpr * view.tx, view.dpr * view.ty); }
    /* the route layer covers only the route, the summit glow and the ring (virtual x, y, w, h),
       so each frame repaints a small layer instead of a second full-screen one */
    var OB = [700, -50, 440, 712];
    function placeOver() {
      if (over === canvas) return;
      var L = OB[0] * view.scale + view.tx, T = OB[1] * view.scale + view.ty, W = OB[2] * view.scale, H = OB[3] * view.scale;
      over.style.left = L.toFixed(2) + "px"; over.style.top = T.toFixed(2) + "px";
      over.style.width = W.toFixed(2) + "px"; over.style.height = H.toFixed(2) + "px";
      over.width = Math.round(W * view.dpr); over.height = Math.round(H * view.dpr);
    }
    function useOver(c2d) {
      if (over === canvas) { useView(c2d); return; }
      var k = view.dpr * view.scale;
      c2d.setTransform(k, 0, 0, k, -OB[0] * k, -OB[1] * k);
    }

    var tail = null;
    function paintBase(w, h, defer) {
      setView(base, w, h);
      g = bctx; useView(g); seed = 1791;
      var sky = g.createLinearGradient(0, -80, 0, 760);
      sky.addColorStop(0, "#0d1016"); sky.addColorStop(0.34, "#151a23"); sky.addColorStop(0.62, "#28303f"); sky.addColorStop(0.8, "#4a566b"); sky.addColorStop(1, "#2b3443");
      g.fillStyle = sky; g.fillRect(-1500, -1500, 4700, 4200);
      var glow = g.createRadialGradient(1010, 330, 10, 1010, 330, 560);
      glow.addColorStop(0, "rgba(152,168,196,.42)"); glow.addColorStop(0.5, "rgba(120,136,165,.14)"); glow.addColorStop(1, "rgba(120,136,165,0)");
      g.fillStyle = glow; g.fillRect(300, -300, 1500, 1300);
      for (var s = 0; s < 420; s++) {
        var sx = random() * 2100 - 300, sy = random() * 430 - 60, rr = random();
        var a = (0.12 + rr * 0.6) * (1 - Math.max(0, sy) / 520);
        g.fillStyle = "rgba(226,232,244," + a.toFixed(3) + ")";
        g.beginPath(); g.arc(sx, sy, rr > 0.94 ? 1.25 : rr > 0.7 ? 0.85 : 0.55, 0, 6.2832); g.fill();
      }
      for (var s2 = 0; s2 < 1100; s2++) { var ax = random() * 1860 - 160, ay = 150 + random() * 400; line([[ax, ay], [ax + 2 + random() * 13, ay - 0.55]], "rgba(190,202,224,.07)", 0.55); }

      ridge([[-900, 500], [-300, 465], [200, 417], [372, 339], [495, 391], [640, 295], [746, 341], [850, 254], [950, 360], [1080, 251], [1203, 328], [1313, 233], [1407, 298], [1530, 212], [1830, 360], [2500, 330]], "#566277", "#414c5f", 0.11, null);
      mist(430, 70, 0.1);
      ridge([[-900, 560], [-200, 520], [176, 440], [342, 410], [480, 464], [630, 333], [716, 353], [775, 285], [860, 350], [1022, 346], [1150, 316], [1235, 240], [1305, 331], [1400, 250], [1500, 324], [1790, 260], [2500, 360]], "#465166", "#333d4f", 0.14, "rgba(190,203,226,.2)");
      mist(505, 60, 0.12);
      ridge([[-900, 760], [-220, 720], [250, 640], [438, 523], [494, 554], [619, 374], [661, 402], [736, 302], [793, 338], [848, 244], [887, 263], [966, 119], [998, 176], [1034, 216], [1051, 205], [1105, 289], [1131, 272], [1168, 335], [1214, 348], [1276, 410], [1354, 378], [1455, 456], [1650, 398], [1780, 470], [2500, 520]], "#9aa6ba", "#242c3a", 0.11, "rgba(220,228,242,.34)");
      face([[438, 523], [619, 374], [603, 482], [548, 535], [481, 644]], "#7d8a9f", "#28303e", -1, 0.76);
      face([[619, 374], [661, 402], [736, 302], [689, 441], [642, 460], [601, 583], [548, 622], [603, 482]], "#4f5a6e", "#222a37", 1, 0.75);
      face([[736, 302], [793, 338], [848, 244], [823, 342], [760, 471], [706, 583], [643, 631], [681, 460]], "#8f9cb1", "#333d4e", -1, 0.95);
      face([[848, 244], [887, 263], [966, 119], [943, 198], [912, 223], [899, 285], [843, 340], [823, 423], [749, 541]], "#b4bfd0", "#3c475a", -1, 1.1);
      face([[966, 119], [993, 201], [974, 278], [934, 332], [917, 401], [851, 459], [798, 610], [733, 646], [782, 458], [843, 340], [899, 285], [912, 223], [943, 198]], "#cbd4e2", "#3a4558", -1, 1.13);
      face([[966, 119], [998, 176], [1034, 216], [1051, 205], [1105, 289], [1131, 272], [1168, 335], [1214, 348], [1276, 410], [1313, 522], [1180, 622], [1103, 467], [1054, 398], [1010, 285], [974, 278], [993, 201]], "#5b677c", "#202733", 1, 1.02);
      face([[993, 201], [1010, 285], [1054, 398], [1103, 467], [1180, 622], [996, 660], [923, 546], [897, 456], [917, 401], [934, 332], [974, 278]], "#465166", "#1e2430", 1, 1);
      face([[1051, 205], [1066, 249], [1101, 314], [1145, 372], [1191, 435], [1156, 417], [1113, 376], [1080, 325]], "#a7b2c5", "#4a556a", 1, 1);
      face([[1354, 378], [1455, 456], [1500, 514], [1530, 654], [1396, 625], [1345, 509], [1302, 451]], "#5f6b80", "#222a37", 1, 0.85);
      mist(600, 80, 0.16);
      ridge([[-900, 700], [-220, 670], [10, 626], [206, 650], [371, 585], [482, 616], [591, 518], [716, 548], [790, 472], [860, 500], [948, 441], [1045, 505], [1150, 551], [1276, 466], [1390, 530], [1510, 450], [1700, 528], [2500, 560]], "rgba(52,62,80,.86)", "#1a202b", 0.14, "rgba(170,184,210,.18)");
      var fg = [[-900, 780], [-300, 752], [120, 710], [240, 730], [385, 660], [537, 678], [652, 617], [745, 638], [850, 561], [945, 580], [1030, 535], [1147, 590], [1255, 566], [1344, 609], [1455, 548], [1623, 575], [1800, 540], [2500, 600]];
      ridge(fg, "#27303e", "#141920", 0.1, "rgba(150,165,192,.14)");
      /* the forest (about a thousand small strokes, near-black under the overlay) is drawn after first paint */
      tail = function () {
        tail = null; g = bctx; useView(g);
        for (var i = 0; i < 700; i++) { var px = random() * 1900 - 100, py = yAt(fg, px) + random() * 59; pine(px, py, 2 + random() * 9, "#10141a"); }
        var dark = [[-900, 740], [-200, 710], [170, 687], [315, 717], [510, 650], [658, 690], [846, 618], [954, 653], [1064, 614], [1248, 674], [1403, 622], [1600, 660], [2500, 700]];
        ridge(dark, "#171c25", "#0e1116", 0.08, null);
        for (var j = 0; j < 360; j++) { var fx = random() * 1900 - 150; pine(fx, yAt(dark, fx) + random() * 22, 3 + random() * 12, "#0a0d11"); }
      };
      if (!defer) tail();
    }

    function frame(t, rk) {
      /* t: 0 = base camp, 1 = summit reached; rk: 0..1, the summit ring landing (1 = at rest) */
      if (rk === undefined) rk = 1;
      var o = octx;
      o.setTransform(1, 0, 0, 1, 0, 0);
      if (o !== bctx) o.clearRect(0, 0, over.width, over.height);
      g = o; useOver(g);
      var lit = Math.max(0, (t - 0.82) / 0.18);
      if (lit > 0) {
        var dawn = g.createRadialGradient(966, 121, 2, 966, 121, 130);
        dawn.addColorStop(0, "rgba(246,214,160," + (0.5 * lit).toFixed(3) + ")"); dawn.addColorStop(0.35, "rgba(240,202,144," + (0.16 * lit).toFixed(3) + ")"); dawn.addColorStop(1, "rgba(240,202,144,0)");
        g.fillStyle = dawn; g.fillRect(810, -40, 320, 330);
      }
      g.save(); g.setLineDash([3.5, 6.5]); g.lineCap = "round";
      line(upTo(t), "rgba(244,212,160,.86)", 1.7); g.setLineDash([]);
      for (var n = 0; n <= 13; n++) {
        var nt = n / 13;
        if (nt > t + 0.0001) break;
        var p = at(nt), camp = n === 0 || n === 3 || n === 7 || n === 12 || n === 13, r = n === 13 ? 4.6 : camp ? 3.6 : 2.5;
        if (t < 1) {
          /* each camp lights briefly as the walker reaches it */
          var k = Math.min(1, (t - nt) / 0.06);
          if (k < 1) { g.beginPath(); g.arc(p[0], p[1], r + (camp ? 12 : 9) * k, 0, 6.2832); g.fillStyle = "rgba(246,214,160," + ((camp ? 0.5 : 0.38) * (1 - k)).toFixed(3) + ")"; g.fill(); }
        }
        g.beginPath(); g.arc(p[0], p[1], r, 0, 6.2832);
        g.fillStyle = n === 13 ? "#fbe6bf" : "#ecc88e"; g.fill();
        g.strokeStyle = "rgba(17,21,28,.9)"; g.lineWidth = 1.2; g.stroke();
      }
      if (t >= 1) {
        /* the summit ring: opens wide once, then settles at rest (r 9.5, the resting frame) */
        var rr, ra;
        if (rk < 0.55) { var a = 1 - Math.pow(1 - rk / 0.55, 3); rr = 4.6 + 7.4 * a; ra = 0.8 - 0.45 * a; }
        else { var b2 = (rk - 0.55) / 0.45, eb = b2 * b2 * (3 - 2 * b2); rr = 12 - 2.5 * eb; ra = 0.35 + 0.2 * eb; }
        g.beginPath(); g.arc(966, 123, rr, 0, 6.2832); g.strokeStyle = "rgba(251,230,191," + ra.toFixed(3) + ")"; g.lineWidth = 1; g.stroke();
      }
      g.restore();
    }

    var walked = false, raf = 0, lastW = 0, lastH = 0;
    function placeGlow() {
      if (!glowEl) return;
      glowEl.style.left = (966 * view.scale + view.tx).toFixed(1) + "px";
      glowEl.style.top = (121 * view.scale + view.ty).toFixed(1) + "px";
    }
    function arrived() { walked = true; placeGlow(); if (mast) mast.classList.add("is-walked"); }
    function inView() {
      if (doc.visibilityState && doc.visibilityState !== "visible") return false;
      var r = canvas.getBoundingClientRect();
      return r.bottom > 0 && r.top < window.innerHeight;
    }
    function paint(animate) {
      var w = canvas.clientWidth, h = canvas.clientHeight;
      if (!w || !h) return;
      if (w === lastW && Math.abs(h - lastH) < 90) return; /* unchanged (the observer's first call) or the mobile URL bar */
      lastW = w; lastH = h;
      cancelAnimationFrame(raf);
      var run = animate && !reduce && !walked && inView();
      paintBase(w, h, run);
      placeOver();
      if (!run) { if (tail) tail(); frame(1, 1); arrived(); return; }
      var start = 0, dur = 2600, settle = 760;
      function step(now) {
        if (!start) start = now;
        var e = now - start, k = Math.min(1, e / dur);
        if (k < 1) { frame(1 - Math.pow(1 - k, 3)); raf = requestAnimationFrame(step); return; }
        var s2 = Math.min(1, (e - dur) / settle);
        frame(1, s2);
        if (s2 < 1) raf = requestAnimationFrame(step); else arrived();
      }
      frame(0);
      raf = requestAnimationFrame(step);
      requestAnimationFrame(function () { setTimeout(function () { if (tail) tail(); }, 0); });
    }
    var queued = 0;
    function queue() { clearTimeout(queued); queued = setTimeout(function () { paint(false); }, 180); }
    try { paint(true); } catch (e) { /* the CSS gradient behind the canvas remains */ }
    if ("ResizeObserver" in window) new ResizeObserver(queue).observe(canvas.parentElement);
    else window.addEventListener("resize", queue);
  });

  /* ==========================================================================
     The threshold: what rises in you. Every answer gets the book's own reply,
     because the book says any reaction is data. Nothing is stored.
     ========================================================================== */
  mod("react", function () {
    var box = $("#react"), line = $("#react-line");
    if (!box || !line) return;
    var btns = $$("[data-react]", box);
    line.hidden = true;
    btns.forEach(function (b) {
      b.addEventListener("click", function () {
        btns.forEach(function (o) { o.setAttribute("aria-pressed", String(o === b)); });
        line.hidden = true; void line.offsetWidth; line.hidden = false;
        /* the reply must land in view, above the bar at the foot of a phone screen. The bar can
           slide up during this very scroll, so its height is kept clear whenever it is drawn. */
        var dock = $("#dock"), floor = window.innerHeight - 12;
        if (dock && dock.offsetHeight > 0 && getComputedStyle(dock).display !== "none") floor = Math.min(floor, window.innerHeight - dock.offsetHeight - 12);
        var over = line.getBoundingClientRect().bottom - floor;
        if (over > 0) window.scrollBy({ top: over, behavior: reduce ? "auto" : "smooth" });
        track("threshold_react", { choice: b.getAttribute("data-react") });
      });
    });
  });

  /* ==========================================================================
     The ascent: twelve gates. One open at a time; deep links (#level-4) work.
     ========================================================================== */
  var LEVELS = [];
  try { LEVELS = JSON.parse($("#ptg-levels").textContent); } catch (e) { LEVELS = []; }

  var ascentReady = false;
  mod("ascent", function () {
    var wrap = $("#levels");
    if (!wrap) return;
    var btns = $$(".lvl__btn", wrap), panels = $$(".lvl__panel", wrap);
    var wide = mq("(min-width: 60.0625em)");
    var current = 0, seen = {};
    var gatesN = $("#gates-n"), gatesLine = $(".gates"), summitLine = $(".ascent__summit");
    function countGates() {
      /* the gate counter: every level opened once counts, and all twelve light the summit line */
      var k = Object.keys(seen).length;
      if (gatesN) gatesN.textContent = String(k);
      if (k >= btns.length) {
        if (summitLine) summitLine.classList.add("is-lit");
        if (gatesLine && !gatesLine.classList.contains("is-all")) { gatesLine.classList.add("is-all"); gatesLine.textContent = "All twelve gates opened."; gatesN = null; }
      }
    }
    function moreCue(pn) {
      /* wide screens: a fade at the foot of a gate that scrolls, until its last line is in view */
      if (pn) pn.classList.toggle("is-more", wide.matches && pn.scrollHeight - pn.clientHeight - pn.scrollTop > 8);
    }
    panels.forEach(function (pn) { pn.addEventListener("scroll", function () { moreCue(pn); }, { passive: true }); });
    window.addEventListener("resize", function () { if (current) moreCue(panels[current - 1]); });
    function fitGate() {
      /* wide screens: a gate taller than the window scrolls inside itself, and always opens at its plate */
      if (current && panels[current - 1]) { panels[current - 1].scrollTop = 0; moreCue(panels[current - 1]); }
    }
    function open(n, opts) {
      opts = opts || {};
      var same = current === n;
      btns.forEach(function (b, i) {
        var on = i + 1 === n && !(same && !wide.matches && !opts.force);
        b.setAttribute("aria-expanded", String(on));
        panels[i].classList.toggle("is-open", on);
      });
      current = (same && !wide.matches && !opts.force) ? 0 : n;
      if (current && !opts.auto) seen[current] = true;
      countGates();
      btns.forEach(function (b, i) {
        b.classList.toggle("is-past", !!current && i + 1 < current);
        b.classList.toggle("is-seen", !!seen[i + 1] && i + 1 !== current);
      });
      fitGate();
      if (current && opts.user) {
        track("level_open", { level: n });
        if (!wide.matches) {
          var top = btns[n - 1].getBoundingClientRect().top + window.scrollY - 70;
          window.scrollTo({ top: top, behavior: reduce ? "auto" : "smooth" });
        }
        if (history.replaceState) history.replaceState(null, "", "#level-" + n);
      }
    }
    btns.forEach(function (b, i) {
      b.addEventListener("click", function () { open(i + 1, { user: true }); });
      b.addEventListener("keydown", function (ev) {
        var to = -1;
        if (ev.key === "ArrowDown") to = (i + 1) % btns.length;
        else if (ev.key === "ArrowUp") to = (i + btns.length - 1) % btns.length;
        else if (ev.key === "Home") to = 0;
        else if (ev.key === "End") to = btns.length - 1;
        else return;
        ev.preventDefault();
        btns[to].focus();
        if (wide.matches) open(to + 1, { force: true });
      });
    });
    function fromHash() {
      var m = /^#level-(\d{1,2})$/.exec(location.hash);
      if (!m || +m[1] < 1 || +m[1] > btns.length) return false;
      var n = +m[1];
      open(n, { force: true });
      /* on wide screens the level wrapper has no box of its own, so the browser cannot scroll to it */
      if (wide.matches) setTimeout(function () { btns[n - 1].scrollIntoView({ block: "center", behavior: reduce ? "auto" : "smooth" }); }, 0);
      return true;
    }
    /* phones start with every gate closed, so the twelve questions read as a list; wide screens open Level I */
    if (!fromHash() && wide.matches) open(1, { force: true, auto: true });
    window.addEventListener("hashchange", fromHash);
    var onWide = function () { if (wide.matches && !current) open(1, { force: true, auto: true }); fitGate(); };

    if (wide.addEventListener) wide.addEventListener("change", onWide); else if (wide.addListener) wide.addListener(onWide);
    if (btns[0] && "IntersectionObserver" in window) {
      new IntersectionObserver(function (es) {
        if (!es.some(function (e) { return e.isIntersecting; })) return;
        if (wide.matches && current && !seen[current]) { seen[current] = true; countGates(); }
      }, { threshold: 0.5 }).observe(btns[0]);
    }
    ascentReady = true;
  });
  /* reveal targets and the gates are both set up: the page may stay in its scripted state */
  window.PTG_READY = ascentReady || !$("#levels");

  /* ---- quote: copy the line, or save it as a card */
  function levelBy(n) { for (var i = 0; i < LEVELS.length; i++) if (LEVELS[i].n === n) return LEVELS[i]; return null; }
  function copyText(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) return navigator.clipboard.writeText(text);
    return new Promise(function (resolve, reject) {
      var ta = doc.createElement("textarea");
      ta.value = text; ta.setAttribute("readonly", ""); ta.style.cssText = "position:fixed;left:-9999px;top:0";
      doc.body.appendChild(ta); ta.select();
      try { doc.execCommand("copy") ? resolve() : reject(); } catch (e) { reject(e); }
      doc.body.removeChild(ta);
    });
  }
  function wrapLines(c, text, maxWidth) {
    var words = text.split(/\s+/), lines = [], cur = "";
    for (var i = 0; i < words.length; i++) {
      var tryLine = cur ? cur + " " + words[i] : words[i];
      if (c.measureText(tryLine).width > maxWidth && cur) { lines.push(cur); cur = words[i]; } else cur = tryLine;
    }
    if (cur) lines.push(cur);
    return lines;
  }
  var MARKS = {
    roots: function (c) { c.moveTo(12, 3); c.lineTo(12, 21); c.moveTo(12, 11.2); c.lineTo(5.6, 20.8); c.moveTo(12, 11.2); c.lineTo(18.4, 20.8); },
    fire: function (c) { c.moveTo(12, 2.6); c.lineTo(20, 21); c.lineTo(4, 21); c.closePath(); c.moveTo(12, 10.4); c.lineTo(15.9, 21); c.lineTo(8.1, 21); c.closePath(); },
    mirror: function (c) { c.arc(12, 12, 9, 0, 6.2832); c.moveTo(12, 3); c.lineTo(12, 21); },
    water: function (c) { c.moveTo(3.5, 7.6); c.lineTo(20.5, 7.6); c.moveTo(3.5, 12); c.lineTo(20.5, 12); c.moveTo(3.5, 16.4); c.lineTo(20.5, 16.4); },
    light: function (c) { c.arc(12, 12, 3.1, 0, 6.2832); [[12, 2.4, 12, 5.8], [12, 18.2, 12, 21.6], [2.4, 12, 5.8, 12], [18.2, 12, 21.6, 12], [5.2, 5.2, 7.6, 7.6], [16.4, 16.4, 18.8, 18.8], [5.2, 18.8, 7.6, 16.4], [16.4, 7.6, 18.8, 5.2]].forEach(function (r) { c.moveTo(r[0], r[1]); c.lineTo(r[2], r[3]); }); },
    bridge: function (c) { c.moveTo(3, 17.2); c.bezierCurveTo(5.4, 13.6, 8.4, 11.6, 12, 11.6); c.bezierCurveTo(15.6, 11.6, 18.6, 13.6, 21, 17.2); c.closePath(); },
    seed: function (c) { c.arc(11, 16.6, 4.2, 0, 6.2832); c.moveTo(11, 12.4); c.lineTo(11, 4.2); c.moveTo(11, 8.4); c.lineTo(15.2, 5.5); },
    ripple: function (c) { c.arc(12, 12, 2.6, 0, 6.2832); c.moveTo(18.2, 12); c.arc(12, 12, 6.2, 0, 6.2832); c.moveTo(21.8, 12); c.arc(12, 12, 9.8, 0, 6.2832); },
    lantern: function (c) { c.rect(7.6, 7.4, 8.8, 13); c.moveTo(9.6, 7.4); c.bezierCurveTo(10, 5.7, 10.8, 4.8, 12, 4.8); c.bezierCurveTo(13.2, 4.8, 14, 5.7, 14.4, 7.4); c.moveTo(13, 13.9); c.arc(12, 13.9, 1, 0, 6.2832); },
    door: function (c) { c.rect(6.4, 3, 11.2, 18); c.moveTo(15.2, 12); c.arc(14.6, 12, 0.6, 0, 6.2832); },
    rings: function (c) { c.arc(12, 12.4, 2.6, 0, 6.2832); c.moveTo(18, 12.4); c.arc(12, 12.4, 6, 0, 6.2832); c.moveTo(21.4, 12.4); c.arc(12, 12.4, 9.4, 0, 6.2832); c.moveTo(12, 3); c.lineTo(12, 6.4); },
    confluence: function (c) { c.moveTo(5, 3.4); c.lineTo(12, 12.6); c.lineTo(19, 3.4); c.moveTo(12, 12.6); c.lineTo(12, 21); },
    mountain: function (c) { c.moveTo(12, 3); c.lineTo(21, 20.6); c.lineTo(3, 20.6); c.closePath(); c.moveTo(8.7, 9.6); c.lineTo(15.3, 9.6); }
  };
  function drawCard(L) {
    var W = 1080, H = 1350, c = doc.createElement("canvas");
    c.width = W; c.height = H;
    var x = c.getContext("2d");
    x.fillStyle = "#171a20"; x.fillRect(0, 0, W, H);
    var gl = x.createRadialGradient(W / 2, 250, 10, W / 2, 250, 760);
    gl.addColorStop(0, "rgba(145,158,178,.2)"); gl.addColorStop(1, "rgba(145,158,178,0)");
    x.fillStyle = gl; x.fillRect(0, 0, W, H);
    x.strokeStyle = "rgba(223,227,234,.22)"; x.lineWidth = 1; x.strokeRect(54.5, 54.5, W - 109, H - 109);
    x.textAlign = "center"; x.textBaseline = "alphabetic";
    function spaced(text, y, size, color, tracking) {
      x.font = "500 " + size + "px 'EB Garamond', Georgia, serif"; x.fillStyle = color;
      var chars = text.toUpperCase().split(""), widths = chars.map(function (ch) { return x.measureText(ch).width; });
      var totalW = widths.reduce(function (a, b) { return a + b; }, 0) + tracking * (chars.length - 1), cx = W / 2 - totalW / 2;
      x.textAlign = "left";
      chars.forEach(function (ch, i) { x.fillText(ch, cx, y); cx += widths[i] + tracking; });
      x.textAlign = "center";
    }
    spaced("Level " + L.num + "  ·  " + L.sym, 170, 26, "#919eb2", 9);
    x.save(); x.translate(W / 2 - 78, 222); x.scale(6.5, 6.5);
    x.beginPath(); (MARKS[L.mk] || MARKS.mountain)(x);
    x.strokeStyle = "#919eb2"; x.lineWidth = 1; x.lineCap = "round"; x.lineJoin = "round"; x.stroke(); x.restore();
    var size = L.epi.length > 62 ? 68 : 78;
    x.font = "italic 400 " + size + "px 'Cormorant Garamond', Georgia, serif"; x.fillStyle = "#f1f3f6";
    var lines = wrapLines(x, "“" + L.epi + "”", W - 250), lh = size * 1.22, y0 = 690 - (lines.length - 1) * lh / 2 + 40;
    lines.forEach(function (ln, i) { x.fillText(ln, W / 2, y0 + i * lh); });
    x.fillStyle = "rgba(223,227,234,.34)"; x.fillRect(W / 2 - 46, 1040, 92, 1);
    spaced("The Path to Greatness", 1120, 30, "#dfe3ea", 11);
    spaced("D. Antione Dixon", 1172, 22, "#a8afbd", 8);
    spaced("eatmediatv.com/pathtogreatness", 1238, 18, "#8891a1", 5);
    return c;
  }
  function flash(btn, word) {
    if (!btn.getAttribute("data-label")) { btn.setAttribute("data-label", btn.textContent); btn.setAttribute("aria-label", btn.textContent); }
    btn.textContent = word; btn.classList.add("is-done");
    clearTimeout(btn.__t);
    btn.__t = setTimeout(function () { btn.textContent = btn.getAttribute("data-label"); btn.classList.remove("is-done"); }, 1600);
  }
  doc.addEventListener("click", function (ev) {
    var t = ev.target.closest && ev.target.closest("[data-copy],[data-card]");
    if (!t) return;
    var n = +(t.getAttribute("data-copy") || t.getAttribute("data-card")), L = levelBy(n);
    if (!L) return;
    if (t.hasAttribute("data-copy")) {
      copyText("“" + L.epi + "”\nD. Antione Dixon, The Path to Greatness (Level " + L.num + ")\n" + SITE + "#level-" + n)
        .then(function () { toast("Line copied"); flash(t, "Copied"); }, function () { toast("Copy is not available here"); });
      track("quote_copy", { level: n });
      return;
    }
    var make = function () {
      var c = drawCard(L), name = "path-to-greatness-level-" + L.num.toLowerCase() + ".png";
      var done = function (blob) {
        if (!blob) { toast("Could not make the card"); return; }
        function save() {
          var url = URL.createObjectURL(blob), a = doc.createElement("a");
          a.href = url; a.download = name; doc.body.appendChild(a); a.click(); a.remove();
          setTimeout(function () { URL.revokeObjectURL(url); }, 4000);
          toast("Card saved"); flash(t, "Saved");
        }
        var file = null;
        try { file = new File([blob], name, { type: "image/png" }); } catch (e) { file = null; }
        if (file && navigator.canShare && navigator.canShare({ files: [file] }) && mq("(pointer: coarse)").matches) {
          /* a dismissed share sheet is the reader's choice; any other failure falls back to a download */
          navigator.share({ files: [file], title: "The Path to Greatness" }).catch(function (err) { if (!err || err.name !== "AbortError") save(); });
          return;
        }
        save();
      };
      if (c.toBlob) c.toBlob(done, "image/png"); else toast("Could not make the card");
      track("quote_card", { level: n });
    };
    if (doc.fonts && doc.fonts.load) {
      Promise.all([doc.fonts.load("italic 400 78px 'Cormorant Garamond'"), doc.fonts.load("500 26px 'EB Garamond'")]).then(make, make);
    } else make();
  });

  /* ==========================================================================
     Look inside: a lightbox over real pages of the book
     ========================================================================== */
  mod("look", function () {
    var dlg = $("#lightbox"), img = $("#lb-img"), cap = $("#lb-cap"), count = $("#lb-count");
    var pages = [];
    try { pages = JSON.parse($("#ptg-look").textContent); } catch (e) { pages = []; }
    if (!dlg || !pages.length || typeof dlg.showModal !== "function") {
      /* without <dialog>, each thumbnail opens the large image directly */
      $$("[data-look]").forEach(function (b) {
        b.addEventListener("click", function () { var p = pages[+b.getAttribute("data-look")]; if (p) window.open("assets/img/look/" + p.s + "-960.webp", "_blank", "noopener"); });
      });
      return;
    }
    var i = 0, opener = null;
    function show(k, dir) {
      i = (k + pages.length) % pages.length;
      var p = pages[i], want = i, big = "assets/img/look/" + p.s + "-960.webp", small = "assets/img/look/" + p.s + "-480.webp";
      img.src = small;
      var hi = new Image();
      hi.onload = function () { if (want === i) img.src = big; };
      hi.src = big;
      img.alt = p.a; cap.textContent = p.c; count.textContent = "Page " + (i + 1) + " of " + pages.length;
      if (dir && !reduce) {
        img.classList.remove("is-in-l", "is-in-r"); void img.offsetWidth;
        img.classList.add(dir > 0 ? "is-in-r" : "is-in-l");
      }
    }
    function grow(from) {
      if (reduce || !from || !img.animate) return;
      var r0 = from.getBoundingClientRect(), r1 = img.getBoundingClientRect();
      if (!r0.width || !r1.width) return;
      var dx = r0.left - r1.left, dy = r0.top - r1.top, sc = r0.width / r1.width;
      img.animate([{ transformOrigin: "0 0", transform: "translate(" + dx + "px," + dy + "px) scale(" + sc + ")" }, { transformOrigin: "0 0", transform: "none" }],
        { duration: 420, easing: "cubic-bezier(.16,1,.3,1)" });
    }
    $$("[data-look]").forEach(function (b) {
      b.addEventListener("click", function () {
        opener = b; show(+b.getAttribute("data-look")); root.style.overflow = "hidden"; dlg.showModal();
        grow($("img", b));
        track("look_inside", { page: pages[i].s });
      });
    });
    $("#lb-close").addEventListener("click", function () { dlg.close(); });
    $("#lb-prev").addEventListener("click", function () { show(i - 1, -1); });
    $("#lb-next").addEventListener("click", function () { show(i + 1, 1); });
    dlg.addEventListener("click", function (ev) { if (ev.target === dlg || ev.target.classList.contains("lightbox__stage") || ev.target.classList.contains("lightbox__in")) dlg.close(); });
    dlg.addEventListener("keydown", function (ev) {
      if (ev.key === "ArrowLeft") { ev.preventDefault(); show(i - 1, -1); }
      else if (ev.key === "ArrowRight") { ev.preventDefault(); show(i + 1, 1); }
    });
    dlg.addEventListener("close", function () { root.style.overflow = ""; if (opener) opener.focus(); });
    var x0 = null;
    dlg.addEventListener("touchstart", function (ev) { x0 = ev.touches[0].clientX; }, { passive: true });
    dlg.addEventListener("touchend", function (ev) {
      if (x0 === null) return;
      var dx = ev.changedTouches[0].clientX - x0; x0 = null;
      if (Math.abs(dx) > 50) show(i + (dx < 0 ? 1 : -1), dx < 0 ? 1 : -1);
    }, { passive: true });
  });
  mod("lookRail", function () {
    var rail = $("#look-rail"), steps = $$("[data-step]");
    if (!rail || !steps.length) return;
    function upd() {
      var max = rail.scrollWidth - rail.clientWidth - 2;
      steps.forEach(function (b) {
        var end = +b.getAttribute("data-step") < 0 ? rail.scrollLeft <= 2 : rail.scrollLeft >= max;
        b.setAttribute("aria-disabled", String(end));
      });
    }
    steps.forEach(function (b) {
      b.removeAttribute("disabled");
      b.addEventListener("click", function () {
        if (b.getAttribute("aria-disabled") === "true") return;
        rail.scrollBy({ left: +b.getAttribute("data-step") * rail.clientWidth * 0.8, behavior: reduce ? "auto" : "smooth" });
      });
    });
    var tick = false;
    rail.addEventListener("scroll", function () { if (!tick) { tick = true; requestAnimationFrame(function () { tick = false; upd(); }); } }, { passive: true });
    window.addEventListener("resize", upd);
    upd();
  });

  /* ==========================================================================
     Excerpt: text size
     ========================================================================== */
  mod("reader", function () {
    var sheet = $("#sheet");
    if (!sheet) return;
    var steps = [1.08, 1.22, 1.36, 1.5], idx = store.get("textsize", 1);
    if (typeof idx !== "number" || idx !== Math.floor(idx) || idx < 0 || idx >= steps.length) idx = 1;
    function apply() { sheet.style.setProperty("--fs", steps[idx] + "rem"); }
    apply();
    $$("[data-size]").forEach(function (b) {
      b.addEventListener("click", function () {
        idx = Math.max(0, Math.min(steps.length - 1, idx + (b.getAttribute("data-size") === "up" ? 1 : -1)));
        apply(); store.set("textsize", idx);
      });
    });
    var more = $("#more-excerpt");
    if (more) more.addEventListener("toggle", function () {
      if (!more.open) return;
      track("excerpt_continue", {});
      /* the summary hides once open; keep keyboard focus in the passage instead of dropping it to the page */
      var a = doc.activeElement, first = $("div > p", more);
      if (first && (!a || a === doc.body || a === $("summary", more))) { first.setAttribute("tabindex", "-1"); first.focus({ preventScroll: true }); }
    });
  });

  /* ==========================================================================
     Field notebook: Level I field work, saved in this browser only
     ========================================================================== */
  mod("notebook", function () {
    var form = $("#notebook");
    if (!form) return;
    var fields = ["p1", "p2", "p3", "p4", "p5", "log"];
    var PROMPTS = {};
    fields.forEach(function (f) { var l = $("label[for='" + f + "']", form); PROMPTS[f] = l ? l.textContent.trim() : f; });
    var status = $("#nb-status"), entriesBox = $("#nb-entries"), list = $("#nb-list"), count = $("#nb-count");
    var data = store.get("notebook", null);
    if (!plain(data)) data = {};
    data.entries = (Array.isArray(data.entries) ? data.entries : []).filter(function (en) { return plain(en) && typeof en.date === "string"; });
    if (!plain(data.draft)) data.draft = {};

    /* answers grow with the text even where CSS field-sizing is missing (iOS Safari, Firefox) */
    var autosize = !(window.CSS && CSS.supports && CSS.supports("field-sizing", "content"));
    function grow(t) { if (!autosize || !t) return; t.style.overflow = "hidden"; t.style.height = "auto"; t.style.height = (t.scrollHeight + 2) + "px"; }
    function values() { var v = {}; fields.forEach(function (f) { v[f] = (form.elements[f].value || "").trim(); }); return v; }
    function any(v) { return fields.some(function (f) { return v[f]; }); }
    function fill(v) { fields.forEach(function (f) { var t = form.elements[f]; t.value = (v && typeof v[f] === "string") ? v[f] : ""; grow(t); }); }
    function sameAs(en, v) { return !!en && fields.every(function (f) { return (en[f] || "") === (v[f] || ""); }); }
    function entryFor(date) { for (var k = 0; k < data.entries.length; k++) if (data.entries[k].date === date) return data.entries[k]; return null; }
    function say(msg) { status.textContent = msg; }
    var stepTo = null, nbNext = $("#nb-next"), nbTop = $(".notebook__top", form);
    function savedMoment() {
      if (nbNext) { nbNext.hidden = false; doc.dispatchEvent(new CustomEvent("ptg:ask")); }
      if (nbTop) { nbTop.classList.remove("is-saved"); void nbTop.offsetWidth; nbTop.classList.add("is-saved"); }
    }

    function render() {
      list.textContent = "";
      var past = data.entries.slice().sort(function (a, b) { return a.date < b.date ? 1 : -1; });
      past.forEach(function (en) {
        var li = doc.createElement("li"), time = doc.createElement("time"), dl = doc.createElement("dl");
        time.setAttribute("datetime", en.date); time.textContent = niceDate(en.date) || en.date;
        fields.forEach(function (f) {
          if (!en[f]) return;
          var div = doc.createElement("div"), dt = doc.createElement("dt"), dd = doc.createElement("dd");
          dt.textContent = PROMPTS[f]; dd.textContent = en[f];
          div.appendChild(dt); div.appendChild(dd); dl.appendChild(div);
        });
        li.appendChild(time); li.appendChild(dl); list.appendChild(li);
      });
      count.textContent = String(past.length);
      entriesBox.hidden = past.length === 0;
    }

    /* today's saved page, or an unsaved draft, comes back on reload */
    var today = todayISO(), todays = entryFor(today);
    /* a draft left over from an earlier day belongs to that day's page, not to today's */
    if (typeof data.draft.date === "string" && data.draft.date !== today) {
      var old = entryFor(data.draft.date);
      if (old) fields.forEach(function (f) { if (typeof data.draft[f] === "string") old[f] = data.draft[f]; });
      else if (any(data.draft)) { var kept = { date: data.draft.date }; fields.forEach(function (f) { kept[f] = typeof data.draft[f] === "string" ? data.draft[f] : ""; }); data.entries.push(kept); }
      data.draft = {}; store.set("notebook", data);
    }
    if (any(data.draft)) { fill(data.draft); say("Your unfinished page is here."); }
    else if (todays) { fill(todays); say("Today’s page is saved. You can keep writing."); }
    render();

    /* one prompt at a time on screen. Phones step through all six fields; wide screens
       step through the five prompts and keep the recognition log in view under them.
       Print and no-JS keep every field. */
    (function stepper() {
      var items = $$(".prompts .prompt", form).concat($$(".notebook__log", form));
      var logBox = $(".notebook__log", form), promptsBox = $(".prompts", form), wide = mq("(min-width: 60.0625em)");
      if (items.length !== fields.length || !logBox || !promptsBox) return;
      items.forEach(function (it) { it.classList.add("nb-item"); });
      var box = doc.createElement("div");
      box.className = "nb-steps";
      box.innerHTML = '<p class="label nb-step" aria-live="polite">Prompt 1 of 5</p><span class="nb-dots" aria-hidden="true"><i></i><i></i><i></i><i></i><i></i><i></i></span><button class="textbtn" type="button" data-nb="-1">Back</button><button class="btn btn--small btn--ghost" type="button" data-nb="1">Next</button>';
      function place() {
        if (wide.matches) promptsBox.parentNode.insertBefore(box, promptsBox.nextSibling);
        else logBox.parentNode.insertBefore(box, logBox.nextSibling);
      }
      function last() { return wide.matches ? items.length - 2 : items.length - 1; }
      place();
      form.classList.add("is-stepped");
      var label = $(".nb-step", box), dots = $$(".nb-dots i", box), back = $("[data-nb='-1']", box), next = $("[data-nb='1']", box), at = 0;
      function paintDots() { fields.forEach(function (f, i) { if (dots[i]) dots[i].classList.toggle("is-filled", !!(form.elements[f].value || "").trim()); }); }
      function show(k, focus) {
        at = Math.max(0, Math.min(last(), k));
        items.forEach(function (it, i) { it.classList.toggle("is-current", i === at); });
        dots.forEach(function (d, i) { d.classList.toggle("is-current", i === at); });
        var ta = $("textarea", items[at]);
        grow(ta); /* a field under display:none could not be measured */
        label.textContent = at === items.length - 1 ? "The recognition log · p. 30" : "Prompt " + (at + 1) + " of " + (items.length - 1);
        back.disabled = at === 0; next.disabled = at === last();
        if (focus && ta) ta.focus();
      }
      box.addEventListener("click", function (ev) {
        var b = ev.target.closest && ev.target.closest("[data-nb]");
        if (!b || b.disabled) return;
        show(at + (+b.getAttribute("data-nb")), true);
      });
      form.addEventListener("input", paintDots);
      stepTo = function (k) { show(k, false); paintDots(); };
      var onWide = function () { place(); show(at, false); };
      if (wide.addEventListener) wide.addEventListener("change", onWide); else if (wide.addListener) wide.addListener(onWide);
      show(0, false); paintDots();
    })();

    var draftTimer = 0;
    form.addEventListener("input", function (ev) {
      if (ev.target && ev.target.tagName === "TEXTAREA") grow(ev.target);
      clearTimeout(draftTimer);
      draftTimer = setTimeout(function () {
        var v = values();
        data.draft = sameAs(entryFor(todayISO()), v) ? {} : v;
        if (any(data.draft)) data.draft.date = todayISO();
        store.set("notebook", data);
      }, 500);
    });
    window.addEventListener("resize", function () { fields.forEach(function (f) { grow(form.elements[f]); }); });
    form.addEventListener("submit", function (ev) {
      ev.preventDefault();
      clearTimeout(draftTimer);
      var v = values();
      if (!any(v)) { say("Write a line first."); if (stepTo) stepTo(0); form.elements.p1.focus(); return; }
      v.date = todayISO();
      data.entries = data.entries.filter(function (en) { return en.date !== v.date; });
      data.entries.push(v);
      if (data.entries.length > 400) data.entries = data.entries.slice(-400);
      data.draft = {};
      if (store.set("notebook", data)) { say("Saved on this device, " + niceDate(v.date) + "."); track("fieldwork_save", {}); savedMoment(); }
      else say("This browser would not save the page. Download or print it before you leave.");
      render();
    });
    $("#nb-clear").addEventListener("click", function () {
      if (any(values()) && !window.confirm("Clear what is written on this page? Saved earlier pages stay.")) return;
      fill({}); data.draft = {}; store.set("notebook", data); say("Page cleared."); if (stepTo) stepTo(0); form.elements.p1.focus();
    });
    $("#nb-print").addEventListener("click", function () { printOnly("print-notebook"); });
    $("#nb-download").addEventListener("click", function () {
      var all = data.entries.slice(), v = values();
      if (any(v) && !sameAs(entryFor(todayISO()), v)) { v.date = todayISO() + " (unsaved)"; all.push(v); }
      if (!all.length) { say("There is nothing to download yet."); return; }
      var out = ["THE PATH TO GREATNESS", "Field work, Level I: The Daily Archaeological Dig", "D. Antione Dixon. " + SITE, ""];
      all.sort(function (a, b) { return a.date < b.date ? -1 : 1; }).forEach(function (en) {
        out.push("----------------------------------------", en.date, "");
        fields.forEach(function (f) { if (en[f]) out.push(PROMPTS[f], en[f], ""); });
      });
      var blob = new Blob([out.join("\r\n")], { type: "text/plain;charset=utf-8" });
      var url = URL.createObjectURL(blob), a = doc.createElement("a");
      a.href = url; a.download = "path-to-greatness-field-notebook.txt"; doc.body.appendChild(a); a.click(); a.remove();
      setTimeout(function () { URL.revokeObjectURL(url); }, 4000);
      say("Notebook downloaded.");
    });
  });

  /* ==========================================================================
     The summit: thirty days, five phases, three sittings a day
     ========================================================================== */
  var PHASES = [null,
    { name: "The Mirror", first: 1 }, { name: "Archaeology", first: 7 }, { name: "Integration", first: 13 },
    { name: "Expression", first: 19 }, { name: "Multiplication", first: 25 }];
  /* [title, practice in one line, printed page]. Titles and wording follow the Elevated Edition, pp. 306-313.
     Days 1, 13 and 19 have no printed day heading there, so each carries the name of its practice. */
  var DAYS = [null,
    ["The Completeness Inventory", "Morning: rate the five statements in the Completeness Inventory near the top of this page and keep the total as your baseline. At two in the afternoon, ask what you are seeking that you might already have. Evening: write your Day 1 Declaration.", 306],
    ["The Recognition Practices", "The “Already Am” Inventory: list ten things you can do without conscious effort. Tonight, finish the sentence “Today I sought ___ but discovered I already had ___.”", 307],
    ["The Recognition Practices", "The “Already Am” Inventory again: ten things you can do without conscious effort. When you catch yourself wanting, pause and ask if you already have it in a form you have not recognized.", 307],
    ["The Mirror Deepens", "Add the Body Scan for Completeness to the morning: hand on heart, hand on stomach, hand on head.", 307],
    ["The Mirror Deepens", "The Body Scan for Completeness again. Keep the midday check and the evening sentence.", 307],
    ["Phase 1 Integration", "Weekly assessment: how many times did you catch yourself seeking, and how many times did you recognize having? Milestone: one hour without seeking validation.", "307–308"],
    ["Identifying Buried Treasure", "Draw your Buried Treasure Map: a natural talent you downplay, a childhood passion you abandoned, an effortless skill you take for granted.", 308],
    ["The Excavation", "The 10% Expression Experiment: choose one buried quality and express it at ten percent intensity today.", 308],
    ["The Excavation", "The 10% Expression Experiment again. The book’s note: resistance is your treasure map.", 308],
    ["Shadow Recognition", "The Trigger-to-Treasure Process: notice what irritates you in others, find where that quality lives in you, and express it consciously today.", 309],
    ["Shadow Recognition", "The Trigger-to-Treasure Process again. Find it in you, even at 1%.", 309],
    ["Phase 2 Integration", "Weekly assessment: buried qualities discovered, shadows recognized as gold. Milestone: did you express one buried quality publicly?", 309],
    ["The Morning Declaration", "Complete the sentence “I am both ___ AND ___.” Then show both qualities in one conversation today.", 309],
    ["The Peace Protocol", "When you are triggered, use the S.T.O.P. Method: Stop, Time, Observe, Peace. Three breaths at the end.", "309–310"],
    ["The Peace Protocol", "S.T.O.P. again. The book’s measure is how long it takes you to get from trigger back to peace.", 310],
    ["The Completeness Conversations", "Have one honest conversation using the Kind Truth Framework: recognition, truth, vision.", 310],
    ["The Completeness Conversations", "The Kind Truth Framework again: “I see you…”, “Here’s what I notice…”, “Here’s what’s possible…”", 310],
    ["Phase 3 Integration", "Weekly assessment: opposite qualities integrated, kind truths delivered. Milestone: can you hold opposing qualities without choosing?", 310],
    ["The Expression Arsenal", "Write ten ways to express your gift in under five minutes. Set a daily alarm and label it EXPRESS NOW.", "310–311"],
    ["The Gift Emergency", "When the alarm sounds, do one at once: write 100 words, create for five minutes, or teach someone one thing. No editing.", 311],
    ["The Gift Emergency", "The alarm again. No editing, just expression.", 311],
    ["The Generosity Overflow", "The Three Streams Practice: give something material, something emotional and something energetic today.", 311],
    ["The Generosity Overflow", "Three streams again: something material, genuine appreciation, good thoughts.", 311],
    ["Phase 4 Integration", "Weekly assessment: times expressed without editing, gifts given from overflow. Milestone: did you create something from joy, not need?", 311],
    ["The Ripple Recognition", "In every interaction today, hold one silent thought about the other person: “You’re already complete.” Notice what shifts.", 312],
    ["The Mentorship Moment", "Teach someone one thing you have recognized this month.", 312],
    ["The Mentorship Moment", "The book’s note for these two days: teaching deepens your own understanding.", 312],
    ["The Integration Mastery", "Live one full day as complete: no seeking, no becoming, just being. Document what happens.", 312],
    ["The Integration Mastery", "A second full day as complete: no seeking, no becoming, just being. Document what happens.", 312],
    ["The Celebration & Continuation", "Retake the inventory near the top of this page and compare it with Day 1. Then choose: repeat the thirty days, guide someone else through them, or design your own.", "312–313"]
  ];

  mod("summit", function () {
    var card = $("#tracker");
    if (!card) return;
    var daysBox = $("#days"), title = $("#phase-title"), dayLabel = $("#day-label"), dayTitle = $("#day-title"),
        dayText = $("#day-text"), dayWhere = $("#day-where"), fill = $("#tracker-fill"), countEl = $("#tracker-count"),
        sinceEl = $("#tracker-since"), checks = $$("input[data-slot]", card), phaseBtns = $$(".phase"), nextBtn = $("#phase-next");
    var state = store.get("tracker", null);
    if (!plain(state) || !plain(state.days)) state = { start: "", days: {} };
    if (typeof state.start !== "string") state.start = "";
    var phase = 1, day = 1;

    function slots(d) { var s = state.days[d]; return Array.isArray(s) && s.length === 3 ? s : [0, 0, 0]; }
    function doneCount(d) { return slots(d).reduce(function (a, b) { return a + (b ? 1 : 0); }, 0); }
    function completeDays() { var n = 0; for (var d = 1; d <= 30; d++) if (doneCount(d) === 3) n++; return n; }
    function firstOpenDay() { for (var d = 1; d <= 30; d++) if (doneCount(d) < 3) return d; return 30; }
    function phaseOf(d) { return Math.min(5, Math.floor((d - 1) / 6) + 1); }

    function renderDays() {
      daysBox.textContent = "";
      var first = PHASES[phase].first;
      for (var d = first; d < first + 6; d++) {
        var b = doc.createElement("button"), n = doneCount(d);
        b.type = "button"; b.className = "day" + (n === 3 ? " is-done" : n ? " is-part" : "");
        if (n && n < 3) b.style.setProperty("--fill", Math.round(n / 3 * 100) + "%");
        b.textContent = String(d);
        b.setAttribute("data-day", String(d));
        b.setAttribute("aria-label", "Day " + d + ", " + (n === 3 ? "complete" : n + " of 3 sittings done"));
        if (d === day) b.setAttribute("aria-current", "true");
        daysBox.appendChild(b);
      }
    }
    function renderDay() {
      var D = DAYS[day];
      dayLabel.textContent = "Day " + day + " · " + PHASES[phaseOf(day)].name;
      dayTitle.textContent = D[0]; dayText.textContent = D[1];
      dayWhere.textContent = "In the book: " + (typeof D[2] === "string" ? "pp. " : "p. ") + D[2] + ".";
      var s = slots(day);
      checks.forEach(function (c, i) { c.checked = !!s[i]; });
    }
    function renderMeta() {
      var n = completeDays();
      fill.style.transform = "scaleX(" + (n / 30).toFixed(4) + ")";
      countEl.textContent = n + " of 30 days complete";
      sinceEl.textContent = state.start ? "Day one: " + niceDate(state.start) : "";
      $$("[data-tally]").forEach(function (el) {
        var p = +el.getAttribute("data-tally"), first = PHASES[p].first, k = 0;
        for (var d = first; d < first + 6; d++) if (doneCount(d) === 3) k++;
        el.textContent = k ? k + " of 6 days" : "";
      });
    }
    function setPhase(p, keepDay) {
      phase = p;
      phaseBtns.forEach(function (b) { b.setAttribute("aria-pressed", String(+b.getAttribute("data-phase") === p)); });
      title.textContent = "Phase " + p + " · " + PHASES[p].name;
      if (nextBtn) { nextBtn.hidden = p >= 5; if (p < 5) nextBtn.textContent = "Next: Phase " + (p + 1) + " · " + PHASES[p + 1].name; }
      if (!keepDay) {
        day = PHASES[p].first;
        for (var d = PHASES[p].first; d < PHASES[p].first + 6; d++) { if (doneCount(d) < 3) { day = d; break; } }
      }
      renderDays(); renderDay();
    }
    phaseBtns.forEach(function (b) {
      b.addEventListener("click", function () {
        setPhase(+b.getAttribute("data-phase"));
        if (mq("(max-width: 60em)").matches) card.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "start" });
      });
    });
    daysBox.addEventListener("click", function (ev) {
      var b = ev.target.closest("[data-day]");
      if (!b) return;
      day = +b.getAttribute("data-day"); renderDays(); renderDay();
      var again = $("[data-day='" + day + "']", daysBox); if (again) again.focus();
    });
    checks.forEach(function (c) {
      c.addEventListener("change", function () {
        var s = slots(day).slice(), was = doneCount(day);
        s[+c.getAttribute("data-slot")] = c.checked ? 1 : 0;
        state.days[day] = s;
        if (!state.start && c.checked) state.start = todayISO();
        if (!store.set("tracker", state)) toast("Not saved: storage is unavailable", 4000);
        renderDays(); renderMeta();
        if (was < 3 && doneCount(day) === 3) {
          var arrivedEl = $("[data-day='" + day + "']", daysBox);
          if (arrivedEl && !reduce) arrivedEl.classList.add("is-arriving");
          track("tracker_day", { day: day });
          toast(day === 30 ? "Thirty days. The summit." : "Day " + day + " complete");
        }
      });
    });
    if (nextBtn) nextBtn.addEventListener("click", function () {
      if (phase >= 5) return;
      setPhase(phase + 1);
      var cur = $("[aria-current='true']", daysBox); if (cur) cur.focus({ preventScroll: true });
      if (mq("(max-width: 60em)").matches) card.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "start" });
    });
    $("#tracker-reset").addEventListener("click", function () {
      if (!completeDays() && !state.start) return;
      if (!window.confirm("Start the thirty days over? Your ticks on this device will be cleared.")) return;
      state = { start: "", days: {} }; store.set("tracker", state);
      setPhase(1); renderMeta(); toast("Tracker reset to Day 1");
    });
    /* open on the first unfinished day */
    day = firstOpenDay(); setPhase(phaseOf(day), true); renderMeta();
    /* the pledge shares the start date */
    window.__ptgTracker = {
      begin: function (iso) { if (!state.start) { state.start = iso; store.set("tracker", state); renderMeta(); } }
    };
  });

  /* ---- the Completeness Inventory */
  mod("inventory", function () {
    var form = $("#inventory");
    if (!form) return;
    var ids = ["i1", "i2", "i3", "i4", "i5"], total = $("#inv-total"), saved = $("#inv-saved");
    var data = store.get("inventory", {});
    if (!plain(data)) data = {};
    ["d1", "d30"].forEach(function (k) { if (!plain(data[k]) || !isFinite(+data[k].score)) delete data[k]; });
    function vals() { return ids.map(function (id) { return +form.elements[id].value || 1; }); }
    function sum() { return vals().reduce(function (a, b) { return a + b; }, 0); }
    function flip(el) { if (reduce || !el) return; el.classList.remove("is-flip"); void el.offsetWidth; el.classList.add("is-flip"); }
    function paint() {
      ids.forEach(function (id, i) {
        var o = $("#o" + (i + 1)), el = form.elements[id], v = el.value;
        if (o && o.textContent !== v) { o.textContent = v; flip(o); }
        el.setAttribute("aria-valuetext", v + " of 10");
        el.style.setProperty("--v", ((v - 1) / 9 * 100).toFixed(1) + "%");
      });
      var t = String(sum());
      if (total.textContent !== t) { total.textContent = t; flip(total.parentNode); }
    }
    function report() {
      var s30 = $("#inv-save30");
      if (s30) s30.hidden = !data.d1;
      var parts = [];
      if (data.d1) parts.push("Day 1: <b>" + (+data.d1.score) + "/50</b> (" + (niceDate(data.d1.date) || "") + ")");
      if (data.d30) parts.push("Day 30: <b>" + (+data.d30.score) + "/50</b> (" + (niceDate(data.d30.date) || "") + ")");
      var html = parts.join(" → ");
      if (data.d1 && data.d30) {
        var diff = data.d30.score - data.d1.score;
        html += diff < 0 ? ". " + Math.abs(diff) + " points less seeking." : diff > 0 ? ". " + diff + " points more seeking." : ". No change in the total.";
      }
      saved.innerHTML = html;
      /* the tracker card further down carries the Day 1 score back to the reader */
      var mirror = $("#inv-mirror");
      if (mirror) {
        mirror.hidden = !data.d1;
        mirror.innerHTML = data.d1 ? "Your Day 1 inventory: <b>" + (+data.d1.score) + "/50</b>. On Day 30, <a href=\"#inventory\">rate the five statements again</a>." : "";
      }
    }
    function keep(which) {
      data[which] = { score: sum(), vals: vals(), date: todayISO() };
      if (!store.set("inventory", data)) { saved.textContent = "This browser would not save the score. Write it down: " + sum() + "/50."; return; }
      report(); toast(which === "d1" ? "Day 1 score saved" : "Day 30 score saved"); track("inventory_save", { which: which });
      if (which === "d1") { var nx = $("#inv-next"); if (nx) { nx.hidden = false; doc.dispatchEvent(new CustomEvent("ptg:ask")); } }
    }
    if (data.d1 && Array.isArray(data.d1.vals) && data.d1.vals.length === 5) ids.forEach(function (id, i) { var v = +data.d1.vals[i]; if (v >= 1 && v <= 10) form.elements[id].value = String(Math.round(v)); });
    form.addEventListener("input", paint);
    form.addEventListener("submit", function (ev) { ev.preventDefault(); keep("d1"); });
    $("#inv-save30").addEventListener("click", function () {
      /* Day 30 is a retake a month on; an early save is allowed, but only on purpose */
      var d1 = data.d1 && Date.parse(data.d1.date + "T00:00:00"), days = d1 ? Math.round((Date.now() - d1) / 864e5) : 0;
      if (d1 && days < 29 && !window.confirm("Your Day 1 score is from " + (days < 1 ? "today" : days === 1 ? "yesterday" : days + " days ago") + ". The book has you retake it on Day 30. Save this as Day 30 anyway?")) return;
      keep("d30");
    });
    paint(); report();
  });

  /* ---- the pledge */
  mod("pledge", function () {
    var box = $("#pledge");
    if (!box) return;
    var name = $("#pledge-name"), date = $("#pledge-date"), btn = $("#pledge-sign");
    var data = store.get("pledge", null);
    if (!plain(data) || typeof data.name !== "string" || typeof data.date !== "string") data = null;
    function render() {
      var signed = !!(data && data.name && data.date);
      box.classList.toggle("is-signed", signed);
      if (signed) { name.value = data.name; date.textContent = niceDate(data.date) || data.date; btn.textContent = "Signed. Sign again"; }
      else { date.innerHTML = "&nbsp;"; btn.textContent = "Sign and begin"; }
    }
    btn.addEventListener("click", function () {
      var v = (name.value || "").trim().slice(0, 80);
      if (!v) { toast("Sign your name first", 4000); name.focus(); return; }
      data = { name: v, date: todayISO() };
      store.set("pledge", data);
      if (window.__ptgTracker) window.__ptgTracker.begin(data.date);
      render(); track("pledge_sign", {});
      doc.dispatchEvent(new CustomEvent("ptg:ask"));
      if (!reduce) { box.classList.remove("is-stamping"); void box.offsetWidth; box.classList.add("is-stamping"); setTimeout(function () { box.classList.remove("is-stamping"); }, 1400); }
    });
    name.addEventListener("keydown", function (ev) { if (ev.key === "Enter") { ev.preventDefault(); btn.click(); } });
    $("#pledge-print").addEventListener("click", function () { printOnly("print-pledge"); });
    render();
  });

  /* ==========================================================================
     Getting the book: buy buttons when it is out, the first-readers form before
     ========================================================================== */
  mod("get", function () {
    var form = $("#signup"), buy = $("#buy"), status = $("#signup-status"), lede = $("#get-lede");
    var LABELS = { hardcover: "Hardcover", paperback: "Paperback", ebook: "E-book", audiobook: "Audiobook", direct: "Buy direct" };
    var links = cfg.BUY_LINKS || {}, live = [];
    Object.keys(LABELS).forEach(function (k) { if (isUrl(links[k])) live.push(k); });
    var to = (cfg.CONTACT_EMAIL && cfg.CONTACT_EMAIL.indexOf("@") > 0) ? cfg.CONTACT_EMAIL : "eatmediatv@gmail.com";

    if (cfg.STATUS === "available" && live.length && buy) {
      live.forEach(function (k, i) {
        var a = doc.createElement("a");
        a.className = "btn " + (i === 0 ? "btn--light" : "btn--ghost");
        a.href = links[k]; a.rel = "noopener"; a.textContent = LABELS[k];
        a.setAttribute("data-cta", "buy-" + k);
        buy.appendChild(a);
      });
      buy.hidden = false;
      if (form) form.hidden = true;
      if (lede) lede.textContent = "The Elevated Edition is out. Choose a format.";
      var h = $("#get-title"); if (h) h.textContent = "Get the book";
      var lab = $("#get-label"); if (lab) lab.textContent = "Available now";
      $$("[data-release-note]").forEach(function (el) { el.textContent = "Available now."; });
      $$("[data-cta='hero'],[data-cta='excerpt'],[data-cta='nav'],[data-cta='dock'],.ask a[data-cta]").forEach(function (a) { a.textContent = "Get the book"; });
      $$("[data-when='available']").forEach(function (el) { el.hidden = false; });
      return;
    }
    if (!form) return;

    var email = form.elements.email, trap = form.elements.ptg_hp || form.elements.website, btn = $("#signup-btn"), label = $(".btn__label", btn);
    var signed = $("#signed"), signedEmail = $("#signed-email"), dlg = $("#thanks"), fine = $("#signup-fine"), promise = $("#get-promise");
    var LEDE = "";
    var opened = Date.now(), busy = false, endpoint = isUrl(cfg.FORM_ENDPOINT) ? cfg.FORM_ENDPOINT : "";
    email.addEventListener("focus", function () { if (!opened) opened = Date.now(); }, { once: true });
    email.addEventListener("input", function () {
      email.removeAttribute("aria-invalid");
      var k = status.getAttribute("data-kind");
      if (k === "error" || k === "hint") { status.textContent = ""; status.setAttribute("data-kind", ""); }
      if (k === "hint") hinted = "";
    });

    /* where this visit came from: first-touch tags are kept for the session */
    function tags() {
      var keys = ["utm_source", "utm_medium", "utm_campaign", "utm_content"], out = {}, q;
      try { q = new URLSearchParams(location.search); } catch (e) { q = null; }
      var saved = {};
      try { saved = JSON.parse(sessionStorage.getItem("ptg.v1.utm") || "{}") || {}; } catch (e) { saved = {}; }
      keys.forEach(function (k) { var v = q && q.get(k); out[k] = v ? v.slice(0, 80) : (saved[k] || ""); });
      try { if (q && keys.some(function (k) { return q.get(k); })) sessionStorage.setItem("ptg.v1.utm", JSON.stringify(out)); } catch (e) { /* storage off */ }
      return out;
    }
    tags();

    function say(msg, kind) { status.textContent = msg; status.setAttribute("data-kind", kind || ""); }
    function setBusy(on) {
      busy = on; btn.disabled = on; btn.classList.toggle("is-busy", on);
      label.textContent = on ? "Adding you…" : "Tell me when it’s out";
    }
    function invalid() {
      email.setAttribute("aria-invalid", "true");
      say("That email address does not look complete.", "error");
      email.focus();
    }
    function showSigned(addr) {
      root.classList.add("is-joined");
      if (!signed) return;
      signedEmail.textContent = addr; signed.hidden = false; form.hidden = true;
      if (lede) lede.textContent = "Your welcome note has Level I’s threshold question. You will hear again when the book is out.";
      if (promise) promise.hidden = true;
    }
    var known = store.get("signedup", null);
    if (plain(known) && typeof known.email === "string" && known.email.indexOf("@") > 0) showSigned(known.email);
    var change = $("#signed-change");
    if (change) change.addEventListener("click", function () {
      signed.hidden = true; form.hidden = false; email.value = ""; email.focus();
      if (lede) lede.textContent = LEDE;
      if (promise && endpoint) promise.hidden = false;
    });

    /* ---- the thank-you dialog */
    var lastFocus = null, leftByLink = false;
    function thank(addr, already) {
      $("#thanks-email") && ($("#thanks-email").textContent = addr);
      var title = $("#thanks-title"), body = $("#thanks-body");
      if (already) {
        title.textContent = "You’re already on the list.";
        body.textContent = addr + " is signed up. You will hear when the book is out.";
      } else {
        title.textContent = "You’re on the list.";
        body.innerHTML = "";
        body.appendChild(doc.createTextNode("A welcome note from D. Antione Dixon is on its way to "));
        var b = doc.createElement("b"); b.textContent = addr; body.appendChild(b);
        body.appendChild(doc.createTextNode(", with Level I’s threshold question and field work. If you don’t find it in your inbox, look in Promotions or Spam."));
      }
      var sheet = $("#join");
      if (sheet && sheet.open) sheet.close();
      if (!dlg || typeof dlg.showModal !== "function") { say(already ? addr + " is already on the list." : "You’re on the list. A welcome note is on its way to " + addr + ".", "ok"); return; }
      lastFocus = doc.activeElement;
      dlg.classList.remove("is-shown");
      root.style.overflow = "hidden";
      dlg.showModal();
      requestAnimationFrame(function () { requestAnimationFrame(function () { dlg.classList.add("is-shown"); }); });
      var first = $(".thanks__actions .btn", dlg); if (first) first.focus();
    }
    if (dlg) {
      dlg.addEventListener("click", function (ev) {
        var c = ev.target.closest && ev.target.closest("[data-close]");
        if (ev.target === dlg || c) { leftByLink = !!(c && c.tagName === "A"); dlg.close(); }
      });
      dlg.addEventListener("close", function () {
        root.style.overflow = ""; dlg.classList.remove("is-shown");
        if (leftByLink) { leftByLink = false; return; }
        var S = window.__ptgSignup || {}, o = S.opener; S.opener = null;
        var target = o && o.getClientRects().length ? o : (signed && !signed.hidden ? change : lastFocus);
        if (target && target.focus && !(target.closest && target.closest("dialog"))) {
          try { target.focus({ preventScroll: true }); } catch (e) { target.focus(); }
        }
      });
      var share = $("#thanks-share");
      if (share) share.addEventListener("click", function () {
        var data = { title: "The Path to Greatness", text: "The Path to Greatness by D. Antione Dixon", url: SITE + "?utm_source=share&utm_medium=referral&utm_campaign=ptg_prelaunch" };
        if (navigator.share) { navigator.share(data).catch(function () { /* dismissed */ }); return; }
        copyText(data.url).then(function () { toast("Link copied"); }, function () { toast(SITE); });
      });
    }

    function payload(addr) {
      var t = tags();
      return {
        email: addr.toLowerCase(), website: trap ? trap.value : "", elapsed: Date.now() - opened,
        page: location.pathname, referrer: doc.referrer || "",
        utm_source: t.utm_source, utm_medium: t.utm_medium, utm_campaign: t.utm_campaign, utm_content: t.utm_content,
        source: form.getAttribute("data-source") || "page form",
        consent: "News about The Path to Greatness; unsubscribe any time"
      };
    }
    function post(body) {
      /* text/plain keeps this a simple request: no CORS preflight, which Apps Script cannot answer */
      var ctl = window.AbortController ? new AbortController() : null;
      var timer = setTimeout(function () { if (ctl) ctl.abort(); }, 15000);
      /* Only a reply the page can read counts as saved, so nobody is thanked for a sign-up that
         never reached the sheet. A refused or unreadable reply reads "did not go through". A lost
         connection, a timeout, or a deployment that redirects to a Google sign-in page (the
         browser blocks it) reads "could not confirm", which stays true in every one of those cases. */
      return fetch(endpoint, { method: "POST", body: JSON.stringify(body), redirect: "follow", signal: ctl ? ctl.signal : undefined })
        .then(function (r) {
          if (!r.ok) { clearTimeout(timer); throw new Error("http " + r.status); }
          return r.json().then(function (j) { clearTimeout(timer); return j; }, function (e) {
            clearTimeout(timer);
            throw (e && e.name === "AbortError") ? e : new Error("unreadable");
          });
        })
        .catch(function (err) { clearTimeout(timer); throw err; });
    }

    var DOMAINS = ["gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com", "aol.com", "me.com", "live.com", "msn.com", "comcast.net", "protonmail.com"];
    function dist(a, b) {
      var d = [], i, j;
      for (i = 0; i <= a.length; i++) { d[i] = [i]; }
      for (j = 0; j <= b.length; j++) d[0][j] = j;
      for (i = 1; i <= a.length; i++) for (j = 1; j <= b.length; j++) {
        var c = a[i - 1] === b[j - 1] ? 0 : 1;
        d[i][j] = Math.min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + c);
        if (i > 1 && j > 1 && a[i - 1] === b[j - 2] && a[i - 2] === b[j - 1]) d[i][j] = Math.min(d[i][j], d[i - 2][j - 2] + 1);
      }
      return d[a.length][b.length];
    }
    function suggest(addr) {
      var at = addr.lastIndexOf("@");
      if (at < 1) return "";
      var dom = addr.slice(at + 1).toLowerCase(), best = "", bd = 3;
      if (DOMAINS.indexOf(dom) >= 0) return "";
      DOMAINS.forEach(function (d) { var k = dist(dom, d); if (k < bd) { bd = k; best = d; } });
      return best && bd <= 2 ? addr.slice(0, at + 1) + best : "";
    }
    var hinted = "";
    function offer(addr, onSubmit) {
      var fix = suggest(addr);
      if (!fix) return false;
      status.textContent = "Did you mean ";
      status.setAttribute("data-kind", "hint");
      var b = doc.createElement("button");
      b.type = "button"; b.className = "textbtn"; b.textContent = fix;
      b.addEventListener("click", function () { email.value = fix; say("", ""); email.focus(); });
      status.appendChild(b); status.appendChild(doc.createTextNode(onSubmit ? "? Press the button again to send it as typed." : "?"));
      return true;
    }
    email.addEventListener("blur", function () { var v = (email.value || "").trim(); if (v && !status.getAttribute("data-kind")) offer(v); });

    form.addEventListener("submit", function (ev) {
      ev.preventDefault();
      if (busy) return;
      var addr = (email.value || "").trim();
      if (!addr || !email.checkValidity() || !/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(addr)) { invalid(); return; }
      /* a likely typo stops the first press only; the second press sends the address as typed */
      if (addr !== hinted && suggest(addr)) { hinted = addr; offer(addr, true); return; }

      if (!endpoint) {
        /* no endpoint configured yet: hand the visitor a ready-made email */
        var subject = "The Path to Greatness: tell me when it is out";
        var mbody = "Please tell me when The Path to Greatness is out.\n\nMy address: " + addr + "\n";
        say("Your mail app should open with a note ready to send. Press send and you will hear back when the book is out.", "ok");
        try { status.scrollIntoView({ block: "nearest", behavior: reduce ? "auto" : "smooth" }); } catch (e) { /* old browser */ }
        track("lead", { method: "mailto" });
        window.location.href = "mailto:" + to + "?subject=" + encodeURIComponent(subject) + "&body=" + encodeURIComponent(mbody);
        return;
      }
      if (trap && trap.value) { thank(addr, false); return; }

      say("", ""); setBusy(true);
      post(payload(addr)).then(function (res) {
        setBusy(false);
        if (res && res.ok) {
          store.set("signedup", { email: addr.toLowerCase(), date: todayISO() });
          track("lead", { method: "sheet", result: res.status || "added" });
          form.reset();
          showSigned(addr.toLowerCase());
          thank(addr.toLowerCase(), res.status === "already");
          return;
        }
        if (res && res.error === "invalid_email") { invalid(); return; }
        say("That did not go through. Please try again in a minute. If it keeps failing, write to " + to + ".", "error");
      }, function (err) {
        setBusy(false);
        if (err && /^(http|unreadable)/.test(err.message || "")) {
          say("That did not go through. Please try again in a minute. If it keeps failing, write to " + to + ".", "error");
          return;
        }
        /* a lost connection or a slow reply: the address may have been saved, and a second try is harmless */
        say("We could not confirm that your address was saved. Please try again in a minute; signing up twice does no harm. If it keeps failing, write to " + to + ".", "error");
      });
    });

    /* until an endpoint is configured, the words match the mail-app fallback */
    if (!endpoint) {
      label.textContent = "Open my email";
      if (lede) lede.textContent = "You will get one reply when the book is out, saying where to buy it.";
      if (fine) fine.textContent = "This opens your own mail app with a note to " + to + ". Nothing is sent until you press send.";
      if (signed && !signed.hidden) { signed.hidden = true; form.hidden = false; }
      if (promise) promise.hidden = true;
      root.classList.remove("is-joined");
    }
    window.__ptgSignup = { live: !!endpoint, form: form, email: email };
  });

  /* ==========================================================================
     Phones: a sign-up button raises the same form in a sheet, keyboard up,
     instead of a jump to the foot of a long page. Desktop: the jump lands
     with the cursor in the field.
     ========================================================================== */
  mod("join", function () {
    var S = window.__ptgSignup, sheet = $("#join"), slot = $("#join-slot");
    function focusLater() { setTimeout(function () { try { S.email.focus({ preventScroll: true }); } catch (e) { S.email.focus(); } }, reduce ? 0 : 900); }
    if (S && S.email && (!S.live || !sheet || !slot || typeof sheet.showModal !== "function")) {
      /* no sheet (mail-app mode, or no dialog support): let the anchor scroll, then put the cursor in the field */
      doc.addEventListener("click", function (ev) {
        var a = ev.target.closest && ev.target.closest("a[data-cta][href='#get']");
        if (!a || root.classList.contains("is-joined") || ev.defaultPrevented || ev.metaKey || ev.ctrlKey || !S.form || S.form.hidden) return;
        focusLater();
      });
      return;
    }
    if (!S || !sheet || !slot) return;
    var form = S.form, home = doc.createComment("signup"), opener = null;
    var SOURCES = { hero: "hero", nav: "menu", dock: "bar", excerpt: "excerpt", inventory: "inventory", fieldwork: "fieldwork", pledge: "pledge" };
    form.parentNode.insertBefore(home, form);
    function close() { if (sheet.open) sheet.close(); }
    sheet.addEventListener("click", function (ev) {
      if (ev.target === sheet || (ev.target.closest && ev.target.closest("[data-close]"))) close();
    });
    sheet.addEventListener("close", function () {
      home.parentNode.insertBefore(form, home.nextSibling);
      form.removeAttribute("data-source");
      var thanksOpen = !!($("#thanks") && $("#thanks").open);
      if (!thanksOpen) root.style.overflow = "";
      if (thanksOpen || !opener) return;
      /* a button inside the closed menu has no box: hand focus to the menu button instead */
      var to = opener.getClientRects().length ? opener : $("#menu-btn") || $("#get");
      if (to && to.focus) { try { to.focus({ preventScroll: true }); } catch (e) { to.focus(); } }
    });
    doc.addEventListener("click", function (ev) {
      var a = ev.target.closest && ev.target.closest("a[data-cta][href='#get']");
      if (!a || root.classList.contains("is-joined") || ev.defaultPrevented || ev.metaKey || ev.ctrlKey) return;
      var where = SOURCES[a.getAttribute("data-cta")] || a.getAttribute("data-cta");
      if (mq("(max-width: 60em)").matches) {
        ev.preventDefault();
        opener = a; S.opener = a;
        form.setAttribute("data-source", where);
        slot.appendChild(form);
        root.style.overflow = "hidden";
        sheet.showModal();
        S.email.focus();
        return;
      }
      /* wide screens: let the anchor scroll, then put the cursor in the field */
      form.setAttribute("data-source", where);
      focusLater();
    });
  });
})();
