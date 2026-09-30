/* ============================================================================
   SITE CONFIG — the ONLY block you need to edit.
   Swap each placeholder for the real value, save, push. Every page reads from
   here: buy buttons, Amazon links, GA4, the email-capture form, and the
   social links on links.html.
   ============================================================================ */
window.BGF_CONFIG = {
  /* Payhip: the product URL is https://payhip.com/b/exquo — the ID is the
     part after /b/. Storefront: https://payhip.com/BlackGeniusFiles */
  PAYHIP_PRODUCT_ID: "exquo",
  PAYHIP_STORE_URL: "https://payhip.com/BlackGeniusFiles",
  PAYHIP_STUDY_URL: "https://payhip.com/b/R0jgn",

  /* Amazon — one canonical product URL per format (verified 2026-09-27).
     Every [data-amazon="<format>"] link on every page is rewired from here,
     so a price change or an Amazon Attribution tag is a one-line edit:
     paste the tagged URL over the plain one and push.
     Do NOT use a.co share links — they carry the sharer's format.
     a.co/d/0g29KbPj resolved to the KINDLE page (B0GX32RB25), not the
     paperback, which is why it was retired. */
  AMAZON_PAPERBACK_URL: "https://www.amazon.com/dp/B0HKT1PV5Y",
  AMAZON_HARDCOVER_URL: "https://www.amazon.com/dp/B0HKW11PSZ",
  AMAZON_KINDLE_URL: "https://www.amazon.com/dp/B0GX32RB25",
  /* Back-compat alias: anything still reading AMAZON_URL gets the paperback. */
  AMAZON_URL: "https://www.amazon.com/dp/B0HKT1PV5Y",

  /* Launch ribbon — a countdown bar across the top of every page.

     It expires on its own. After LAUNCH_ENDS passes, the ribbon stops
     rendering everywhere and nothing has to be committed, deployed or
     remembered at the close; leaving this block untouched is the correct
     end state. LAUNCH_RIBBON:false only hides it EARLY.

     LAUNCH_ENDS carries an explicit UTC offset on purpose, so the deadline
     means the same instant for every visitor regardless of their timezone.
     -07:00 is Pacific Daylight Time; 8 Oct 2026 falls before DST ends on
     1 Nov, so PT is -07:00 and not -08:00 on that date. */
  LAUNCH_RIBBON: true,
  LAUNCH_ENDS: "2026-10-08T19:00:00-07:00",

  /* Google Analytics 4 measurement ID. */
  GA4_MEASUREMENT_ID: "G-FXDJLKSKDG",

  /* Kit (ConvertKit) form endpoint — posts field "email_address". */
  FORM_ACTION: "https://app.kit.com/forms/9748584/subscriptions",

  /* links.html hub destinations. */
  YOUTUBE_URL: "https://www.youtube.com/@theblackgeniusfiles",
  PINTEREST_URL: "PINTEREST_URL",
  PODCAST_URL: "https://podcasts.apple.com/us/podcast/the-all-black-everything-podcast/id1527013923",
  CONTACT_EMAIL: "eatmediatv@gmail.com",
};
/* ========================== end of config block ============================ */

