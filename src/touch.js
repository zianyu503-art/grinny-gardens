// Touch controls: floating move stick (left), drag-to-look (right), action buttons.

export function isTouchDevice() {
  const force = new URLSearchParams(location.search).get('touch');
  if (force === '1') return true;
  if (force === '0') return false;
  return (navigator.maxTouchPoints > 0 || 'ontouchstart' in window) && matchMedia('(pointer: coarse)').matches;
}

const BUTTONS = [
  // id, label, area class, action
  ['tClawL', '左爪', 'claw l', { mouse: 0 }],
  ['tClawR', '右爪', 'claw r', { mouse: 2 }],
  ['tUse', '互動', 'use', { tap: 'KeyE' }],
  ['tCrouch', '蹲', 'small crouch', { tap: 'KeyC' }],
  ['tFlash', '燈', 'small flash', { tap: 'KeyF' }],
  ['tMap', '地圖', 'top map', { tap: 'KeyM' }],
  ['tPause', 'II', 'top pause', { pause: true }],
];

export function setupTouch(game) {
  const input = game.input;
  input.touchMode = true;
  document.body.classList.add('touch');
  const root = document.createElement('div');
  root.id = 'touchUI';
  root.innerHTML = `
    <div id="tLook"></div>
    <div id="tStickZone"><div id="tStick"><i></i></div></div>
    ${BUTTONS.map(([id, label, cls]) => `<button id="${id}" class="tbtn ${cls}">${label}</button>`).join('')}
    <div id="tRotate">請將手機橫放<br><small>橫向畫面才能看清楚周圍</small></div>`;
  document.body.appendChild(root);

  // ---------------------------------------------------- move stick
  const zone = root.querySelector('#tStickZone');
  const stick = root.querySelector('#tStick');
  const knob = stick.firstElementChild;
  const R = 56;
  let stickId = null, ox = 0, oy = 0;
  zone.addEventListener('touchstart', (e) => {
    e.preventDefault();
    if (stickId !== null) return;
    const t = e.changedTouches[0];
    stickId = t.identifier; ox = t.clientX; oy = t.clientY;
    stick.style.left = `${ox}px`; stick.style.top = `${oy}px`;
    stick.classList.add('on');
  }, { passive: false });
  const moveStick = (e) => {
    for (const t of e.changedTouches) {
      if (t.identifier !== stickId) continue;
      let dx = t.clientX - ox, dy = t.clientY - oy;
      const d = Math.hypot(dx, dy);
      if (d > R) { dx *= R / d; dy *= R / d; }
      knob.style.transform = `translate(${dx}px, ${dy}px)`;
      input.axis.x = dx / R; input.axis.z = dy / R; input.axis.active = true;
      stick.classList.toggle('sprint', Math.hypot(dx, dy) / R > 0.93 && dy < 0);
    }
  };
  const endStick = (e) => {
    for (const t of e.changedTouches) {
      if (t.identifier !== stickId) continue;
      stickId = null;
      input.axis.x = input.axis.z = 0; input.axis.active = false;
      knob.style.transform = '';
      stick.classList.remove('on', 'sprint');
    }
  };
  zone.addEventListener('touchmove', (e) => { e.preventDefault(); moveStick(e); }, { passive: false });
  zone.addEventListener('touchend', endStick);
  zone.addEventListener('touchcancel', endStick);

  // ---------------------------------------------------- look
  const look = root.querySelector('#tLook');
  const lookIds = new Map();
  look.addEventListener('touchstart', (e) => {
    e.preventDefault();
    for (const t of e.changedTouches) lookIds.set(t.identifier, [t.clientX, t.clientY]);
  }, { passive: false });
  look.addEventListener('touchmove', (e) => {
    e.preventDefault();
    for (const t of e.changedTouches) {
      const last = lookIds.get(t.identifier);
      if (!last) continue;
      input.look((t.clientX - last[0]) * 1.6, (t.clientY - last[1]) * 1.6);
      lookIds.set(t.identifier, [t.clientX, t.clientY]);
    }
  }, { passive: false });
  const endLook = (e) => { for (const t of e.changedTouches) lookIds.delete(t.identifier); };
  look.addEventListener('touchend', endLook);
  look.addEventListener('touchcancel', endLook);

  // ---------------------------------------------------- buttons
  for (const [id, , , act] of BUTTONS) {
    const b = root.querySelector('#' + id);
    b.addEventListener('touchstart', (e) => {
      e.preventDefault();
      b.classList.add('down');
      if (act.mouse !== undefined) input.tapMouse(act.mouse);
      if (act.tap) input.tap(act.tap);
      if (act.pause) game.pause();
      navigator.vibrate?.(10);
    }, { passive: false });
    b.addEventListener('touchend', () => b.classList.remove('down'));
  }

  // claw buttons show charge / out state, use button only when something is in reach
  const clawL = root.querySelector('#tClawL'), clawR = root.querySelector('#tClawR'), use = root.querySelector('#tUse');
  game.onHudTick = () => {
    const l = game.claw.state(0), r = game.claw.state(1);
    clawL.classList.toggle('charged', l.charged); clawR.classList.toggle('charged', r.charged);
    clawL.classList.toggle('hidden', !game.claw.enabled); clawR.classList.toggle('hidden', !game.claw.enabled);
    use.classList.toggle('ready', !!document.getElementById('prompt').textContent);
    root.classList.toggle('hidden', !!(!game.started || game.paused || game.ended));
  };

  // ---------------------------------------------------- orientation
  const rot = root.querySelector('#tRotate');
  const checkOrient = () => rot.classList.toggle('show', innerHeight > innerWidth);
  addEventListener('resize', checkOrient);
  checkOrient();

  // block pinch-zoom / double-tap zoom on the game
  document.addEventListener('gesturestart', (e) => e.preventDefault());
  document.addEventListener('dblclick', (e) => e.preventDefault());
}

/** Swap keyboard wording in hints for touch wording. */
export function touchText(t) {
  return t
    .replace(/滑鼠左鍵 \/ 右鍵：發射左爪 \/ 右爪。?/g, '點「左爪」「右爪」按鈕發射爪子。')
    .replace(/按 E 互動/g, '點「互動」按鈕')
    .replace(/按 C 蹲下/g, '點「蹲」')
    .replace(/按 M 打開地圖/g, '點右上角「地圖」打開')
    .replace(/\[E\] /g, '')
    .replace(/\[M\] /g, '');
}
