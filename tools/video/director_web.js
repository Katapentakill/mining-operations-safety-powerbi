// Director de la toma del informe en el Power BI Service. Se pega ENTERO en la página del informe (javascript_tool de la extensión Claude in Chrome
// o la consola de Chrome) y luego se lanza con:  setTimeout(()=>window.__D.run2(),500)
// - Todo ocurre dentro de la página con eventos sintéticos: no hay llamadas de la extensión durante la grabación (sin banner de depuración ni etiqueta «Claude is working here»).
// - Dibuja su propio cursor y el anillo naranja de cada clic (quedan grabados por ffmpeg gdigrab).
// - Guarda en __D.log el momento exacto (Date.now()) de cada clic, tecla y escena, y en __D.meta la geometría del lienzo. Leerlos DESPUÉS de grabar.
// - Usa setTimeout y no requestAnimationFrame: rAF se detiene si Chrome queda tapado por otra ventana y el guion se congela.
(() => {
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const log = [];
  document.getElementById('__dst')?.remove(); document.getElementById('__dcur')?.remove();
  const st = document.createElement('style'); st.id = '__dst';
  st.textContent = '@keyframes __ring{0%{transform:translate(-50%,-50%) scale(.2);opacity:.95}100%{transform:translate(-50%,-50%) scale(1);opacity:0}} .__ring{position:fixed;width:130px;height:130px;border-radius:50%;border:5px solid #ff6200;box-shadow:0 0 18px #ff620088;pointer-events:none;z-index:2147483646;animation:__ring .7s ease-out forwards}';
  document.head.appendChild(st);
  const cur = document.createElement('div'); cur.id = '__dcur';
  cur.style.cssText = 'position:fixed;left:0;top:0;width:32px;height:32px;pointer-events:none;z-index:2147483647;transform:translate(-9999px,-9999px)';
  cur.innerHTML = '<svg width="32" height="32" viewBox="0 0 32 32"><path d="M4 2 L4 24 L10 19 L14 28 L18 26 L14 17 L22 17 Z" fill="#fff" stroke="#111" stroke-width="2" stroke-linejoin="round"/></svg>';
  document.body.appendChild(cur);
  let cx = -1, cy = -1;
  const setCur = (x, y) => { cx = x; cy = y; cur.style.transform = 'translate(' + (x - 4) + 'px,' + (y - 2) + 'px)'; };
  const glide = async (x, y, ms = 700) => { if (cx < 0) setCur(x - 160, y + 110); const x0 = cx, y0 = cy, t0 = performance.now(); for (;;) { const p = Math.min(1, (performance.now() - t0) / ms); const e = p < .5 ? 2 * p * p : 1 - Math.pow(-2 * p + 2, 2) / 2; setCur(x0 + (x - x0) * e, y0 + (y - y0) * e); if (p >= 1) break; await sleep(16); } };
  const fire = (el, x, y) => { const o = { bubbles: true, cancelable: true, composed: true, clientX: x, clientY: y, pointerId: 1, pointerType: 'mouse', isPrimary: true, button: 0, buttons: 1, view: window }; for (const t of ['pointerover', 'pointermove', 'pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click']) { const E = t.startsWith('pointer') ? PointerEvent : MouseEvent; el.dispatchEvent(new E(t, o)); } };
  const ring = (x, y) => { const r = document.createElement('div'); r.className = '__ring'; r.style.left = x + 'px'; r.style.top = y + 'px'; document.body.appendChild(r); setTimeout(() => r.remove(), 800); };
  const center = (el) => { const b = el.getBoundingClientRect(); return [b.x + b.width / 2, b.y + b.height / 2]; };
  const click = async (el, label, ms = 700) => { const [x, y] = center(el); await glide(x, y, ms); await sleep(160); ring(x, y); log.push({ t: Date.now(), k: 'click', x, y, label }); fire(document.elementFromPoint(x, y) || el, x, y); };
  const nav = (name) => [...document.querySelectorAll('.pageNavigator[role=button]')].find((e) => e.textContent.trim() === name);
  const item = (txt) => [...document.querySelectorAll('.slicerText')].find((e) => e.textContent.trim() === txt);
  window.__D = { sleep, log, glide, fire, ring, center, click, nav, item, setCur };

  window.__D.run = async () => {
    const D = window.__D, S = D.sleep, L = D.log;
    L.length = 0; D.done = false; D.err = null;
    const mark = (name) => L.push({ t: Date.now(), k: 'scene', name });
    // esperar a que el banner de depuración de la extensión desaparezca (la página recupera su alto) y se estabilice
    let ok = 0; while (ok < 25) { if (innerHeight >= 900) ok++; else ok = 0; await S(100); }
    const da = document.querySelector('.displayArea').getBoundingClientRect();
    const cw = da.width, ch = cw * 9 / 16;
    const cv = { x: da.x, y: da.y + da.height - ch, w: cw, h: ch }; // lienzo del informe, en px de la ventana del navegador
    D.meta = { cv, iw: innerWidth, ih: innerHeight, ow: outerWidth, oh: outerHeight, sx: screenX, sy: screenY };
    const P = (fx, fy) => [cv.x + fx * cv.w, cv.y + fy * cv.h];
    const wander = async (pts, ms = 900, pause = 350) => { for (const [fx, fy] of pts) { const [x, y] = P(fx, fy); await D.glide(x, y, ms); await S(pause); } };
    const go = async (n) => { await D.click(D.nav(n), 'nav ' + n, 900); };
    const dd = (re) => [...document.querySelectorAll('.slicer-dropdown-menu')].find((e) => re.test(e.getAttribute('aria-label') || ''));
    const scrollList = async (to, ms = 900) => {
      let sc = document.querySelector('.slicerText'); while (sc && !(sc.scrollHeight > sc.clientHeight + 5 && /auto|scroll/.test(getComputedStyle(sc).overflowY))) sc = sc.parentElement;
      if (!sc) return; const from = sc.scrollTop, t0 = performance.now();
      for (;;) { const p = Math.min(1, (performance.now() - t0) / ms); sc.scrollTop = from + (sc.scrollHeight - from) * p; if (p >= 1) break; await S(16); }
    };
    const toggleYear = async (y) => {
      await D.click(dd(/Año/), 'año abrir', 800); await S(1300);
      await scrollList('end', 1000); await S(700);
      await D.click(D.item(String(y)), 'año ' + y, 700); await S(1100);
      await D.click(dd(/Año/), 'año cerrar', 550); await S(700);
    };
    // cubierta negra: marca de sincronía (blackdetect la encuentra en el video) y entrada suave
    const cover = document.createElement('div');
    cover.style.cssText = 'position:fixed;inset:0;background:#000;z-index:2147483640;opacity:1;transition:opacity .8s;pointer-events:none';
    document.body.appendChild(cover); L.push({ t: Date.now(), k: 'cover_on' });
    await S(1300); cover.style.opacity = '0'; L.push({ t: Date.now(), k: 'cover_off' }); await S(900);
    mark('acerca'); await wander([[0.5, 0.45], [0.5, 0.7]], 1200, 1200); await S(6500);
    mark('resumen'); await go('Resumen'); await S(1800);
    await wander([[0.12, 0.24], [0.37, 0.24], [0.62, 0.24], [0.87, 0.24]], 900, 700); await S(1500);
    mark('anio'); await toggleYear(2024); await wander([[0.3, 0.62]], 900, 500); await S(5500);
    mark('anio_reset'); await toggleYear(2024); await S(1500); // volver a pulsar 2024 lo quita: queda «Todas»
    mark('accidentes'); await go('Accidentes'); await S(1500); await wander([[0.25, 0.55], [0.72, 0.5], [0.5, 0.82]], 1100, 1300); await S(2500);
    mark('infracciones'); await go('Infracciones'); await S(1500); await wander([[0.25, 0.55], [0.72, 0.6], [0.5, 0.35]], 1100, 1300); await S(2800);
    mark('plantilla'); await go('Plantilla'); await S(1500); await wander([[0.3, 0.55], [0.7, 0.55]], 1100, 1500); await S(3000);
    mark('mapa'); await go('Mapa'); await S(3500); await wander([[0.3, 0.55], [0.34, 0.74]], 1100, 900);
    mark('ficha');
    const bars = [...document.querySelectorAll('svg rect.bar')].filter((r) => r.getBoundingClientRect().width > 0).sort((a, b) => b.getBoundingClientRect().width - a.getBoundingClientRect().width);
    await D.click(bars[0], 'ranking Morenci', 1000); await S(5500); // deja a Morenci seleccionado en la página Mapa
    mark('detalle'); await go('Detalle'); await S(2200);
    await D.click(dd(/Mina/), 'mina abrir', 900); await S(1200);
    const inp = [...document.querySelectorAll('input.searchInput')].find((i) => i.getBoundingClientRect().width > 0); // hay otro searchInput oculto (el de Año)
    await D.click(inp, 'mina buscar', 700); inp.focus(); await S(400);
    mark('escribir');
    const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set; let v = '';
    for (const c of 'morenci') {
      v += c; const code = c.toUpperCase().charCodeAt(0); const kd = { key: c, code: 'Key' + c.toUpperCase(), keyCode: code, which: code, bubbles: true, cancelable: true };
      L.push({ t: Date.now(), k: 'key', ch: c });
      inp.dispatchEvent(new KeyboardEvent('keydown', kd)); inp.dispatchEvent(new KeyboardEvent('keypress', kd));
      setter.call(inp, v); inp.dispatchEvent(new InputEvent('input', { bubbles: true, data: c, inputType: 'insertText' })); inp.dispatchEvent(new KeyboardEvent('keyup', kd));
      await S(330);
    }
    await S(1700);
    await D.click(D.item('Freeport-McMoRan Morenci Inc.'), 'mina elegir', 900); await S(1300);
    await D.click(dd(/Mina/), 'mina cerrar', 600); mark('detalle_ok'); await wander([[0.3, 0.6]], 900, 300); await S(6500);
    mark('final'); await go('Resumen'); await S(1500); await wander([[0.5, 0.6]], 1000, 200); await S(5500);
    cover.style.transition = 'opacity 1s'; cover.style.opacity = '1'; L.push({ t: Date.now(), k: 'cover_end' }); await S(1500);
    mark('fin'); D.done = true;
  };
  window.__D.run2 = async () => { try { await window.__D.run(); } catch (e) { window.__D.err = e.message + ' @' + String(e.stack || '').slice(0, 400); window.__D.done = true; } };
  return 'director instalado';
})();
