import React from 'react';
import {AbsoluteFill, Easing, Html5Audio, Sequence, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {BAR, BARS, BEAT, FPS, MUSIC, RESULTS, SCENES, type Scene, TEXT, VOICE, cues} from './intro-data';

export const INTRO_FRAMES = BARS * BAR;

const ACCENT = '#6EE7B7';
const RED = '#F87171';
const BG = '#0A0C10';
const PANEL = '#11141B';
const DIM = '#8A93A6';
const SOFT = '#C9D1DC';
const SANS = "-apple-system, 'SF Pro Display', 'Helvetica Neue', Arial, sans-serif";
const MONO = 'Menlo, Monaco, monospace';
const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;
const ease = Easing.bezier(0.33, 0, 0.2, 1);

const bars = (n: number) => n * BAR;

function pulse(frame: number) {
  return Math.exp(-((frame % BEAT) / BEAT) * 5);
}

function draw(frame: number, start: number, len = 24) {
  return interpolate(frame, [start, start + len], [0, 1], {...clamp, easing: ease});
}

function pop(frame: number, at: number, fps: number, damping = 11) {
  return spring({frame: frame - at, fps, config: {damping, stiffness: 170, mass: 0.7}});
}

type IconName =
  | 'shield' | 'book' | 'layers' | 'lock' | 'unlock' | 'chat' | 'logo' | 'person' | 'robot' | 'box' | 'page' | 'laptop'
  | 'flag' | 'folder' | 'code' | 'slices' | 'check' | 'puzzle' | 'plug' | 'toolbox' | 'wrench';

const ICONS: Record<IconName, string[]> = {
  slices: ['M22 66 h56 v12 h-56 z', 'M22 46 h56 v12 h-56 z', 'M22 26 h56 v12 h-56 z'],
  shield: ['M50 14 L80 26 V50 C80 68 66 80 50 86 C34 80 20 68 20 50 V26 Z', 'M36 50 l10 10 l20 -22'],
  book: ['M50 26 C40 18 26 18 18 22 V78 C26 74 40 74 50 82 C60 74 74 74 82 78 V22 C74 18 60 18 50 26 Z', 'M50 26 V82'],
  layers: ['M50 18 L84 34 L50 50 L16 34 Z', 'M16 50 L50 66 L84 50', 'M16 66 L50 82 L84 66'],
  lock: ['M28 46 h44 v36 h-44 z', 'M36 46 V34 a14 14 0 0 1 28 0 V46', 'M50 60 v10'],
  unlock: ['M28 46 h44 v36 h-44 z', 'M36 46 V30 a14 14 0 0 1 28 0', 'M50 60 v10'],
  chat: ['M18 24 H82 V66 H46 L30 80 V66 H18 Z', 'M34 40 H66', 'M34 52 H56'],
  person: ['M50 20 m-14 0 a14 14 0 1 0 28 0 a14 14 0 1 0 -28 0', 'M22 84 C22 62 34 52 50 52 C66 52 78 62 78 84'],
  robot: ['M24 34 H76 V78 H24 Z', 'M50 34 V20', 'M50 16 m-4 0 a4 4 0 1 0 8 0 a4 4 0 1 0 -8 0', 'M38 52 v4', 'M62 52 v4', 'M38 66 H62'],
  box: ['M14 40 H66 V90 H14 Z', 'M14 40 L32 22 H86 L66 40', 'M66 40 L86 22 V72 L66 90'],
  page: ['M28 12 H60 L76 28 V88 H28 Z', 'M60 12 V28 H76', 'M38 46 H66', 'M38 60 H66', 'M38 74 H56'],
  laptop: ['M24 26 H76 V62 H24 Z', 'M12 72 H88 L82 82 H18 Z'],
  flag: ['M30 88 V14', 'M30 16 H76 L64 31 L76 46 H30'],
  folder: ['M12 28 H40 L48 36 H88 V82 H12 Z', 'M12 46 H88'],
  code: ['M36 32 L18 50 L36 68', 'M64 32 L82 50 L64 68', 'M56 24 L44 76'],
  check: ['M24 52 L42 70 L76 32'],
  puzzle: ['M28 30 H43 a7 7 0 1 1 14 0 H72 V45 a7 7 0 1 1 0 14 V74 H57 a7 7 0 1 0 -14 0 H28 Z'],
  plug: ['M38 14 V30', 'M62 14 V30', 'M28 30 H72 V48 C72 62 62 70 50 70 C38 70 28 62 28 48 Z', 'M50 70 V88'],
  toolbox: ['M12 40 H88 V84 H12 Z', 'M36 40 V28 H64 V40', 'M12 58 H88', 'M44 53 V63 H56 V53'],
  wrench: ['M66 14 a20 20 0 0 0 -19 27 L16 72 a8 8 0 0 0 12 12 L59 53 a20 20 0 0 0 27 -19 L74 46 L62 40 L56 28 Z'],
  logo: ['M50 10 L85 30 V70 L50 90 L15 70 V30 Z', 'M50 30 L67 40 V60 L50 70 L33 60 V40 Z', 'M50 10 V30', 'M85 70 L67 60', 'M15 70 L33 60'],
};

const Icon: React.FC<{name: IconName; size: number; progress: number; color?: string; width?: number}> = ({name, size, progress, color = ACCENT, width = 5}) => (
  <svg width={size} height={size} viewBox="0 0 100 100" fill="none" style={{overflow: 'visible'}}>
    {ICONS[name].map((d, i) => (
      <path
        key={i}
        d={d}
        pathLength={1}
        stroke={color}
        strokeWidth={width}
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeDasharray={1}
        strokeDashoffset={1 - Math.min(1, Math.max(0, progress * ICONS[name].length - i * 0.6))}
      />
    ))}
  </svg>
);

const Glyph: React.FC<{
  name: IconName;
  x: number;
  y: number;
  size: number;
  at: number;
  color?: string;
  ring?: string;
  opacity?: number;
  sy?: number;
  label?: string;
  labelColor?: string;
  dashed?: boolean;
}> = ({name, x, y, size, at, color = ACCENT, ring, opacity = 1, sy = 1, label, labelColor = SOFT, dashed}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const s = pop(frame, at, fps);
  if (frame < at) return null;
  return (
    <div style={{position: 'absolute', left: x - size / 2, top: y - size / 2, width: size, height: size, opacity: Math.min(1, s * 2) * opacity, transform: `scale(${s}, ${s * sy})`, transformOrigin: '50% 100%'}}>
      <div
        style={{
          width: size,
          height: size,
          borderRadius: size / 2,
          background: ring ? 'rgba(17,20,27,0.92)' : undefined,
          border: ring ? `3px ${dashed ? 'dashed' : 'solid'} ${ring}` : undefined,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <Icon name={name} size={ring ? size * 0.58 : size} progress={draw(frame, at, 20)} color={color} />
      </div>
      {label && (
        <div style={{position: 'absolute', top: size + 10, left: -160, width: size + 320, textAlign: 'center', fontFamily: SANS, fontWeight: 700, fontSize: 34, color: labelColor}}>{label}</div>
      )}
    </div>
  );
};

const Tag: React.FC<{text: string; x: number; y: number; at: number; color?: string; size?: number; solid?: boolean}> = ({text, x, y, at, color = ACCENT, size = 32, solid}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const s = pop(frame, at, fps, 10);
  if (frame < at) return null;
  return (
    <div
      style={{
        position: 'absolute',
        left: x,
        top: y,
        transform: `translate(-50%, -50%) scale(${s})`,
        opacity: Math.min(1, s * 2),
        fontFamily: SANS,
        fontWeight: 700,
        fontSize: size,
        color: solid ? BG : color,
        background: solid ? color : 'rgba(17,20,27,0.92)',
        border: `2px solid ${color}`,
        borderRadius: 999,
        padding: '8px 24px',
        whiteSpace: 'nowrap',
      }}
    >
      {text}
    </div>
  );
};

// The on-screen line for each spoken line, revealed word by word as the voice starts it. Words after a colon are
// the point of the sentence, so they take the accent colour.
const Say: React.FC<{lines: string[]; at: number[]; size?: number; top?: number; last?: number}> = ({lines, at, size = 62, top = 72, last}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  return (
    <div style={{position: 'absolute', top, left: 120, right: 120, height: 230}}>
      {lines.map((line, i) => {
        const next = at[i + 1] ?? last;
        const out = next === undefined ? 0 : interpolate(frame, [next - 6, next + 4], [0, 1], clamp);
        if (frame < at[i] - 1 || out >= 1) return null;
        let accent = false;
        return (
          <div key={i} style={{position: 'absolute', inset: 0, display: 'flex', flexWrap: 'wrap', justifyContent: 'center', alignContent: 'flex-start', opacity: 1 - out, transform: `translateY(${-30 * out}px)`}}>
            {line.split(' ').map((w, wi) => {
              const s = spring({frame: frame - at[i] - wi * 2, fps, config: {damping: 14, stiffness: 160, mass: 0.6}});
              const color = accent ? ACCENT : '#FFF';
              if (w.endsWith(':')) accent = true;
              return (
                <span key={wi} style={{display: 'inline-block', marginRight: '0.24em', fontFamily: SANS, fontWeight: 800, fontSize: size, lineHeight: 1.14, letterSpacing: '-0.03em', color, opacity: Math.min(1, s * 1.5), transform: `translateY(${(1 - s) * 50}px)`}}>
                  {w}
                </span>
              );
            })}
          </div>
        );
      })}
    </div>
  );
};

const Background: React.FC = () => {
  const frame = useCurrentFrame();
  const p = pulse(frame);
  const inLift = [[MUSIC.liftA, MUSIC.break], [MUSIC.liftB, MUSIC.groove], [MUSIC.liftC, MUSIC.outro]].some(([a, b]) => frame >= bars(a) && frame < bars(b));
  const lift = inLift ? 1 : 0.35;
  return (
    <AbsoluteFill style={{background: BG, overflow: 'hidden'}}>
      <AbsoluteFill
        style={{
          background: `radial-gradient(1100px 700px at ${50 + Math.sin(frame / 90) * 20}% ${30 + Math.cos(frame / 120) * 10}%, rgba(110,231,183,${0.08 + 0.05 * p * lift}), transparent 65%)`,
        }}
      />
      {[0, 1, 2].map((i) => {
        const x = ((frame * (0.6 + i * 0.25) + i * 700) % 2600) - 400;
        return (
          <div key={i} style={{position: 'absolute', left: x, top: 120 + i * 330, width: 420, height: 420, borderRadius: '50%', border: '1px solid rgba(110,231,183,0.08)', transform: `scale(${1 + 0.04 * p * lift})`}} />
        );
      })}
      <AbsoluteFill style={{backgroundImage: 'radial-gradient(rgba(255,255,255,0.06) 1.2px, transparent 1.2px)', backgroundSize: '48px 48px', backgroundPosition: `${-frame * 0.3}px ${-frame * 0.15}px`, opacity: 0.6}} />
    </AbsoluteFill>
  );
};

const Wipe: React.FC = () => {
  const frame = useCurrentFrame();
  const x = interpolate(frame, [0, 12], [-1, 1], {...clamp, easing: ease});
  return <div style={{position: 'absolute', top: 0, bottom: 0, left: `${x * 100}%`, width: '100%', background: ACCENT, opacity: 0.9, transform: 'skewX(-12deg)'}} />;
};

const Fade: React.FC<{len: number; children: React.ReactNode}> = ({len, children}) => {
  const frame = useCurrentFrame();
  const o = interpolate(frame, [0, 6, len - 6, len], [0, 1, 1, 0], clamp);
  const t = frame / len;
  return (
    <AbsoluteFill style={{opacity: o, transform: `scale(${1 + 0.03 * t}) translate(${Math.sin(t * Math.PI) * 10}px, ${Math.sin(t * Math.PI * 1.6) * 6}px)`}}>
      {children}
    </AbsoluteFill>
  );
};

const PIECES: IconName[] = ['puzzle', 'plug', 'robot'];
const PIECE_AT = [{x: 520, y: 500}, {x: 960, y: 450}, {x: 1400, y: 520}];

const Problem: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const c = cues('problem');
  const T = TEXT.problem;
  const apart = draw(frame, c[1] + 4, 40);
  const lostAt = c[1] + 85;
  const lost = interpolate(frame, [lostAt + 40, lostAt + 130], [1, 0.3], clamp);
  const srcX = [700, 1220];
  const srcIcons: IconName[] = ['chat', 'laptop'];
  return (
    <AbsoluteFill>
      <Say lines={T.lines} at={c} />
      {[720, 880, 1040, 1200].map((x, i) => (
        <Glyph key={i} name="person" x={x} y={850} size={110} at={4 + i * 4} color={SOFT} opacity={1 - apart * 0.5} />
      ))}
      {PIECES.map((ic, i) => {
        const at = c[0] + 40 + i * 20;
        const s = spring({frame: frame - at, fps, config: {damping: 10, stiffness: 90, mass: 1}});
        if (frame < at) return null;
        const from = [{x: -200, y: 300}, {x: 960, y: -200}, {x: 2100, y: 300}][i];
        const out = [{x: 180, y: 380}, {x: 960, y: 330}, {x: 1740, y: 400}][i];
        const home = PIECE_AT[i];
        const x = interpolate(s, [0, 1], [from.x, home.x]) + (out.x - home.x) * apart + Math.sin(frame / 18 + i * 2) * 10;
        const y = interpolate(s, [0, 1], [from.y, home.y]) + (out.y - home.y) * apart + Math.cos(frame / 22 + i) * 12;
        return (
          <div key={i} style={{position: 'absolute', left: x - 90, top: y - 90, width: 180, height: 180, opacity: 1 - apart * 0.75, transform: `rotate(${(1 - Math.min(1, s)) * 90 + Math.sin(frame / 25 + i) * 8}deg)`}}>
            <div style={{width: 180, height: 180, borderRadius: 32, border: `3px dashed ${SOFT}`, background: 'rgba(17,20,27,0.9)', display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
              <Icon name={ic} size={110} progress={1} color={SOFT} />
            </div>
            <div style={{position: 'absolute', top: 196, left: -60, width: 300, textAlign: 'center', fontFamily: SANS, fontWeight: 700, fontSize: 34, color: SOFT}}>{T.pieces[i]}</div>
          </div>
        );
      })}
      {srcX.map((x, s) => (
        <React.Fragment key={s}>
          <div style={{opacity: lost}}>
            <Glyph name={srcIcons[s]} x={x} y={560} size={170} at={lostAt + s * 10} ring="rgba(255,255,255,0.3)" color={SOFT} label={T.places[s]} dashed />
          </div>
          {Array.from({length: 9}).map((_, k) => {
            const start = lostAt + 20 + k * 7 + s * 4;
            const t = interpolate(frame, [start, start + 55], [0, 1], clamp);
            if (t <= 0 || t >= 1) return null;
            const a = ((k * 137 + s * 61) % 360) * (Math.PI / 180);
            const d = (150 + ((k * 29) % 110)) * ease(t);
            return (
              <div key={k} style={{position: 'absolute', left: x + Math.cos(a) * d - 13, top: 560 + Math.sin(a) * d * 0.8 - 13, width: 26, height: 26, borderRadius: 6, background: ACCENT, opacity: 1 - t, transform: `rotate(${t * 200}deg) scale(${1 - t * 0.5})`, filter: `blur(${t * 4}px)`}} />
            );
          })}
        </React.Fragment>
      ))}
    </AbsoluteFill>
  );
};

const Turn: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const c = cues('turn');
  const box = {x: 960, y: 700};
  const boxPop = pop(frame, c[0] + 6, fps, 10);
  const slots = [760, 840, 920, 1000, 1080, 1160].map((x) => ({x, y: box.y - 170}));
  const tools: {icon: IconName; slot: number; at: number; from: Pt; ours: boolean}[] = [
    ...PIECES.map((icon, i) => ({icon, slot: i + 1, at: c[0] + 26 + i * 10, from: PIECE_AT[i], ours: true})),
    {icon: 'laptop', slot: 0, at: c[0] + 90, from: {x: -150, y: 640}, ours: false},
    {icon: 'chat', slot: 4, at: c[0] + 100, from: {x: 2070, y: 600}, ours: false},
    {icon: 'code', slot: 5, at: c[0] + 110, from: {x: 2070, y: 760}, ours: false},
  ];
  const n = 5;
  const team = Array.from({length: n}).map((_, i) => {
    const a = Math.PI + (i * Math.PI) / (n - 1);
    return {x: box.x + Math.cos(a) * 640, y: box.y + 40 + Math.sin(a) * 330, at: c[1] + 10 + i * 8};
  });
  return (
    <AbsoluteFill>
      <Say lines={TEXT.turn.lines} at={c} />
      <svg width={1920} height={1080} style={{position: 'absolute'}}>
        {team.map((p, i) => (
          <path key={i} d={`M${box.x} ${box.y} Q ${(box.x + p.x) / 2} ${p.y - 40} ${p.x} ${p.y}`} stroke={ACCENT} strokeWidth={4} fill="none" pathLength={1} strokeDasharray={1} strokeDashoffset={1 - draw(frame, p.at - 14, 18)} opacity={0.6} />
        ))}
      </svg>
      <div style={{position: 'absolute', left: box.x - 150, top: box.y - 150, width: 300, height: 300, transform: `scale(${boxPop * (1 + 0.04 * pulse(frame))})`, opacity: frame < c[0] + 6 ? 0 : 1}}>
        <div style={{width: 300, height: 300, borderRadius: 150, background: 'rgba(17,20,27,0.92)', display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
          <Icon name="toolbox" size={240} progress={draw(frame, c[0] + 6, 20)} />
        </div>
      </div>
      {tools.map((t, i) => {
        const s = spring({frame: frame - t.at, fps, config: {damping: 12, stiffness: 150}});
        const to = slots[t.slot];
        const x = interpolate(s, [0, 1], [t.from.x, to.x]);
        const y = interpolate(s, [0, 1], [t.from.y, to.y]) - Math.sin(Math.min(1, s) * Math.PI) * 60;
        const size = interpolate(s, [0, 1], [t.ours ? 150 : 90, 66]);
        const snap = frame >= t.at + 14 ? Math.exp(-(frame - t.at - 14) / 6) : 0;
        if (frame < t.at - 20 && !t.ours) return null;
        return (
          <div key={i} style={{position: 'absolute', left: x - size / 2, top: y - size / 2, width: size, height: size}}>
            <Icon name={t.icon} size={size} progress={1} color={t.ours ? ACCENT : SOFT} />
            {snap > 0.05 && <div style={{position: 'absolute', left: -20, top: -20, width: size + 40, height: size + 40, borderRadius: '50%', border: `3px solid ${ACCENT}`, opacity: snap, transform: `scale(${1.6 - snap * 0.6})`}} />}
          </div>
        );
      })}
      <div style={{opacity: 1 - draw(frame, c[1] - 6, 10)}}>
        <Tag text={TEXT.turn.yours} x={box.x} y={box.y + 200} at={c[0] + 120} color={SOFT} size={30} />
      </div>
      {team.map((p, i) => (
        <Glyph key={i} name="person" x={p.x} y={p.y} size={100} at={p.at} ring={ACCENT} />
      ))}
    </AbsoluteFill>
  );
};

type Pt = {x: number; y: number};

function along(pts: Pt[], t: number): {p: Pt; passed: number} {
  const seg = pts.slice(1).map((b, i) => Math.hypot(b.x - pts[i].x, b.y - pts[i].y));
  const total = seg.reduce((a, b) => a + b, 0);
  let left = t * total;
  for (let i = 0; i < seg.length; i++) {
    if (left <= seg[i]) {
      const u = seg[i] ? left / seg[i] : 0;
      return {p: {x: pts[i].x + (pts[i + 1].x - pts[i].x) * u, y: pts[i].y + (pts[i + 1].y - pts[i].y) * u}, passed: i};
    }
    left -= seg[i];
  }
  return {p: pts[pts.length - 1], passed: pts.length - 1};
}

const MapScene: React.FC = () => {
  const frame = useCurrentFrame();
  const c = cues('map');
  const T = TEXT.map;
  const lead = {x: 260, y: 620};
  const nodes: {x: number; y: number; icon: IconName; col: number}[] = [
    {x: 760, y: 470, icon: 'layers', col: 0},
    {x: 1150, y: 470, icon: 'slices', col: 1},
    {x: 1540, y: 560, icon: 'shield', col: 2},
    {x: 1150, y: 640, icon: 'slices', col: 1},
    {x: 760, y: 640, icon: 'layers', col: 0},
    {x: 760, y: 810, icon: 'layers', col: 0},
    {x: 1150, y: 810, icon: 'slices', col: 1},
    {x: 1540, y: 740, icon: 'shield', col: 2},
  ];
  const pts = [{x: lead.x + 70, y: lead.y - 10}, ...nodes];
  const t = interpolate(frame, [c[0] + 12, c[1] - 6], [0, 1], {...clamp, easing: Easing.inOut(Easing.quad)});
  const pen = along(pts, t);
  const reachedAt = nodes.map((_, i) => {
    for (let f = c[0] + 12; f <= c[1]; f++) {
      if (along(pts, interpolate(f, [c[0] + 12, c[1] - 6], [0, 1], {...clamp, easing: Easing.inOut(Easing.quad)})).passed > i) return f;
    }
    return c[1];
  });
  const firstInCol = [0, 1, 2].map((col) => Math.min(...nodes.map((n, i) => (n.col === col ? reachedAt[i] : Infinity))));
  const drawn = [...pts.slice(0, pen.passed + 1), pen.p];
  const frameDraw = draw(frame, c[1], 30);
  return (
    <AbsoluteFill>
      <Say lines={T.lines} at={c} />
      <Glyph name="person" x={lead.x} y={lead.y} size={170} at={2} ring={ACCENT} label={T.lead} labelColor="#FFF" />
      <svg width={1920} height={1080} style={{position: 'absolute'}}>
        <polyline points={drawn.map((p) => `${p.x},${p.y}`).join(' ')} stroke={ACCENT} strokeWidth={5} fill="none" strokeLinejoin="round" strokeLinecap="round" opacity={0.7} />
        <rect x={620} y={330} width={1080} height={570} rx={40} stroke={ACCENT} strokeWidth={4} fill="none" strokeDasharray="18 14" pathLength={1000} strokeDashoffset={0} opacity={frameDraw} style={{clipPath: `inset(0 ${(1 - frameDraw) * 100}% 0 0)`}} />
        {t > 0 && t < 1 && <circle cx={pen.p.x} cy={pen.p.y} r={12 + 4 * pulse(frame)} fill="#FFF" />}
      </svg>
      {nodes.map((n, i) => (
        <Glyph key={i} name={n.icon} x={n.x} y={n.y} size={100} at={reachedAt[i]} ring={ACCENT} />
      ))}
      {T.kinds.map((k, col) => (
        <Tag key={k} text={k} x={[760, 1150, 1540][col]} y={375} at={firstInCol[col]} size={30} />
      ))}
      <Tag text={T.frame} x={1160} y={900} at={c[1] + 18} size={36} solid />
    </AbsoluteFill>
  );
};

const Join: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const c = cues('join');
  const T = TEXT.join;
  const hub = {x: 960, y: 640};
  const n = 7;
  const people = Array.from({length: n}).map((_, i) => {
    const a = Math.PI + (i * 2 * Math.PI) / n;
    return {x: hub.x + Math.cos(a) * 580, y: hub.y + Math.sin(a) * 240, at: i === 0 ? 0 : c[0] + 6 + i * 6};
  });
  const period = 44;
  const glow = pulse(frame);
  return (
    <AbsoluteFill>
      <Say lines={T.lines} at={c} />
      <svg width={1920} height={1080} style={{position: 'absolute'}}>
        {people.map((p, i) => (
          <line key={i} x1={p.x} y1={p.y} x2={hub.x} y2={hub.y} stroke="rgba(110,231,183,0.25)" strokeWidth={3} strokeDasharray="8 10" strokeDashoffset={-frame} opacity={draw(frame, p.at + 8, 12)} />
        ))}
        {people.map((p, i) =>
          [0, 1].map((dir) => {
            if (dir === 1 && frame < c[1]) return null;
            const start = Math.max(p.at + 16, dir ? c[1] : 0) + ((i * 11 + dir * 22) % period);
            if (frame < start) return null;
            const u = ((frame - start) % period) / period;
            const a = dir ? hub : p;
            const b = dir ? p : hub;
            const x = a.x + (b.x - a.x) * u;
            const y = a.y + (b.y - a.y) * u;
            return <circle key={`${i}${dir}`} cx={x} cy={y} r={10} fill={dir ? '#FFF' : ACCENT} opacity={Math.min(1, u * 5, (1 - u) * 5)} />;
          }),
        )}
      </svg>
      {people.map((p, i) => {
        const arrive = frame >= c[1] ? ((frame - (c[1] + ((i * 11 + 22) % period))) % period + period) % period : period;
        const spark = arrive < 12 ? 1 - arrive / 12 : 0;
        return (
          <React.Fragment key={i}>
            <Glyph name="person" x={p.x} y={p.y} size={100} at={p.at} ring={i === 0 ? ACCENT : 'rgba(255,255,255,0.35)'} color={i === 0 ? ACCENT : SOFT} />
            {spark > 0 && <div style={{position: 'absolute', left: p.x - 70, top: p.y - 70, width: 140, height: 140, borderRadius: 70, border: `3px solid #FFF`, opacity: spark, transform: `scale(${1.6 - spark * 0.6})`}} />}
          </React.Fragment>
        );
      })}
      <div style={{position: 'absolute', left: hub.x - 120, top: hub.y - 120, width: 240, height: 240, borderRadius: 120, boxShadow: `0 0 ${60 + 60 * glow}px rgba(110,231,183,${0.25 + 0.25 * glow})`, opacity: pop(frame, 4, fps)}} />
      <Glyph name="robot" x={hub.x} y={hub.y} size={220} at={4} ring={ACCENT} label={T.agent} labelColor="#FFF" />
    </AbsoluteFill>
  );
};

type Line = {from: string; text: string};

const Chat: React.FC<{lines: Line[]; times: number[]}> = ({lines, times}) => {
  const frame = useCurrentFrame();
  const o = draw(frame, times[0] - 10, 12);
  return (
    <div style={{width: 1240, borderRadius: 24, background: PANEL, border: '1px solid rgba(255,255,255,0.1)', boxShadow: '0 40px 120px rgba(0,0,0,0.6)', padding: '28px 36px', display: 'flex', flexDirection: 'column', gap: 20, opacity: o, transform: `translateY(${(1 - o) * 30}px)`}}>
      {lines.map((l, i) => {
        const b = draw(frame, times[i], 10);
        const ai = l.from === 'ai';
        const typing = ai && frame >= times[i] - 22 && frame < times[i];
        return (
          <div key={i} style={{display: 'flex', justifyContent: ai ? 'flex-start' : 'flex-end', alignItems: 'center', gap: 18, height: 84}}>
            {ai && <Icon name="robot" size={64} progress={typing ? 1 : b} />}
            {typing ? (
              <div style={{display: 'flex', gap: 10, padding: '22px 28px', borderRadius: 22, background: 'rgba(110,231,183,0.12)', border: `2px solid ${ACCENT}`}}>
                {[0, 1, 2].map((d) => (
                  <div key={d} style={{width: 14, height: 14, borderRadius: 7, background: ACCENT, transform: `translateY(${Math.sin((frame + d * 4) / 3) * 5}px)`}} />
                ))}
              </div>
            ) : (
              <div style={{maxWidth: 940, fontFamily: SANS, fontSize: 40, lineHeight: 1.3, color: ai ? '#FFF' : BG, background: ai ? 'rgba(110,231,183,0.12)' : '#E6EAF0', border: ai ? `2px solid ${ACCENT}` : 'none', borderRadius: 22, padding: '14px 28px', opacity: b, transform: `translateY(${(1 - b) * 16}px) scale(${0.9 + 0.1 * b})`}}>
                {l.text}
              </div>
            )}
            {!ai && <Icon name="person" size={64} progress={b} color={SOFT} />}
          </div>
        );
      })}
    </div>
  );
};

const Steer: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const c = cues('steer');
  const T = TEXT.steer;
  const times = [c[0] + 6, c[1], c[1] + 30, c[2] + 6];
  const opened = frame >= times[2] + 8;
  const stamp = spring({frame: frame - c[2] - 50, fps, config: {damping: 12, stiffness: 200}});
  return (
    <AbsoluteFill>
      <Say lines={T.lines} at={c} />
      <div style={{position: 'absolute', top: 290, left: 0, right: 0, display: 'flex', justifyContent: 'center'}}>
        <Chat lines={T.chat} times={times} />
      </div>
      <div style={{position: 'absolute', left: 1640, top: 520, transform: `scale(${1 + (opened ? 0.15 * Math.exp(-(frame - times[2] - 8) / 6) : 0)})`, opacity: draw(frame, times[1], 10)}}>
        <Icon name={opened ? 'unlock' : 'lock'} size={130} progress={1} color={opened ? ACCENT : SOFT} />
      </div>
      {frame >= c[2] + 50 && (
        <div style={{position: 'absolute', left: 960, top: 930, transform: `translate(-50%, -50%) scale(${2 - stamp}) rotate(${(1 - stamp) * -8}deg)`, opacity: Math.min(1, stamp * 2), display: 'flex', alignItems: 'center', gap: 16, background: ACCENT, color: BG, borderRadius: 999, padding: '12px 36px 12px 20px', fontFamily: SANS, fontWeight: 800, fontSize: 44}}>
          <Icon name="check" size={52} progress={1} color={BG} width={10} />
          {T.passed}
        </div>
      )}
    </AbsoluteFill>
  );
};

const curve = (a: Pt, b: Pt) => `M${a.x} ${a.y} C ${a.x + (b.x - a.x) * 0.5} ${a.y}, ${a.x + (b.x - a.x) * 0.5} ${b.y}, ${b.x} ${b.y}`;

const Skill: React.FC<{at: number}> = ({at}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const T = TEXT.memory;
  const box = {x: 430, y: 660};
  const land = at + 34;
  const drop = spring({frame: frame - at - 6, fps, config: {damping: 10, stiffness: 140}});
  const cols = 6;
  const rows = 4;
  const before = 8;
  const after = 19;
  const lit = before + (after - before) * draw(frame, land + 4, 36);
  const beam = draw(frame, land, 14);
  return (
    <AbsoluteFill>
      <Glyph name="toolbox" x={box.x} y={box.y} size={230} at={at - 4} ring={ACCENT} />
      <div style={{position: 'absolute', left: box.x - 50, top: interpolate(drop, [0, 1], [300, box.y - 210]), width: 100, height: 100, opacity: frame < at + 6 ? 0 : 1, transform: `rotate(${(1 - Math.min(1, drop)) * -40}deg)`}}>
        <Icon name="wrench" size={100} progress={1} color="#FFF" />
      </div>
      <Tag text={T.skill} x={box.x} y={box.y + 170} at={land} solid />
      <svg width={1920} height={1080} style={{position: 'absolute'}}>
        <line x1={box.x + 130} y1={box.y} x2={box.x + 130 + (900 - box.x - 150) * beam} y2={box.y} stroke={ACCENT} strokeWidth={5} strokeDasharray="12 10" strokeDashoffset={-frame * 2} opacity={beam > 0 ? 0.8 : 0} />
      </svg>
      <div style={{position: 'absolute', left: 900, top: 450, width: cols * 110, display: 'flex', flexWrap: 'wrap', gap: 14, opacity: draw(frame, at, 12)}}>
        {Array.from({length: cols * rows}).map((_, i) => {
          const order = (i * 7) % (cols * rows);
          const on = lit > order;
          const k = Math.max(0, Math.min(1, lit - order));
          const fresh = order >= before;
          return <div key={i} style={{width: 96, height: 96, borderRadius: 18, border: `3px solid ${on ? ACCENT : 'rgba(255,255,255,0.15)'}`, background: on ? `rgba(110,231,183,${fresh ? 0.12 + 0.3 * (1 - k) : 0.12})` : 'transparent', transform: `scale(${on && fresh ? 1 + 0.18 * Math.max(0, 1 - k * 2) : 1})`}} />;
        })}
      </div>
      <Tag text={T.system} x={900 + (cols * 110 - 14) / 2} y={400} at={at + 6} />
    </AbsoluteFill>
  );
};

const Memory: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const c = cues('memory');
  const T = TEXT.memory;
  const root = {x: 330, y: 630};
  const topics = [440, 630, 820].map((y) => ({x: 900, y}));
  const books = Array.from({length: 7}).map((_, i) => ({x: 1460, y: 390 + i * 82, parent: i < 2 ? 0 : i < 5 ? 1 : 2}));
  const lessons = Array.from({length: 7}).map((_, k) => ({start: c[0] + 8 + k * 12, from: {x: [80, 600, 200, 700, 60, 520, 300][k], y: [380, 400, 980, 960, 700, 1000, 360][k]}}));
  const bump = lessons.reduce((m, l) => {
    const d = frame - (l.start + 24);
    return d >= 0 && d < 10 ? Math.max(m, 1 - d / 10) : m;
  }, 0);
  const dim = interpolate(frame, [c[2] - 8, c[2] + 6], [1, 0.05], clamp);
  return (
    <AbsoluteFill>
      <Say lines={T.lines} at={c} />
      <div style={{position: 'absolute', inset: 0, opacity: dim}}>
      <svg width={1920} height={1080} style={{position: 'absolute'}}>
        {topics.map((t, i) => (
          <path key={i} d={curve({x: root.x + 90, y: root.y}, {x: t.x - 60, y: t.y})} stroke={ACCENT} strokeWidth={4} fill="none" pathLength={1} strokeDasharray={1} strokeDashoffset={1 - draw(frame, c[1] + i * 6, 24)} opacity={0.6} />
        ))}
        {books.map((b, i) => {
          const t = topics[b.parent];
          return <path key={i} d={curve({x: t.x + 60, y: t.y}, {x: b.x - 45, y: b.y})} stroke={ACCENT} strokeWidth={3} fill="none" pathLength={1} strokeDasharray={1} strokeDashoffset={1 - draw(frame, c[1] + 30 + i * 5, 20)} opacity={0.5} />;
        })}
      </svg>
      {lessons.map((l, k) => {
        const t = interpolate(frame, [l.start, l.start + 24], [0, 1], {...clamp, easing: ease});
        if (t <= 0 || t >= 1) return null;
        return <div key={k} style={{position: 'absolute', left: l.from.x + (root.x - l.from.x) * t - 12, top: l.from.y + (root.y - l.from.y) * t - 12, width: 24, height: 24, borderRadius: 12, background: ACCENT, boxShadow: '0 0 20px rgba(110,231,183,0.8)'}} />;
      })}
      <div style={{transform: `scale(${1 + 0.12 * bump})`, transformOrigin: `${root.x}px ${root.y}px`, position: 'absolute', inset: 0}}>
        <Glyph name="page" x={root.x} y={root.y} size={180} at={2} ring={ACCENT} />
      </div>
      {topics.map((t, i) => (
        <Glyph key={i} name="page" x={t.x} y={t.y} size={110} at={c[1] + i * 6 + 20} ring={ACCENT} />
      ))}
      {books.map((b, i) => (
        <Glyph key={i} name="book" x={b.x} y={b.y} size={74} at={c[1] + 48 + i * 5} ring="rgba(110,231,183,0.6)" />
      ))}
      <Tag text={T.levels[0]} x={root.x} y={root.y + 135} at={10} />
      <Tag text={T.levels[1]} x={900} y={930} at={c[1] + 30} />
      <Tag text={T.levels[2]} x={1700} y={630} at={c[1] + 85} />
      </div>
      {frame >= c[2] - 4 && <Skill at={c[2]} />}
    </AbsoluteFill>
  );
};

const Compounds: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const c = cues('compounds');
  const T = TEXT.compounds;
  const ox = 140;
  const oy = 900;
  const w = 720;
  const h = 520;
  const fn = (u: number) => ({x: ox + u * w, y: oy - (0.08 + 0.92 * u ** 2.2) * h});
  const grow = draw(frame, c[0] + 6, 100);
  const path = Array.from({length: 41}).map((_, i) => fn((i / 40) * grow));
  const ball = fn(grow);
  const listIn = draw(frame, c[1] - 4, 14);
  const notes = Array.from({length: 5}).map((_, k) => ({at: c[1] + 10 + k * 13, row: k}));
  const redAt = c[1] + 90;
  const redFall = spring({frame: frame - redAt, fps, config: {damping: 12, stiffness: 140}});
  const redTurn = draw(frame, redAt + 22, 26);
  const listX = 1060;
  const listY = 400;
  const person = {x: 1720, y: 560};
  const redX = interpolate(redTurn, [0, 1], [listX + 210, person.x]);
  const redY = interpolate(redFall, [0, 1], [300, 420]) + Math.sin(redTurn * Math.PI) * -80 + redTurn * (person.y - 420 + 90);
  const alert = frame >= redAt + 48 ? Math.exp(-((frame - redAt - 48) % 30) / 8) : 0;
  return (
    <AbsoluteFill>
      <Say lines={T.lines} at={c} />
      <svg width={1920} height={1080} style={{position: 'absolute'}}>
        <line x1={ox} y1={oy} x2={ox + w + 20} y2={oy} stroke="rgba(255,255,255,0.3)" strokeWidth={3} opacity={draw(frame, 0, 12)} />
        <line x1={ox} y1={oy} x2={ox} y2={oy - h - 20} stroke="rgba(255,255,255,0.3)" strokeWidth={3} opacity={draw(frame, 0, 12)} />
        <polyline points={path.map((p) => `${p.x},${p.y}`).join(' ')} stroke={ACCENT} strokeWidth={7} fill="none" strokeLinecap="round" />
        {grow > 0 && <circle cx={ball.x} cy={ball.y} r={14 + grow * 26 + 4 * pulse(frame)} fill={ACCENT} opacity={0.9} />}
      </svg>
      {T.growth.map((g, i) => {
        const u = 0.3 + i * 0.22;
        const p = fn(u);
        return <Tag key={g} text={g} x={p.x - 140} y={p.y - 10} at={c[0] + 6 + Math.round(u * 100)} size={30} />;
      })}
      <div style={{position: 'absolute', left: listX, top: listY, width: 420, height: 470, borderRadius: 22, background: PANEL, border: '2px solid rgba(255,255,255,0.15)', opacity: listIn, transform: `translateY(${(1 - listIn) * 30}px)`}}>
        <div style={{fontFamily: SANS, fontWeight: 700, fontSize: 32, color: DIM, padding: '18px 26px'}}>{T.list}</div>
      </div>
      {notes.map((nt, k) => {
        const s = spring({frame: frame - nt.at, fps, config: {damping: 11, stiffness: 160}});
        if (frame < nt.at) return null;
        const y = interpolate(s, [0, 1], [260, listY + 80 + nt.row * 74]);
        return <div key={k} style={{position: 'absolute', left: listX + 26, top: y, width: 368, height: 56, borderRadius: 12, background: 'rgba(110,231,183,0.14)', border: `2px solid ${ACCENT}`, opacity: Math.min(1, s * 3), transform: `rotate(${(1 - s) * (k % 2 ? 6 : -6)}deg)`}}>
          <div style={{margin: '20px 22px', height: 10, width: 180 + (k * 37) % 120, borderRadius: 5, background: 'rgba(110,231,183,0.6)'}} />
        </div>;
      })}
      {frame >= redAt && (
        <div style={{position: 'absolute', left: redX - 50, top: redY - 40, width: 100, height: 80, borderRadius: 14, background: 'rgba(248,113,113,0.18)', border: `3px solid ${RED}`, display: 'flex', alignItems: 'center', justifyContent: 'center', opacity: redTurn >= 1 ? 0 : 1}}>
          <Icon name="flag" size={52} progress={1} color={RED} />
        </div>
      )}
      <div style={{position: 'absolute', left: person.x - 100, top: person.y - 100, width: 200, height: 200, borderRadius: 100, border: `4px solid ${RED}`, opacity: alert, transform: `scale(${1.4 - alert * 0.4})`}} />
      <Glyph name="person" x={person.x} y={person.y} size={130} at={redAt + 10} ring={frame >= redAt + 48 ? RED : 'rgba(255,255,255,0.35)'} color={frame >= redAt + 48 ? RED : SOFT} />
      <Tag text={T.urgent} x={person.x} y={person.y + 110} at={redAt + 48} color={RED} solid size={30} />
    </AbsoluteFill>
  );
};

const History: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const c = cues('history');
  const T = TEXT.history;
  const laneY = [440, 590];
  const rewind = interpolate(frame, [c[1], c[1] + 36], [0, 1], {...clamp, easing: Easing.inOut(Easing.cubic)});
  const offset = -frame * 0.8 + rewind * 1500;
  const today = 1640;
  const yearAgo = today - 1500 - 110;
  const commits = Array.from({length: 22}).map((_, i) => yearAgo - 600 + i * 150);
  const lanesDim = interpolate(frame, [c[2] - 6, c[2] + 10], [1, 0.3], clamp);
  const blur = Math.abs(interpolate(frame, [c[1], c[1] + 18, c[1] + 36], [0, 1, 0], clamp));
  const zoom = pop(frame, c[1] + 40, fps, 10);
  const leaving = interpolate(frame, [c[2] + 10, c[2] + 50], [1, 0.12], clamp);
  const newcomer = c[2] + 46;
  const handoff = draw(frame, c[2] + 60, 30);
  return (
    <AbsoluteFill>
      <Say lines={T.lines} at={c} />
      <div style={{position: 'absolute', inset: 0, opacity: lanesDim}}>
        <svg width={1920} height={1080} style={{position: 'absolute', filter: `blur(${blur * 3}px)`}}>
          {laneY.map((y, i) => (
            <line key={i} x1={300} y1={y} x2={1860} y2={y} stroke={i ? 'rgba(110,231,183,0.5)' : 'rgba(255,255,255,0.25)'} strokeWidth={4} opacity={draw(frame, i * 8, 16)} />
          ))}
          {commits.map((cx, i) => {
            const x = cx + offset;
            if (x < 300 || x > 1860) return null;
            return <circle key={i} cx={x} cy={laneY[0]} r={13} fill={PANEL} stroke={SOFT} strokeWidth={4} />;
          })}
        </svg>
        {[{x: today + offset, text: T.today}, {x: commits[4] + offset, text: T.yearAgo}].map((m, i) =>
          m.x > 300 && m.x < 1860 ? (
            <div key={i} style={{position: 'absolute', left: m.x, top: 330, transform: 'translateX(-50%)', display: 'flex', flexDirection: 'column', alignItems: 'center'}}>
              <div style={{fontFamily: SANS, fontWeight: 800, fontSize: 30, color: i ? '#FFF' : DIM, background: i ? 'rgba(110,231,183,0.2)' : undefined, borderRadius: 10, padding: '4px 14px'}}>{m.text}</div>
              <div style={{width: 3, height: 320, background: i ? ACCENT : 'rgba(255,255,255,0.25)'}} />
            </div>
          ) : null,
        )}
        <div style={{position: 'absolute', inset: 0, filter: `blur(${blur * 3}px)`, overflow: 'hidden', clipPath: 'inset(0 60px 0 300px)'}}>
          {commits.map((cx, i) => {
            const x = cx + offset;
            if (i % 2 || x < 200 || x > 1960) return null;
            const label = T.notes[(i / 2) % 3];
            const isYear = cx === commits[4];
            return (
              <div key={i} style={{position: 'absolute', left: x, top: laneY[1], transform: `translate(-50%, -50%) scale(${isYear ? 1 + 0.25 * zoom : 1})`, background: isYear && zoom > 0.1 ? ACCENT : 'rgba(17,20,27,0.95)', color: isYear && zoom > 0.1 ? BG : ACCENT, border: `2px solid ${ACCENT}`, borderRadius: 12, padding: '8px 16px', fontFamily: SANS, fontWeight: 700, fontSize: 26, whiteSpace: 'nowrap', opacity: draw(frame, 10 + i, 10)}}>
                {label}
              </div>
            );
          })}
        </div>
        <div style={{position: 'absolute', left: 110, top: laneY[0] - 22, fontFamily: SANS, fontWeight: 700, fontSize: 34, color: SOFT, display: 'flex', gap: 14, alignItems: 'center'}}>
          <Icon name="code" size={44} progress={draw(frame, 0, 16)} color={SOFT} />
          {T.lanes[0]}
        </div>
        <div style={{position: 'absolute', left: 110, top: laneY[1] - 22, fontFamily: SANS, fontWeight: 700, fontSize: 34, color: ACCENT, display: 'flex', gap: 14, alignItems: 'center'}}>
          <Icon name="book" size={44} progress={draw(frame, 8, 16)} />
          {T.lanes[1]}
        </div>
      </div>
      {frame >= c[2] && (
        <>
          <div style={{opacity: leaving}}>
            <Glyph name="person" x={560} y={840} size={140} at={c[2]} ring="rgba(255,255,255,0.4)" color={SOFT} dashed={leaving < 0.9} />
          </div>
          {[0, 1, 2].map((k) => {
            const from = {x: 760 + k * 120, y: 840};
            const to = {x: 1200 + k * 34, y: 830 - k * 8};
            const s = pop(frame, c[2] + 14 + k * 5, fps, 10);
            const x = from.x + (to.x - from.x) * handoff;
            const y = from.y + (to.y - from.y) * handoff - Math.sin(handoff * Math.PI) * 60;
            return (
              <div key={k} style={{position: 'absolute', left: x - 40, top: y - 40, transform: `scale(${s}) rotate(${(k - 1) * 8 * (1 - handoff)}deg)`}}>
                <Icon name="page" size={80} progress={1} />
              </div>
            );
          })}
          <Glyph name="person" x={1420} y={840} size={140} at={newcomer} ring={ACCENT} />
          {handoff >= 1 && <div style={{position: 'absolute', left: 1420 - 100, top: 840 - 100, width: 200, height: 200, borderRadius: 100, boxShadow: `0 0 ${40 + 40 * pulse(frame)}px rgba(110,231,183,0.5)`}} />}
        </>
      )}
    </AbsoluteFill>
  );
};

