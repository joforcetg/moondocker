(function () {
  'use strict';

  function esc(s) {
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function setStatus(msg, isError, loading) {
    var el = document.getElementById('status');
    el.className = isError ? 'error' : '';
    el.textContent = msg;
    if (loading) {
      var cur = document.createElement('span');
      cur.className = 'cursor';
      cur.textContent = '▊';
      el.appendChild(cur);
    }
  }

  function setCoords(lat, lon) {
    var el = document.getElementById('coords');
    el.textContent = Number(lat).toFixed(3) + ', ' + Number(lon).toFixed(3);
  }

  function fetchSky(lat, lon) {
    setStatus('fetching sky data… ', false, true);
    fetch('/api/sky?lat=' + lat + '&lon=' + lon)
      .then(function (r) {
        if (!r.ok) throw new Error('server error ' + r.status);
        return r.json();
      })
      .then(function (data) { render(data, lat, lon); })
      .catch(function (err) {
        setStatus('error: ' + err.message, true);
      });
  }

  function moonSvg(illumPct, phaseName) {
    var C = 50, R = 46;
    var f = Math.max(0, Math.min(1, Number(illumPct) / 100));
    var n = String(phaseName || '').toLowerCase();
    var waxing = n.indexOf('waxing') >= 0 || n.indexOf('first') >= 0;
    var rx = R * (1 - 2 * f);                 // >0 crescent, <0 gibbous, 0 quarter
    var limbSweep = waxing ? 1 : 0;           // lit limb on lit side
    var termSweep = waxing ? (rx < 0 ? 1 : 0) // terminator bulge direction
                           : (rx < 0 ? 0 : 1);
    var top = C - R, bot = C + R;
    var d = 'M' + C + ',' + top +
            ' A' + R + ',' + R + ' 0 0,' + limbSweep + ' ' + C + ',' + bot +
            ' A' + Math.abs(rx).toFixed(2) + ',' + R + ' 0 0,' + termSweep + ' ' + C + ',' + top +
            ' Z';
    return '<svg class="moon-svg" viewBox="0 0 100 100" width="100" height="100" ' +
             'xmlns="http://www.w3.org/2000/svg" aria-hidden="true">' +
             '<circle class="moon-shadow" cx="50" cy="50" r="46"/>' +
             '<path class="moon-lit" d="' + d + '"/>' +
             '<circle class="moon-limb" cx="50" cy="50" r="46"/>' +
           '</svg>';
  }

  function renderMoon(moon) {
    var rise    = moon.rise    || '—';
    var transit = moon.transit || '—';
    var set     = moon.set     || '—';

    var timesRow = moon.note
      ? '<div class="moon-note">' + esc(moon.note) + '</div>'
      : '<div class="moon-times">' +
          '<span><span class="dim">rise</span> <span class="val">' + esc(rise) + '</span></span>' +
          '<span><span class="dim">transit</span> <span class="val">' + esc(transit) + '</span></span>' +
          '<span><span class="dim">set</span> <span class="val">' + esc(set) + '</span></span>' +
        '</div>';

    var nextRow = '';
    if (moon.next_full_in_days != null || moon.next_new_in_days != null) {
      var parts = [];
      if (moon.next_full_in_days != null)
        parts.push('<span><span class="dim">full in</span> <span class="val">' +
                   esc(String(moon.next_full_in_days)) + 'd</span></span>');
      if (moon.next_new_in_days != null)
        parts.push('<span><span class="dim">new in</span> <span class="val">' +
                   esc(String(moon.next_new_in_days)) + 'd</span></span>');
      nextRow = '<div class="moon-next">' + parts.join('') + '</div>';
    }

    var el = document.getElementById('moon');
    el.innerHTML =
      '<div class="moon-phase">' +
        '<span class="moon-glyph"></span>' +
        '<span class="moon-name">' + esc(moon.phase_name) + '</span>' +
        '<span class="moon-illum">' + esc(String(moon.illumination_pct)) + '% lit</span>' +
      '</div>' + timesRow + nextRow;

    // inject the SVG moon via DOMParser (computed numbers only, no untrusted data)
    var glyph = el.querySelector('.moon-glyph');
    var doc = new DOMParser().parseFromString(
      moonSvg(moon.illumination_pct, moon.phase_name), 'image/svg+xml');
    glyph.appendChild(document.importNode(doc.documentElement, true));
  }

  function renderSkymap(svg) {
    var doc = new DOMParser().parseFromString(svg, 'image/svg+xml');
    var svgEl = doc.documentElement;
    var container = document.getElementById('skymap');
    container.innerHTML = '';
    container.appendChild(document.importNode(svgEl, true));
  }

  function renderLegendDefault(legend) {
    document.getElementById('legend-hdr').textContent =
      legend.title ? 'Legend : ' + legend.title : 'Legend';
    var el = document.getElementById('legend');
    el.innerHTML = '';
    if (legend.culture) {
      var cul = document.createElement('div');
      cul.className = 'legend-culture';
      cul.textContent = legend.culture;
      el.appendChild(cul);
    }
    var p = document.createElement('p');
    p.className = 'myth-text';
    p.textContent = legend.text || '';
    el.appendChild(p);
  }

  function renderMythFigure(image) {
    if (!image || !image.url) return null;
    var fig = document.createElement('figure');
    fig.className = 'myth-figure';
    var img = document.createElement('img');
    img.src = image.url;
    img.alt = image.title || '';
    img.loading = 'lazy';
    fig.appendChild(img);
    var cap = document.createElement('figcaption');
    var bits = [image.title, image.author, image.license].filter(Boolean).join(' · ');
    if (image.credit_url) {
      var a = document.createElement('a');
      a.href = image.credit_url; a.target = '_blank'; a.rel = 'noopener';
      a.textContent = bits || 'Wikimedia Commons';
      cap.appendChild(a);
    } else {
      cap.textContent = bits;
    }
    fig.appendChild(cap);
    return fig;
  }

  function showConstellationMyth(name) {
    fetch('/api/myth/' + encodeURIComponent(name))
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (m) {
        if (!m || !m.text) return;
        document.getElementById('legend-hdr').textContent = 'Legend : ' + name;
        var el = document.getElementById('legend');
        el.innerHTML = '';
        if (m.title) {
          var h = document.createElement('div');
          h.className = 'myth-title';
          h.textContent = m.title;
          el.appendChild(h);
        }
        var p = document.createElement('p');
        p.className = 'myth-text';
        p.textContent = m.text;
        el.appendChild(p);
        var fig = renderMythFigure(m.image);
        if (fig) el.appendChild(fig);
      })
      .catch(function () { /* text stays; no user-facing error */ });
  }

  var activeConst = null;
  var defaultLegend = null;

  function clearHighlight() {
    var sky = document.getElementById('skymap');
    sky.classList.remove('has-hl');
    sky.querySelectorAll('.hl').forEach(function (n) { n.classList.remove('hl'); });
  }

  function highlight(name) {
    var sky = document.getElementById('skymap');
    var sel = '[data-constellation~="' + name.replace(/"/g, '\\"') + '"]';
    var nodes = sky.querySelectorAll(sel);
    if (!nodes.length) return;
    sky.classList.add('has-hl');
    nodes.forEach(function (n) { n.classList.add('hl'); });
  }

  function selectConstellation(name, card) {
    if (activeConst === name) {           // re-click → back to default
      deselect();
      return;
    }
    deselect();
    activeConst = name;
    card.classList.add('active');
    highlight(name);
    showConstellationMyth(name);
  }

  function deselect() {
    if (activeConst) {
      var prev = document.querySelector('.const-card.active');
      if (prev) prev.classList.remove('active');
    }
    activeConst = null;
    clearHighlight();
    if (defaultLegend) renderLegendDefault(defaultLegend);
  }

  function renderConstellations(list) {
    var container = document.getElementById('constellations');
    if (!list.length) {
      container.innerHTML = '<span class="const-empty">none visible</span>';
      return;
    }
    var sorted = list.slice().sort(function (a, b) {
      return (b.above_horizon ? 1 : 0) - (a.above_horizon ? 1 : 0);
    });
    container.innerHTML = '';
    sorted.forEach(function (c) {
      var card = document.createElement('div');
      card.className = 'const-card ' + (c.above_horizon ? 'above' : 'below') +
                       (c.has_myth ? '' : ' no-myth');
      card.innerHTML =
        '<span class="const-marker">' + (c.above_horizon ? '▲' : '▽') + '</span>' +
        '<span class="const-name"></span>' +
        '<span class="const-abbr"></span>';
      card.querySelector('.const-name').textContent = c.name;
      card.querySelector('.const-abbr').textContent = c.abbr;
      if (c.has_myth) {
        card.setAttribute('role', 'button');
        card.setAttribute('tabindex', '0');
        card.addEventListener('click', function () { selectConstellation(c.name, card); });
        card.addEventListener('keydown', function (e) {
          if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); selectConstellation(c.name, card); }
        });
      }
      container.appendChild(card);
    });
  }

  function render(data, lat, lon) {
    setCoords(lat, lon);
    activeConst = null;
    defaultLegend = data.legend;
    renderMoon(data.moon);
    renderSkymap(data.skymap_svg);
    renderConstellations(data.constellations);
    renderLegendDefault(data.legend);
    document.getElementById('status').textContent = '';
    document.getElementById('panels').hidden = false;
  }

  function noLocation() {
    setStatus(
      'location unavailable — set LAT and LON env vars and restart the container',
      true
    );
  }

  function tryFallback() {
    var fb = window.__FALLBACK__;
    if (fb && fb.lat !== null && fb.lon !== null) {
      fetchSky(fb.lat, fb.lon);
    } else {
      noLocation();
    }
  }

  function init() {
    if (navigator.geolocation) {
      setStatus('locating… ', false, true);
      navigator.geolocation.getCurrentPosition(
        function (pos) { fetchSky(pos.coords.latitude, pos.coords.longitude); },
        tryFallback
      );
    } else {
      tryFallback();
    }
  }

  document.addEventListener('DOMContentLoaded', init);
}());
