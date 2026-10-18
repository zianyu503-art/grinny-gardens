export class Input {
  constructor(canvas) {
    this.canvas = canvas;
    this.keys = new Set();
    this.pressed = new Set(); // edge-triggered this frame
    this.mouse = { dx: 0, dy: 0, buttons: new Set(), clicked: new Set() };
    this.locked = false;
    this.sensitivity = 1;
    this.enabled = true;
    addEventListener('keydown', (e) => {
      if (e.repeat) return;
      this.keys.add(e.code);
      this.pressed.add(e.code);
      if (['Space', 'Tab'].includes(e.code)) e.preventDefault();
    });
    addEventListener('keyup', (e) => this.keys.delete(e.code));
    addEventListener('blur', () => this.keys.clear());
    canvas.addEventListener('contextmenu', (e) => e.preventDefault());
    addEventListener('mousedown', (e) => {
      if (!this.locked) return;
      this.mouse.buttons.add(e.button);
      this.mouse.clicked.add(e.button);
    });
    addEventListener('mouseup', (e) => this.mouse.buttons.delete(e.button));
    addEventListener('mousemove', (e) => {
      if (!this.locked) return;
      this.mouse.dx += e.movementX;
      this.mouse.dy += e.movementY;
    });
    document.addEventListener('pointerlockchange', () => {
      this.locked = document.pointerLockElement === canvas;
      this.onLockChange?.(this.locked);
    });
  }

  lock() {
    try {
      const p = this.canvas.requestPointerLock?.({ unadjustedMovement: true });
      p?.catch?.(() => this.canvas.requestPointerLock()?.catch?.(() => {}));
    } catch { /* pointer lock unavailable (e.g. embedded preview) */ }
  }

  down(code) { return this.enabled && this.keys.has(code); }
  hit(code) { return this.enabled && this.pressed.has(code); }
  click(btn) { return this.enabled && this.mouse.clicked.has(btn); }

  consumeMouse() {
    const d = { x: this.mouse.dx * this.sensitivity, y: this.mouse.dy * this.sensitivity };
    this.mouse.dx = this.mouse.dy = 0;
    return this.enabled ? d : { x: 0, y: 0 };
  }

  endFrame() {
    this.pressed.clear();
    this.mouse.clicked.clear();
  }
}