const Dots: React.FC<{lit: number; total: number; size: number; at: number; from?: number}> = ({lit, total, size, at, from = 0}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  return (
    <div style={{display: 'flex', justifyContent: 'center', gap: size * 0.35}}>
      {Array.from({length: total}).map((_, i) => {
        const on = i < from ? 1 : i < lit ? pop(frame, at + (i - from) * 8, fps, 9) : 0;
        return <div key={i} style={{width: size, height: size, borderRadius: size / 2, border: `3px solid ${i < lit ? ACCENT : 'rgba(255,255,255,0.25)'}`, background: on > 0 ? ACCENT : 'transparent', opacity: i < from ? 0.55 : 1, transform: `scale(${i >= from && i < lit ? 0.6 + 0.4 * on : 1})`}} />;
      })}
    </div>
  );
};

const Panel: React.FC<{x: number; y: number; w: number; h: number; at: number; title: string; children: React.ReactNode}> = ({x, y, w, h, at, title, children}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const s = pop(frame, at, fps, 13);
  if (frame < at) return null;
  return (
    <div style={{position: 'absolute', left: x, top: y, width: w, height: h, borderRadius: 24, background: 'rgba(17,20,27,0.92)', border: '1px solid rgba(110,231,183,0.3)', opacity: Math.min(1, s * 2), transform: `translateY(${(1 - s) * 30}px) scale(${0.96 + 0.04 * s})`}}>
      <div style={{position: 'absolute', left: 28, top: 20, fontFamily: SANS, fontWeight: 700, fontSize: 30, color: SOFT}}>{title}</div>
      {children}
    </div>
  );
};

