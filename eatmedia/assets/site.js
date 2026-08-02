document.querySelectorAll('[data-year]').forEach(function (el) {
  el.textContent = new Date().getFullYear();
});

var navToggle = document.querySelector('.nav-toggle');
var nav = document.querySelector('nav.primary');
if (navToggle && nav) {
  navToggle.addEventListener('click', function () {
    var open = nav.classList.toggle('open');
    navToggle.setAttribute('aria-expanded', open ? 'true' : 'false');
  });
  nav.querySelectorAll('a').forEach(function (a) {
    a.addEventListener('click', function () {
      nav.classList.remove('open');
      navToggle.setAttribute('aria-expanded', 'false');
    });
  });
}

if (!window.matchMedia('(prefers-reduced-motion: reduce)').matches && 'IntersectionObserver' in window) {
  var revealEls = document.querySelectorAll('main section:not(.hero)');
  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (entry.isIntersecting) {
        entry.target.classList.add('in-view');
        io.unobserve(entry.target);
      }
    });
  }, { threshold: 0.1, rootMargin: '0px 0px -40px 0px' });
  revealEls.forEach(function (el) {
    el.classList.add('reveal');
    io.observe(el);
  });
}

var heroFrame = document.getElementById('hero-video');
if (heroFrame) {
  var revealHero = function () { heroFrame.classList.add('is-ready'); };
  heroFrame.addEventListener('load', revealHero);
  // Safety net: reveal the video even if the load event never fires,
  // so the hero never gets stuck showing only the poster image.
  setTimeout(revealHero, 4000);

  // The loop=1 query param is not always reliable on its own for embedded
  // Vimeo iframes; the Player SDK's 'ended' handler is the documented,
  // dependable way to guarantee looping. Falls back to native loop=1 if
  // the SDK fails to load (e.g. blocked by an ad/privacy blocker).
  if (window.Vimeo && window.Vimeo.Player) {
    try {
      var heroPlayer = new window.Vimeo.Player(heroFrame);
      heroPlayer.on('ended', function () { heroPlayer.play(); });
    } catch (e) {
      /* native loop=1 still applies */
    }
  }
}
