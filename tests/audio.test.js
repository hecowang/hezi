import test from 'node:test';
import assert from 'node:assert/strict';
import {speechCatalog,quizText,lessonText,wordText,feedbackText,guideText} from '../speech-text.js';
import {words} from '../course.js';
import {createOfflinePlayer} from '../audio-player.js';
test('所有课程和提示的播放文本都在生成目录中',()=>{const texts=new Set(speechCatalog());assert.equal(texts.size,501);assert.ok(texts.has(guideText));for(const w of words)for(const text of [quizText(w),lessonText(w),wordText(w),feedbackText(w[0],true),feedbackText(w[0],false)])assert.ok(texts.has(text))});
test('新播放停止旧音频，不调用云接口；缺失文件提示',async()=>{const instances=[],failures=[];class FakeAudio{constructor(url){this.url=url;instances.push(this)}pause(){this.stopped=true}play(){return Promise.resolve()}}const player=createOfflinePlayer({'米':'audio/1.mp3','水':'audio/2.mp3'},{AudioClass:FakeAudio,onFailure:m=>failures.push(m)});player.play('米');player.play('水');assert.ok(instances[0].stopped);assert.equal(instances[1].url,'audio/2.mp3');player.play('不存在');assert.ok(instances[1].stopped);assert.equal(failures.length,1)});