const LineChart: React.FC<{at: number; w: number; h: number}> = ({at, w, h}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const C = RESULTS.coverage;
  const FLOOR = 50;
  const left = 60;
  const top = 80;
  const pw = w - 150;
  const ph = h - 160;
  const pts = C.points.map((p, i) => ({x: left + (i / (C.points.length - 1)) * pw, y: top + ph * (1 - (p.value - FLOOR) / (100 - FLOOR))}));
  const grow = draw(frame, at + 10, 60);
  const reach = grow * (pts.length - 1);
  const shown = pts.filter((_, i) => i <= reach);
  const k = Math.floor(reach);
  const tip = k < pts.length - 1 ? {x: pts[k].x + (pts[k + 1].x - pts[k].x) * (reach - k), y: pts[k].y + (pts[k + 1].y - pts[k].y) * (reach - k)} : pts[pts.length - 1];
  const axisAt = [0, 1, pts.length - 1];
  const endPop = pop(frame, at + 72, fps, 9);
  return (
    <svg width={w} height={h} style={{position: 'absolute', left: 0, top: 0, overflow: 'visible'}}>
      <line x1={left} y1={top + ph} x2={left + pw} y2={top + ph} stroke="rgba(255,255,255,0.3)" strokeWidth={2} />
      <line x1={left} y1={top} x2={left + pw} y2={top} stroke="rgba(255,255,255,0.1)" strokeWidth={2} strokeDasharray="6 8" />
      <polygon points={[...shown, tip].map((p) => `${p.x},${p.y}`).join(' ') + ` ${tip.x},${top + ph} ${left},${top + ph}`} fill="rgba(110,231,183,0.12)" />
      <polyline points={[...shown, tip].map((p) => `${p.x},${p.y}`).join(' ')} stroke={ACCENT} strokeWidth={6} fill="none" strokeLinejoin="round" strokeLinecap="round" />
      {pts.map((p, i) => (i <= reach ? <circle key={i} cx={p.x} cy={p.y} r={i === pts.length - 1 ? 10 + 3 * endPop : 7} fill={ACCENT} /> : null))}
      {axisAt.map((i, j) => (
        <text key={i} x={pts[i].x} y={top + ph + 40} textAnchor="middle" fontFamily={SANS} fontSize={26} fill={DIM}>{C.axis[j]}</text>
      ))}
      <text x={pts[0].x + 14} y={pts[0].y + 54} fontFamily={SANS} fontWeight={800} fontSize={44} fill="#FFF" opacity={draw(frame, at + 10, 10)}>{C.labels[0]}</text>
      {frame >= at + 72 && <text x={pts[pts.length - 1].x} y={pts[pts.length - 1].y - 24} textAnchor="end" fontFamily={SANS} fontWeight={800} fontSize={60 * endPop} fill={ACCENT}>{C.labels[1]}</text>}
    </svg>
  );
};

