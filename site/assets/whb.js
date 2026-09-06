/* What History Buried — runtime, ported 1:1 from the Claude Design prototype
   (design-src/What History Buried - Official Site.dc.html). Renders the
   dynamic regions (case files, timeline, archive, modals), the hidden-artifact
   game, ambience, and effects. Integration hooks (email capture via
   BGF_CONFIG.FORM_ACTION) live in subscribe(). */
(function () {
  "use strict";

  /* ---------------- data (verbatim from the design) ---------------- */
  var SEALNAMES = { a: "The Opening Seal", b: "The Clerk’s Pen", c: "The Cartographer’s Mark", d: "The Conductor’s Lantern", e: "The 1905 Plate", f: "The Ledger’s Spine", g: "The Tide Mark" };

  var VERDICTS = ["ERASED", "BURNED", "UNCREDITED", "REWRITTEN", "SHORTCHANGED", "REWRITTEN", "REVOKED", "REWRITTEN", "UNCREDITED", "OMITTED", "BURNED", "BLACKLISTED"];

  var ACHDEFS = [
    { k: "first", t: "FIRST RECOVERY", d: "One seal found. Six remain." },
    { k: "cart", t: "THE CARTOGRAPHER", d: "The 1375 record, restored." },
    { k: "reader", t: "CASE READER", d: "Six case files opened." },
    { k: "docket", t: "FULL DOCKET", d: "All twelve case files opened." },
    { k: "arch", t: "THE ARCHIVIST", d: "All seven artifacts recovered." },
    { k: "kon", t: "OFF THE RECORD", d: "You found what was never filed." }
  ];

  var PARTS = [
    { label: "Part One", title: "The World They Built", desc: "From an emperor who moved the price of gold to the woman the machines answered to — genius at the scale of the world, and the long work of erasing it." },
    { label: "Part Two", title: "The Generals", desc: "An intelligence network, a stolen warship, and a continent-wide system run on coded language — resistance organized like a campaign." },
    { label: "Part Three", title: "What Was Promised and Taken", desc: "What freedom was promised, in writing, by the people who had earned it — and how the promise was taken back." },
    { label: "Part Four", title: "The Invention They Buried", desc: "Inventions, fortunes, and enterprises built in full view — and quietly transferred to other names." },
    { label: "Part Five", title: "The Architecture of Silence", desc: "The machinery of silence itself — a passport, a file, a blacklist — and the one thing it could not take." }
  ];

  var CASES = [
    { i: 0, part: 0, file: "BGF-001", name: "Mansa Musa", who: "Mali Empire · r. c. 1312–c. 1332", title: "The King Who Moved the Price of Gold", img: "img/ch01_opener.jpg", ex: [{ s: "img/ch01_hajj.jpg", c: "The pilgrimage crossing the Sahara, 1324" }, { s: "img/ch01_mosque.jpg", c: "Djinguereber Mosque, photographed c. 1905" }],
      hook: "In 1324, one traveler’s spending sank the price of gold in Cairo — for more than ten years.",
      built: "An empire the size of Western Europe, astride the goldfields that supplied the Mediterranean world’s money. Caravans moved gold north and salt south, and Mali taxed the traffic at both ends.",
      buried: "Fifty years after the pilgrimage, Europe’s best map named him, gold in hand. As Europe turned toward conquest, that detailed West Africa was redrawn as blank space — terra incognita.",
      evid: "al-ʿUmari, Cairo, 1337 · Catalan Atlas, 1375 — BnF Ms. Espagnol 30",
      corr: { legend: "$400,000,000,000", truth: "A treasury that governed the gold supply", src: "AL-ʿUMARI, 1337 · SCHULTZ" } },
    { i: 1, part: 0, file: "BGF-002", name: "Benjamin Banneker", who: "1731–1806 · Maryland", title: "The Man Who Mailed the Proof", img: "img/ch02_01.jpg", ex: [{ s: "img/ch02_02.jpg", c: "The wooden striking clock, 1753" }, { s: "img/ch02_05.jpg", c: "The funeral-day fire, 1806" }],
      hook: "A wooden clock built after studying a borrowed pocket watch — once. Then six years of published almanacs.",
      built: "A striking clock, every gear cut by hand from wood, in 1753. Six straight years of astronomical almanacs. In 1791, the survey of the new federal district — and a letter challenging Jefferson, in plain language, on the people he owned.",
      buried: "On the day of his funeral, his house burned — taking the wooden clock and most of his papers with it.",
      evid: "Banneker–Jefferson correspondence, 1791 · the surviving almanacs" },
    { i: 2, part: 0, file: "BGF-003", name: "Katherine Johnson", who: "NASA · 1918–2020", title: "The Woman the Machine Answered To", img: "img/ch03_01.jpg", ex: [{ s: "img/ch03_02.jpg", c: "The segregated West Area computers, Langley" }, { s: "img/ch03_04.jpg", c: "Glenn waits on her arithmetic, February 1962" }],
      hook: "Before Friendship 7 flew, John Glenn asked for her by name — to check the computer’s numbers by hand.",
      built: "The orbital-trajectory mathematics of American spaceflight, worked out by hand in the segregated “West Computers” at Langley — and trusted over the machine by the man sitting on top of the rocket.",
      buried: "Her name sat in the NASA archive, on the reports, for decades before the country said it aloud.",
      evid: "NASA Langley technical reports · NASA photographic archive" },
    { i: 3, part: 1, file: "BGF-004", name: "Harriet Tubman", who: "Combahee River Raid · 1863", title: "The Spy Who Freed 750 People in One Night", img: "img/ch04_01.jpg", ex: [{ s: "img/ch04_02.jpg", c: "Scouts and river pilots — the network" }, { s: "img/ch04_05.jpg", c: "The dispatch that recorded the raid, 1863" }],
      hook: "Three Union gunboats up the Combahee in darkness. More than 750 people free before sunrise.",
      built: "A working intelligence network of scouts and river pilots behind Confederate lines — and the raid it made possible, June 1–2, 1863.",
      buried: "The official Union reports of the raid were never found; the first account ran in a newspaper. The legend that grew in their place undercounts what she actually did.",
      evid: "The documentary record, per Larson · press account, 1863",
      corr: { legend: "300 people · 19 trips", truth: "About 70 people, some 13 trips — and 750 freed in a single night at Combahee", src: "LARSON, FROM THE DOCUMENTARY RECORD" } },
    { i: 4, part: 1, file: "BGF-005", name: "Robert Smalls", who: "Charleston · 1862", title: "The Warship and the Schoolhouse", img: "img/ch05_01.jpg", ex: [{ s: "img/ch05_02.jpg", c: "The captain’s coat, the correct signals" }, { s: "img/ch05_05.jpg", c: "The prize-money appraisal, 1862" }],
      hook: "He sailed a Confederate warship out of Charleston Harbor in the captain’s coat — giving every correct signal.",
      built: "The CSS Planter, eased past the forts before dawn and delivered to the U.S. Navy — secret codebooks and all — on May 13, 1862. Six years later: the law creating South Carolina’s first free public-school system.",
      buried: "Congress’s prize money for the Planter was appraised far below the ship’s worth — and most of it was kept by others.",
      evid: "U.S. Navy records, May 13, 1862 · S.C. Constitutional Convention, 1868" },
    { i: 5, part: 1, file: "BGF-006", name: "The Underground Railroad", who: "William Still & the Network", title: "The Names They Saved", img: "img/ch06_00.jpg", ex: [{ s: "img/ch06_02.jpg", c: "Signals subtler than the legend" }, { s: "img/ch06_04.jpg", c: "A church cellar on the network" }],
      hook: "A continent-wide network run on coded language — and a ledger of real names, kept at mortal risk.",
      built: "Safe houses, night movement across hundreds of miles of hostile country, Black churches as the network’s urban nodes — and William Still’s meticulous records of the people who passed through.",
      buried: "The “quilt code” is the kind of legend that outran the record; the real signaling was subtler. The real archive is the names themselves — saved on paper.",
      evid: "William Still’s records, published 1872" },
    { i: 6, part: 2, file: "BGF-007", name: "Garrison Frazier", who: "Savannah · January 1865", title: "The Answer Was Land", img: "img/ch07_01.jpg", ex: [{ s: "img/ch07_02.jpg", c: "The Savannah Colloquy, January 12, 1865" }, { s: "img/ch07_05.jpg", c: "The Edisto Island petition, 1865" }],
      hook: "Asked what his people needed, the sixty-seven-year-old minister answered in one word: land.",
      built: "The Savannah Colloquy, January 12, 1865 — twenty Black ministers, questioned in writing, answering in writing. Special Field Order No. 15 set aside the Lowcountry: forty acres to each family.",
      buried: "Within the year, presidential pardons restored the land to its former enslavers. The freedpeople of Edisto Island petitioned the President in writing, refusing to leave.",
      evid: "Colloquy transcript, Jan. 12, 1865 · Special Field Order No. 15 · Edisto petition, 1865" },
    { i: 7, part: 2, file: "BGF-008", name: "John Roy Lynch", who: "Reconstruction · Mississippi", title: "The Man Who Wrote Back", img: "img/ch08_01.jpg", ex: [{ s: "img/ch08_03.jpg", c: "Outside the schoolhouse window" }, { s: "img/ch08_05.jpg", c: "Writing the correction, 1913" }],
      hook: "He taught himself within sight of a schoolhouse he was barred from entering — then wrote the rebuttal.",
      built: "Reconstruction legislatures that built public schools and rewrote state constitutions — with Lynch in the room, an eyewitness.",
      buried: "At Columbia, the Dunning School recast Reconstruction as a tragedy of Black incompetence. Lynch answered with The Facts of Reconstruction (1913) — an eyewitness rebuttal.",
      evid: "The Facts of Reconstruction, 1913" },
    { i: 8, part: 3, file: "BGF-009", name: "Granville T. Woods", who: "Holder of some forty-five patents", title: "The Patent and the Pauper", img: "img/ch09_01.jpg", ex: [{ s: "img/ch09_03.jpg", c: "The induction telegraph" }, { s: "img/ch09_04.jpg", c: "Ruled for Woods — twice" }],
      hook: "Edison sued, claiming the invention as his own. The court ruled for Woods — twice.",
      built: "The induction telegraph: moving trains that could finally communicate, and collisions prevented. One of some forty-five U.S. patents.",
      buried: "He held the patents; he died owning nothing, and lay in an unmarked grave for sixty-five years.",
      evid: "The U.S. patent record · court rulings, per Fouché",
      corr: { legend: "60 patents", truth: "Around 45 U.S. patents — held, defended, twice upheld against Edison", src: "FOUCHÉ, FROM THE PATENT RECORD" } },
    { i: 9, part: 3, file: "BGF-010", name: "Madam C. J. Walker", who: "1867–1919", title: "The Field and the Factory", img: "img/ch10_01.jpg", ex: [{ s: "img/ch10_03.jpg", c: "The Walker agents — a national force" }, { s: "img/ch10_04.jpg", c: "Villa Lewaro, Irvington-on-Hudson" }],
      hook: "Eighteen years washing other people’s laundry for about a dollar a day. Then a national company.",
      built: "A manufacturing company and a national sales force — tens of thousands of trained, commissioned Black women agents — and Villa Lewaro, her thirty-four-room mansion built deliberately among the Hudson’s wealthiest.",
      buried: "The wealthiest self-made woman in America — named in under four percent of textbooks.",
      evid: "Company and estate records · textbook survey" },
    { i: 10, part: 3, file: "BGF-011", name: "America’s Black Millionaires", who: "1848–1921", title: "The Ledger and the Fire", img: "img/ch11_01.jpg", ex: [{ s: "img/ch11_02.jpg", c: "William Leidesdorff — a San Francisco fortune by 1848" }, { s: "img/ch11_05.jpg", c: "Greenwood burns — May 31–June 1, 1921" }],
      hook: "The fortunes existed — by 1848, by 1870, by 1900. Then thirty-five blocks burned in under two days.",
      built: "William Leidesdorff’s San Francisco fortune by 1848. Mary Ellen Pleasant’s investments and civil-rights suits. Robert Reed Church Sr.’s Memphis real estate — the South’s first Black fortune. Greenwood: “Black Wall Street.”",
      buried: "Greenwood ablaze, May 31–June 1, 1921 — thirty-five blocks destroyed. Pleasant recast by her biographers as “Mammy Pleasant.” The pattern, repeated.",
      evid: "Census, probate, and press records · Tulsa, 1921" },
    { i: 11, part: 4, file: "BGF-012", name: "Paul Robeson", who: "1898–1976", title: "The Most Dangerous Man in America", img: "img/ch12_00.jpg", ex: [{ s: "img/ch12_05.jpg", c: "Sung across the Atlantic by telephone, 1957" }, { s: "img/ch12_06.jpg", c: "The FBI file, opened 1941" }],
      hook: "A government spent seven years trying to silence one voice. It could not.",
      built: "A voice heard around the world — and when the passport was gone, a concert sung to Welsh miners across the Atlantic by telephone, 1957.",
      buried: "Peekskill, 1949 — a coordinated attack, not a crowd that lost control. The passport revoked in 1950. An FBI file from 1941 until after his death — one of its largest on any performer.",
      evid: "State Department records, 1950 · the FBI file · Peekskill record, 1949" }
  ];

  var TL = [
    { y: "1312", t: "Musa comes to power in Mali — an empire that rivals Western Europe by area, astride the goldfields that supply the Mediterranean world’s money." },
    { y: "1324", t: "The pilgrimage. One traveler’s spending depresses the price of gold in Cairo; al-ʿUmari records the damage in 1337. The Djinguereber Mosque rises at Timbuktu, completed 1327." },
    { y: "1375", t: "The Catalan Atlas places Musa at the center of West Africa — named, titled, gold in hand. Europe knew.", img: "img/ch01_hajj.jpg", alt: "The hajj procession crossing the Sahara" },
    { y: "after", t: "As Europe turns toward conquest and the slave trade, its maps redraw a detailed West Africa as blank space — terra incognita. Erasure as a cartographic act." },
    { y: "1753", t: "Benjamin Banneker builds a striking clock from hand-cut wood, after studying a borrowed pocket watch once." },
    { y: "1791", t: "Banneker helps survey the new federal district — and writes to Jefferson, challenging the distance between his stated principles and the people he owned." },
    { y: "1862", t: "Before dawn on May 13, Robert Smalls eases the CSS Planter out of Charleston Harbor and delivers her — codebooks and all — to the U.S. Navy." },
    { y: "1863", t: "Tubman’s Combahee River Raid, June 1–2: three gunboats upriver in darkness; more than 750 people free before sunrise.", img: "img/ch04_03.jpg", alt: "Union gunboats moving up the Combahee in darkness" },
    { y: "1865", t: "Savannah, January 12. Asked what his people need, Garrison Frazier answers: land. Special Field Order No. 15 sets aside the Lowcountry — and within the year, presidential pardons take it back." },
    { y: "1868", t: "At South Carolina’s constitutional convention, Smalls helps write the state’s first free public-school system." },
    { y: "1887", t: "Granville Woods patents the induction telegraph; moving trains can finally speak. Edison sues, and loses. Twice." },
    { y: "1913", t: "John Roy Lynch answers the Dunning School with The Facts of Reconstruction — an eyewitness rebuttal." },
    { y: "1919", t: "Madam C. J. Walker dies the wealthiest self-made woman in America — later named in under four percent of textbooks." },
    { y: "1921", t: "Greenwood, Tulsa — May 31–June 1: thirty-five blocks of “Black Wall Street” destroyed in under two days.", img: "img/ch11_05.jpg", alt: "Greenwood ablaze, 1921" },
    { y: "1950", t: "The State Department revokes Paul Robeson’s passport, collapsing his income and his stages. The FBI file runs from 1941 until after his death." },
    { y: "1957", t: "His stages gone, Robeson sings to Welsh miners across the Atlantic — by telephone." },
    { y: "2020", t: "Katherine Johnson dies at 101. Her name sat in the NASA archive, on the reports, for decades before the country said it aloud." }
  ];

  /* ---------------- template hover styles ---------------- */
  var css = document.createElement("style");
  css.textContent =
    ".whbSpineDot:hover>span{transform:rotate(45deg) scale(1.45)}" +
    ".whbCard:hover{transform:translateY(-5px);border-color:rgba(194,162,74,.55);box-shadow:0 26px 52px -22px rgba(0,0,0,.85)}" +
    ".whbGoldBtn:hover{background:#e7b24e}" +
    ".whbGhostBtn:hover{border-color:rgba(194,162,74,.5);color:#e7b24e}";
  document.head.appendChild(css);

  /* ---------------- state ---------------- */
  function load() { try { return JSON.parse(localStorage.getItem("whb_archive") || "{}"); } catch (e) { return {}; } }
  var st0 = load();
  var snd0 = false; try { snd0 = localStorage.getItem("whb_snd") === "on"; } catch (e) {}
  var S = { seals: st0.seals || {}, opened: st0.opened || {}, ach: st0.ach || {}, ocI: null, vol2: false, toast: null, atlasDone: !!(st0.ach && st0.ach.cart), snd: snd0 };

  function persist() { try { localStorage.setItem("whb_archive", JSON.stringify({ seals: S.seals, opened: S.opened, ach: S.ach })); } catch (e) {} }

  function tagUrl(u) { return window.BGF_WITH_UTMS ? window.BGF_WITH_UTMS(u) : u; }
  var $ = function (sel) { return document.querySelector(sel); };
  var $$ = function (sel) { return Array.prototype.slice.call(document.querySelectorAll(sel)); };
  function slotEl(name) { return $('[data-slot="' + name + '"]'); }

  /* ---------------- templates ---------------- */
  function spineHTML() {
    return CASES.map(function (c) {
      var tip = "FILE " + c.file + " — " + c.name + (S.opened[c.i] ? " · opened" : "");
      var bc = S.opened[c.i] ? "#e7b24e" : "rgba(194,162,74,.38)";
      var bg = S.opened[c.i] ? "#C2A24A" : "transparent";
      return '<button data-i="' + c.i + '" data-act="open" title="' + tip + '" aria-label="' + tip + '" class="whbSpineDot" style="width:16px;height:16px;padding:0;background:transparent;border:none;cursor:pointer;display:flex;align-items:center;justify-content:center"><span style="width:8px;height:8px;transform:rotate(45deg);border:1px solid ' + bc + ";background:" + bg + ';display:block;transition:transform .25s"></span></button>';
    }).join("");
  }

  function caseCardHTML(c) {
    var seen = S.opened[c.i] ? "OPENED ●" : "";
    return '<button data-i="' + c.i + '" data-act="open" class="whbCard" style="text-align:left;border:1px solid #3c1d13;background:radial-gradient(ellipse at 28% 18%,rgba(158,62,42,.16),transparent 62%),#261009;padding:0;cursor:pointer;display:flex;flex-direction:column;font-family:inherit;color:inherit;transition:transform .35s cubic-bezier(.2,.7,.2,1),border-color .35s,box-shadow .35s">' +
      '<span style="position:relative;display:block;overflow:hidden;width:100%">' +
      '<img src="' + c.img + '" alt="' + c.name + '" loading="lazy" style="display:block;width:100%;aspect-ratio:4/5;object-fit:cover;filter:saturate(.82) contrast(1.03)" />' +
      '<span aria-hidden="true" style="position:absolute;inset:0;background:linear-gradient(180deg,rgba(14,13,11,.26),transparent 34%,rgba(14,13,11,.9) 94%)"></span>' +
      '<span style="position:absolute;top:12px;left:12px;font-family:\'Archivo\',sans-serif;font-size:9.5px;letter-spacing:.24em;color:#e7b24e;border:1px solid rgba(231,178,78,.4);padding:5px 9px;background:rgba(14,13,11,.55)">FILE&nbsp;' + c.file + "</span>" +
      '<span style="position:absolute;top:12px;right:12px;font-family:\'Archivo\',sans-serif;font-size:9px;letter-spacing:.2em;color:#C2A24A">' + seen + "</span>" +
      '<span style="position:absolute;left:14px;right:14px;bottom:13px;display:block">' +
      '<span style="display:block;font-family:\'Playfair Display\',serif;font-weight:800;font-size:24px;line-height:1.05;color:#f1e6cc">' + c.name + "</span>" +
      '<span style="display:block;margin-top:7px;font-family:\'Archivo\',sans-serif;font-size:9.5px;letter-spacing:.16em;text-transform:uppercase;color:#c3b08a">' + c.who + "</span>" +
      "</span></span>" +
      '<span style="display:flex;flex-direction:column;gap:10px;padding:16px 16px 18px;width:100%;box-sizing:border-box">' +
      '<span style="font-family:\'Newsreader\',serif;font-style:italic;font-size:16.5px;line-height:1.45;color:#e7b24e">' + c.title + "</span>" +
      '<span style="font-size:14.5px;line-height:1.62;color:#8d7c5e">' + c.hook + "</span>" +
      '<span style="margin-top:4px;font-family:\'Archivo\',sans-serif;font-weight:600;font-size:10px;letter-spacing:.24em;color:#C2A24A">OPEN&nbsp;FILE&nbsp;→</span>' +
      "</span></button>";
  }

  function partsHTML() {
    return PARTS.map(function (p, pi) {
      var cases = CASES.filter(function (c) { return c.part === pi; });
      return '<div style="margin-top:clamp(48px,7vh,78px)">' +
        '<div style="display:flex;flex-wrap:wrap;align-items:baseline;gap:10px 20px;border-bottom:1px solid #442216;padding-bottom:16px">' +
        '<span style="font-family:\'Archivo\',sans-serif;font-weight:700;letter-spacing:.3em;text-transform:uppercase;font-size:11px;color:#e7b24e">' + p.label + "</span>" +
        '<span style="font-family:\'Playfair Display\',serif;font-weight:700;font-size:clamp(22px,3vw,30px);color:#f1e6cc">' + p.title + "</span>" +
        '<span style="margin-left:auto;font-style:italic;color:#8d7c5e;font-size:14.5px;max-width:52ch">' + p.desc + "</span>" +
        "</div>" +
        '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:18px;margin-top:24px">' +
        cases.map(caseCardHTML).join("") +
        "</div></div>";
    }).join("");
  }

  function tlHTML() {
    return TL.map(function (e) {
      return '<div data-reveal style="display:grid;grid-template-columns:clamp(52px,9vw,92px) 34px 1fr;column-gap:14px">' +
        '<span style="text-align:right;font-family:\'Playfair Display\',serif;font-weight:800;font-size:clamp(17px,2.2vw,22px);color:#e7b24e;line-height:1.25">' + e.y + "</span>" +
        '<span aria-hidden="true" style="display:flex;flex-direction:column;align-items:center">' +
        '<span style="width:9px;height:9px;transform:rotate(45deg);border:1.5px solid #C2A24A;background:#0E0D0B;margin-top:8px;flex-shrink:0"></span>' +
        '<span style="flex:1;width:1px;background:rgba(194,162,74,.26);margin-top:6px"></span>' +
        "</span>" +
        '<div style="padding-bottom:clamp(34px,5vh,52px)">' +
        '<p style="margin:2px 0 0;font-size:17px;line-height:1.68;color:#c3b08a;max-width:58ch">' + e.t + "</p>" +
        (e.img ? '<img src="' + e.img + '" alt="' + (e.alt || "") + '" loading="lazy" style="margin-top:14px;width:min(380px,100%);aspect-ratio:3/2;object-fit:cover;border:1px solid #442216;filter:saturate(.8)" />' : "") +
        "</div></div>";
    }).join("");
  }

  function rosterHTML() {
    return Object.keys(SEALNAMES).map(function (k) {
      var got = S.seals[k];
      return '<span style="font-family:\'Archivo\',sans-serif;font-size:10px;letter-spacing:.16em;color:#8d7c5e;border:1px solid #442216;padding:8px 13px;display:inline-flex;align-items:center;gap:8px"><span style="color:#C2A24A">' + (got ? "●" : "○") + "</span>" + SEALNAMES[k] + "&nbsp;—&nbsp;" + (got ? "RECOVERED" : "MISSING") + "</span>";
    }).join("");
  }

  function achHTML() {
    var base = "font-family:Archivo,sans-serif;font-size:10px;letter-spacing:.14em;padding:9px 14px;display:inline-flex;align-items:center;";
    return ACHDEFS.map(function (a) {
      var got = S.ach[a.k];
      var stl = base + (got ? "color:#e7b24e;border:1px solid rgba(194,162,74,.55);background:rgba(194,162,74,.07)" : "color:#564a36;border:1px solid #1f1810");
      return '<span style="' + stl + '"><span aria-hidden="true">' + (got ? "◆" : "◇") + "</span>&nbsp;&nbsp;" + a.t + "&nbsp;·&nbsp;<em>" + a.d + "</em></span>";
    }).join("");
  }

  function modalHTML(c) {
    var corr = c.corr;
    return '<div role="dialog" aria-modal="true" aria-label="Case file" style="position:fixed;inset:0;z-index:110;display:flex;align-items:center;justify-content:center;padding:18px">' +
      '<button data-act="close" aria-label="Close file" style="position:absolute;inset:0;background:rgba(6,5,4,.84);backdrop-filter:blur(8px);border:none;cursor:pointer"></button>' +
      '<div style="position:relative;max-width:960px;width:100%;max-height:88vh;overflow:auto;background:radial-gradient(ellipse at 30% 15%,rgba(158,62,42,.17),transparent 60%),#2a130c;border:1px solid rgba(194,162,74,.35);display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));animation:fadeup .4s cubic-bezier(.2,.7,.2,1)">' +
      '<div style="position:relative;min-height:360px">' +
      '<div role="img" aria-label="' + c.name + '" style="position:absolute;inset:0;background-image:url(\'' + c.img + "');background-size:cover;background-position:center;filter:saturate(.85)\"></div>" +
      '<span aria-hidden="true" style="position:absolute;inset:0;background:linear-gradient(180deg,rgba(14,13,11,.3),transparent 40%,rgba(22,18,9,.5))"></span>' +
      '<span style="position:absolute;top:14px;left:14px;font-family:\'Archivo\',sans-serif;font-size:9.5px;letter-spacing:.24em;color:#e7b24e;border:1px solid rgba(231,178,78,.4);padding:5px 10px;background:rgba(14,13,11,.6)">FILE&nbsp;' + c.file + "&nbsp;·&nbsp;DECLASSIFIED</span>" +
      '<span aria-hidden="true" style="position:absolute;right:16px;bottom:18px;text-align:center;font-family:\'Archivo\',sans-serif;font-weight:800;letter-spacing:.24em;font-size:clamp(13px,1.7vw,17px);color:#c93a2e;border:3px double #c93a2e;border-radius:5px;padding:10px 16px 9px;background:rgba(14,13,11,.4);animation:stampIn .5s cubic-bezier(.2,1.4,.3,1) .35s both">' + VERDICTS[c.i] + '<span style="display:block;font-size:7.5px;letter-spacing:.28em;font-weight:600;margin-top:5px;color:#d4776c">FILE&nbsp;REOPENED&nbsp;·&nbsp;WHB&nbsp;VOL.&nbsp;1</span></span>' +
      "</div>" +
      '<div style="padding:clamp(26px,3.6vw,44px);display:flex;flex-direction:column;gap:17px">' +
      '<h3 style="margin:0;font-family:\'Playfair Display\',serif;font-weight:800;font-size:clamp(28px,3.6vw,40px);line-height:1.03;color:#f1e6cc">' + c.name + "</h3>" +
      '<p style="margin:0;font-family:\'Archivo\',sans-serif;font-size:10.5px;letter-spacing:.2em;text-transform:uppercase;color:#c3b08a">' + c.who + "</p>" +
      '<p style="margin:0;font-family:\'Newsreader\',serif;font-style:italic;font-size:19px;color:#e7b24e">' + c.title + "</p>" +
      "<div>" +
      '<p style="margin:0;font-family:\'Archivo\',sans-serif;font-weight:700;font-size:9.5px;letter-spacing:.26em;color:#e7b24e">WHAT&nbsp;WAS&nbsp;BUILT</p>' +
      '<p style="margin:8px 0 0;font-size:16px;line-height:1.7;color:#c3b08a">' + c.built + "</p></div>" +
      "<div>" +
      '<p style="margin:0;font-family:\'Archivo\',sans-serif;font-weight:700;font-size:9.5px;letter-spacing:.26em;color:#b32a20">WHAT&nbsp;WAS&nbsp;BURIED</p>' +
      '<p style="margin:8px 0 0;font-size:16px;line-height:1.7;color:#c3b08a">' + c.buried + "</p></div>" +
      (corr ? '<div style="border:1px solid rgba(179,42,32,.45);padding:18px 20px">' +
        '<p style="margin:0;font-family:\'Archivo\',sans-serif;font-weight:700;font-size:9.5px;letter-spacing:.26em;color:#b32a20">STRUCK&nbsp;&amp;&nbsp;CORRECTED</p>' +
        '<p style="margin:10px 0 0;font-family:\'Playfair Display\',serif;font-weight:700;font-size:19px;color:#8d7c5e;text-decoration:line-through;text-decoration-color:#b32a20;text-decoration-thickness:2.5px">' + corr.legend + "</p>" +
        '<p style="margin:8px 0 0;font-family:\'Playfair Display\',serif;font-weight:700;font-size:17px;line-height:1.4;color:#f1e6cc">' + corr.truth + "</p>" +
        '<p style="margin:12px 0 0;font-family:\'Archivo\',sans-serif;font-size:9.5px;letter-spacing:.14em;color:#8d7c5e">SOURCE&nbsp;—&nbsp;' + corr.src + "</p></div>" : "") +
      "<div>" +
      '<p style="margin:0;font-family:\'Archivo\',sans-serif;font-weight:700;font-size:9.5px;letter-spacing:.26em;color:#C2A24A">PRIMARY&nbsp;ANCHORS</p>' +
      '<p style="margin:8px 0 0;font-family:\'Archivo\',sans-serif;font-size:12px;line-height:1.65;color:#8d7c5e">' + c.evid + "</p></div>" +
      (c.ex && c.ex.length ? "<div>" +
        '<p style="margin:0;font-family:\'Archivo\',sans-serif;font-weight:700;font-size:9.5px;letter-spacing:.26em;color:#C2A24A">EXHIBITS</p>' +
        '<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:10px">' +
        c.ex.map(function (x) {
          return '<figure style="margin:0"><img src="' + x.s + '" alt="' + x.c + '" loading="lazy" style="display:block;width:100%;aspect-ratio:3/2;object-fit:cover;border:1px solid #442216;filter:saturate(.85)" /><figcaption style="margin-top:7px;font-family:\'Archivo\',sans-serif;font-size:10px;letter-spacing:.08em;line-height:1.5;color:#8d7c5e">' + x.c + "</figcaption></figure>";
        }).join("") +
        "</div></div>" : "") +
      '<div style="display:flex;flex-wrap:wrap;gap:12px;margin-top:6px">' +
      '<a href="' + tagUrl("https://payhip.com/b/exquo") + '" rel="noopener" class="whbGoldBtn" style="font-family:\'Archivo\',sans-serif;font-weight:700;font-size:11px;letter-spacing:.18em;text-transform:uppercase;text-decoration:none;color:#0E0D0B;background:#C2A24A;padding:14px 22px">Read the Full Case — Get the Book</a>' +
      '<button data-act="share" class="whbGhostBtn" style="font-family:\'Archivo\',sans-serif;font-weight:600;font-size:11px;letter-spacing:.18em;text-transform:uppercase;color:#c3b08a;background:transparent;border:1px solid #442216;padding:14px 22px;cursor:pointer">Share This Case</button>' +
      '<button data-act="close" class="whbGhostBtn" style="font-family:\'Archivo\',sans-serif;font-weight:600;font-size:11px;letter-spacing:.18em;text-transform:uppercase;color:#c3b08a;background:transparent;border:1px solid #442216;padding:14px 22px;cursor:pointer">Close File</button>' +
      "</div></div>" +
      '<button data-act="close" aria-label="Close file" class="whbGhostBtn" style="position:absolute;top:10px;right:10px;width:38px;height:38px;background:rgba(14,13,11,.72);border:1px solid #442216;color:#c3b08a;font-size:15px;cursor:pointer">✕</button>' +
      "</div></div>";
  }

  function vol2HTML() {
    return '<div role="dialog" aria-modal="true" aria-label="Declassified preview" style="position:fixed;inset:0;z-index:120;display:flex;align-items:center;justify-content:center;padding:18px">' +
      '<button data-act="close" aria-label="Close" style="position:absolute;inset:0;background:rgba(6,5,4,.86);backdrop-filter:blur(8px);border:none;cursor:pointer"></button>' +
      '<div style="position:relative;max-width:560px;width:100%;background:radial-gradient(ellipse at 30% 15%,rgba(158,62,42,.17),transparent 60%),#2a130c;border:1px solid rgba(194,162,74,.45);padding:clamp(34px,5vw,54px);text-align:center;animation:fadeup .4s cubic-bezier(.2,.7,.2,1)">' +
      '<span style="position:absolute;top:-15px;left:50%;transform:translateX(-50%) rotate(-7deg);font-family:\'Archivo\',sans-serif;font-weight:800;letter-spacing:.3em;font-size:11px;color:#0E0D0B;border:2px solid #C2A24A;background:#C2A24A;padding:8px 15px">DECLASSIFIED</span>' +
      '<p style="margin:0;font-family:\'Archivo\',sans-serif;font-weight:600;letter-spacing:.32em;text-transform:uppercase;font-size:10.5px;color:#8d7c5e">Off the Record</p>' +
      '<p style="margin:18px 0 0;font-family:\'Playfair Display\',serif;font-weight:800;font-size:clamp(30px,5vw,44px);letter-spacing:.04em;color:#f1e6cc">VOLUME TWO</p>' +
      '<p style="margin:18px auto 0;font-size:16.5px;font-style:italic;line-height:1.68;color:#c3b08a;max-width:42ch">The Black Genius Files continue — Volume Two is in preparation at E.A.T. Media.</p>' +
      '<p style="margin:22px 0 0;font-family:\'Archivo\',sans-serif;font-size:10.5px;letter-spacing:.22em;color:#C2A24A">YOU FOUND WHAT WAS NEVER FILED. THE ARCHIVE REMEMBERS CURIOSITY.</p>' +
      '<button data-act="close" class="whbGhostBtn" style="margin-top:28px;font-family:\'Archivo\',sans-serif;font-weight:600;font-size:11px;letter-spacing:.18em;text-transform:uppercase;color:#c3b08a;background:transparent;border:1px solid #442216;padding:13px 24px;cursor:pointer">Reseal</button>' +
      "</div></div>";
  }

  function toastHTML(t, s) {
    return '<div role="status" style="position:fixed;right:22px;bottom:22px;z-index:130;background:radial-gradient(ellipse at 30% 15%,rgba(158,62,42,.17),transparent 60%),#2a130c;border:1px solid rgba(194,162,74,.5);padding:16px 20px;display:flex;gap:13px;align-items:flex-start;animation:toastIn .45s cubic-bezier(.2,.7,.2,1);max-width:340px;box-shadow:0 22px 50px rgba(0,0,0,.65)">' +
      '<span aria-hidden="true" style="color:#e7b24e;font-size:16px;line-height:1.2">✦</span>' +
      '<div><p style="margin:0;font-family:\'Archivo\',sans-serif;font-weight:700;font-size:10.5px;letter-spacing:.22em;color:#e7b24e">' + t + "</p>" +
      '<p style="margin:5px 0 0;font-size:14px;line-height:1.5;color:#c3b08a">' + s + "</p></div></div>";
  }

  /* ---------------- render ---------------- */
  function render() {
    var found = Object.keys(S.seals).length;
    var openedN = Object.keys(S.opened).length;
    $$('[data-txt="found"]').forEach(function (el) { el.textContent = found; });
    $$('[data-txt="openedN"]').forEach(function (el) { el.textContent = openedN; });
    Object.keys(SEALNAMES).forEach(function (k) {
      var K = k.toUpperCase();
      $$('[data-txt="s' + K + '"]').forEach(function (el) { el.textContent = S.seals[k] ? "●" : "✦"; });
      $$('[data-titlebind="t' + K + '"]').forEach(function (el) {
        var t = S.seals[k] ? SEALNAMES[k] + " — recovered" : "Something is buried here";
        el.title = t; el.setAttribute("aria-label", "Hidden artifact");
      });
    });
    var meter = $("[data-meter]"); if (meter) meter.style.width = (found / 7 * 100) + "%";
    var sb = $("[data-sndbtn]");
    if (sb) { sb.style.color = S.snd ? "#e7b24e" : "#5a4d38"; sb.title = S.snd ? "Archive ambience on — click to mute" : "Enable archive ambience (off by default)"; }
    var sp = slotEl("spine"); if (sp) sp.innerHTML = spineHTML();
    var pt = slotEl("parts"); if (pt) pt.innerHTML = partsHTML();
    var ab = slotEl("atlasbadge");
    if (ab) ab.innerHTML = S.atlasDone ? '<span style="position:absolute;top:14px;left:14px;font-family:\'Archivo\',sans-serif;font-weight:700;font-size:10px;letter-spacing:.26em;color:#0E0D0B;background:#C2A24A;padding:7px 12px">RECORD&nbsp;RESTORED&nbsp;✦</span>' : "";
    var ro = slotEl("roster"); if (ro) ro.innerHTML = rosterHTML();
    var ac = slotEl("ach"); if (ac) ac.innerHTML = achHTML();
    var lk = $('[data-vis="locked"]'); if (lk) lk.style.display = found < 7 ? "contents" : "none";
    var un = $('[data-vis="unlocked"]'); if (un) un.style.display = found >= 7 ? "contents" : "none";
    var mo = slotEl("modal"); if (mo) mo.innerHTML = S.ocI != null ? modalHTML(CASES[S.ocI]) : "";
    var v2 = slotEl("vol2"); if (v2) v2.innerHTML = S.vol2 ? vol2HTML() : "";
    var to = slotEl("toast"); if (to) to.innerHTML = S.toast ? toastHTML(S.toast.t, S.toast.s) : "";
  }

  /* ---------------- behaviors ---------------- */
  var _tt;
  function fire(t, s) { clearTimeout(_tt); S.toast = { t: t, s: s }; render(); _tt = setTimeout(function () { S.toast = null; render(); }, 4200); }

  function grant(k, extraAch) {
    if (S.seals[k]) { fire("ALREADY RECOVERED", SEALNAMES[k] + " is in your archive."); return; }
    S.seals[k] = 1;
    var n = Object.keys(S.seals).length;
    if (n === 1) S.ach.first = 1;
    if (n === 7) S.ach.arch = 1;
    if (extraAch) S.ach[extraAch] = 1;
    persist(); sfx("chime");
    fire("ARTIFACT RECOVERED — " + n + " OF 7", SEALNAMES[k] + (n === 7 ? ". The restricted file is open." : ""));
  }

  var _st2;
  function openCase(i) {
    S.opened[i] = 1;
    var n = Object.keys(S.opened).length;
    var note = null;
    if (n >= 6 && !S.ach.reader) { S.ach.reader = 1; note = ["ACHIEVEMENT — CASE READER", "Six case files opened."]; }
    if (n === 12 && !S.ach.docket) { S.ach.docket = 1; note = ["ACHIEVEMENT — FULL DOCKET", "All twelve case files opened."]; }
    S.ocI = i; persist(); render();
    if (note) fire(note[0], note[1]);
    sfx("paper"); clearTimeout(_st2); _st2 = setTimeout(function () { sfx("stamp"); }, 480);
    document.body.style.overflow = "hidden";
  }

  function closeModal() { S.ocI = null; S.vol2 = false; render(); document.body.style.overflow = ""; }

  function subscribe() {
    var input = $('#acquire input[type="email"]');
    var email = input ? input.value.trim() : "";
    var cfg = window.BGF_CONFIG || {};
    var live = cfg.FORM_ACTION && /^https:\/\//.test(cfg.FORM_ACTION);
    if (!live) { fire("THE RECOVERY LIST", "Signup opens at launch — this is a preview."); return; }
    if (!email || email.indexOf("@") < 1) { fire("THE RECOVERY LIST", "Enter your email address to receive Chapter 1."); if (input) input.focus(); return; }
    if (window.BGF_TRACK_LEAD) window.BGF_TRACK_LEAD("free_chapter");
    var f = document.createElement("form");
    f.method = "post"; f.action = cfg.FORM_ACTION; f.style.display = "none";
    var em = document.createElement("input"); em.name = "email_address"; em.value = email; f.appendChild(em);
    document.body.appendChild(f); f.submit();
  }

  function share() {
    var c = S.ocI != null ? CASES[S.ocI] : null; if (!c) return;
    var url = location.origin + location.pathname + "#bgf-" + String(c.i + 1).padStart(3, "0");
    var done = function () { fire("CASE LINK COPIED", c.file + " · " + c.name + " — paste it anywhere."); };
    if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(url).then(done, function () { fire("SHARE THIS LINK", url); });
    else fire("SHARE THIS LINK", url);
  }

  /* ---- sound engine (verbatim port) ---- */
  var _ac = null, _amb = null;
  function sndInit() {
    if (_ac) return;
    try {
      var A = new (window.AudioContext || window.webkitAudioContext)();
      _ac = A;
      var len = A.sampleRate * 4, buf = A.createBuffer(1, len, A.sampleRate), d = buf.getChannelData(0);
      var last = 0;
      for (var i = 0; i < len; i++) { var w = Math.random() * 2 - 1; last = (last + 0.02 * w) / 1.02; d[i] = last * 3.5; }
      var src = A.createBufferSource(); src.buffer = buf; src.loop = true;
      var lp = A.createBiquadFilter(); lp.type = "lowpass"; lp.frequency.value = 300;
      _amb = A.createGain(); _amb.gain.value = 0;
      src.connect(lp); lp.connect(_amb); _amb.connect(A.destination);
      src.start();
    } catch (e) { _ac = null; }
  }
  function sndRamp(on) {
    if (!_ac) return;
    if (_ac.state === "suspended") _ac.resume();
    var g = _amb.gain, t = _ac.currentTime;
    g.cancelScheduledValues(t); g.setValueAtTime(g.value, t); g.linearRampToValueAtTime(on ? 0.045 : 0, t + 1.2);
  }
  function sfx(kind) {
    if (!S.snd || !_ac) return;
    var A = _ac, t = A.currentTime, out = A.destination;
    var noise = function (dur, type, freq, vol) {
      var n = A.createBufferSource(), b = A.createBuffer(1, Math.max(1, A.sampleRate * dur | 0), A.sampleRate), d = b.getChannelData(0);
      for (var i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1;
      n.buffer = b;
      var f = A.createBiquadFilter(); f.type = type; f.frequency.value = freq;
      var g = A.createGain(); g.gain.setValueAtTime(vol, t); g.gain.exponentialRampToValueAtTime(0.001, t + dur);
      n.connect(f); f.connect(g); g.connect(out); n.start(t);
    };
    var tone = function (freq, dur, vol, delay) {
      var o = A.createOscillator(); o.frequency.value = freq;
      var g = A.createGain(); g.gain.setValueAtTime(0, t + delay); g.gain.linearRampToValueAtTime(vol, t + delay + 0.015); g.gain.exponentialRampToValueAtTime(0.001, t + delay + dur);
      o.connect(g); g.connect(out); o.start(t + delay); o.stop(t + delay + dur + 0.05);
    };
    if (kind === "paper") noise(0.3, "highpass", 1100, 0.09);
    if (kind === "stamp") { noise(0.06, "lowpass", 500, 0.45); tone(75, 0.16, 0.5, 0); }
    if (kind === "chime") { tone(660, 0.7, 0.06, 0); tone(990, 0.9, 0.045, 0.09); }
  }
  function sndToggle() {
    S.snd = !S.snd;
    sndInit(); render(); sndRamp(S.snd); if (S.snd) sfx("chime");
    try { localStorage.setItem("whb_snd", S.snd ? "on" : "off"); } catch (e) {}
    fire(S.snd ? "ARCHIVE AMBIENCE — ON" : "ARCHIVE AMBIENCE — OFF", S.snd ? "Room tone and reading-room sounds enabled." : "The archive falls silent.");
  }

  function atlasMove(e) {
    var v = +e.target.value;
    var L = $("[data-atlaslayer]"); var H = $("[data-atlashandle]");
    if (L) L.style.clipPath = "inset(0 0 0 " + v + "%)";
    if (H) H.style.left = v + "%";
    if (v >= 96 && !S.atlasDone) { S.atlasDone = true; grant("c", "cart"); render(); }
  }

  function unseal() { S.ach.kon = 1; S.vol2 = true; persist(); render(); sfx("chime"); document.body.style.overflow = "hidden"; }

  /* ---------------- events (delegated) ---------------- */
  var ACTIONS = { collect: function (el) { grant(el.dataset.k); }, open: function (el) { openCase(+el.dataset.i); }, close: closeModal, subscribe: subscribe, share: share, sndToggle: sndToggle };
  document.addEventListener("click", function (ev) {
    var el = ev.target.closest("[data-act]");
    if (el && ACTIONS[el.dataset.act]) ACTIONS[el.dataset.act](el);
  });
  document.addEventListener("input", function (ev) {
    var el = ev.target.closest('[data-act-input="atlasMove"]');
    if (el) atlasMove(ev);
  });

  /* ---------------- mount ---------------- */
  function mount() {
    var tl = slotEl("tl"); if (tl) tl.innerHTML = tlHTML();
    render();

    var rm = matchMedia("(prefers-reduced-motion: reduce)").matches;

    // reveal-on-scroll with fail-open fallbacks (verbatim port)
    if (!rm) {
      var els = $$("[data-reveal]");
      var pending = new Set(els);
      var ob = null;
      var show = function (el) { el.style.opacity = "1"; el.style.transform = "none"; pending.delete(el); if (ob) ob.unobserve(el); };
      els.forEach(function (el) {
        el.style.opacity = "0"; el.style.transform = "translateY(28px)";
        el.style.transition = "opacity .9s cubic-bezier(.2,.7,.2,1), transform .9s cubic-bezier(.2,.7,.2,1)";
        el.style.transitionDelay = (el.dataset.reveal || 0) + "ms";
      });
      try {
        ob = new IntersectionObserver(function (en) { en.forEach(function (x) { if (x.isIntersecting) show(x.target); }); }, { threshold: 0.15, rootMargin: "0px 0px -6% 0px" });
        els.forEach(function (el) { ob.observe(el); });
      } catch (e) {}
      var sweep = function () { pending.forEach(function (el) { var r = el.getBoundingClientRect(); if (r.top < innerHeight * 1.05 && r.bottom > -40) show(el); }); };
      addEventListener("scroll", sweep, { passive: true });
      addEventListener("resize", sweep, { passive: true });
      setTimeout(sweep, 350);
      setTimeout(function () { pending.forEach(function (el) { show(el); }); }, 6000);
    }

    // dust
    if (!rm) mountDust();

    // konami + escape
    var seq = ["ArrowUp", "ArrowUp", "ArrowDown", "ArrowDown", "ArrowLeft", "ArrowRight", "ArrowLeft", "ArrowRight", "b", "a"];
    var ki = 0;
    addEventListener("keydown", function (e) {
      if (e.key === "Escape" && (S.ocI != null || S.vol2)) { closeModal(); return; }
      var key = e.key.length === 1 ? e.key.toLowerCase() : e.key;
      if (key === seq[ki]) { ki++; if (ki === seq.length) { ki = 0; unseal(); } }
      else ki = (key === seq[0]) ? 1 : 0;
    });

    // Touch equivalent of the konami code: swipe up-up-down-down-left-right-
    // left-right, then two quick taps (mirrors "B A" — the hint text's arrows
    // read the same way as swipe directions). Passive listeners; scrolling
    // and normal taps still behave exactly as before.
    var touchSeq = ["up", "up", "down", "down", "left", "right", "left", "right", "tap", "tap"];
    var ti = 0, tsx, tsy, tst;
    var SWIPE_MIN = 40, TAP_MAX = 12, TAP_MAX_MS = 350;
    addEventListener("touchstart", function (e) {
      var t = e.touches && e.touches[0]; if (!t) return;
      tsx = t.clientX; tsy = t.clientY; tst = Date.now();
    }, { passive: true });
    addEventListener("touchend", function (e) {
      if (tsx == null) return;
      var t = e.changedTouches && e.changedTouches[0]; if (!t) { tsx = null; return; }
      var dx = t.clientX - tsx, dy = t.clientY - tsy, dt = Date.now() - tst;
      tsx = null;
      var token;
      if (Math.abs(dx) < TAP_MAX && Math.abs(dy) < TAP_MAX && dt < TAP_MAX_MS) token = "tap";
      else if (Math.max(Math.abs(dx), Math.abs(dy)) >= SWIPE_MIN) token = Math.abs(dx) > Math.abs(dy) ? (dx > 0 ? "right" : "left") : (dy > 0 ? "down" : "up");
      else return; // ambiguous drag — ignore without disturbing progress
      if (token === touchSeq[ti]) { ti++; if (ti === touchSeq.length) { ti = 0; unseal(); } }
      else ti = (token === touchSeq[0]) ? 1 : 0;
    }, { passive: true });

    // progress bar + hero parallax
    var sc = function () {
      var h = document.documentElement;
      var p = h.scrollTop / ((h.scrollHeight - h.clientHeight) || 1) * 100;
      var bar = $("[data-prog]"); if (bar) bar.style.width = p + "%";
      var hi = $("[data-heroimg]");
      if (hi && !rm) { var y = Math.min(h.scrollTop, 1000); hi.style.transform = "translateY(" + (y * 0.16) + "px)"; }
    };
    addEventListener("scroll", sc, { passive: true });
    sc();

    // deep link #bgf-NNN
    var dm = location.hash.match(/^#bgf-0*(\d{1,3})$/i);
    if (dm && CASES[+dm[1] - 1]) setTimeout(function () { openCase(+dm[1] - 1); }, 700);

    // spine visibility
    var spfit = function () { var sp = $("[data-spine]"); if (sp) sp.style.display = innerWidth < 1120 ? "none" : "flex"; };
    spfit(); addEventListener("resize", spfit);

    // resume stored ambience on first gesture
    if (S.snd) {
      var once = function () { sndInit(); sndRamp(true); removeEventListener("pointerdown", once); removeEventListener("keydown", once); };
      addEventListener("pointerdown", once); addEventListener("keydown", once);
    }
  }

  function mountDust() {
    var c = $("[data-dust]"); if (!c) return;
    var x = c.getContext("2d"); var w, h;
    var fit = function () { w = c.width = innerWidth; h = c.height = innerHeight; };
    fit(); addEventListener("resize", fit);
    var ps = [];
    for (var i = 0; i < 64; i++) ps.push({ x: Math.random(), y: Math.random(), r: 0.5 + Math.random() * 1.7, s: 0.12 + Math.random() * 0.3, o: 0.06 + Math.random() * 0.22, ph: Math.random() * 6.28 });
    var tick = function (t) {
      x.clearRect(0, 0, w, h);
      for (var j = 0; j < ps.length; j++) {
        var p = ps[j];
        p.y -= p.s / h; p.x += Math.sin(t / 2800 + p.ph) * 0.00016;
        if (p.y < -0.02) { p.y = 1.02; p.x = Math.random(); }
        x.globalAlpha = p.o * (0.55 + 0.45 * Math.sin(t / 950 + p.ph));
        x.fillStyle = "#e7b24e";
        x.beginPath(); x.arc(p.x * w, p.y * h, p.r, 0, 6.283); x.fill();
      }
      requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", mount);
  else mount();
})();
