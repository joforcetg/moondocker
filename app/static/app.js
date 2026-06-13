(function () {
  'use strict';

  function esc(s) {
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function setStatus(msg, isError) {
    var el = document.getElementById('status');
    el.textContent = msg;
    el.className = isError ? 'error' : '';
  }

  function fetchSky(lat, lon) {
    setStatus('fetching sky data…');
    fetch('/api/sky?lat=' + lat + '&lon=' + lon)
      .then(function (r) {
        if (!r.ok) throw new Error('server error ' + r.status);
        return r.json();
      })
      .then(render)
      .catch(function (err) {
        setStatus('error: ' + err.message, true);
      });
  }

  function renderMoon(moon) {
    var rise    = moon.rise    || '—';
    var transit = moon.transit || '—';
    var set     = moon.set     || '—';

    document.getElementById('moon').innerHTML =
      '<div class="moon-phase">' +
        '<span class="moon-glyph">' + esc(moon.phase_glyph) + '</span>' +
        '<span>' + esc(moon.phase_name) + '</span>' +
        '<span class="dim">illumination:</span>' +
        '<span>' + esc(String(moon.illumination_pct)) + '%</span>' +
      '</div>' +
      '<div class="moon-times">' +
        '<span><span class="dim">rise</span> ' + esc(rise) + '</span>' +
        '<span><span class="dim">transit</span> ' + esc(transit) + '</span>' +
        '<span><span class="dim">set</span> ' + esc(set) + '</span>' +
      '</div>';
  }

  function renderSkymap(svg) {
    var doc = new DOMParser().parseFromString(svg, 'image/svg+xml');
    var svgEl = doc.documentElement;
    var container = document.getElementById('skymap');
    container.innerHTML = '';
    container.appendChild(document.importNode(svgEl, true));
  }

  function renderConstellations(list) {
    if (!list.length) {
      document.getElementById('constellations').textContent = 'none visible';
      return;
    }
    var sorted = list.slice().sort(function (a, b) {
      return (b.above_horizon ? 1 : 0) - (a.above_horizon ? 1 : 0);
    });
    document.getElementById('constellations').innerHTML = sorted.map(function (c) {
      var cls    = c.above_horizon ? 'above' : 'below';
      var marker = c.above_horizon ? '▲' : '▽';
      return '<div class="const-row">' +
        '<span class="const-marker ' + cls + '">' + marker + '</span>' +
        '<span class="const-name">' + esc(c.name) + '</span>' +
        '<span class="const-abbr">(' + esc(c.abbr) + ')</span>' +
      '</div>';
    }).join('');
  }

  function renderMythology(myth) {
    document.getElementById('legend-hdr').textContent =
      'ᛚᛖᚷᛖᚾᛞ : ' + myth.constellation;
    var p = document.createElement('p');
    p.className = 'myth-text';
    p.textContent = myth.text;
    var el = document.getElementById('legend');
    el.innerHTML = '';
    el.appendChild(p);
  }

  function render(data) {
    renderMoon(data.moon);
    renderSkymap(data.skymap_svg);
    renderConstellations(data.constellations);
    renderMythology(data.mythology);
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
      setStatus('locating…');
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
