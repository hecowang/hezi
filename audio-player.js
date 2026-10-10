export function createOfflinePlayer(clips, { AudioClass = globalThis.Audio, onFailure = () => {} } = {}) {
  let current, sequence = 0;
  function stop() { sequence++; if(current) { current.pause(); current=null; } }
  function play(text) {
    stop();
    const url=clips[text];
    if(!url) { onFailure('语音尚未准备好，请重新启动程序补齐音频。'); return; }
    const id=sequence;
    current=new AudioClass(url);
    current.onerror=()=>{ if(id===sequence)onFailure('音频播放失败，请检查设备声音或重新启动程序。'); };
    current.play().catch(error=>{ if(id===sequence)onFailure(error.name==='NotAllowedError'?'请点“听一听”或“听题目”播放声音。':'音频播放失败，请稍后再试。'); });
  }
  return { play, stop };
}