const Pair: React.FC<{from: number; to: number; at: number; w: number; h: number; big?: boolean}> = ({from, to, at, w, h, big}) => {
  const frame = useCurrentFrame();
  const bars = [from, to];
  const bw = big ? 150 : 110;
  const gap = big ? 120 : 80;
  const base = h - 70;
  const max = h - (big ? 210 : 150);
  const x0 = (w - (2 * bw + gap)) / 2;
  return (
    <>
      {bars.map((v, i) => {
        const t = draw(frame, at + 10 + i * 24, 26);
        const bh = (v / 100) * max * t;
        const x = x0 + i * (bw + gap);
        return (
          <React.Fragment key={i}>
            <div style={{position: 'absolute', left: x, top: base - bh, width: bw, height: bh, borderRadius: '14px 14px 4px 4px', background: i ? ACCENT : 'rgba(255,255,255,0.25)'}} />
            <div style={{position: 'absolute', left: x - 40, width: bw + 80, top: base - bh - (big ? 84 : 64), textAlign: 'center', fontFamily: SANS, fontWeight: 800, fontSize: big ? 72 : 52, color: i ? ACCENT : '#FFF', opacity: t, fontVariantNumeric: 'tabular-nums'}}>
              {Math.round(v * Math.min(1, t * 1.2))}%
            </div>
            <div style={{position: 'absolute', left: x - 50, width: bw + 100, top: base + 12, textAlign: 'center', fontFamily: SANS, fontSize: 26, color: DIM}}>{RESULTS.pair[i]}</div>
          </React.Fragment>
        );
      })}
    </>
  );
};

