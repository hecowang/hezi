import test from 'node:test';import assert from 'node:assert/strict';import {emptyState,recordAnswer,dueWords,refundEligible,dayKey,words} from '../course.js';
test('正确回答隔日复习，错题立即回到复习队列',()=>{const s=emptyState();recordAnswer(s,'米',true,1000);assert.equal(dueWords(s,1000).length,0);assert.equal(dueWords(s,1000+86400000)[0][0],'米');recordAnswer(s,'米',false,2000);assert.equal(s.records.米.streak,0);assert.equal(dueWords(s,2000).length,1)});
test('返还需每个字两次答对，不能仅靠点击完成',()=>{const s=emptyState();for(const w of words)recordAnswer(s,w[0],true);assert.equal(refundEligible(s),false);for(const w of words)recordAnswer(s,w[0],true);assert.equal(refundEligible(s),true);recordAnswer(s,'米',false);assert.equal(refundEligible(s),false)});
test('学习日期使用中国时区',()=>assert.equal(dayKey(new Date('2026-09-30T17:00:00Z')),'2026-10-01'));

test('100个不重复生活字，每字含拼音、词语、例句和图标',()=>{assert.equal(words.length,100);assert.equal(new Set(words.map(w=>w[0])).size,100);for(const w of words){assert.equal(w.length,5);assert.equal([...w[0]].length,1);assert.ok(w.every(Boolean));assert.ok(w[2].includes(w[0]));assert.ok(w[3].includes(w[0]))}});
