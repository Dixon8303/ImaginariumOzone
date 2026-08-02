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

  /* Amazon listing — the trade paperback. (The $12.99 Kindle ebook link is
     deliberately not used anywhere: it undercuts the direct price.) */
  AMAZON_URL: "https://a.co/d/0g29KbPj",

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

    /* ---- Outbound purchase-click tracking ---------------------------------
       Any buy button carrying data-track-buy fires a GA4 event on click —
       covers the ebook and Study & Trivia Companion cards today, and any
       paperback/hardcover card added later automatically, with no JS
       changes: just add the same data attributes to the new button. */
    document.addEventListener("click", function (ev) {
      var el = ev.target.closest("[data-track-buy]");
      if (!el || typeof window.gtag !== "function") return;
      window.gtag("event", "buy_click", {
        item_name: el.dataset.trackBuy,
        price: el.dataset.trackPrice || "",
        currency: "USD",
        link_url: el.href || "",
      });
    });
  }

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

    // Amazon paperback links.
    if (isUrl(cfg.AMAZON_URL)) {
      document.querySelectorAll("a[data-amazon]").forEach(function (a) {
        a.href = cfg.AMAZON_URL;
      });
    }

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

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", wire);
  } else {
    wire();
  }
})();