const Results: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const c = cues('results');
  const R = RESULTS;
  const weeks = 7;
  const swap = draw(frame, c[5] - 14, 20);
  const speed = frame >= c[5] - 4;
  const tag = pop(frame, speed ? c[5] - 4 : c[1] - 6, fps, 10);
  const timeOut = draw(frame, c[1] - 14, 10);
  const shrink = draw(frame, c[3] + 20, 40);
  const backlogW = 700;
  return (
    <AbsoluteFill>
      <Say lines={R.lines} at={c} size={58} />
      <div style={{position: 'absolute', left: 0, right: 0, top: 0, bottom: 0, opacity: 1 - timeOut}}>
        <svg width={1920} height={1080} style={{position: 'absolute'}}>
          <line x1={560} y1={600} x2={1360} y2={600} stroke="rgba(255,255,255,0.2)" strokeWidth={4} />
          <line x1={560} y1={600} x2={560 + 800 * draw(frame, c[0] + 20, c[1] - c[0] - 40)} y2={600} stroke={ACCENT} strokeWidth={6} />
        </svg>
        {Array.from({length: weeks}).map((_, i) => {
          const at = c[0] + 20 + ((c[1] - c[0] - 40) * i) / (weeks - 1);
          const s = pop(frame, at, fps, 9);
          return <div key={i} style={{position: 'absolute', left: 560 + (800 * i) / (weeks - 1) - 24, top: 576, width: 48, height: 48, borderRadius: 24, border: `4px solid ${ACCENT}`, background: frame >= at ? ACCENT : BG, transform: `scale(${frame >= at ? 0.8 + 0.2 * s : 0.8})`}} />;
        })}
        {[0, 1].map((i) => (
          <div key={i} style={{position: 'absolute', left: (i ? 1360 : 560) - 100, width: 200, top: 650, textAlign: 'center', fontFamily: SANS, fontWeight: 700, fontSize: 32, color: SOFT}}>{R.weeks[i]}</div>
        ))}
      </div>
      {frame >= c[1] - 6 && (
        <div style={{position: 'absolute', left: 960, top: 262, transform: `translate(-50%, -50%) scale(${tag})`, fontFamily: SANS, fontWeight: 800, fontSize: 26, letterSpacing: '0.1em', textTransform: 'uppercase', color: BG, background: ACCENT, borderRadius: 999, padding: '5px 24px'}}>
          {TEXT.results.sections[speed ? 1 : 0]}
        </div>
      )}
      <div style={{position: 'absolute', inset: 0, opacity: 1 - swap, transform: `translateX(${-swap * 300}px)`}}>
        <Panel x={120} y={300} w={820} h={360} at={c[1] - 4} title={R.coverage.title}>
          <LineChart at={c[1]} w={820} h={360} />
        </Panel>
        <Panel x={980} y={300} w={820} h={360} at={c[2] - 4} title={R.playbook.title}>
          <Pair from={R.playbook.from} to={R.playbook.to} at={c[2]} w={820} h={360} />
        </Panel>
        <Panel x={120} y={684} w={820} h={226} at={c[3] - 4} title={R.backlog.title}>
          <div style={{position: 'absolute', left: 28, top: 90, width: backlogW, height: 56, borderRadius: 12, border: '2px dashed rgba(255,255,255,0.2)'}} />
          <div style={{position: 'absolute', left: 28, top: 90, width: backlogW * (1 - (1 - R.backlog.to / R.backlog.from) * shrink), height: 56, borderRadius: 12, background: `rgba(255,255,255,${0.25 + 0.2 * shrink})`, border: `2px solid ${shrink >= 1 ? ACCENT : 'transparent'}`}} />
          <div style={{position: 'absolute', left: 28 + backlogW * (1 - (1 - R.backlog.to / R.backlog.from) * shrink) + 16, top: 92, fontFamily: SANS, fontWeight: 800, fontSize: 44, color: '#FFF', fontVariantNumeric: 'tabular-nums'}}>
            {Math.round(R.backlog.from + (R.backlog.to - R.backlog.from) * shrink)}
          </div>
          {shrink >= 1 && <Tag text={R.backlog.note} x={560} y={190} at={c[3] + 62} solid size={30} />}
        </Panel>
        <Panel x={980} y={684} w={820} h={226} at={c[4] - 4} title="">
          <div style={{position: 'absolute', left: 28, top: 26, fontFamily: SANS, fontWeight: 800, fontSize: 96, color: ACCENT, fontVariantNumeric: 'tabular-nums'}}>{Math.round(R.found.to * draw(frame, c[4], 30))}%</div>
          <div style={{position: 'absolute', left: 270, top: 44, right: 24, fontFamily: SANS, fontWeight: 700, fontSize: 32, color: '#FFF', lineHeight: 1.2}}>{R.found.label}</div>
          <div style={{position: 'absolute', left: 28, top: 150, display: 'flex', alignItems: 'center', gap: 22, opacity: draw(frame, c[4] + 90, 12)}}>
            <Dots lit={R.found.mini[0]} total={R.found.mini[1]} size={22} at={c[4] + 96} />
            <div style={{fontFamily: SANS, fontSize: 28, color: SOFT}}>{R.found.note}</div>
          </div>
        </Panel>
      </div>
      {frame >= c[5] - 14 && (
        <div style={{position: 'absolute', inset: 0, opacity: swap, transform: `translateX(${(1 - swap) * 300}px)`}}>
          {R.speed.map((m, i) => (
            <Panel key={i} x={i ? 1000 : 160} y={310} w={760} h={600} at={c[5] + (i ? 100 : 30)} title="">
              <div style={{position: 'absolute', left: 30, right: 30, top: 24, textAlign: 'center', fontFamily: SANS, fontWeight: 700, fontSize: 34, color: '#FFF', lineHeight: 1.2}}>{m.title}</div>
              <Pair from={m.from} to={m.to} at={c[5] + (i ? 100 : 30)} w={760} h={600} big />
            </Panel>
          ))}
        </div>
      )}
      <div style={{position: 'absolute', left: 360, right: 360, bottom: 40, textAlign: 'center', fontFamily: SANS, fontSize: 28, fontWeight: 500, color: '#FFF', background: 'rgba(8,10,14,0.72)', border: '1px solid rgba(110,231,183,0.35)', borderRadius: 16, padding: '10px 28px', opacity: draw(frame, c[1], 14)}}>
        {R.caveat.map((line) => (
          <div key={line}>{line}</div>
        ))}
      </div>
    </AbsoluteFill>
  );
};

