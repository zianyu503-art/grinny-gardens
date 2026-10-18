const $ = (id) => document.getElementById(id);

export class HUD {
  constructor() {
    this.el = {
      hud: $('hud'), objective: $('objective'), prompt: $('prompt'), subtitle: $('subtitle'), hint: $('hint'),
      battery: $('battery'), stamina: $('stamina'), staminaWrap: $('staminaWrap'), crosshair: $('crosshair'),
      inventory: $('inventory'), fade: $('fade'), clawL: $('clawL'), clawR: $('clawR'),
    };
    this.queue = [];
    this.subTimer = 0;
    this.hintTimer = 0;
  }

  show(on) { this.el.hud.classList.toggle('hidden', !on); }
  /** Optional text filter (touch devices swap keyboard wording). */
  tr(t) { return this.filter ? this.filter(t) : t; }

  objective(t) { this.el.objective.textContent = t || ''; }
  prompt(t) { t = this.tr(t || ''); if (this.el.prompt.textContent !== t) this.el.prompt.textContent = t; }

  hint(t, dur = 6) { this.el.hint.textContent = this.tr(t); this.hintTimer = dur; }

  /** Queue subtitle lines: [{who, text, dur}] */
  say(lines, interrupt = false) {
    if (interrupt) { this.queue = []; this.subTimer = 0; }
    this.queue.push(...lines);
  }

  battery(v) {
    this.el.battery.style.width = `${Math.max(0, v)}%`;
    this.el.battery.classList.toggle('low', v < 20);
  }

  stamina(v) {
    this.el.stamina.style.width = `${v}%`;
    this.el.staminaWrap.style.opacity = v > 99 ? 0.25 : 1;
  }

  crosshair(target, charged) {
    this.el.crosshair.classList.toggle('target', !!target);
    this.el.crosshair.classList.toggle('charged', !!charged);
  }

  claws(l, r) {
    for (const [el, s] of [[this.el.clawL, l], [this.el.clawR, r]]) {
      el.classList.toggle('charged', s.charged);
      el.classList.toggle('out', s.out);
    }
  }

  inventory(items) { this.el.inventory.innerHTML = items.filter(Boolean).map((i) => this.tr(i)).join('<br>'); }

  fade(to, seconds = 1.2) {
    this.el.fade.style.transition = `opacity ${seconds}s`;
    this.el.fade.style.opacity = to;
  }

  update(dt) {
    if (this.hintTimer > 0) {
      this.hintTimer -= dt;
      if (this.hintTimer <= 0) this.el.hint.textContent = '';
    }
    this.subTimer -= dt;
    if (this.subTimer <= 0) {
      const next = this.queue.shift();
      if (next) {
        this.el.subtitle.innerHTML = next.who ? `<span class="who">${next.who}：</span>${next.text}` : next.text;
        this.subTimer = next.dur ?? Math.max(2.5, next.text.length * 0.16);
        next.onShow?.();
      } else {
        this.el.subtitle.textContent = '';
        this.subTimer = 0.2;
      }
    }
  }

  get talking() { return this.queue.length > 0 || this.subTimer > 0.3; }
}
