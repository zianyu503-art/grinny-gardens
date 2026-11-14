// Pre-record every spoken line (PA announcements and tapes) with macOS `say`, as small AAC files
// in public/voice/. The game plays them through its own tape / loudspeaker effects (audio.voice).
//
// usage: node tools/make_voices.mjs        (macOS only; needs the zh_TW voice "Meijia")
import { execFileSync } from 'node:child_process';
import { mkdirSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { PA, TAPES, PA2, TAPES2, THROW, MEI_END, PA3, TAPES3, DIRECTOR3, DIRECTOR3_BROKEN } from '../src/story.js';

const OUT = fileURLToPath(new URL('../public/voice/', import.meta.url));
mkdirSync(OUT, { recursive: true });
const tmp = join(tmpdir(), 'grinny_voice.aiff');

const clean = (t) => t.replace(/[（）()「」]/g, '').replace(/沙沙/g, '').trim();
const lines = [];
for (const [key, text] of Object.entries({ ...PA, ...PA2, ...PA3 })) lines.push([`pa_${key}`, text, 165]);
for (const l of [...THROW, ...MEI_END]) lines.push([l.voice, clean(l.text), 160]);
for (const l of [...DIRECTOR3, ...DIRECTOR3_BROKEN]) if (l.voice) lines.push([l.voice, clean(l.text), 150]);
for (const [id, tape] of Object.entries({ ...TAPES, ...TAPES2, ...TAPES3 })) {
  tape.lines.forEach((l, i) => lines.push([`tape_${id}_${i}`, clean(l.text), 175]));
}

for (const [id, text, rate] of lines) {
  execFileSync('say', ['-v', 'Meijia', '-r', String(rate), '-o', tmp, text]);
  execFileSync('afconvert', ['-f', 'm4af', '-d', 'aac', '-b', '40000', '-c', '1', tmp, join(OUT, `${id}.m4a`)]);
  console.log(id, text);
}
rmSync(tmp, { force: true });
console.log(`${lines.length} lines written to public/voice/`);
