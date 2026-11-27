import {Composition} from 'remotion';
import {INTRO_FRAMES, Intro} from './Intro';
import {FPS} from './intro-data';

export const Root = () => <Composition id="TrampoIntro" component={Intro} durationInFrames={INTRO_FRAMES} fps={FPS} width={1920} height={1080} />;