const End: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const c = cues('end');
  const T = TEXT.end;
  const len = bars(SCENES.end[1] - SCENES.end[0]);
  const hub = {x: 960, y: 630};
  const icons: IconName[] = ['book', 'layers', 'shield'];
  const gather = draw(frame, c[1] + 4, 24);
  const folder = pop(frame, c[1] + 14, fps, 9);
  const clear = draw(frame, c[2] - 8, 10);
  const logo = pop(frame, c[2] + 4, fps, 13);
  const fadeOut = interpolate(frame, [len - 24, len], [1, 0], clamp);
  const hubGrow = draw(frame, c[0], c[1] - c[0]);
  return (
    <AbsoluteFill style={{opacity: fadeOut}}>
      <Say lines={T.lines} at={c} size={c.length && frame >= c[2] ? 110 : 62} />
      <div style={{position: 'absolute', inset: 0, opacity: 1 - clear}}>
        {[0, 1, 2].map((r) => {
          const u = ((frame - c[0] + r * 20) % 60) / 60;
          return frame > c[0] && gather < 1 ? <div key={r} style={{position: 'absolute', left: hub.x - 100, top: hub.y - 100, width: 200, height: 200, borderRadius: 100, border: `2px solid ${ACCENT}`, opacity: (1 - u) * 0.6, transform: `scale(${1 + u * (1.4 + hubGrow)})`}} /> : null;
        })}
        <div style={{position: 'absolute', left: hub.x - 90, top: hub.y - 90, opacity: 1 - gather, transform: `scale(${(0.8 + 0.4 * hubGrow) * pop(frame, c[0], fps)})`}}>
          <Icon name="logo" size={180} progress={draw(frame, c[0], 30)} width={4} />
        </div>
        {icons.map((ic, i) => {
          const a = (frame / 50) + (i * 2 * Math.PI) / 3;
          const r = (1 - gather) * (300 + 40 * hubGrow);
          const x = hub.x + Math.cos(a) * r;
          const y = hub.y + Math.sin(a) * r * 0.55;
          return (
            <div key={i} style={{opacity: 1 - gather}}>
              <Glyph name={ic} x={x} y={y} size={120} at={c[0] + 10 + i * 10} ring={ACCENT} label={gather < 0.2 ? T.parts[i] : undefined} labelColor="#FFF" />
            </div>
          );
        })}
        {frame >= c[1] + 14 && (
          <div style={{position: 'absolute', left: hub.x - 130, top: hub.y - 130, width: 260, height: 260, transform: `scale(${folder})`, display: 'flex', flexDirection: 'column', alignItems: 'center'}}>
            <Icon name="folder" size={260} progress={1} />
            <div style={{fontFamily: SANS, fontWeight: 800, fontSize: 44, color: '#FFF', marginTop: 4}}>{T.yours}</div>
          </div>
        )}
      </div>
      {frame >= c[2] && (
        <div style={{position: 'absolute', left: 0, right: 0, top: 330, display: 'flex', flexDirection: 'column', alignItems: 'center', opacity: Math.min(1, logo * 2), transform: `translateY(${(1 - logo) * 40}px)`}}>
          <div style={{transform: `scale(${1 + 0.05 * pulse(frame)})`}}>
            <Icon name="logo" size={150} progress={draw(frame, c[2], 30)} width={4} />
          </div>
          <div style={{fontFamily: SANS, fontWeight: 800, fontSize: 168, letterSpacing: '-0.045em', color: '#FFF', marginTop: 6}}>
            {TEXT.name}
            <span style={{color: ACCENT}}>.</span>
          </div>
          <div style={{fontFamily: SANS, fontSize: 48, color: SOFT}}>{TEXT.tagline}</div>
          <div style={{fontFamily: SANS, fontSize: 36, color: DIM, marginTop: 40}}>{TEXT.endLine}</div>
        </div>
      )}
    </AbsoluteFill>
  );
};

