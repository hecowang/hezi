import { words, characterMetadata } from './course.js';
export const guideText = '欢迎来到禾字。点一下大喇叭，听这个字。手指往上滑，看下一个字；往下滑，再看前一个字。也可以点下面的箭头。慢慢看，慢慢听，不着急。';
export const lessonText = w => w[2] ? `${w[0]}。${w[2]}。${w[3]}` : `${w[0]}。`;
export const wordText = w => w[2] ? `${w[0]}，${w[2]}` : `${w[0]}。`;
export const quizText = w => w[2] ? `请找出${w[0]}。${w[2]}的${w[0]}` : `请找出${w[0]}。`;
export const feedbackText = (char, correct) => correct ? `认对了！这个字就是「${char}」。` : `没关系，这个字是「${char}」。再听一遍。`;
export function speechJobs() {
  const jobs = new Map([[guideText,{text:guideText}]]);
  for(const w of words) {
    const meta=characterMetadata[w[0]];
    const pronunciations=meta.core ? undefined : [`${w[0]}/(${meta.phonetic})`];
    for(const text of [lessonText(w),wordText(w),quizText(w),feedbackText(w[0],true),feedbackText(w[0],false)])
      jobs.set(text,pronunciations ? {text,pronunciations} : {text});
  }
  return [...jobs.values()];
}
export const speechCatalog = () => speechJobs().map(job=>job.text);
