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

    document.getElementById('moon').innerHTML =
      '<div class="moon-phase">' +
        '<span class="moon-glyph">' + esc(moon.phase_glyph) + '</span>' +
        '<span class="moon-name">' + esc(moon.phase_name) + '</span>' +
        '<span class="moon-illum">' + esc(String(moon.illumination_pct)) + '% lit</span>' +
      '</div>' +
      timesRow;
  }

  function renderSkymap(svg) {
    var doc = new DOMParser().parseFromString(svg, 'image/svg+xml');
    var svgEl = doc.documentElement;
    var container = document.getElementById('skymap');
    container.innerHTML = '';
    container.appendChild(document.importNode(svgEl, true));
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
    container.innerHTML = sorted.map(function (c) {
      var cls    = c.above_horizon ? 'above' : 'below';
      var marker = c.above_horizon ? '▲' : '▽';
      return '<span class="const-chip ' + cls + '">' +
        '<span class="const-marker">' + marker + '</span>' +
        '<span class="const-name">' + esc(c.name) + '</span>' +
        '<span class="const-abbr">' + esc(c.abbr) + '</span>' +
      '</span>';
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

  function render(data, lat, lon) {
    setCoords(lat, lon);
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
