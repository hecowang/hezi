import { words } from './course.js';
export const guideText = '欢迎来到禾字。点一下大喇叭，听这个字。手指往上滑，看下一个字；往下滑，再看前一个字。也可以点下面的箭头。慢慢看，慢慢听，不着急。';
export const lessonText = w => `${w[0]}。${w[2]}。${w[3]}`;
export const wordText = w => `${w[0]}，${w[2]}`;
export const quizText = w => `请找出${w[0]}。${w[2]}的${w[0]}`;
export const feedbackText = (char, correct) => correct ? `认对了！这个字就是「${char}」。` : `没关系，这个字是「${char}」。再听一遍。`;
export const speechCatalog = () => [...new Set([guideText, ...words.flatMap(w => [lessonText(w), wordText(w), quizText(w), feedbackText(w[0], true), feedbackText(w[0], false)])])];
