import { loadAll } from './assets.js';
import { audio } from './audio.js';

const $ = (id) => document.getElementById(id);
const startBtn = $('startBtn');

async function boot() {
  await loadAll((k) => { $('loadbar').firstElementChild.style.width = `${Math.round(k * 100)}%`; });
  const { Game } = await import('./game.js');
  const game = (window.game = new Game($('game')));

  // debug: ?zone=carousel|funhouse|tunnel|coaster|ferris jumps ahead with the needed progress
  const zone = new URLSearchParams(location.search).get('zone');
  if (zone) skipTo(game, zone);

  startBtn.disabled = false;
  startBtn.textContent = '開始';
  startBtn.onclick = () => {
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
    game.checkpoint = { x: 0, z: 37, yaw: 0 };
  }
  if (idx >= 2) {
    game.flags.fuses = 3; game.flags.fusesIn = 3;
    I.jaw.position.y = -3.3;
    game.physics.setEnabled(I.jawCollider, false);
    game.checkpoint = { x: 0, z: -2.5, yaw: 0 };
  }
  if (idx >= 3) {
    game.flags.keycard = true;
    I.fhDoor.getObjectByName('Door').rotation.y = 1.5;
    game.physics.setEnabled(I.fhDoorCollider, false);
    game.checkpoint = { x: 0, z: -38.5, yaw: 0 };
  }
  if (idx >= 4) {
    I.tunDoor.getObjectByName('Door').rotation.y = 1.5;
    game.physics.setEnabled(I.tunDoorCollider, false);
    game.checkpoint = { x: 0, z: -72.5, yaw: 0 };
  }
  if (idx >= 5) {
    game.flags.chase = true; game.flags.bridgeDown = true;
    game.checkpoint = { x: 0, z: -146, yaw: 0 };
  }
  game.triggers.forEach((t) => { if (!t.repeatable) t.done = false; });
}

window.addEventListener('click', () => audio.ctx?.resume(), { once: true });
boot().catch((e) => {
  console.error(e);
  startBtn.textContent = '載入失敗：' + e.message;
});
