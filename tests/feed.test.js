import test from 'node:test';import assert from 'node:assert/strict';
import {emptyState,learnedCount} from '../course.js';
import {restoredIndex,rememberPosition,markHeard,visibleWindow} from '../feed-state.js';
test('新用户从第一个字开始，旧用户保留位置，非法位置被限制',()=>{assert.equal(restoredIndex(emptyState(),100),0);assert.equal(restoredIndex({lastWordIndex:8},100),8);assert.equal(restoredIndex({lastWordIndex:200},100),99);assert.equal(restoredIndex({lastWordIndex:-1},100),0);assert.equal(restoredIndex({lastWordIndex:'8'},100),0)});
test('浏览和听完都不冒充练习掌握，听完不重复计数',()=>{const state=emptyState();rememberPosition(state,5);assert.equal(learnedCount(state),0);markHeard(state,'米','2026-10-10');markHeard(state,'米','2026-10-10');assert.equal(state.heard.length,1);assert.equal(state.days.length,1);assert.equal(learnedCount(state),0)});

test('3500字始终只挂载至多5张附近卡片，首尾可访问',()=>{for(const index of [0,1,100,1749,3498,3499]){const range=visibleWindow(index,3500);assert.ok(range.start<=index&&index<range.end);assert.ok(range.end-range.start<=5);assert.ok(range.start>=0&&range.end<=3500)}assert.equal(visibleWindow(0,3500).start,0);assert.equal(visibleWindow(3499,3500).end,3500)});
