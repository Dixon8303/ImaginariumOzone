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

  /* Kit (ConvertKit) form endpoint for the first-readers list, in the form
     https://app.kit.com/forms/XXXXXXX/subscriptions (posts "email_address").
     Empty = the form opens the visitor's own mail app instead. */
  FORM_ACTION: "",

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
  function toast(msg) {
    if (!toastEl) return;
    toastEl.textContent = msg;
    toastEl.classList.add("is-on");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { toastEl.classList.remove("is-on"); }, 2600);
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
  (function header() {
    var head = $("#head"), bar = $("#progress"), nav = $("#nav"), btn = $("#menu-btn"), dock = $("#dock");
    if (!head) return;
    var ticking = false;
    function update() {
      ticking = false;
      var y = window.scrollY || 0;
      head.classList.toggle("is-stuck", y > 24);
      var max = Math.max(1, doc.documentElement.scrollHeight - window.innerHeight);
      if (bar) bar.style.transform = "scaleX(" + Math.min(1, y / max).toFixed(4) + ")";
      if (dock) {
        var get = $("#get"), nearEnd = get && get.getBoundingClientRect().top < window.innerHeight * 0.9;
        dock.classList.toggle("is-on", y > window.innerHeight * 0.85 && !nearEnd);
      }
    }
    window.addEventListener("scroll", function () { if (!ticking) { ticking = true; requestAnimationFrame(update); } }, { passive: true });
    window.addEventListener("resize", update);
    update();

    function setMenu(open) {
      nav.classList.toggle("is-open", open);
      btn.setAttribute("aria-expanded", String(open));
      btn.setAttribute("aria-label", open ? "Close menu" : "Open menu");
      doc.body.style.overflow = open ? "hidden" : "";
    }
    if (btn && nav) {
      btn.addEventListener("click", function () { setMenu(!nav.classList.contains("is-open")); });
      nav.addEventListener("click", function (ev) { if (ev.target.closest("a")) setMenu(false); });
      doc.addEventListener("keydown", function (ev) {
        if (ev.key === "Escape" && nav.classList.contains("is-open")) { setMenu(false); btn.focus(); }
      });
      window.addEventListener("resize", function () { if (window.innerWidth > 1060) setMenu(false); });
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
  })();

  /* ==========================================================================
     Reveal on scroll. Content is visible by default; this only adds motion.
     ========================================================================== */
  (function reveal() {
    var items = $$(".rv");
    if (reduce || !("IntersectionObserver" in window)) { items.forEach(function (el) { el.classList.add("is-in"); }); return; }
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) { if (en.isIntersecting) { en.target.classList.add("is-in"); io.unobserve(en.target); } });
    }, { rootMargin: "0px 0px -8% 0px", threshold: 0.05 });
    items.forEach(function (el) { io.observe(el); });
    /* never leave anything hidden if the observer is slow to fire */
    setTimeout(function () { items.forEach(function (el) { if (el.getBoundingClientRect().top < window.innerHeight) el.classList.add("is-in"); }); }, 1200);
  })();

  /* ==========================================================================
     Hero: the mountain at blue hour, engraved once, then the route is walked.
     Virtual canvas 1500 x 790; the summit is at (966,119).
     ========================================================================== */
  (function heroArt() {
    var canvas = $("#ascent-art");
    if (!canvas || !canvas.getContext) return;
    var ctx = canvas.getContext("2d");
    if (!ctx) return;
    var base = doc.createElement("canvas"), bctx = base.getContext("2d");
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
      var dpr = Math.min(window.devicePixelRatio || 1, 1.75);
      c.width = Math.round(w * dpr); c.height = Math.round(h * dpr);
      var small = w < 780, scale = Math.max(w / 1500, h / 790);
      view = { dpr: dpr, scale: scale, tx: small ? w * 0.63 - 966 * scale : (w - 1500 * scale) * 0.62, ty: small ? h * 0.2 - 119 * scale : (h - 790 * scale) * 0.42 };
    }
    function useView(c2d) { c2d.setTransform(view.dpr * view.scale, 0, 0, view.dpr * view.scale, view.dpr * view.tx, view.dpr * view.ty); }

    function paintBase(w, h) {
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
      for (var i = 0; i < 700; i++) { var px = random() * 1900 - 100, py = yAt(fg, px) + random() * 59; pine(px, py, 2 + random() * 9, "#10141a"); }
      var dark = [[-900, 740], [-200, 710], [170, 687], [315, 717], [510, 650], [658, 690], [846, 618], [954, 653], [1064, 614], [1248, 674], [1403, 622], [1600, 660], [2500, 700]];
      ridge(dark, "#171c25", "#0e1116", 0.08, null);
      for (var j = 0; j < 360; j++) { var fx = random() * 1900 - 150; pine(fx, yAt(dark, fx) + random() * 22, 3 + random() * 12, "#0a0d11"); }
    }

    function frame(t) {
      /* t: 0 = base camp, 1 = summit reached */
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.drawImage(base, 0, 0);
      g = ctx; useView(g);
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
        var p = at(nt), camp = n === 0 || n === 3 || n === 7 || n === 12 || n === 13;
        g.beginPath(); g.arc(p[0], p[1], n === 13 ? 4.6 : camp ? 3.6 : 2.5, 0, 6.2832);
        g.fillStyle = n === 13 ? "#fbe6bf" : "#ecc88e"; g.fill();
        g.strokeStyle = "rgba(17,21,28,.9)"; g.lineWidth = 1.2; g.stroke();
      }
      if (t >= 1) { g.beginPath(); g.arc(966, 123, 9.5, 0, 6.2832); g.strokeStyle = "rgba(251,230,191,.55)"; g.lineWidth = 1; g.stroke(); }
      g.restore();
    }

    var walked = false, raf = 0, lastW = 0, lastH = 0;
    function paint(animate) {
      var w = canvas.clientWidth, h = canvas.clientHeight;
      if (!w || !h) return;
      if (w === lastW && Math.abs(h - lastH) < 90 && walked) return; /* mobile URL bar: do not repaint */
      lastW = w; lastH = h;
      cancelAnimationFrame(raf);
      paintBase(w, h);
      canvas.width = base.width; canvas.height = base.height;
      if (!animate || reduce || walked) { walked = true; frame(1); return; }
      var start = 0, dur = 2600;
      function step(now) {
        if (!start) start = now;
        var k = Math.min(1, (now - start) / dur), eased = 1 - Math.pow(1 - k, 3);
        frame(eased);
        if (k < 1) raf = requestAnimationFrame(step); else walked = true;
      }
      frame(0);
      raf = requestAnimationFrame(step);
    }
    var queued = 0;
    function queue() { if (queued) return; queued = requestAnimationFrame(function () { queued = 0; paint(false); }); }
    try { paint(true); } catch (e) { /* the CSS gradient behind the canvas remains */ }
    if ("ResizeObserver" in window) new ResizeObserver(queue).observe(canvas.parentElement);
    else window.addEventListener("resize", queue);
  })();

  /* ==========================================================================
     The ascent: twelve gates. One open at a time; deep links (#level-4) work.
     ========================================================================== */
  var LEVELS = [];
  try { LEVELS = JSON.parse($("#ptg-levels").textContent); } catch (e) { LEVELS = []; }

  (function ascent() {
    var wrap = $("#levels");
    if (!wrap) return;
    var btns = $$(".lvl__btn", wrap), panels = $$(".lvl__panel", wrap);
    var wide = window.matchMedia("(min-width: 961px)");
    var current = 0;
    function open(n, opts) {
      opts = opts || {};
      var same = current === n;
      btns.forEach(function (b, i) {
        var on = i + 1 === n && !(same && !wide.matches && !opts.force);
        b.setAttribute("aria-expanded", String(on));
        panels[i].classList.toggle("is-open", on);
      });
      current = (same && !wide.matches && !opts.force) ? 0 : n;
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
      if (m && +m[1] >= 1 && +m[1] <= btns.length) { open(+m[1], { force: true }); return true; }
      return false;
    }
    if (!fromHash()) open(1, { force: true });
    window.addEventListener("hashchange", fromHash);
    var onWide = function () { if (wide.matches && !current) open(1, { force: true }); };
    if (wide.addEventListener) wide.addEventListener("change", onWide); else if (wide.addListener) wide.addListener(onWide);
  })();

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
    x.save(); x.translate(W / 2 - 60, 230); x.scale(5, 5);
    x.beginPath(); (MARKS[L.mk] || MARKS.mountain)(x);
    x.strokeStyle = "#919eb2"; x.lineWidth = 1.2; x.lineCap = "round"; x.lineJoin = "round"; x.stroke(); x.restore();
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
  doc.addEventListener("click", function (ev) {
    var t = ev.target.closest && ev.target.closest("[data-copy],[data-card]");
    if (!t) return;
    var n = +(t.getAttribute("data-copy") || t.getAttribute("data-card")), L = levelBy(n);
    if (!L) return;
    if (t.hasAttribute("data-copy")) {
      copyText("“" + L.epi + "” — D. Antione Dixon, The Path to Greatness (Level " + L.num + ")\n" + SITE + "#level-" + n)
        .then(function () { toast("Line copied"); }, function () { toast("Copy is not available here"); });
      track("quote_copy", { level: n });
      return;
    }
    var make = function () {
      var c = drawCard(L), name = "path-to-greatness-level-" + L.num.toLowerCase() + ".png";
      var done = function (blob) {
        if (!blob) { toast("Could not make the card"); return; }
        var file = null;
        try { file = new File([blob], name, { type: "image/png" }); } catch (e) { file = null; }
        if (file && navigator.canShare && navigator.canShare({ files: [file] }) && window.matchMedia("(pointer: coarse)").matches) {
          navigator.share({ files: [file], title: "The Path to Greatness" }).catch(function () { /* dismissed */ });
          return;
        }
        var url = URL.createObjectURL(blob), a = doc.createElement("a");
        a.href = url; a.download = name; doc.body.appendChild(a); a.click(); a.remove();
        setTimeout(function () { URL.revokeObjectURL(url); }, 4000);
        toast("Card saved");
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
  (function look() {
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
    function show(k) {
      i = (k + pages.length) % pages.length;
      var p = pages[i];
      img.src = "assets/img/look/" + p.s + "-960.webp";
      img.alt = p.a; cap.textContent = p.c; count.textContent = (i + 1) + " / " + pages.length;
    }
    $$("[data-look]").forEach(function (b) {
      b.addEventListener("click", function () { opener = b; show(+b.getAttribute("data-look")); dlg.showModal(); track("look_inside", { page: pages[i].s }); });
    });
    $("#lb-close").addEventListener("click", function () { dlg.close(); });
    $("#lb-prev").addEventListener("click", function () { show(i - 1); });
    $("#lb-next").addEventListener("click", function () { show(i + 1); });
    dlg.addEventListener("click", function (ev) { if (ev.target === dlg || ev.target.classList.contains("lightbox__stage") || ev.target.classList.contains("lightbox__in")) dlg.close(); });
    dlg.addEventListener("keydown", function (ev) {
      if (ev.key === "ArrowLeft") { ev.preventDefault(); show(i - 1); }
      else if (ev.key === "ArrowRight") { ev.preventDefault(); show(i + 1); }
    });
    dlg.addEventListener("close", function () { if (opener) opener.focus(); });
    var x0 = null;
    dlg.addEventListener("touchstart", function (ev) { x0 = ev.touches[0].clientX; }, { passive: true });
    dlg.addEventListener("touchend", function (ev) {
      if (x0 === null) return;
      var dx = ev.changedTouches[0].clientX - x0; x0 = null;
      if (Math.abs(dx) > 50) show(i + (dx < 0 ? 1 : -1));
    }, { passive: true });
  })();

  /* ==========================================================================
     Excerpt: text size
     ========================================================================== */
  (function reader() {
    var sheet = $("#sheet");
    if (!sheet) return;
    var steps = [1.08, 1.22, 1.36, 1.5], idx = store.get("textsize", 1);
    if (typeof idx !== "number" || idx < 0 || idx >= steps.length) idx = 1;
    function apply() { sheet.style.setProperty("--fs", steps[idx] + "rem"); }
    apply();
    $$("[data-size]").forEach(function (b) {
      b.addEventListener("click", function () {
        idx = Math.max(0, Math.min(steps.length - 1, idx + (b.getAttribute("data-size") === "up" ? 1 : -1)));
        apply(); store.set("textsize", idx);
      });
    });
    var more = $("#more-excerpt");
    if (more) more.addEventListener("toggle", function () { if (more.open) track("excerpt_continue", {}); });
  })();

  /* ==========================================================================
     Field notebook: Level I field work, saved in this browser only
     ========================================================================== */
  (function notebook() {
    var form = $("#notebook");
    if (!form) return;
    var fields = ["p1", "p2", "p3", "p4", "p5", "log"];
    var PROMPTS = {};
    fields.forEach(function (f) { var l = $("label[for='" + f + "']", form); PROMPTS[f] = l ? l.textContent.trim() : f; });
    var status = $("#nb-status"), entriesBox = $("#nb-entries"), list = $("#nb-list"), count = $("#nb-count");
    var data = store.get("notebook", null);
    if (!data || typeof data !== "object") data = { draft: {}, entries: [] };
    if (!Array.isArray(data.entries)) data.entries = [];
    if (!data.draft || typeof data.draft !== "object") data.draft = {};

    function values() { var v = {}; fields.forEach(function (f) { v[f] = (form.elements[f].value || "").trim(); }); return v; }
    function any(v) { return fields.some(function (f) { return v[f]; }); }
    function fill(v) { fields.forEach(function (f) { form.elements[f].value = (v && typeof v[f] === "string") ? v[f] : ""; }); }
    function say(msg) { status.textContent = msg; }

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
    var today = todayISO(), todays = null;
    data.entries.forEach(function (en) { if (en.date === today) todays = en; });
    if (any(data.draft)) { fill(data.draft); say("Your unfinished page is here."); }
    else if (todays) { fill(todays); say("Today’s page is saved. You can keep writing."); }
    render();

    var draftTimer = 0;
    form.addEventListener("input", function () {
      clearTimeout(draftTimer);
      draftTimer = setTimeout(function () { data.draft = values(); store.set("notebook", data); }, 500);
    });
    form.addEventListener("submit", function (ev) {
      ev.preventDefault();
      var v = values();
      if (!any(v)) { say("Write a line first."); form.elements.p1.focus(); return; }
      v.date = todayISO();
      data.entries = data.entries.filter(function (en) { return en.date !== v.date; });
      data.entries.push(v);
      if (data.entries.length > 400) data.entries = data.entries.slice(-400);
      data.draft = {};
      if (store.set("notebook", data)) { say("Saved on this device, " + niceDate(v.date) + "."); track("fieldwork_save", {}); }
      else say("This browser would not save the page. Download or print it before you leave.");
      render();
    });
    $("#nb-clear").addEventListener("click", function () {
      if (any(values()) && !window.confirm("Clear what is written on this page? Saved earlier pages stay.")) return;
      fill({}); data.draft = {}; store.set("notebook", data); say("Page cleared."); form.elements.p1.focus();
    });
    $("#nb-print").addEventListener("click", function () { printOnly("print-notebook"); });
    $("#nb-download").addEventListener("click", function () {
      var all = data.entries.slice(), v = values();
      if (any(v)) { v.date = todayISO() + " (unsaved)"; all.push(v); }
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
  })();

  /* ==========================================================================
     The summit: thirty days, five phases, three sittings a day
     ========================================================================== */
  var PHASES = [null,
    { name: "The Mirror", first: 1 }, { name: "Archaeology", first: 7 }, { name: "Integration", first: 13 },
    { name: "Expression", first: 19 }, { name: "Multiplication", first: 25 }];
  /* [title, practice in one line, printed page]. Wording follows pp. 306-313. */
  var DAYS = [null,
    ["The Baseline Assessment", "Rate the five statements beside this card and keep the total as your baseline. At two in the afternoon, ask what you are seeking that you might already have.", 306],
    ["The Recognition Practices", "The “Already Am” Inventory: list ten things you can do without conscious effort. Tonight, finish the sentence “Today I sought ___ but discovered I already had ___.”", 307],
    ["The Recognition Practices", "Repeat the “Already Am” Inventory with ten new entries. When you catch yourself wanting, pause and ask whether you already have it in a form you have not recognized.", 307],
    ["The Mirror Deepens", "Add the Body Scan for Completeness to the morning: hand on heart, hand on stomach, hand on head.", 307],
    ["The Mirror Deepens", "The Body Scan for Completeness again, slower. Keep the midday check and the evening sentence.", 307],
    ["Phase 1 Integration", "Weekly assessment: how many times did you catch yourself seeking, and how many times did you recognize having? Milestone: one hour without seeking validation.", 307],
    ["Identifying Buried Treasure", "Draw your Buried Treasure Map: a natural talent you downplay, a childhood passion you abandoned, an effortless skill you take for granted.", 308],
    ["The Excavation", "The 10% Expression Experiment: choose one buried quality and express it at ten percent intensity today.", 308],
    ["The Excavation", "The 10% Expression Experiment, second day. The book’s note: resistance is your treasure map.", 308],
    ["Shadow Recognition", "The Trigger-to-Treasure Process: notice what irritates you in others, find where that quality lives in you, and express it consciously today.", 309],
    ["Shadow Recognition", "The Trigger-to-Treasure Process with a second irritation. One percent is enough to find.", 309],
    ["Phase 2 Integration", "Weekly assessment: buried qualities discovered, shadows recognized as gold. Milestone: did you express one buried quality publicly?", 309],
    ["The Both/And Practice", "Morning declaration: complete the sentence “I am both ___ AND ___.” Then show both qualities in one conversation today.", 309],
    ["The Peace Protocol", "When you are triggered, use the S.T.O.P. Method: Stop, Time, Observe, Peace. Three breaths at the end.", 309],
    ["The Peace Protocol", "S.T.O.P. again. The book’s measure is how long it takes you to get from trigger back to peace.", 310],
    ["The Completeness Conversations", "Have one honest conversation using the Kind Truth Framework: recognition, truth, vision.", 310],
    ["The Completeness Conversations", "A second conversation with the Kind Truth Framework: “I see you…”, “Here’s what I notice…”, “Here’s what’s possible…”", 310],
    ["Phase 3 Integration", "Weekly assessment: opposite qualities integrated, kind truths delivered. Milestone: can you hold opposing qualities without choosing?", 310],
    ["The Expression Commitment", "Build your Expression Arsenal: write ten ways to express your gift in under five minutes. Set a daily alarm and label it EXPRESS NOW.", 310],
    ["The Gift Emergency", "When the alarm sounds, do one at once: write 100 words, create for five minutes, or teach someone one thing. No editing.", 311],
    ["The Gift Emergency", "The alarm again. No editing, just expression.", 311],
    ["The Generosity Overflow", "The Three Streams Practice: give something material, something emotional and something energetic today.", 311],
    ["The Generosity Overflow", "Three streams again: a small material gift, genuine appreciation, good thoughts.", 311],
    ["Phase 4 Integration", "Weekly assessment: times expressed without editing, gifts given from overflow. Milestone: did you create something from joy, not need?", 311],
    ["The Ripple Recognition", "In every interaction today, hold one silent thought about the other person: “You’re already complete.” Notice what shifts.", 312],
    ["The Mentorship Moment", "Teach someone one thing you have recognized this month.", 312],
    ["The Mentorship Moment", "Teach a second person. The book’s note: teaching deepens your own understanding.", 312],
    ["The Integration Mastery", "Live one full day as complete: no seeking, no becoming, just being. Document what happens.", 312],
    ["The Integration Mastery", "A second full day as complete. Write down what was different from yesterday.", 312],
    ["The Celebration & Continuation", "Retake the inventory and compare it with Day 1. Then choose: repeat the thirty days, guide someone else through them, or design your own.", 312]
  ];

  (function summit() {
    var card = $("#tracker");
    if (!card) return;
    var daysBox = $("#days"), title = $("#phase-title"), dayLabel = $("#day-label"), dayTitle = $("#day-title"),
        dayText = $("#day-text"), dayWhere = $("#day-where"), fill = $("#tracker-fill"), countEl = $("#tracker-count"),
        sinceEl = $("#tracker-since"), checks = $$("input[data-slot]", card), phaseBtns = $$(".phase");
    var state = store.get("tracker", null);
    if (!state || typeof state !== "object" || typeof state.days !== "object" || state.days === null) state = { start: "", days: {} };
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
      dayWhere.textContent = "Full instructions: p. " + D[2] + ".";
      var s = slots(day);
      checks.forEach(function (c, i) { c.checked = !!s[i]; });
    }
    function renderMeta() {
      var n = completeDays();
      fill.style.width = (n / 30 * 100).toFixed(2) + "%";
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
      if (!keepDay) {
        day = PHASES[p].first;
        for (var d = PHASES[p].first; d < PHASES[p].first + 6; d++) { if (doneCount(d) < 3) { day = d; break; } }
      }
      renderDays(); renderDay();
    }
    phaseBtns.forEach(function (b) {
      b.addEventListener("click", function () {
        setPhase(+b.getAttribute("data-phase"));
        if (window.matchMedia("(max-width: 960px)").matches) card.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "start" });
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
        if (!store.set("tracker", state)) toast("Not saved: storage is unavailable");
        renderDays(); renderMeta();
        if (was < 3 && doneCount(day) === 3) {
          track("tracker_day", { day: day });
          toast(day === 30 ? "Thirty days. The summit." : "Day " + day + " complete");
        }
      });
    });
    $("#tracker-reset").addEventListener("click", function () {
      if (!completeDays() && !state.start) return;
      if (!window.confirm("Start the thirty days over? Your ticks on this device will be cleared.")) return;
      state = { start: "", days: {} }; store.set("tracker", state);
      setPhase(1); renderMeta(); toast("Back at base camp");
    });
    /* open on the first unfinished day */
    day = firstOpenDay(); setPhase(phaseOf(day), true); renderMeta();
    /* the pledge shares the start date */
    window.__ptgTracker = {
      begin: function (iso) { if (!state.start) { state.start = iso; store.set("tracker", state); renderMeta(); } }
    };
  })();

  /* ---- the Completeness Inventory */
  (function inventory() {
    var form = $("#inventory");
    if (!form) return;
    var ids = ["i1", "i2", "i3", "i4", "i5"], total = $("#inv-total"), saved = $("#inv-saved");
    var data = store.get("inventory", {});
    if (!data || typeof data !== "object") data = {};
    function vals() { return ids.map(function (id) { return +form.elements[id].value || 1; }); }
    function sum() { return vals().reduce(function (a, b) { return a + b; }, 0); }
    function paint() {
      ids.forEach(function (id, i) { var o = $("#o" + (i + 1)); if (o) o.textContent = form.elements[id].value; form.elements[id].setAttribute("aria-valuetext", form.elements[id].value + " of 10"); });
      total.textContent = String(sum());
    }
    function report() {
      var parts = [];
      if (data.d1) parts.push("Day 1: <b>" + (+data.d1.score) + "/50</b> (" + (niceDate(data.d1.date) || "") + ")");
      if (data.d30) parts.push("Day 30: <b>" + (+data.d30.score) + "/50</b> (" + (niceDate(data.d30.date) || "") + ")");
      var html = parts.join(" → ");
      if (data.d1 && data.d30) {
        var diff = data.d30.score - data.d1.score;
        html += diff < 0 ? ". " + Math.abs(diff) + " points less seeking." : diff > 0 ? ". " + diff + " points more than Day 1." : ". No change in the total.";
      }
      saved.innerHTML = html;
    }
    function keep(which) {
      data[which] = { score: sum(), vals: vals(), date: todayISO() };
      if (!store.set("inventory", data)) { saved.textContent = "This browser would not save the score. Write it down: " + sum() + "/50."; return; }
      report(); toast(which === "d1" ? "Day 1 score saved" : "Day 30 score saved"); track("inventory_save", { which: which });
    }
    if (data.d1 && Array.isArray(data.d1.vals) && data.d1.vals.length === 5) ids.forEach(function (id, i) { var v = +data.d1.vals[i]; if (v >= 1 && v <= 10) form.elements[id].value = String(Math.round(v)); });
    form.addEventListener("input", paint);
    form.addEventListener("submit", function (ev) { ev.preventDefault(); keep("d1"); });
    $("#inv-save30").addEventListener("click", function () { keep("d30"); });
    paint(); report();
  })();

  /* ---- the pledge */
  (function pledge() {
    var box = $("#pledge");
    if (!box) return;
    var name = $("#pledge-name"), date = $("#pledge-date"), btn = $("#pledge-sign");
    var data = store.get("pledge", null);
    function render() {
      var signed = !!(data && data.name && data.date);
      box.classList.toggle("is-signed", signed);
      if (signed) { name.value = data.name; date.textContent = niceDate(data.date) || data.date; btn.textContent = "Signed. Sign again"; }
      else { date.innerHTML = "&nbsp;"; btn.textContent = "Sign and begin"; }
    }
    btn.addEventListener("click", function () {
      var v = (name.value || "").trim().slice(0, 80);
      if (!v) { toast("Sign your name first"); name.focus(); return; }
      data = { name: v, date: todayISO() };
      store.set("pledge", data);
      if (window.__ptgTracker) window.__ptgTracker.begin(data.date);
      render(); toast("The revolution begins now"); track("pledge_sign", {});
    });
    name.addEventListener("keydown", function (ev) { if (ev.key === "Enter") { ev.preventDefault(); btn.click(); } });
    $("#pledge-print").addEventListener("click", function () { printOnly("print-pledge"); });
    render();
  })();

  /* ==========================================================================
     Getting the book: buy buttons when it is out, the first-readers form before
     ========================================================================== */
  (function get() {
    var form = $("#signup"), buy = $("#buy"), status = $("#signup-status"), lede = $("#get-lede");
    var LABELS = { hardcover: "Hardcover", paperback: "Paperback", ebook: "E-book", audiobook: "Audiobook", direct: "Buy direct" };
    var links = cfg.BUY_LINKS || {}, live = [];
    Object.keys(LABELS).forEach(function (k) { if (isUrl(links[k])) live.push(k); });

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
      $$("[data-release-note]").forEach(function (el) { el.textContent = "Available now."; });
      $$("[data-cta='hero'],[data-cta='band'],[data-cta='nav'],[data-cta='dock']").forEach(function (a) { a.textContent = "Get the book"; });
      return;
    }
    if (!form) return;
    var email = form.elements.email_address;
    if (isUrl(cfg.FORM_ACTION)) {
      form.action = cfg.FORM_ACTION;
      form.addEventListener("submit", function (ev) {
        if (form.elements.company.value) { ev.preventDefault(); return; }
        if (!email.checkValidity()) { ev.preventDefault(); status.textContent = "That address does not look complete."; email.focus(); return; }
        track("lead", { method: "kit" });
      });
      return;
    }
    /* no list connected yet: hand the visitor a ready-made email instead of pretending */
    form.addEventListener("submit", function (ev) {
      ev.preventDefault();
      if (form.elements.company.value) return;
      if (!email.value || !email.checkValidity()) { status.textContent = "That address does not look complete."; email.focus(); return; }
      var to = (cfg.CONTACT_EMAIL && cfg.CONTACT_EMAIL.indexOf("@") > 0) ? cfg.CONTACT_EMAIL : "eatmediatv@gmail.com";
      var subject = "The Path to Greatness: first readers";
      var body = "Please tell me when The Path to Greatness is out.\n\nMy address: " + email.value + "\n";
      status.textContent = "Your mail app should open with a note ready to send. Send it and you are on the list.";
      track("lead", { method: "mailto" });
      window.location.href = "mailto:" + to + "?subject=" + encodeURIComponent(subject) + "&body=" + encodeURIComponent(body);
    });
  })();
})();