const PARTS: [Scene, React.FC][] = [
  ['problem', Problem],
  ['turn', Turn],
  ['map', MapScene],
  ['join', Join],
  ['steer', Steer],
  ['memory', Memory],
  ['compounds', Compounds],
  ['history', History],
  ['results', Results],
  ['end', End],
];

const SPEECH: [number, number][] = PARTS.flatMap(([key]) => cues(key).map((at, i) => [bars(SCENES[key][0]) + at, bars(SCENES[key][0]) + at + Math.ceil(VOICE[key][i] * FPS)] as [number, number]));

const MUSIC_UP = 0.45;
const MUSIC_UNDER_VOICE = 0.16;
// Longer than half the breath between two lines, so the music stays down between them instead of pumping.
const DUCK_HOLD = 12;
const DUCK_RAMP = 18;

function musicVolume(f: number) {
  const gap = SPEECH.reduce((m, [a, b]) => Math.min(m, f < a ? a - f : f > b ? f - b : 0), Infinity);
  return MUSIC_UNDER_VOICE + (MUSIC_UP - MUSIC_UNDER_VOICE) * Math.min(1, Math.max(0, gap - DUCK_HOLD) / DUCK_RAMP);
}

export const Intro: React.FC = () => (
  <AbsoluteFill style={{background: BG}}>
    <Background />
    {PARTS.map(([key, Part]) => {
      const [a, b] = SCENES[key];
      return (
        <Sequence key={key} from={bars(a)} durationInFrames={bars(b - a)}>
          <Fade len={bars(b - a)}>
            <Part />
          </Fade>
        </Sequence>
      );
    })}
    {PARTS.slice(1).map(([key]) => (
      <Sequence key={key} from={bars(SCENES[key][0]) - 6} durationInFrames={14}>
        <Wipe />
      </Sequence>
    ))}
    <Html5Audio src={staticFile('music.wav')} volume={musicVolume} />
    {PARTS.flatMap(([key]) =>
      cues(key).map((at, i) => (
        <Sequence key={`${key}-${i}`} from={bars(SCENES[key][0]) + at} durationInFrames={Math.ceil(VOICE[key][i] * FPS) + 15} layout="none">
          <Html5Audio src={staticFile(`voice/${key}-${i}.mp3`)} />
        </Sequence>
      )),
    )}
  </AbsoluteFill>
);
