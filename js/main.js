// CasinoForensicsUnit — small, dependency-free script.
// 1) mobile menu  2) render casino records from data/casinos.json (only fully sourced ones)

(function () {
  // ---- Mobile menu ----
  var toggle = document.querySelector('.nav-toggle');
  var list = document.getElementById('nav-list');
  if (toggle && list) {
    toggle.addEventListener('click', function () {
      var open = list.classList.toggle('open');
      toggle.setAttribute('aria-expanded', String(open));
    });
  }

  // ---- Casino list ----
  var target = document.getElementById('casino-list');
  if (!target) return;

  // Every field we display must come with a source and a "verified on" date.
  // A record missing either is NOT shown, so unsourced claims can never appear on the site.
  var FIELDS = [
    ['license', 'License'],
    ['redemptionTest', 'Redemption / withdrawal test'],
    ['termsReviewed', 'Terms reviewed'],
    ['stateAvailability', 'Availability']
  ];

  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text; // textContent: never inject raw HTML
    return e;
  }

  function isSafeUrl(u) { return typeof u === 'string' && /^https:\/\//i.test(u); }

  function validRecord(c) {
    if (!c || !c.name || !c.verifiedOn || c.status !== 'verified') return false;
    if (c.type !== 'real-money' && c.type !== 'sweepstakes') return false;
    if (!Array.isArray(c.payoutMethods) || !c.payoutMethods.length) return false;
    return FIELDS.every(function (f) {
      var v = c[f[0]];
      return v && v.value && isSafeUrl(v.sourceUrl) && v.checkedOn;
    });
  }

  fetch('data/casinos.json', { cache: 'no-store' })
    .then(function (r) { return r.json(); })
    .then(function (data) {
      var records = (data && data.casinos) || [];
      var good = records.filter(function (c) {
        var ok = validRecord(c);
        if (!ok) console.warn('CFU: skipped record without full sourcing:', c && c.name);
        return ok;
      });
      if (!good.length) return; // keep the built-in empty state
      target.innerHTML = '';
      good.forEach(function (c) {
        var card = el('article', 'frame c-teal casino-card');
        card.appendChild(el('span', 'stamp verified', 'CFU Verified · ' + c.verifiedOn));
        card.appendChild(el('h3', null, c.name));
        card.appendChild(el('p', 'source', (c.type === 'sweepstakes' ? 'Sweepstakes casino' : 'Real-money casino') + ' · Payouts: ' + c.payoutMethods.join(', ')));
        var dl = el('dl');
        FIELDS.forEach(function (f) {
          var v = c[f[0]];
          dl.appendChild(el('dt', null, f[1]));
          var dd = el('dd', null, v.value + ' ');
          var a = el('a', 'source', '(source, checked ' + v.checkedOn + ')');
          a.href = v.sourceUrl; a.rel = 'noopener nofollow'; a.target = '_blank';
          dd.appendChild(a);
          dl.appendChild(dd);
        });
        card.appendChild(dl);
        target.appendChild(card);
      });
    })
    .catch(function () { /* leave the empty state in place */ });
})();
