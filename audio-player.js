export function createOfflinePlayer(clips, { AudioClass = globalThis.Audio, onFailure = () => {}, onState = () => {}, onEnded = () => {} } = {}) {
  // Reuse one audio element so a tap can unlock subsequent card playback on phones.
  let audio, sequence=0;
  function stop() { sequence++; if(audio)audio.pause(); onState('idle'); }
  function play(text) {
    stop();const id=sequence,url=clips[text];
    if(!url){onState('error');onFailure('语音尚未准备好，请重新启动程序补齐音频。');return;}
    audio ||= new AudioClass();audio.src=url;audio.currentTime=0;
    audio.onended=()=>{if(id===sequence){onState('idle');onEnded(text);}};
    audio.onerror=()=>{if(id===sequence){onState('error');onFailure('音频播放失败，请检查设备声音。');}};
    onState('loading');
    audio.play().then(()=>{if(id===sequence)onState('playing');}).catch(error=>{
      if(id!==sequence)return;
      onState(error.name==='NotAllowedError'?'blocked':'error');
      // A blocked autoplay becomes a visible speaker button, rather than a text-only instruction.
      if(error.name!=='NotAllowedError')onFailure('音频播放失败，请稍后再试。');
    });
  }
  return {play,stop};
}
