import test from 'node:test';import assert from 'node:assert/strict';
import {emptyState,learnedCount} from '../course.js';
import {restoredIndex,rememberPosition,markHeard} from '../feed-state.js';
test('新用户从第一个字开始，旧用户保留位置，非法位置被限制',()=>{assert.equal(restoredIndex(emptyState(),100),0);assert.equal(restoredIndex({lastWordIndex:8},100),8);assert.equal(restoredIndex({lastWordIndex:200},100),99);assert.equal(restoredIndex({lastWordIndex:-1},100),0);assert.equal(restoredIndex({lastWordIndex:'8'},100),0)});
test('浏览和听完都不冒充练习掌握，听完不重复计数',()=>{const state=emptyState();rememberPosition(state,5);assert.equal(learnedCount(state),0);markHeard(state,'米','2026-10-10');markHeard(state,'米','2026-10-10');assert.equal(state.heard.length,1);assert.equal(state.days.length,1);assert.equal(learnedCount(state),0)});
