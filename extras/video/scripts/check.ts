// npm run check. Fails when a number the video shows or speaks is not in README.md's "Measured on the reference
// system" section, when a digit appears outside the measurements without being listed as not one, when the beat grid
// does not hold together, when a spoken line does not fit its scene, or when on-screen or spoken text carries an en
// or em dash, a word from JARGON or a word from ALARM.
import {existsSync, readFileSync} from 'node:fs';
import {resolve} from 'node:path';
import grid from '../src/grid.json';
import {NARRATION, NOT_MEASUREMENTS, READ, RESULTS, TEXT, VOICE, cueEnd, type Scene} from '../src/intro-data';

const SHOWN_NUMBER_KEYS = new Set(['from', 'to', 'value']);
const NUMBER = /\d+(?:\.\d+)?/g;
// The film is for readers who are not engineers.
const JARGON = /\b(cards?|premise|slices?|runbooks?|QA|ledger|verification|unattended|index|telemetry|sessions?|test first|ready for release|dependency)\b/i;
// The film describes ordinary work; alarm words make a viewer read it as a security story.
const ALARM = /(vulnerab|critical|severity|\bCVEs?\b|security patch)/i;

function strings(v: unknown, out: string[] = []): string[] {
  if (typeof v === 'string') out.push(v);
  else if (Array.isArray(v)) v.forEach((x) => strings(x, out));
  else if (v && typeof v === 'object') Object.values(v).forEach((x) => strings(x, out));
  return out;
}

function shownNumbers(results: unknown, out: string[] = []): string[] {
  if (typeof results === 'string') out.push(...(results.match(NUMBER) ?? []));
  else if (Array.isArray(results)) results.forEach((x) => shownNumbers(x, out));
  else if (results && typeof results === 'object') {
    for (const [k, x] of Object.entries(results)) {
      if (typeof x === 'number') {
        // A counter that starts at no change (0% smaller, 1.0 times) shows a baseline, not a measurement.
        if (SHOWN_NUMBER_KEYS.has(k) && !(k === 'from' && (x === 0 || x === 1))) out.push(String(x));
      } else shownNumbers(x, out);
    }
  }
  return out;
}

export function measuredSection(readme: string): string {
  const at = readme.indexOf('## Measured on the reference system');
  if (at < 0) throw new Error('README.md has no "## Measured on the reference system" section');
  const end = readme.indexOf('\n## ', at + 4);
  return readme.slice(at, end < 0 ? undefined : end);
}

export function numbersMissing(results: unknown, section: string): string[] {
  const have = new Set(section.match(NUMBER) ?? []);
  return [...new Set(shownNumbers(results))].filter((n) => !have.has(n));
}

const problems: string[] = [];
const readme = readFileSync(resolve(process.argv[2] ?? resolve(__dirname, '../../../README.md')), 'utf8');
const section = measuredSection(readme);

const planted = JSON.parse(JSON.stringify(RESULTS));
planted.caveat.push('7777');
if (!numbersMissing(planted, section).includes('7777')) problems.push('self-test: a planted 7777 was not caught, so this check is broken');
if (!JARGON.test('close the card')) problems.push('self-test: planted jargon was not caught, so this check is broken');
if (!ALARM.test('a Critical fix')) problems.push('self-test: a planted alarm word was not caught, so this check is broken');
if (numbersMissing(['up 7777%'], section).length !== 1) problems.push('self-test: a planted spoken number was not caught, so this check is broken');
if (numbersMissing(RESULTS, 'no numbers here').length === 0) problems.push('self-test: an empty section passed, so this check is broken');

for (const n of numbersMissing(RESULTS, section)) problems.push(`the video shows ${n}, which README.md's measured section does not have`);
for (const n of numbersMissing(NARRATION, section)) problems.push(`the voice says ${n}, which README.md's measured section does not have`);

for (const s of strings(TEXT)) {
  if (/\d/.test(s) && !NOT_MEASUREMENTS.includes(s)) problems.push(`"${s}" carries a number outside RESULTS: move it there or list it in NOT_MEASUREMENTS`);
}
for (const s of strings([TEXT, RESULTS, NARRATION])) {
  if (/[\u2013\u2014]/.test(s)) problems.push(`dash in "${s}"`);
  if (JARGON.test(s)) problems.push(`jargon in "${s}"`);
  if (ALARM.test(s)) problems.push(`alarm word in "${s}"`);
}

const beat = (grid.fps * 60) / grid.bpm;
if (!Number.isInteger(beat)) problems.push(`a beat is ${beat} frames: pick fps and bpm so a beat is a whole number of frames`);
let cursor = 0;
for (const [name, [a, b]] of Object.entries(grid.scenes)) {
  if (a !== cursor || b <= a) problems.push(`scene ${name} is bars ${a} to ${b}; it should start at bar ${cursor} and end after it starts`);
  cursor = b;
}
if (cursor !== grid.bars) problems.push(`the scenes end at bar ${cursor}, the grid at bar ${grid.bars}`);
const marks = Object.values(grid.music);
if (marks.some((m, i) => i && m <= marks[i - 1])) problems.push('the music sections are not in increasing order');
if (grid.music.end !== grid.bars) problems.push(`the music ends at bar ${grid.music.end}, the video at bar ${grid.bars}`);
for (const [lift, scene] of [['liftA', 'join'], ['liftB', 'compounds'], ['liftC', 'results']] as const) {
  if (grid.music[lift] !== grid.scenes[scene][0]) problems.push(`music ${lift} is bar ${grid.music[lift]}, but the ${scene} scene starts at bar ${grid.scenes[scene][0]}`);
}

for (const scene of Object.keys(grid.scenes) as Scene[]) {
  const [a, b] = grid.scenes[scene];
  const lines = NARRATION[scene] ?? [];
  if (VOICE[scene]?.length !== lines.length) problems.push(`scene ${scene} has ${lines.length} spoken lines but ${VOICE[scene]?.length ?? 0} clips: run scripts/voice.py`);
  else if (READ[scene].length !== lines.length) problems.push(`scene ${scene} has ${lines.length} spoken lines but ${READ[scene].length} READ entries`);
  else if (cueEnd(scene) > (b - a) * beat * 4) problems.push(`scene ${scene} needs ${cueEnd(scene)} frames for its voice, but has ${(b - a) * beat * 4}: add bars`);
  lines.forEach((_, i) => {
    if (!existsSync(resolve(__dirname, `../public/voice/${scene}-${i}.mp3`))) problems.push(`public/voice/${scene}-${i}.mp3 is missing: run scripts/voice.py`);
  });
}

for (const p of problems) console.log('FAIL', p);
if (problems.length) process.exit(1);
console.log(`check: ${shownNumbers(RESULTS).length} shown and ${shownNumbers(NARRATION).length} spoken numbers all in README.md, grid of ${grid.bars} bars at ${grid.bpm} BPM holds, every voice line fits its scene, no dashes, no jargon, no alarm words`);
