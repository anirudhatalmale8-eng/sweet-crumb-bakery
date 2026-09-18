/* ═══════════════════════════════════════════════════════════
   Sweet Crumb — small bits of behaviour, no dependencies.
   1. reveal-on-scroll   2. sticky bar shadow   3. mobile nav
   4. "open now" chip    5. today's row in the hours table
   ═══════════════════════════════════════════════════════════ */
(function () {
  'use strict';

  /* ── 1. reveal on scroll ─────────────────────────────────
     A rAF-throttled sweep rather than IntersectionObserver: IO
     reports nothing when an element goes from "below the fold" to
     "above the fold" between two frames (both states are simply
     "not intersecting"), so a fast flick or a jump to a #hash can
     leave things stranded at opacity 0. This samples position
     instead, so anything already scrolled past is revealed too. */
  var pending = [].slice.call(document.querySelectorAll('.r'));
  var queued = false;

  function sweep() {
    queued = false;
    var h = window.innerHeight || document.documentElement.clientHeight;
    pending = pending.filter(function (el) {
      var box = el.getBoundingClientRect();
      var inView = box.top < h * 0.92 && box.bottom > 0;
      if (inView || box.bottom <= 0) { el.classList.add('in'); return false; }
      return true;
    });
    if (!pending.length) {
      window.removeEventListener('scroll', request);
      window.removeEventListener('resize', request);
    }
  }
  function request() {
    if (queued || !pending.length) return;
    queued = true;
    requestAnimationFrame(sweep);
  }
  window.addEventListener('scroll', request, { passive: true });
  window.addEventListener('resize', request);
  sweep();

  /* ── 2. sticky bar gets a shadow once you scroll ─────── */
  var bar = document.getElementById('bar');
  var onScroll = function () {
    bar.classList.toggle('is-stuck', window.scrollY > 12);
  };
  onScroll();
  window.addEventListener('scroll', onScroll, { passive: true });

  /* ── 3. mobile nav ───────────────────────────────────── */
  var burger = document.getElementById('burger');
  var nav = document.getElementById('nav');
  var setNav = function (open) {
    nav.classList.toggle('is-open', open);
    burger.setAttribute('aria-expanded', String(open));
  };
  burger.addEventListener('click', function () {
    setNav(burger.getAttribute('aria-expanded') !== 'true');
  });
  nav.addEventListener('click', function (e) {
    if (e.target.closest('a')) setNav(false);
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') setNav(false);
  });

  /* ── 4 & 5. shop clock, always in India time ─────────── */
  var OPEN_HOUR = 8;      // 8:00
  var CLOSE_HOUR = 20;    // 20:00
  var DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

  function puneNow() {
    // Read the wall clock in Asia/Kolkata so the badge is right
    // for the shop, whatever timezone the visitor is in.
    try {
      var parts = new Intl.DateTimeFormat('en-GB', {
        timeZone: 'Asia/Kolkata',
        weekday: 'short', hour: '2-digit', minute: '2-digit', hour12: false
      }).formatToParts(new Date());
      var get = function (t) {
        var p = parts.find(function (x) { return x.type === t; });
        return p ? p.value : '';
      };
      var dayIndex = DAYS.indexOf(get('weekday').slice(0, 3));
      var hour = parseInt(get('hour'), 10);
      if (dayIndex < 0 || isNaN(hour)) throw new Error('unparsed');
      return { day: dayIndex, hour: hour === 24 ? 0 : hour, minute: parseInt(get('minute'), 10) || 0 };
    } catch (err) {
      var d = new Date();
      return { day: d.getDay(), hour: d.getHours(), minute: d.getMinutes() };
    }
  }

  function paintClock() {
    var now = puneNow();
    var minutes = now.hour * 60 + now.minute;
    var isOpen = minutes >= OPEN_HOUR * 60 && minutes < CLOSE_HOUR * 60;

    var chip = document.getElementById('openChip');
    var label = document.getElementById('openLabel');
    if (chip && label) {
      chip.classList.toggle('is-shut', !isOpen);
      label.textContent = isOpen
        ? chip.getAttribute('data-open-text')
        : chip.getAttribute('data-shut-text');
      chip.title = isOpen
        ? 'We close at 8:00 pm'
        : (minutes < OPEN_HOUR * 60 ? 'We open at 8:00 am' : 'Back at 8:00 am tomorrow');
    }

    var rows = document.querySelectorAll('#hours tr');
    rows.forEach(function (tr) {
      tr.classList.toggle('is-today', Number(tr.dataset.day) === now.day);
    });
  }
  paintClock();
  setInterval(paintClock, 60000);

  /* footer year */
  var yr = document.getElementById('yr');
  if (yr) yr.textContent = new Date().getFullYear();
})();
