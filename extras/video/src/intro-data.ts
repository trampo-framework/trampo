// Every string the intro shows or speaks lives here or in narration.json, so scripts/check.ts can hold each number to
// README.md. Tempo, length and scene bars come from grid.json, which scripts/music.py reads too. voice.json holds the
// length in seconds of each spoken line, written by scripts/voice.py.
import grid from './grid.json';
import narration from './narration.json';
import voice from './voice.json';

export const FPS = grid.fps;
export const BEAT = (FPS * 60) / grid.bpm;
export const BAR = BEAT * 4;
export const BARS = grid.bars;
export const SCENES = grid.scenes;
export const MUSIC = grid.music;
export type Scene = keyof typeof SCENES;

// The product name, on screen and in the voice. narration.json writes it as {name}; after a rename, respeak the
// scenes that say it: scripts/voice.py turn end.
export const NAME = 'Trampo';

export const NARRATION = Object.fromEntries(Object.entries(narration.lines).map(([k, v]) => [k, v.map((l) => l.replaceAll('{name}', NAME))])) as Record<Scene, string[]>;
export const VOICE: Record<Scene, number[]> = voice;

export const TEXT = {
  name: NAME,
  tagline: 'Working rules for Claude Code, with people in charge',
  endLine: 'Open source',
  problem: {
    lines: ['Most AI tools give you pieces: a component, a plugin, a bot.', 'None is a way of working your team builds. And what the AI learns gets lost: in one chat, on one laptop.'],
    pieces: ['component', 'plugin', 'bot'],
    places: ['one chat', 'one laptop'],
  },
  turn: {
    lines: [`${NAME} is a toolbox your team builds as it needs, reusing the tools you already have.`, 'It starts small and grows into how your team already works.'],
    yours: 'tools you already have',
  },
  map: {
    lines: ['Your tech lead maps how the team works: systems, steps, checks.', 'Start with one project.'],
    lead: 'tech lead',
    kinds: ['systems', 'steps', 'checks'],
    frame: 'one project',
  },
  join: {
    lines: ['Then the whole team works through it, every day.', 'Each piece of work teaches the developer and the agent at the same time.'],
    agent: 'agent',
    learns: 'learns',
  },
  steer: {
    lines: ['You give the directions.', 'Nothing starts until you say yes.', 'Not done until an independent check passes.'],
    chat: [
      {from: 'person', text: 'Add a dark mode to the settings page.'},
      {from: 'ai', text: 'Here is my plan. Shall I start?'},
      {from: 'person', text: 'Yes, go ahead.'},
      {from: 'ai', text: 'Built. Waiting for the independent check.'},
    ],
    passed: 'Check passed',
  },
  memory: {
    lines: ['Every lesson goes into one shared place, in plain files.', 'One file becomes topics, then playbooks for each system.', 'Teach it a new skill, and it shows you more of your system.'],
    levels: ['one file', 'topics', 'playbooks'],
    skill: 'new skill',
    system: 'your system',
  },
  compounds: {
    lines: ['More people using it means more knowledge, more playbooks, more fixes.', 'Anything spotted on the way is recorded and sorted later. Urgent items go to a person straight away.'],
    growth: ['people', 'knowledge', 'playbooks', 'fixes'],
    list: 'to sort later',
    urgent: 'urgent',
  },
  history: {
    lines: ['Version control kept your code. This keeps the why: decisions, goals, how it was tested.', "How did we do this a year ago? It's written down.", 'Someone leaves, their knowledge stays. Someone new starts from it.'],
    lanes: ['code', 'the why'],
    notes: ['decision', 'goal', 'how it was tested'],
    yearAgo: 'a year ago',
    today: 'today',
  },
  results: {
    sections: ['Quality', 'Speed'],
  },
  end: {
    lines: ['After a while it runs itself: the memory, the plans and the checks all grow in one place.', "It's all yours. Stop any time and keep everything.", 'Start small.'],
    parts: ['memory', 'plans', 'checks'],
    yours: 'yours',
  },
};

// Every number in the results scene, from README.md, "Measured on the reference system". The check holds them to it.
export const RESULTS = {
  lines: [
    "A real team's story. They started small. Seven weeks later:",
    "Playbooks cover nearly 9 in 10 pieces of the agent's work.",
    'More work follows a playbook.',
    'The backlog of pending software updates is 86% smaller.',
    '57% of work found something on the way.',
    'It got faster too.',
  ],
  weeks: ['week 1', 'week 7'],
  coverage: {
    title: "Agent's work covered by a playbook",
    points: [{value: 63}, {value: 74}, {value: 77}, {value: 80}, {value: 80}, {value: 83}, {value: 86}, {value: 89}],
    axis: ['start', 'week 1', 'week 7'],
    labels: ['63%', '89%'],
  },
  playbook: {title: 'Work that follows a playbook', from: 29, to: 45},
  backlog: {title: 'Pending software updates', from: 100, to: 14, note: '86% smaller'},
  found: {to: 57, label: 'of work found something on the way', note: '1 in 6 findings became a fix or planned work', mini: [1, 6]},
  speed: [
    {title: 'Finished work that needed no one to type a word', from: 42, to: 52},
    {title: 'Finished work done by the agent', from: 70, to: 78},
  ],
  pair: ['first weeks', 'last weeks'],
  caveat: ["Measured on a real team's work.", 'A person approved every release.'],
};

// Strings outside RESULTS that carry digits but are not measurements.
export const NOT_MEASUREMENTS: string[] = [];

// What a viewer reads while each spoken line plays, one entry per line of NARRATION.
export const READ: Record<Scene, string[]> = {
  problem: TEXT.problem.lines,
  turn: TEXT.turn.lines,
  map: TEXT.map.lines,
  join: TEXT.join.lines,
  steer: TEXT.steer.lines,
  memory: TEXT.memory.lines,
  compounds: TEXT.compounds.lines,
  history: TEXT.history.lines,
  results: RESULTS.lines,
  end: TEXT.end.lines,
};

export const LEAD_S = 0.5;
export const GAP_S = 0.6;
const readS = (s: string) => 0.3 * s.split(/\s+/).length + 1;

// Frame, from the start of its scene, at which each spoken line starts. A line holds the screen for as long as it
// takes to say plus a breath, or to read at 0.3 s a word plus 1 s, whichever is longer.
export function cues(scene: Scene): number[] {
  const out: number[] = [];
  let t = LEAD_S;
  VOICE[scene].forEach((len, i) => {
    out.push(Math.round(t * FPS));
    t += Math.max(len + GAP_S, readS(READ[scene][i] ?? ''));
  });
  return out;
}

export function cueEnd(scene: Scene): number {
  const c = cues(scene);
  const i = c.length - 1;
  return c[i] + Math.round(Math.max(VOICE[scene][i] + GAP_S, readS(READ[scene][i] ?? '')) * FPS);
}
