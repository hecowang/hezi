export function restoredIndex(state, total) {
  return Number.isInteger(state.lastWordIndex) ? Math.max(0, Math.min(total-1, state.lastWordIndex)) : 0;
}
export function rememberPosition(state, index) { state.lastWordIndex=index; return state; }
export function markHeard(state, char, day) {
  state.heard=Array.isArray(state.heard)?state.heard:[];
  if(!state.heard.includes(char))state.heard.push(char);
  if(!state.days.includes(day))state.days.push(day);
  return state;
}
