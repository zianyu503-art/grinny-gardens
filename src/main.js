import { loadAll, CH2_MODELS, CH3_MODELS } from './assets.js';
import { audio } from './audio.js';
import { isTouchDevice, setupTouch, touchText } from './touch.js';

const $ = (id) => document.getElementById(id);
const startBtn = $('startBtn');

async function boot() {
  const params = new URLSearchParams(location.search);
  const chapter = params.get('ch') === '3' ? 3 : params.get('ch') === '2' ? 2 : 1;
  const progress = (k) => { $('loadbar').firstElementChild.style.width = `${Math.round(k * 100)}%`; };
  let Game;
  if (chapter === 3) {
    $('title').querySelector('h2').textContent = '第三章　失物招領';
    $('title').querySelector('.vhs-tag').innerHTML = 'PLAY ▶ &nbsp; 1996.09.01 &nbsp; 02:13';
    $('endTitle').textContent = '第三章　未完';
    const ch3 = await import('./chapter3.js');
    await Promise.all([loadAll(progress, CH3_MODELS, true), ch3.loadChapter3()]);
    Game = ch3.Chapter3;
  } else if (chapter === 2) {
    $('title').querySelector('h2').textContent = '第二章　歡樂製造部';
    $('title').querySelector('.vhs-tag').innerHTML = 'PLAY ▶ &nbsp; 1996.09.01 &nbsp; 00:41';
    $('endTitle').textContent = '第二章　完';
    const ch2 = await import('./chapter2.js');
    await Promise.all([loadAll(progress, CH2_MODELS), ch2.loadChapter2()]);
    Game = ch2.Chapter2;
  } else {
    await loadAll(progress);
    ({ Game } = await import('./game.js'));
  }
  $('ch2Btn').onclick = () => { location.search = '?ch=2'; };
  $('ch3Btn').onclick = () => { location.search = '?ch=3'; };
  const touch = isTouchDevice();
  if (touch) {
    document.body.classList.add('touch');
    $('title').querySelector('.controls').innerHTML = '左半邊：拖曳移動（推到底奔跑）· 右半邊：拖曳轉頭<br>按鈕：左爪／右爪、互動、蹲、燈、地圖　·　請橫放手機';
  }
  const game = (window.game = new Game($('game'), { touch }));
  if (touch) { setupTouch(game); game.hud.filter = touchText; }

  // debug: ?zone=carousel|funhouse|tunnel|coaster|ferris jumps ahead with the needed progress
  const zone = chapter === 1 ? params.get('zone') : null;
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
