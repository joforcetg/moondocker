# Mobile UI Optimisation — Design Spec

**Date:** 2026-06-20
**Status:** Approved
**Approach:** A — CSS polish + scroll-to-legend (minimal diff)

## Problem

The existing layout is mobile-first in structure (single column, `viewport` meta, `clamp()` fonts) but has six concrete gaps that degrade the experience on touch devices:

1. Constellation cards have sub-44px touch targets (`0.25rem 0.55rem` padding → ~28px height).
2. No `touch-action: manipulation` on interactive cards — 300ms tap delay on old Android.
3. No `:active` visual feedback on tap (only `:hover`/`:focus-visible` states exist).
4. `.moon-next` spans lack the mobile margin reduction that `.moon-times` already has at `max-width: 480px`.
5. No `env(safe-area-inset-*)` support — content hidden behind iOS notch / home-indicator.
6. Selecting a constellation updates the legend panel off-screen; user must manually scroll down.
7. On 320px screens the topbar wordmark and coords can collide.

## Scope

Two files only: `app/static/style.css`, `app/static/app.js`. No HTML changes. No new dependencies. All 64 backend tests unaffected.

## Changes

### style.css

**1. Touch targets — constellation cards**

```css
.const-card[role="button"] {
  min-height: 44px;
  align-items: center;
  touch-action: manipulation;
  padding: 0.4rem 0.7rem;
}
```

Raises touch target to WCAG 2.5.5 minimum (44×44 px). `touch-action: manipulation` suppresses double-tap zoom and eliminates 300ms click delay without blocking scroll.

**2. Active / press state**

```css
.const-card[role="button"]:active {
  background: rgba(255, 255, 255, 0.04);
}
```

Instant visual confirmation on tap, matching the dark theme.

**3. moon-next mobile margins (inside existing `@media (max-width: 480px)` block)**

```css
.moon-next span { margin-right: 1rem; display: inline-block; }
```

Mirrors the existing `.moon-times span` fix at the same breakpoint, preventing overflow of "full in Xd / new in Xd" on 320–375px screens.

**4. iOS safe-area insets**

```css
@supports (padding: env(safe-area-inset-bottom)) {
  body {
    padding-left:   max(1.25rem, env(safe-area-inset-left));
    padding-right:  max(1.25rem, env(safe-area-inset-right));
    padding-bottom: max(1.25rem, env(safe-area-inset-bottom));
  }
}
```

Degrades gracefully on browsers without `env()` support.

**5. Narrow-screen topbar (320px)**

```css
@media (max-width: 380px) {
  .coords { display: none; }
}
```

At 320px the wordmark ("Moonseek" in Fraktur at ~1.5rem) and the lat/lon string collide. Hiding coords at this breakpoint is acceptable — the coords are decorative metadata; the lat/lon is already shown to the user by the browser geolocation permission prompt and is not navigational content.

### app.js

**6. Scroll-to-legend on constellation selection**

Inside `selectConstellation()`, after `showConstellationMyth(name)`:

```js
var legendPanel = document.getElementById('legend').closest('.panel');
if (legendPanel) legendPanel.scrollIntoView({ behavior: 'smooth', block: 'start' });
```

`scrollIntoView` with `behavior: 'smooth'` is supported in all modern mobile browsers. On desktop the legend is already in the viewport (right column), so scroll is a no-op. The guard (`if (legendPanel)`) prevents errors if the DOM structure ever changes.

## What is NOT changed

- Layout structure (single column mobile, two-column desktop at ≥900px) — already correct.
- Sky map sizing (`min(520px, 70vh)`) — already responsive.
- Font sizes (`clamp()`) — already responsive.
- Topbar flex layout — already wraps correctly above 380px.
- Backend, API, tests — untouched.

## Success criteria

- Constellation cards measure ≥44px tall on a 375px-wide viewport (Chrome DevTools mobile emulation).
- Tapping a card shows immediate background change (`:active`).
- Selecting a constellation smoothly scrolls the legend panel into view on mobile.
- No horizontal scroll at 320px viewport width.
- On iOS (or Safari with `env()` support), body bottom padding accounts for home-indicator.
- All 64 tests pass.
