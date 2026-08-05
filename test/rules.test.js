/* Pull the real game-logic functions out of index.html and exercise them
   against the rules the user specified. No mocking of the logic itself —
   the actual source text is evaluated. */
const fs = require('fs');
const HTML = fs.readFileSync(process.argv[2], 'utf8');
// the page has several inline <script> blocks (Firebase config, then the app) —
// the game logic is the largest one
const SRC = [...HTML.matchAll(/<script(?![^>]*src)[^>]*>([\s\S]*?)<\/script>/g)]
  .map(m => m[1])
  .sort((a, b) => b.length - a.length)[0];

function grab(startRe, endMarker) {
  const i = SRC.search(startRe);
  if (i < 0) throw new Error('not found: ' + startRe);
  const j = SRC.indexOf(endMarker, i);
  return SRC.slice(i, j + endMarker.length);
}

const pieces = [
  grab(/const ROUTE = \[/, '\n];'),
  grab(/const QUESTIONS = \[/, '\n];'),
  grab(/const TURBO_MIN_LEG/, 'isTurbulenceLeg(legIndex){ return TURBULENCE_LEGS.includes(legIndex); }'),
  grab(/function adminRevealAnswer\(\)\{/, '\n}'),
  grab(/function adminTogglePowerQuestion\(\)\{/, '\n}'),
  grab(/function isTurboEligibleNow\(\)\{/, '\n}'),
  grab(/function me_turbulenceActive\(\)/, 'isTurbulenceLeg(state.currentQ); }'),
].join('\n');

let state, myPlayerId, toasts;
const sandbox = { saveState(){}, toast(m){ toasts.push(m); },
                  confirm(){ return true; }, prompt(){ return 'RESET'; } };
const load = new Function('sandbox', `
  const {saveState, toast, confirm, prompt} = sandbox;
  let state, myPlayerId;
  ${pieces}
  return {
    setState:(s,me)=>{ state=s; myPlayerId=me; },
    getState:()=>state,
    adminRevealAnswer, adminTogglePowerQuestion, isTurboEligibleNow,
    pickQuestionIndex, isTurbulenceLeg, ROUTE, QUESTIONS, TURBO_MIN_LEG, TURBULENCE_LEGS,
  };
`)(sandbox);

const G = load;
const FINISH = G.ROUTE.length - 1;

function mkState(over = {}) {
  return Object.assign({
    gameState: 'locked', currentQ: 0, currentQuestionIndex: 0,
    questionIndexByLeg: {}, powerQuestionActive: false, powerQuestionUsed: false,
    questionOpenedAt: 0, revealedLegs: {}, undoSnapshot: null, paused: false,
    players: {}, winnerId: null, milestones: {HAN:null,SPC:null,SGN:null}, awardShown: false,
  }, over);
}
function mkPlayer(id, over = {}) {
  return Object.assign({ id, name:id, avatar:'😎', position:0, correctCount:0,
                         answers:{}, totalAnswerTime:0, turboUsed:false }, over);
}
const CORRECT = () => G.QUESTIONS[0].correct;
const WRONG   = () => (G.QUESTIONS[0].correct + 1) % 4;

let pass = 0, fail = 0;
function check(name, actual, expected) {
  const ok = JSON.stringify(actual) === JSON.stringify(expected);
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}` + (ok ? '' : `\n        expected ${JSON.stringify(expected)}, got ${JSON.stringify(actual)}`));
  ok ? pass++ : fail++;
}

/* ---------- 1. question pools per leg ---------- */
const pools = { '0-3': new Set(), '4-7': new Set(), '8+': new Set() };
for (let t = 0; t < 3000; t++) {
  pools['0-3'].add(G.pickQuestionIndex(t % 4, false));
  pools['4-7'].add(G.pickQuestionIndex(4 + (t % 4), false));
  pools['8+'].add(G.pickQuestionIndex(8 + (t % 4), false));
}
const range = s => [Math.min(...s), Math.max(...s)];
check('legs 1-4 draw from Q1-10',   range(pools['0-3']), [0, 9]);
check('legs 5-8 draw from Q11-20',  range(pools['4-7']), [10, 19]);
check('legs 9-12 draw from Q21-30', range(pools['8+']),  [20, 29]);
const powerPool = new Set();
for (let t = 0; t < 2000; t++) powerPool.add(G.pickQuestionIndex(0, true));
check('Power Question forces Q21-30 even on leg 1', range(powerPool), [20, 29]);
check('question bank size', G.QUESTIONS.length, 30);
check('turbulence on legs 6 and 10 (0-based 5,9)', G.TURBULENCE_LEGS, [5, 9]);
check('Turbo unlock node is MUC', G.ROUTE[G.TURBO_MIN_LEG].code, 'MUC');

/* ---------- 2. normal leg ---------- */
function runLeg(over, players) {
  const s = mkState(over);
  players.forEach(p => { s.players[p.id] = p; });
  G.setState(s, null);
  toasts = [];
  G.adminRevealAnswer();
  return s;
}
let s = runLeg({ currentQ: 0 }, [
  mkPlayer('right', { answers: { 0: { choice: CORRECT(), submitted: true, timeTaken: 5000 } } }),
  mkPlayer('wrong', { answers: { 0: { choice: WRONG(),   submitted: true, timeTaken: 5000 } } }),
  mkPlayer('silent'),
]);
check('normal: correct advances 1', s.players.right.position, 1);
check('normal: wrong holds',        s.players.wrong.position, 0);
check('normal: no answer holds',    s.players.silent.position, 0);

/* ---------- 3. Turbo Boost ---------- */
s = runLeg({ currentQ: 6 }, [
  mkPlayer('boostWin',  { position: 5, answers: { 6: { choice: CORRECT(), submitted: true, turbo: true, timeTaken: 3000 } } }),
  mkPlayer('boostLose', { position: 5, answers: { 6: { choice: WRONG(),   submitted: true, turbo: true, timeTaken: 3000 } } }),
  mkPlayer('armedNoSubmit', { position: 5, answers: { 6: { choice: CORRECT(), submitted: false, turbo: true } } }),
]);
check('turbo correct -> +2', s.players.boostWin.position, 7);
check('turbo wrong   -> -1', s.players.boostLose.position, 4);
check('turbo armed but never submitted -> no penalty', s.players.armedNoSubmit.position, 5);

/* Turbo eligibility is per player position */
G.setState(mkState({ currentQ: 9 }), 'behind');
G.getState().players.behind = mkPlayer('behind', { position: 2 });
check('turbo locked while player is behind MUC (even on leg 10)', G.isTurboEligibleNow(), false);
G.setState(mkState({ currentQ: 4 }), 'atMuc');
G.getState().players.atMuc = mkPlayer('atMuc', { position: 4 });
check('turbo unlocked once player reaches MUC', G.isTurboEligibleNow(), true);

/* ---------- 4. Power Question ---------- */
s = runLeg({ currentQ: 8, powerQuestionActive: true }, [
  mkPlayer('fast', { position: 5, answers: { 8: { choice: CORRECT(), submitted: true, timeTaken: 2000 } } }),
  mkPlayer('slow', { position: 5, answers: { 8: { choice: CORRECT(), submitted: true, timeTaken: 9000 } } }),
  mkPlayer('miss', { position: 5, answers: { 8: { choice: WRONG(),   submitted: true, timeTaken: 1000 } } }),
]);
check('power: fastest correct -> +2', s.players.fast.position, 7);
check('power: other correct   -> +1', s.players.slow.position, 6);
check('power: wrong holds (no penalty)', s.players.miss.position, 5);

/* ---------- 5. Turbulence ---------- */
s = runLeg({ currentQ: 5 }, [
  mkPlayer('tRight',  { position: 5, answers: { 5: { choice: CORRECT(), submitted: true, timeTaken: 1000 } } }),
  mkPlayer('tWrong',  { position: 5, answers: { 5: { choice: WRONG(),   submitted: true, timeTaken: 1000 } } }),
  mkPlayer('tSilent', { position: 5 }),
  mkPlayer('tFloor',  { position: 0, answers: { 5: { choice: WRONG(),   submitted: true, timeTaken: 1000 } } }),
]);
check('turbulence: correct holds',        s.players.tRight.position, 5);
check('turbulence: wrong -1',             s.players.tWrong.position, 4);
check('turbulence: no answer also -1',    s.players.tSilent.position, 4);
check('turbulence: cannot go below START', s.players.tFloor.position, 0);

/* Turbulence must override Power Question */
s = runLeg({ currentQ: 5, powerQuestionActive: true }, [
  mkPlayer('pt', { position: 5, answers: { 5: { choice: CORRECT(), submitted: true, timeTaken: 1000 } } }),
]);
check('turbulence overrides an armed Power Question', s.players.pt.position, 5);

/* Arming Power on a turbulence leg is refused */
G.setState(mkState({ currentQ: 5, gameState: 'lobby' }), null);
toasts = [];
G.adminTogglePowerQuestion();
check('cannot arm Power Question on a turbulence leg', G.getState().powerQuestionActive, false);

/* ---------- 6. idempotency ---------- */
s = mkState({ currentQ: 0 });
s.players.p = mkPlayer('p', { answers: { 0: { choice: CORRECT(), submitted: true, timeTaken: 1000 } } });
G.setState(s, null); toasts = [];
G.adminRevealAnswer();
const afterFirst = s.players.p.position;
s.gameState = 'question';           // admin re-opens the same leg
G.adminRevealAnswer();
check('reveal twice does not double-move', s.players.p.position, afterFirst);
check('correctCount not double-counted', s.players.p.correctCount, 1);

/* ---------- 7. winner tie-break ---------- */
s = runLeg({ currentQ: 11 }, [
  mkPlayer('slowFinisher', { position: FINISH - 1, correctCount: 9, totalAnswerTime: 90000,
                             answers: { 11: { choice: CORRECT(), submitted: true, timeTaken: 9000 } } }),
  mkPlayer('fastFinisher', { position: FINISH - 1, correctCount: 9, totalAnswerTime: 30000,
                             answers: { 11: { choice: CORRECT(), submitted: true, timeTaken: 1000 } } }),
]);
check('both reached FINISH', [s.players.slowFinisher.position, s.players.fastFinisher.position], [FINISH, FINISH]);
check('winner is the faster of the tied finishers', s.winnerId, 'fastFinisher');

/* ---------- 8. undo snapshot captured ---------- */
check('undo snapshot recorded for the revealed leg', s.undoSnapshot && s.undoSnapshot.leg, 11);

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