(function () {
  "use strict";
  var cfg = window.BGF_CONFIG;

  function isSet(value) {
    // A value is "real" once it no longer looks like an ALL_CAPS placeholder.
    return value && !/^[A-Z0-9_]+$/.test(value);
  }
  function isUrl(value) {
    return isSet(value) && /^https:\/\//.test(value);
  }

  /* ---- GA4 ---------------------------------------------------------------- */
  if (/^G-[A-Z0-9]{4,}$/.test(cfg.GA4_MEASUREMENT_ID)) {
    var ga = document.createElement("script");
    ga.async = true;
    ga.src =
      "https://www.googletagmanager.com/gtag/js?id=" + cfg.GA4_MEASUREMENT_ID;
    document.head.appendChild(ga);
    window.dataLayer = window.dataLayer || [];
    window.gtag = function () {
      window.dataLayer.push(arguments);
    };
    window.gtag("js", new Date());
    window.gtag("config", cfg.GA4_MEASUREMENT_ID);

    /* ---- Outbound click attribution ---------------------------------------
       One delegated listener classifies EVERY link that leaves this site, so
       a link is measured the moment it is added rather than only when someone
       remembers the data-track-buy attribute. That attribute previously
       covered the two product cards and nothing else, which left links.html,
       press-kit.html and check-your-email.html reporting no clicks at all.

       "Leaves this site" cannot be a hostname comparison: the archive site,
       the Genius Index and the assessment all share dixon8303.github.io with
       this one, so comparing hostnames would silently drop exactly the
       cross-property clicks worth measuring. Compare the path prefix instead —
       every page of this site sits directly under one base path. */
    var SITE_BASE = window.location.pathname.replace(/[^/]*$/, "");

    function isOutbound(a) {
      if (!/^https?:$/i.test(a.protocol)) return false;
      if (a.hostname !== window.location.hostname) return true;
      return a.pathname.indexOf(SITE_BASE) !== 0;
    }

    // Order matters: a subscribe link is also a youtube.com link, and the
    // subscribe intent is the one worth counting.
    //   amazon_click — any Amazon format (paperback / hardcover / kindle).
    //                  A separate event NAME, not a parameter, so Amazon
    //                  click-throughs show in GA4 with zero configuration.
    //   buy_click    — direct sales through Payhip (PDF, companion).
    function classify(href) {
      if (/sub_confirmation/.test(href)) return "subscribe_click";
      if (/payhip\.com/.test(href)) return "buy_click";
      if (/ImaginariumOzone\/book/.test(href)) return "book_click";
      if (/youtube\.com|youtu\.be/.test(href)) return "youtube_click";
      if (/podcasts\.apple\.com/.test(href)) return "podcast_click";
      if (/calendly\.com/.test(href)) return "interview_click";
      if (/amazon\.[a-z.]+|amzn\.to|a\.co/.test(href)) return "amazon_click";
      return "outbound_click";
    }

    document.addEventListener("click", function (ev) {
      var a = ev.target.closest && ev.target.closest("a[href]");
      if (!a || typeof window.gtag !== "function") return;
      if (!isOutbound(a)) return;
      // One event per click. Parameters say WHICH format, WHERE on the page,
      // and WHERE the visitor came from, so one report answers "which
      // placement sold which format to which channel". Register format,
      // placement and retailer as event-scoped custom dimensions in GA4
      // (Admin > Custom definitions) to see them in standard reports.
      var params = {
        link_url: a.href,
        link_text: (a.innerText || "").trim().slice(0, 80),
        transport_type: "beacon",
      };
      var buy = a.closest("[data-track-buy]");
      if (buy) {
        params.item_name = buy.dataset.trackBuy;
        params.format = buy.dataset.trackBuy;
        params.price = buy.dataset.trackPrice || "";
        params.currency = "USD";
      }
      params.retailer = /payhip\.com/.test(a.href) ? "payhip"
        : /amazon\.[a-z.]+|amzn\.to|a\.co/.test(a.href) ? "amazon" : "";
      var spot = a.closest("[data-placement]");
      if (spot) params.placement = spot.dataset.placement;
      var src = utms().utm_source;
      if (src) params.campaign_source = src;
      window.gtag("event", classify(a.href), params);
    }, true);

    /* Funnel step between "arrived" and "clicked to buy": the visitor
       actually reached the format chooser. Fires once per page view. */
    function watchAcquire() {
      var box = document.getElementById("acquire");
      if (!box || !("IntersectionObserver" in window)) return;
      var io = new IntersectionObserver(function (entries) {
        entries.forEach(function (en) {
          if (!en.isIntersecting) return;
          window.gtag("event", "acquire_view", { transport_type: "beacon" });
          io.disconnect();
        });
      }, { threshold: 0.25 });
      io.observe(box);
    }
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", watchAcquire);
    } else {
      watchAcquire();
    }
  }

  /* Email capture. The Chapter 1 signup posts a real form to Kit and so
     navigates away — the beacon transport is what keeps the event alive. */
  window.BGF_TRACK_LEAD = function (method) {
    if (typeof window.gtag !== "function") return;
    window.gtag("event", "lead", { method: method, transport_type: "beacon" });
  };

  /* ---- UTM passthrough ----------------------------------------------------
     The traffic engine tags every inbound link (utm_source=youtube|pinterest,
     utm_campaign=bgf_engine, utm_content=<id>). Capture those params once,
     remember them for the visit, and append them to every outbound
     Payhip / Amazon link so attribution survives the click. */
  var UTM_KEYS = ["utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term"];
  var STORE_KEY = "bgf_utm";

  function currentUtms() {
    var params = new URLSearchParams(window.location.search);
    var found = {};
    UTM_KEYS.forEach(function (k) {
      if (params.get(k)) found[k] = params.get(k);
    });
    return found;
  }
  function storedUtms() {
    try {
      return JSON.parse(sessionStorage.getItem(STORE_KEY) || "{}");
    } catch (e) {
      return {};
    }
  }
  var inbound = currentUtms();
  if (Object.keys(inbound).length) {
    try {
      sessionStorage.setItem(STORE_KEY, JSON.stringify(inbound));
    } catch (e) {
      /* private mode — fall back to this page's params only */
    }
  }
  function utms() {
    var merged = storedUtms();
    Object.keys(inbound).forEach(function (k) {
      merged[k] = inbound[k];
    });
    return merged;
  }
  function withUtms(url) {
    var tags = utms();
    if (!Object.keys(tags).length) return url;
    try {
      var u = new URL(url, window.location.href);
      UTM_KEYS.forEach(function (k) {
        if (tags[k] && !u.searchParams.has(k)) u.searchParams.set(k, tags[k]);
      });
      return u.toString();
    } catch (e) {
      return url;
    }
  }
  var OUTBOUND = /(^|\.)(payhip\.com|amazon\.[a-z.]+|amzn\.to|a\.co)$/i;
  // For links rendered after page load (e.g. the case-file modal).
  window.BGF_WITH_UTMS = withUtms;

  /* ---- Wire the page ------------------------------------------------------ */
  function wire() {
    // Payhip buy buttons: [data-payhip] anchors carry the overlay classes.
    // The static href is the no-JS fallback straight to the product page.
    if (isSet(cfg.PAYHIP_PRODUCT_ID)) {
      document.querySelectorAll("a[data-payhip]").forEach(function (a) {
        a.href = "https://payhip.com/b/" + cfg.PAYHIP_PRODUCT_ID;
        a.setAttribute("data-product", cfg.PAYHIP_PRODUCT_ID);
      });
    }

    // Amazon links, one URL per format: data-amazon="paperback" | "hardcover"
    // | "kindle". A bare data-amazon (no value) means the paperback — the
    // campaign's lead format.
    var AMAZON = {
      paperback: cfg.AMAZON_PAPERBACK_URL || cfg.AMAZON_URL,
      hardcover: cfg.AMAZON_HARDCOVER_URL,
      kindle: cfg.AMAZON_KINDLE_URL,
    };
    document.querySelectorAll("a[data-amazon]").forEach(function (a) {
      var url = AMAZON[a.getAttribute("data-amazon") || "paperback"];
      if (isUrl(url)) a.href = url;
    });

    // links.html hub destinations + contact.
    var hub = {
      youtube: cfg.YOUTUBE_URL,
      pinterest: cfg.PINTEREST_URL,
      podcast: cfg.PODCAST_URL,
      store: cfg.PAYHIP_STORE_URL,
      study: cfg.PAYHIP_STUDY_URL,
    };
    Object.keys(hub).forEach(function (key) {
      if (!isUrl(hub[key])) return;
      document.querySelectorAll('a[data-link="' + key + '"]').forEach(function (a) {
        a.href = hub[key];
      });
    });
    if (isSet(cfg.CONTACT_EMAIL) && cfg.CONTACT_EMAIL.indexOf("@") > 0) {
      document.querySelectorAll('a[data-link="contact"]').forEach(function (a) {
        a.href = "mailto:" + cfg.CONTACT_EMAIL;
      });
    }

    // Email capture form(s).
    document.querySelectorAll("form[data-capture]").forEach(function (form) {
      if (isUrl(cfg.FORM_ACTION)) {
        form.action = cfg.FORM_ACTION;
      } else {
        form.addEventListener("submit", function (ev) {
          ev.preventDefault();
          var note = form.querySelector(".form-note");
          if (note) note.textContent = "Sign-up opens soon — the list isn't connected yet.";
        });
      }
    });

    // Tag every outbound Payhip / Amazon link with the visit's UTMs.
    document.querySelectorAll('a[href^="http"]').forEach(function (a) {
      try {
        var host = new URL(a.href).hostname;
        if (OUTBOUND.test(host)) a.href = withUtms(a.href);
      } catch (e) {
        /* ignore malformed hrefs */
      }
    });
  }

  /* ---- Launch ribbon ------------------------------------------------------
     Renders only while the launch is running, so it disappears by itself the
     moment LAUNCH_ENDS passes — there is no off-switch to remember to throw
     on the closing night. Everything is guarded: a missing, malformed or
     already-past date renders nothing at all rather than a broken bar. */
  function launchRibbon() {
    if (cfg.LAUNCH_RIBBON === false) return;

    var ends = Date.parse(cfg.LAUNCH_ENDS || "");
    if (isNaN(ends)) return;                 // unset or malformed — stay silent
    if (Date.now() >= ends) return;          // the launch is over; this is the end state

    var bar = document.createElement("a");
    bar.href = "./#acquire";
    bar.id = "bgf-launch-ribbon";
    bar.setAttribute("role", "status");
    bar.style.cssText =
      "display:flex;align-items:center;justify-content:center;gap:10px;flex-wrap:wrap;" +
      "padding:9px 16px;text-align:center;text-decoration:none;" +
      "background:linear-gradient(90deg,#9a6a18,#C2A24A 55%,#9a6a18);color:#0E0D0B;" +
      "font-family:'Archivo',sans-serif;font-weight:700;" +
      "font-size:clamp(10px,2.3vw,11.5px);letter-spacing:.14em;text-transform:uppercase";

    var label = document.createElement("span");
    var clock = document.createElement("span");
    clock.style.cssText = "font-variant-numeric:tabular-nums;opacity:.82";
    bar.appendChild(label);
    bar.appendChild(clock);

    function tick() {
      var left = ends - Date.now();
      if (left <= 0) {                       // crossed the deadline mid-visit
        if (bar.parentNode) bar.parentNode.removeChild(bar);
        clearInterval(timer);
        return;
      }
      var mins = Math.floor(left / 60000);
      var days = Math.floor(mins / 1440);
      var hrs = Math.floor((mins % 1440) / 60);
      label.textContent = "Launch week · What History Buried is out now";
      clock.textContent = days > 0
        ? "— " + days + (days === 1 ? " day" : " days") + " " + hrs + "h left"
        : (hrs > 0 ? "— " + hrs + "h " + (mins % 60) + "m left"
                   : "— " + (mins % 60) + "m left");
    }
    tick();
    var timer = setInterval(tick, 30000);

    /* index.html keeps its nav in a fixed flex-column wrapper, so the ribbon
       stacks above the nav there with no overlap maths. Every other page has
       no fixed chrome, so it simply sits at the top of the document. */
    var chrome = document.getElementById("top-chrome");
    if (chrome) chrome.insertBefore(bar, chrome.firstChild);
    else document.body.insertBefore(bar, document.body.firstChild);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () { wire(); launchRibbon(); });
  } else {
    wire();
    launchRibbon();
  }
})();
