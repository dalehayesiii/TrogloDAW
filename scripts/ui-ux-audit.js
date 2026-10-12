/* ui-ux-audit measurement engine.
 * Runs INSIDE the target page via mcp__claude-in-chrome__javascript_tool.
 * Measures the checkable, numeric rules a screenshot can't (contrast ratios,
 * tap-target px, off-grid spacing, near-miss misalignment, layout-triggering
 * animation, focus/reduced-motion handling). Returns a JSON string.
 *
 * Thresholds are sourced (WCAG 2.2, Material, web.dev) — see SKILL.md.
 * Every check is wrapped so one failure can't kill the run.
 */
(() => {
  const OUT = { viewport: { w: innerWidth, h: innerHeight, dpr: devicePixelRatio }, checks: {}, errors: [] };
  const safe = (name, fn) => { try { OUT.checks[name] = fn(); } catch (e) { OUT.errors.push(name + ': ' + e.message); } };
  const round = (n) => Math.round(n * 100) / 100;

  // ---- helpers ----
  const vis = (el) => {
    const s = getComputedStyle(el), r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none' && s.opacity !== '0';
  };
  const allEls = [...document.querySelectorAll('body *')].slice(0, 6000);
  const visEls = allEls.filter((el) => { try { return vis(el); } catch { return false; } });

  const sel = (el) => {
    if (!el || el === document.body) return 'body';
    let s = el.tagName.toLowerCase();
    if (el.id) return s + '#' + el.id;
    const c = (el.className && typeof el.className === 'string') ? el.className.trim().split(/\s+/).slice(0, 2).join('.') : '';
    if (c) s += '.' + c;
    return s;
  };
  const locate = (el) => {
    const path = [sel(el)];
    let p = el.parentElement, hops = 0;
    while (p && p !== document.body && hops < 2) { path.unshift(sel(p)); p = p.parentElement; hops++; }
    const txt = (el.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 40);
    return path.join(' > ') + (txt ? ` — "${txt}"` : '');
  };

  const parseColor = (str) => {
    const m = str && str.match(/rgba?\(([^)]+)\)/);
    if (!m) return null;
    const p = m[1].split(',').map((x) => parseFloat(x));
    return { r: p[0], g: p[1], b: p[2], a: p[3] === undefined ? 1 : p[3] };
  };
  const over = (fg, bg) => { // composite fg (may be semi-transparent) over bg (opaque)
    const a = fg.a;
    return { r: fg.r * a + bg.r * (1 - a), g: fg.g * a + bg.g * (1 - a), b: fg.b * a + bg.b * (1 - a), a: 1 };
  };
  const lum = ({ r, g, b }) => {
    const f = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b);
  };
  const ratio = (a, b) => { const L1 = lum(a), L2 = lum(b), hi = Math.max(L1, L2), lo = Math.min(L1, L2); return (hi + 0.05) / (lo + 0.05); };
  const effBg = (el) => { // walk up compositing until opaque, default white
    let acc = { r: 255, g: 255, b: 255, a: 1 }, node = el, found = false;
    const stack = [];
    while (node && node !== document.documentElement) {
      const c = parseColor(getComputedStyle(node).backgroundColor);
      if (c && c.a > 0) { stack.push(c); if (c.a === 1) { found = true; break; } }
      node = node.parentElement;
    }
    if (!found) stack.push({ r: 255, g: 255, b: 255, a: 1 });
    // composite from bottom (opaque) up to topmost
    acc = stack.pop();
    while (stack.length) acc = over(stack.pop(), acc);
    return acc;
  };

  // ---- 1. Contrast (WCAG 1.4.3): text 4.5:1, large text 3:1 ----
  safe('contrast', () => {
    const fails = [], seen = new Set();
    let checked = 0;
    for (const el of visEls) {
      if (checked > 1200) break;
      const hasText = [...el.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim().length > 1);
      if (!hasText) continue;
      checked++;
      const cs = getComputedStyle(el);
      const fg = parseColor(cs.color); if (!fg) continue;
      const bg = effBg(el);
      const fgc = fg.a < 1 ? over(fg, bg) : fg;
      const size = parseFloat(cs.fontSize), weight = parseInt(cs.fontWeight) || 400;
      const large = size >= 24 || (size >= 18.66 && weight >= 700);
      const min = large ? 3 : 4.5;
      const cr = ratio(fgc, bg);
      if (cr < min) {
        const key = round(cr) + '|' + Math.round(size) + '|' + cs.color;
        if (seen.has(key)) continue; seen.add(key);
        fails.push({ ratio: round(cr), required: min, fontPx: round(size), weight, color: cs.color, where: locate(el) });
      }
    }
    fails.sort((a, b) => a.ratio - b.ratio);
    return { checked, failCount: fails.length, worst: fails.slice(0, 25) };
  });

  // ---- 2. Tap targets (WCAG 2.5.8 AA 24px; 44px mobile/AAA) ----
  safe('tapTargets', () => {
    const q = 'a,button,input:not([type=hidden]),select,textarea,[role=button],[role=link],[role=tab],[role=checkbox],[role=switch],[onclick]';
    const small = [], seen = new Set();
    for (const el of document.querySelectorAll(q)) {
      if (!vis(el)) continue;
      const r = el.getBoundingClientRect();
      const w = round(r.width), h = round(r.height);
      if (w >= 44 && h >= 44) continue;
      const sev = (w < 24 || h < 24) ? 'AA-fail' : 'mobile-warn';
      const label = (el.getAttribute('aria-label') || el.textContent || el.getAttribute('title') || el.value || '').trim().slice(0, 40);
      const key = sev + '|' + w + 'x' + h + '|' + label;
      if (seen.has(key)) continue; seen.add(key);
      small.push({ size: w + 'x' + h, severity: sev, label, where: locate(el) });
    }
    return { failCount: small.filter((x) => x.severity === 'AA-fail').length, warnCount: small.filter((x) => x.severity === 'mobile-warn').length, items: small.slice(0, 30) };
  });

  // ---- 3. Spacing on the 8pt grid (4pt tolerated) ----
  safe('spacingGrid', () => {
    const freq = {}; // value -> count
    const bump = (v) => { const r = Math.round(v); if (r > 0 && r <= 160) freq[r] = (freq[r] || 0) + 1; };
    for (const el of visEls) {
      const s = getComputedStyle(el);
      ['paddingTop', 'paddingRight', 'paddingBottom', 'paddingLeft', 'marginTop', 'marginBottom', 'columnGap', 'rowGap', 'gap'].forEach((p) => {
        const v = parseFloat(s[p]); if (!isNaN(v)) bump(v);
      });
    }
    const off4 = [], off8 = [];
    for (const [v, c] of Object.entries(freq)) {
      const n = +v;
      if (n % 4 !== 0) off4.push({ px: n, uses: c });
      else if (n % 8 !== 0) off8.push({ px: n, uses: c }); // on 4-grid but off 8
    }
    off4.sort((a, b) => b.uses - a.uses); off8.sort((a, b) => b.uses - a.uses);
    return { distinctValues: Object.keys(freq).length, off4Grid: off4.slice(0, 15), off8Grid: off8.slice(0, 12) };
  });

  // ---- 4. Near-miss misalignment (edges off by 1-6px within a container) ----
  safe('misalignment', () => {
    const flags = [];
    const containers = visEls.filter((el) => el.children.length >= 3);
    for (const c of containers.slice(0, 800)) {
      const kids = [...c.children].filter(vis);
      if (kids.length < 3) continue;
      for (const edge of ['left', 'right']) {
        const vals = kids.map((k) => ({ k, v: Math.round(k.getBoundingClientRect()[edge]) }));
        const tally = {}; vals.forEach(({ v }) => tally[v] = (tally[v] || 0) + 1);
        const dom = +Object.entries(tally).sort((a, b) => b[1] - a[1])[0][0];
        const domCount = tally[dom];
        if (domCount < Math.ceil(kids.length * 0.6)) continue; // need a clear alignment line
        for (const { k, v } of vals) {
          const d = Math.abs(v - dom);
          if (d >= 1 && d <= 6) {
            flags.push({ edge, offBy: d + 'px', line: dom, container: sel(c), item: locate(k) });
          }
        }
      }
      if (flags.length > 40) break;
    }
    return { count: flags.length, items: flags.slice(0, 25) };
  });

  // ---- 5. Animation: layout-triggering props + linear easing (web.dev/Material) ----
  safe('animation', () => {
    const LAYOUT = ['width', 'height', 'top', 'left', 'right', 'bottom', 'margin'];
    const layoutAnim = [], linearEase = [], seen = new Set();
    for (const el of visEls) {
      const s = getComputedStyle(el);
      const props = (s.transitionProperty || '').split(',').map((x) => x.trim());
      const durs = (s.transitionDuration || '').split(',').map((x) => parseFloat(x));
      const anims = durs.some((d) => d > 0);
      if (!anims && s.animationName === 'none') continue;
      const bad = props.filter((p) => LAYOUT.some((l) => p === l || p.startsWith(l + '-') || p === 'all'));
      if (bad.length && anims) {
        const key = sel(el) + bad.join();
        if (!seen.has(key)) { seen.add(key); layoutAnim.push({ props: bad.join(','), where: locate(el) }); }
      }
      const tf = s.transitionTimingFunction || '';
      if (anims && /linear/.test(tf) && props.some((p) => /transform|opacity|all/.test(p))) {
        const key = 'lin' + sel(el);
        if (!seen.has(key)) { seen.add(key); linearEase.push({ where: locate(el) }); }
      }
    }
    return { layoutTriggering: layoutAnim.slice(0, 20), linearEasing: linearEase.slice(0, 15) };
  });

  // ---- 6. Focus + reduced-motion + color-only cues, from stylesheets ----
  safe('cssAudit', () => {
    let reducedMotion = false, focusOutlineRemoved = false, focusVisiblePresent = false, rulesScanned = 0;
    for (const ss of document.styleSheets) {
      let rules; try { rules = ss.cssRules; } catch { continue; } // cross-origin
      if (!rules) continue;
      const walk = (list) => {
        for (const r of list) {
          rulesScanned++;
          if (r.media && /prefers-reduced-motion/.test(r.conditionText || r.media.mediaText || '')) reducedMotion = true;
          if (r.cssRules) walk(r.cssRules);
          const st = r.selectorText;
          if (!st) continue;
          if (/:focus-visible/.test(st)) focusVisiblePresent = true;
          if (/:focus(?!-visible)/.test(st) && /outline\s*:\s*(none|0)/.test(r.style && r.style.cssText || '')) focusOutlineRemoved = true;
        }
      };
      try { walk(rules); } catch (e) { /* keep going */ }
    }
    return { reducedMotionHandled: reducedMotion, focusOutlineRemoved, focusVisiblePresent, focusRisk: focusOutlineRemoved && !focusVisiblePresent, rulesScanned };
  });

  // ---- 7. Consistency: distinct fonts / sizes / colors (chaos signals) ----
  safe('consistency', () => {
    const fams = {}, sizes = new Set(), colors = new Set(), radii = new Set(), shadows = new Set();
    let n = 0;
    for (const el of visEls) {
      if (n++ > 3000) break;
      const s = getComputedStyle(el);
      const hasText = [...el.childNodes].some((x) => x.nodeType === 3 && x.textContent.trim());
      if (hasText) {
        const fam = (s.fontFamily || '').split(',')[0].replace(/["']/g, '').trim();
        if (fam) fams[fam] = (fams[fam] || 0) + 1;
        sizes.add(Math.round(parseFloat(s.fontSize)));
        colors.add(s.color);
      }
      if (s.borderRadius && s.borderRadius !== '0px') radii.add(s.borderRadius);
      if (s.boxShadow && s.boxShadow !== 'none') shadows.add(s.boxShadow);
    }
    return {
      fontFamilies: Object.keys(fams).length, fontFamilyList: Object.keys(fams).slice(0, 8),
      distinctFontSizes: sizes.size, distinctTextColors: colors.size,
      distinctRadii: radii.size, distinctShadows: shadows.size,
      note: 'flag: >3 font families, >12 font sizes, >10 text colors, >6 radii, or >6 shadows suggests inconsistency'
    };
  });

  // ---- 8. Horizontal overflow at this viewport (layout break) ----
  safe('overflow', () => {
    const docW = document.documentElement.scrollWidth;
    const over = docW - innerWidth;
    const culprits = [];
    if (over > 2) {
      for (const el of visEls) {
        const r = el.getBoundingClientRect();
        if (r.right > innerWidth + 2 && r.width <= innerWidth + over + 2 && r.width > 20) {
          culprits.push({ overBy: Math.round(r.right - innerWidth) + 'px', where: locate(el) });
        }
        if (culprits.length > 12) break;
      }
    }
    return { horizontalOverflowPx: Math.max(0, over), culprits: culprits.slice(0, 8) };
  });

  // ---- 9. Images: upscaled/blurry + missing alt ----
  safe('images', () => {
    const upscaled = [], noAlt = [];
    for (const img of document.images) {
      if (!vis(img)) continue;
      const r = img.getBoundingClientRect();
      if (img.naturalWidth > 0 && r.width > img.naturalWidth * 1.35 && r.width > 40) {
        upscaled.push({ displayed: Math.round(r.width), natural: img.naturalWidth, src: (img.currentSrc || img.src || '').slice(-60) });
      }
      if (img.getAttribute('alt') === null) noAlt.push({ src: (img.currentSrc || img.src || '').slice(-60) });
    }
    return { upscaled: upscaled.slice(0, 12), missingAlt: noAlt.slice(0, 12) };
  });

  OUT.summary = {
    contrastFails: OUT.checks.contrast?.failCount ?? '?',
    tapTargetFails: OUT.checks.tapTargets?.failCount ?? '?',
    tapTargetMobileWarn: OUT.checks.tapTargets?.warnCount ?? '?',
    offGridValues: (OUT.checks.spacingGrid?.off4Grid?.length ?? 0),
    misalignments: OUT.checks.misalignment?.count ?? '?',
    layoutAnimations: OUT.checks.animation?.layoutTriggering?.length ?? '?',
    focusRisk: OUT.checks.cssAudit?.focusRisk ?? '?',
    reducedMotionHandled: OUT.checks.cssAudit?.reducedMotionHandled ?? '?',
    horizontalOverflowPx: OUT.checks.overflow?.horizontalOverflowPx ?? '?'
  };
  return JSON.stringify(OUT);
})();
