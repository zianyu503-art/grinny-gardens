import { loadAll } from './assets.js';
import { audio } from './audio.js';
import { isTouchDevice, setupTouch, touchText } from './touch.js';

const $ = (id) => document.getElementById(id);
const startBtn = $('startBtn');

async function boot() {
  await loadAll((k) => { $('loadbar').firstElementChild.style.width = `${Math.round(k * 100)}%`; });
  const { Game } = await import('./game.js');
  const touch = isTouchDevice();
  if (touch) {
    document.body.classList.add('touch');
    $('title').querySelector('.controls').innerHTML = '左半邊：拖曳移動（推到底奔跑）· 右半邊：拖曳轉頭<br>按鈕：左爪／右爪、互動、蹲、燈、地圖　·　請橫放手機';
  }
  const game = (window.game = new Game($('game'), { touch }));
  if (touch) { setupTouch(game); game.hud.filter = touchText; }

  // debug: ?zone=carousel|funhouse|tunnel|coaster|ferris jumps ahead with the needed progress
  const zone = new URLSearchParams(location.search).get('zone');
  if (zone) skipTo(game, zone);

  startBtn.disabled = false;
  startBtn.textContent = '開始';
  startBtn.onclick = () => {
    if (touch) {
      document.documentElement.requestFullscreen?.().then(() => screen.orientation?.lock?.('landscape')).catch(() => {});
    }
    $('title').classList.add('hidden');
    game.input.lock();
    game.start();
    if (zone) game.player.place(game.checkpoint.x, game.checkpoint.z, game.checkpoint.yaw);
  };

  let last = performance.now();
  const loop = (now) => {
    const dt = (now - last) / 1000;
    last = now;
    game.frame(dt);
    requestAnimationFrame(loop);
  };
  requestAnimationFrame(loop);
}

function skipTo(game, zone) {
  const order = ['entrance', 'carousel', 'funhouse', 'tunnel', 'coaster', 'ferris'];
  const idx = order.indexOf(zone);
  const I = game.level.items;
  if (idx >= 1) {
    game.flags.pack = true; game.flags.map = true; game.claw.show(true);
    game.scene.remove(I.packPickup);
    I.doorL.rotation.y = 1.45; I.doorR.rotation.y = -1.45;
    game.physics.setEnabled(I.gateCollider, false);
    game.checkpoint = { ...game.route.carousel.cp };
  }
  if (idx >= 2) {
    game.flags.fuses = 3; game.flags.fusesIn = 3;
    I.jaw.position.y = -(I.jawDrop ?? 3.3);
    game.physics.setEnabled(I.jawCollider, false);
    game.checkpoint = { ...game.route.funhouse.cp };
  }
  if (idx >= 3) {
    game.flags.keycard = true;
    I.fhDoor.getObjectByName('Door').rotation.y = 1.5;
    game.physics.setEnabled(I.fhDoorCollider, false);
    game.checkpoint = { ...game.route.tunnel.cp };
  }
  if (idx >= 4) {
    I.tunDoor.getObjectByName('Door').rotation.y = 1.5;
    game.physics.setEnabled(I.tunDoorCollider, false);
    game.checkpoint = { ...game.route.coaster.cp };
  }
  if (idx >= 5) {
    game.flags.chase = true; game.flags.bridgeDown = true;
    game.checkpoint = { ...game.route.ferris.cp };
  }
  game.triggers.forEach((t) => { if (!t.repeatable) t.done = false; });
}

window.addEventListener('click', () => audio.ctx?.resume(), { once: true });
boot().catch((e) => {
  console.error(e);
  startBtn.textContent = '載入失敗：' + e.message;
});
