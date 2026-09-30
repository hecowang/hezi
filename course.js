export const lessons = [
 {title:'一日三餐',scene:'厨房里，都是熟悉的字',icon:'🍚',words:[['米','mǐ','大米','一碗米饭，吃得香。','🍚'],['水','shuǐ','喝水','口渴了，喝一杯水。','💧'],['菜','cài','买菜','去菜市场，买点新鲜菜。','🥬']]},
 {title:'出门走走',scene:'认得路，出门更从容',icon:'🚌',words:[['车','chē','公交车','坐公交车去赶集。','🚌'],['门','mén','大门','出门记得关好门。','🚪'],['人','rén','家人','一家人，坐在一起。','👨‍👩‍👧']]},
 {title:'看看指示牌',scene:'生活中的小提醒',icon:'🪧',words:[['出','chū','出口','出口在这边。','↗️'],['入','rù','入口','从入口走进去。','🚶'],['停','tíng','停车','这里可以停车。','🅿️']]},
 {title:'家乡的日子',scene:'从熟悉的田野开始',icon:'🌾',words:[['田','tián','田地','田里的庄稼长高了。','🌾'],['山','shān','山坡','远处有一座山。','⛰️'],['日','rì','日出','太阳出来了，新的一天。','🌅']]}
];
export const words = lessons.flatMap(l=>l.words);
export const dayKey = (date = new Date()) => new Intl.DateTimeFormat('sv-SE',{timeZone:'Asia/Shanghai'}).format(date);
export const emptyState = () => ({version:1,records:{},days:[],pledge:false,refunded:false});
export function recordAnswer(state,char,correct,now=Date.now()) {
 const old=state.records[char] || {streak:0,attempts:0};
 const streak=correct?old.streak+1:0;
 state.records[char]={streak,attempts:old.attempts+1,due:now+(correct?[1,3,7,14][Math.min(streak-1,3)]:0)*86400000};
 return state;
}
export const learnedCount = s => Object.values(s.records).filter(r=>r.streak>0).length;
export const dueWords = (s,now=Date.now()) => words.filter(w=>s.records[w[0]]?.due<=now);
export const refundEligible = s => words.every(w=>s.records[w[0]]?.streak>=2);
