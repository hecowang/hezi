import { words } from './course.js';
export const guideText = '欢迎来到禾字。点开始学字，看大字，听一听，再试着认一认。每天一点点，学得慢也没关系。';
export const lessonText = w => `${w[0]}。${w[2]}。${w[3]}`;
export const wordText = w => `${w[0]}，${w[2]}`;
export const quizText = w => `请找出${w[0]}。${w[2]}的${w[0]}`;
export const feedbackText = (char, correct) => correct ? `认对了！这个字就是「${char}」。` : `没关系，这个字是「${char}」。再听一遍。`;
export const speechCatalog = () => [...new Set([guideText, ...words.flatMap(w => [lessonText(w), wordText(w), quizText(w), feedbackText(w[0], true), feedbackText(w[0], false)])])];
