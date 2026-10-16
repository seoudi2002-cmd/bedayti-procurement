(()=>{
"use strict";
const TZ="Africa/Cairo";
const NAMES=[["الرزّاق","يسوق الرزق لكل خلقه، ويقدّره بحكمته"],["الوهّاب","كثير العطاء بلا سبب ولا مقابل"],["الفتّاح","يفتح أبواب الخير المغلقة"],["الغنيّ","المستغني عن كل ما سواه"],["المُغني","يُغني من يشاء من عباده"],["الباسط","يبسط الرزق ويوسّعه"],["الكريم","كثير الخير دائم العطاء"],["الحفيظ","يحفظ ما استُودع عنده"],["الوكيل","من توكّل عليه كفاه"],["المُقيت","خالق الأقوات ومقدّرها"],["الحسيب","الكافي، والمحاسب على كل شيء"],["الشكور","يضاعف الجزاء على القليل"],["اللطيف","يدبّر الأمور بخفاء ورفق"],["الواسع","وسع عطاؤه كل شيء"],["البَرّ","كثير الإحسان إلى عباده"],["الحكيم","يضع كل شيء في موضعه"],["المُهيمن","الرقيب القائم على كل شيء"],["القويّ","كامل القدرة لا يُعجزه شيء"],["المتين","شديد القوة لا يلحقه ضعف"],["العليم","أحاط علمه بكل شيء"],["الحليم","لا يعجّل بالعقوبة"],["الصمد","المقصود في الحوائج كلها"]];
const HADITH=[
 ["أحبُّ الأعمال إلى الله أدومُها وإن قلّ","متفق عليه","البخاري 6464 · مسلم 783"],
 ["ما نقصت صدقةٌ من مال","صحيح مسلم","2588"],
 ["ليس الغِنى عن كثرة العَرَض، ولكنّ الغِنى غِنى النفس","متفق عليه","البخاري 6446 · مسلم 1051"],
 ["لو أنكم كنتم توكّلون على الله حقَّ توكّله لرزقكم كما يرزق الطير، تغدو خِماصًا وتروح بِطانًا","سنن الترمذي","2344 · حسن صحيح"],
 ["ما أكل أحدٌ طعامًا قطّ خيرًا من أن يأكل من عمل يده","صحيح البخاري","2072"],
 ["اليدُ العليا خيرٌ من اليد السفلى","متفق عليه","البخاري 1427 · مسلم 1033"],
 ["المؤمن القويّ خيرٌ وأحبّ إلى الله من المؤمن الضعيف، وفي كلٍّ خير، احرص على ما ينفعك، واستعن بالله ولا تعجز","صحيح مسلم","2664"],
 ["اعقِلها وتوكّل","سنن الترمذي","2517 · حسن"],
 ["لا تزول قدما عبدٍ يوم القيامة حتى يُسأل عن عمره فيمَ أفناه، وعن علمه فيمَ فعل، وعن ماله من أين اكتسبه وفيمَ أنفقه، وعن جسمه فيمَ أبلاه","سنن الترمذي","2417 · حسن صحيح"],
 ["انظروا إلى من هو أسفل منكم، ولا تنظروا إلى من هو فوقكم، فهو أجدرُ ألّا تزدروا نعمة الله عليكم","صحيح مسلم","2963"],
 ["إنك أن تذر ورثتك أغنياء خيرٌ من أن تذرهم عالةً يتكفّفون الناس","متفق عليه","البخاري 1295 · مسلم 1628"],
 ["البيّعان بالخيار ما لم يتفرّقا، فإن صدقا وبيّنا بورك لهما في بيعهما، وإن كتما وكذبا مُحقت بركة بيعهما","متفق عليه","البخاري 2079 · مسلم 1532"],
 ["من أصبح منكم آمنًا في سِربه، معافًى في جسده، عنده قوتُ يومه، فكأنما حِيزت له الدنيا","سنن الترمذي","2346 · حسن"],
 ["نِعمَ المالُ الصالحُ للمرء الصالح","مسند أحمد","17763 · صحيح"],
 ["إن الله يحب إذا عمل أحدكم عملًا أن يُتقنه","المعجم الأوسط للطبراني","حسّنه الألباني"],
 ["إن هذا المال خَضِرةٌ حلوة، فمن أخذه بسخاوة نفسٍ بورك له فيه","متفق عليه","البخاري 1472 · مسلم 1035"],
 ["ما من يومٍ يُصبح العباد فيه إلا ملكان ينزلان، فيقول أحدهما: اللهم أعطِ منفقًا خلفًا، ويقول الآخر: اللهم أعطِ ممسكًا تلفًا","متفق عليه","البخاري 1442 · مسلم 1010"],
 ["من أحبّ أن يُبسط له في رزقه، ويُنسأ له في أثره، فليصل رحمه","متفق عليه","البخاري 5986 · مسلم 2557"],
 ["اللهم إني أعوذ بك من الهمّ والحزن، والعجز والكسل، والبخل والجبن، وضَلَع الدَّين، وغلبة الرجال","صحيح البخاري","6369"],
 ["اغتنم خمسًا قبل خمس: شبابك قبل هرمك، وصحتك قبل سقمك، وغناك قبل فقرك، وفراغك قبل شغلك، وحياتك قبل موتك","المستدرك للحاكم","7846 · صحيح"]
];
const NAMES99="الله الرحمن الرحيم الملك القدوس السلام المؤمن المهيمن العزيز الجبار المتكبر الخالق البارئ المصور الغفار القهار الوهاب الرزاق الفتاح العليم القابض الباسط الخافض الرافع المعز المذل السميع البصير الحكم العدل اللطيف الخبير الحليم العظيم الغفور الشكور العلي الكبير الحفيظ المقيت الحسيب الجليل الكريم الرقيب المجيب الواسع الحكيم الودود المجيد الباعث الشهيد الحق الوكيل القوي المتين الولي الحميد المحصي المبدئ المعيد المحيي المميت الحي القيوم الواجد الماجد الواحد الصمد القادر المقتدر المقدم المؤخر الأول الآخر الظاهر الباطن الوالي المتعالي البر التواب المنتقم العفو الرؤوف مالك_الملك ذو_الجلال_والإكرام المقسط الجامع الغني المغني المانع الضار النافع النور الهادي البديع الباقي الوارث الرشيد الصبور".split(" ").map(x=>x.replace(/_/g," "));
const MEAN99={"الله": "الإله المعبود الذي تألهه القلوب وتتجه إليه بالعبادة", "الرحمن": "ذو الرحمة الواسعة التي وسعت كل شيء", "الرحيم": "يوصل رحمته لعباده المؤمنين", "الملك": "صاحب الملك التام والتصرف المطلق في كل شيء", "القدوس": "المنزّه عن كل نقص وعيب", "السلام": "السالم من كل عيب، ومصدر السلامة لعباده", "المؤمن": "يؤمّن عباده من الخوف ويصدّق وعده", "المهيمن": "الرقيب القائم على كل شيء", "العزيز": "الغالب الذي لا يُغلب", "الجبار": "يجبر الكسر ويقهر كل شيء بعظمته", "المتكبر": "المتعالي عن صفات الخلق", "الخالق": "المبدع المقدّر لكل مخلوق", "البارئ": "الذي خلق الخلق بريئًا من التفاوت", "المصور": "الذي صوّر المخلوقات على صور مختلفة", "الغفار": "كثير المغفرة يستر الذنوب ويمحوها", "القهار": "الغالب لكل شيء بقدرته", "الوهاب": "كثير العطاء بلا سبب ولا مقابل", "الرزاق": "يسوق الرزق لكل خلقه، ويقدّره بحكمته", "الفتاح": "يفتح أبواب الخير المغلقة", "العليم": "أحاط علمه بكل شيء", "القابض": "يقبض الأرزاق والأرواح بحكمته", "الباسط": "يبسط الرزق ويوسّعه", "الخافض": "يخفض من يشاء بعدله", "الرافع": "يرفع من يشاء بفضله", "المعز": "يهب العزة لمن يشاء", "المذل": "يُذلّ من يشاء بعدله", "السميع": "يسمع كل صوت وإن خفي", "البصير": "يرى كل شيء وإن دقّ", "الحكم": "الفاصل بين خلقه بالحق", "العدل": "لا يظلم أحدًا ويضع كل شيء موضعه", "اللطيف": "يدبّر الأمور بخفاء ورفق", "الخبير": "العالم ببواطن الأمور وخفاياها", "الحليم": "لا يعجّل بالعقوبة", "العظيم": "ذو العظمة الكاملة في ذاته وصفاته", "الغفور": "كثير الغفران لعباده", "الشكور": "يضاعف الجزاء على القليل", "العلي": "المتعالي فوق خلقه بذاته وقدره", "الكبير": "ذو الكبرياء في كل شيء", "الحفيظ": "يحفظ ما استُودع عنده", "المقيت": "خالق الأقوات ومقدّرها", "الحسيب": "الكافي، والمحاسب على كل شيء", "الجليل": "ذو الجلال والعظمة", "الكريم": "كثير الخير دائم العطاء", "الرقيب": "الحافظ المطّلع على كل شيء", "المجيب": "يجيب دعاء من دعاه", "الواسع": "وسع عطاؤه كل شيء", "الحكيم": "يضع كل شيء في موضعه", "الودود": "يحب عباده الصالحين ويحبونه", "المجيد": "ذو المجد والعظمة والفضل", "الباعث": "يبعث الخلق يوم القيامة", "الشهيد": "المطّلع على كل شيء شاهد عليه", "الحق": "الثابت الوجود الذي لا شك فيه", "الوكيل": "من توكّل عليه كفاه", "القوي": "كامل القدرة لا يُعجزه شيء", "المتين": "شديد القوة لا يلحقه ضعف", "الولي": "الناصر المتولّي لأمور عباده المؤمنين", "الحميد": "المحمود في ذاته وأفعاله", "المحصي": "أحصى كل شيء عددًا", "المبدئ": "الذي بدأ الخلق من العدم", "المعيد": "يعيد الخلق بعد فنائهم", "المحيي": "يهب الحياة لمن يشاء", "المميت": "يقبض الأرواح بأجلها", "الحي": "كامل الحياة الذي لا يموت", "القيوم": "القائم بنفسه المقيم لغيره", "الواجد": "الذي لا يعوزه شيء ولا يفوته مطلوب", "الماجد": "عظيم المجد والإحسان", "الواحد": "المنفرد بذاته وصفاته وأفعاله", "الصمد": "المقصود في الحوائج كلها", "القادر": "له القدرة على كل شيء", "المقتدر": "بالغ القدرة التامة", "المقدم": "يقدّم من يشاء بحكمته", "المؤخر": "يؤخّر من يشاء بحكمته", "الأول": "الذي ليس قبله شيء", "الآخر": "الذي ليس بعده شيء", "الظاهر": "الذي ليس فوقه شيء", "الباطن": "الذي ليس دونه شيء", "الوالي": "المتصرف في خلقه المدبّر لأمورهم", "المتعالي": "المنزّه عن صفات النقص", "البر": "كثير الإحسان إلى عباده", "التواب": "يقبل توبة التائبين", "المنتقم": "ينتقم من المجرمين بعدله", "العفو": "يمحو الذنوب ويتجاوز عنها", "الرؤوف": "شديد الرحمة بعباده", "مالك الملك": "يتصرف في ملكه كيف يشاء", "ذو الجلال والإكرام": "صاحب العظمة والفضل والإحسان", "المقسط": "العادل في حكمه", "الجامع": "يجمع الخلق ليوم الحساب", "الغني": "المستغني عن كل ما سواه", "المغني": "يُغني من يشاء من عباده", "المانع": "يمنع ما يشاء بحكمته", "الضار": "يقدّر الضر لحكمة بالغة", "النافع": "يقدّر النفع لمن يشاء", "النور": "منوّر السماوات والأرض وهادي القلوب", "الهادي": "يهدي من يشاء إلى الحق", "البديع": "مبدع الخلق على غير مثال سابق", "الباقي": "الذي لا يفنى", "الوارث": "يبقى بعد فناء الخلق", "الرشيد": "يرشد الخلق ويدبّر بحكمة", "الصبور": "لا يعجّل بالعقوبة ويمهل"};
const nmKey=x=>String(x).replace(/[\u064B-\u0652\u0640]/g,'').replace(/[أإآ]/g,'ا').replace(/\s+/g,' ').trim();
const nmMean=n=>{const k=nmKey(n);const a=NAMES.find(x=>nmKey(x[0])===k);if(a)return a[1];const e=Object.entries(MEAN99).find(([q])=>nmKey(q)===k);return e?e[1]:"من أسماء الله الحسنى"};
const DUAS=[
 ["اللهم اكفني بحلالك عن حرامك، وأغنني بفضلك عمّن سواك","سنن الترمذي","3563 · حسن"],
 ["اللهم إني أسألك علمًا نافعًا، ورزقًا طيبًا، وعملًا متقبّلًا","سنن ابن ماجه","925 · صحيح"]
];
const MARRIAGE=[
 {k:"v",t:"وأنكحوا الأيامى منكم والصالحين من عبادكم وإمائكم إن يكونوا فقراء يغنهم الله من فضله",a:"سورة النور",b:"من الآية 32"},
 {k:"h",t:"يا معشر الشباب، من استطاع منكم الباءة فليتزوّج",a:"متفق عليه",b:"البخاري 5066 · مسلم 1400"},
 {k:"h",t:"ثلاثةٌ حقٌّ على الله عونُهم: المجاهد في سبيل الله، والمكاتَب الذي يريد الأداء، والناكح الذي يريد العفاف",a:"سنن الترمذي",b:"1655 · حسن"},
 {k:"h",t:"خيرُ الصَّداق أيسرُه",a:"سنن أبي داود",b:"2117 · صحيح"}
];
const GOAL_ITEMS=[["engage","الخطوبة (حفلة وهدايا)"],["mahr","المهر"],["wed","الفرح"],["finish","تجهيزات وتشطيب الشقة"],["furn","الأثاث"],["appl","الأجهزة الكهربائية"],["linen","المفروشات وأدوات المطبخ"],["other","شهر العسل ومصاريف أخرى"]];
const SCEN={
 eco:{n:"اقتصادي",shabka:15,v:{engage:15000,mahr:25000,wed:50000,finish:80000,furn:90000,appl:60000,linen:25000,other:20000}},
 mid:{n:"متوسط",shabka:20,v:{engage:40000,mahr:50000,wed:120000,finish:150000,furn:150000,appl:100000,linen:50000,other:50000}},
 lux:{n:"مريح",shabka:35,v:{engage:80000,mahr:100000,wed:250000,finish:250000,furn:250000,appl:160000,linen:80000,other:100000}}};
const VERSES=[
 ["وما من دابة في الأرض إلا على الله رزقها","سورة هود","الآية 6"],
 ["ومن يتق الله يجعل له مخرجا ۝ ويرزقه من حيث لا يحتسب","سورة الطلاق","الآيتان 2–3"],
 ["لئن شكرتم لأزيدنكم","سورة إبراهيم","الآية 7"],
 ["وفي السماء رزقكم وما توعدون","سورة الذاريات","الآية 22"],
 ["إن الله هو الرزاق ذو القوة المتين","سورة الذاريات","الآية 58"],
 ["وما أنفقتم من شيء فهو يخلفه وهو خير الرازقين","سورة سبأ","الآية 39"],
 ["مثل الذين ينفقون أموالهم في سبيل الله كمثل حبة أنبتت سبع سنابل في كل سنبلة مائة حبة","سورة البقرة","من الآية 261"],
 ["والذين إذا أنفقوا لم يسرفوا ولم يقتروا وكان بين ذلك قواما","سورة الفرقان","الآية 67"],
 ["المال والبنون زينة الحياة الدنيا والباقيات الصالحات خير عند ربك ثوابا وخير أملا","سورة الكهف","الآية 46"],
 ["فإذا قضيت الصلاة فانتشروا في الأرض وابتغوا من فضل الله","سورة الجمعة","من الآية 10"],
 ["خذ من أموالهم صدقة تطهرهم وتزكيهم بها","سورة التوبة","من الآية 103"],
 ["ولا تؤتوا السفهاء أموالكم التي جعل الله لكم قياما","سورة النساء","من الآية 5"]
];
const SACRED=(()=>{const out=[];DUAS.forEach(d=>out.push({k:"d",t:d[0],a:d[1],b:d[2]}));MARRIAGE.forEach(m=>out.push(m));const n=Math.max(HADITH.length,VERSES.length);for(let i=0;i<n;i++){if(VERSES[i])out.push({k:"v",t:VERSES[i][0],a:VERSES[i][1],b:VERSES[i][2]});if(HADITH[i])out.push({k:"h",t:HADITH[i][0],a:HADITH[i][1],b:HADITH[i][2]})}return out})();
const DOCTRINE=["القلعة تُبنى بالانضباط قبل الحجارة","الخطة تكسب المعركة قبل ما تبدأ","الاحتياطي سلاح، مش رفاهية","الخوف بيبيع بالرخيص؛ بِع بالخطة مش بالذعر","كل جنيه له مهمة","الصبر مضاعِف الأرباح الأول","اعرف أرضك قبل ما تتحرك"];
const CLASS={gold:{n:"ذهب",c:"#C9A24E"},fixed:{n:"دخل ثابت",c:"#6E8BD6"},liquid:{n:"سيولة",c:"#9AA0B4"},growth:{n:"نمو (أسهم)",c:"#2F8F63"}};
const SHL={yes:"شرعي",no:"غير شرعي",contested:"محل خلاف",unknown:"غير محدد"};
const SHC={yes:"#2F8F63",contested:"#E2A541",unknown:"#5E6680",no:"#E06A5F"};
const SH=v=>v===true?"yes":v===false||v==null||v===""?"unknown":String(v);
const FCLS={gold:"صندوق ذهب",liquid:"أسواق نقد",growth:"صندوق أسهم",mixed:"متوازن",stock:"سهم مباشر",fixed:"دخل ثابت"};

/* state */
const DEF=()=>({v:1,gold:[],prices:{k24:{buy:0,sell:0},k21:{buy:0,sell:0},at:null,src:""},funds:[],certs:[],cash:[],tx:[],rec:[],sg:[],cats:[],budgets:{},debts:[],
  income:{salary:0,expenses:0,extras:[]},targets:{gold:25,fixed:30,liquid:15,growth:30},
  assump:{gold:12,fixed:18,liquid:18,growth:20,infl:14,monthly:15000,years:10},settings:{autoGalla:true}});
let S=DEF(); let HIST={snaps:{}};
const LS={get(k){try{return JSON.parse(localStorage.getItem("hisn:"+k))}catch(e){return null}},set(k,v){try{localStorage.setItem("hisn:"+k,JSON.stringify(v));return true}catch(e){return false}}};
const N0=v=>{const n=Number(v);return isFinite(n)?n:0};
function merge(d){const b=DEF();if(!d)return b;const o=Object.assign(b,JSON.parse(JSON.stringify(d)));
  ["income","targets","assump","settings","prices"].forEach(k=>o[k]=Object.assign(DEF()[k],o[k]||{}));["gold","funds","certs","cash","tx","rec","sg","cats","debts"].forEach(k=>{if(!Array.isArray(o[k]))o[k]=[]});if(!o.budgets||typeof o.budgets!=="object"||Array.isArray(o.budgets))o.budgets={};{const p=o.prices;if(p&&!p.ref&&N0(p.k24&&p.k24.buy)&&p.at){const g=p.global&&N0(p.global.egp24)&&Math.abs(new Date(p.global.at)-new Date(p.at))<36e5*6?N0(p.global.egp24):null;p.ref={k24buy:N0(p.k24.buy),k24sell:N0(p.k24.sell),k21buy:N0(p.k21&&p.k21.buy),k21sell:N0(p.k21&&p.k21.sell),global:g,at:p.at}}}if(!Array.isArray(o.income.extras))o.income.extras=[];o.certs.forEach(c=>{if(!Array.isArray(c.brkHist))c.brkHist=[];if(Number(c.breakTotal)>0&&c.breakAt&&!c.brkHist.some(h=>h.d===c.breakAt))c.brkHist.push({d:c.breakAt,v:Number(c.breakTotal)});c.brkHist.sort((a,b)=>String(a.d).localeCompare(String(b.d)))});return o}
const cached=LS.get("state"); if(cached) S=merge(cached);
const cachedH=LS.get("hist"); if(cachedH&&cachedH.snaps) HIST=cachedH;
let SEED_AT=null;

/* helpers */
const $=s=>document.querySelector(s);
const esc=s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const N=v=>{const n=Number(v);return isFinite(n)?n:0};
const fmt=(n,d=0)=>N(n).toLocaleString("en-US",{minimumFractionDigits:d,maximumFractionDigits:d});
const sgn=n=>`<span class="num ${n>=0?"up":"down"}">${n>=0?"+":"−"}${fmt(Math.abs(n))}</span>`;
const pct=(n,d=1)=>`<span class="num ${n>=0?"up":"down"}">${n>=0?"+":"−"}${Math.abs(n*100).toFixed(d)}%</span>`;
const uid=()=>Math.random().toString(36).slice(2,9);
const clamp=(x,a=0,b=1)=>Math.max(a,Math.min(b,x));
function today(){return new Intl.DateTimeFormat("en-CA",{timeZone:TZ,year:"numeric",month:"2-digit",day:"2-digit"}).format(new Date())}
function dParse(s){if(!s)return null;const m=String(s).match(/^(\d{4})-(\d{2})-(\d{2})/);return m?new Date(Date.UTC(+m[1],+m[2]-1,+m[3])):null}
const DAY=864e5;
function daysBetween(a,b){const x=dParse(a),y=dParse(b);return x&&y?Math.round((y-x)/DAY):0}
function dLabel(s){const d=dParse(s);if(!d)return "—";return d.toLocaleDateString("ar-EG-u-nu-latn",{timeZone:"UTC",day:"numeric",month:"short",year:"numeric"})}
function hijri(d){try{return new Intl.DateTimeFormat("ar-SA-u-ca-islamic-umalqura-nu-latn",{timeZone:TZ,day:"numeric",month:"long",year:"numeric"}).format(d)}catch(e){return ""}}
function toast(t){const el=document.createElement("div");el.className="toast";el.textContent=t;document.body.append(el);setTimeout(()=>el.remove(),3000)}
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
function ageH(iso){if(!iso)return Infinity;return (Date.now()-new Date(iso).getTime())/36e5}

/* calculations */
function goldPrice(k){const p=S.prices;const b24=N(p.k24.buy),b21=N(p.k21.buy);k=N(k);if(k===24)return b24;if(k===21)return b21||b24*21/24;return b24*k/24}
function streak(){const [y,m]=String(S.settings.streakStart).split("-").map(Number);const t=today();return (+t.slice(0,4)-y)*12+(+t.slice(5,7)-m)+1}
function nextPay(c,t){const d=Math.min(28,Math.max(1,N(c.payDay)||1));const [y,m,dd]=t.split("-").map(Number);let Y=y,M=m;if(dd>d){M++;if(M>12){M=1;Y++}}return `${Y}-${String(M).padStart(2,"0")}-${String(d).padStart(2,"0")}`}
function couponsBetween(from,mat,day){if(!from||!mat)return 0;let n=0;let [Y,M]=from.split("-").map(Number);const d=Math.min(28,N(day)||1);
  for(let i=0;i<240;i++){const s=`${Y}-${String(M).padStart(2,"0")}-${String(d).padStart(2,"0")}`;if(s>mat)break;n++;M++;if(M>12){M=1;Y++}}return n}
function countPaid(c,t){if(c.recvFrom){let [Y,M,D]=c.recvFrom.split("-").map(Number);const d=Math.min(28,N(c.payDay)||1);if(D>d){M++;if(M>12){M=1;Y++}}let n=0;for(let i=0;i<240;i++){const s=`${Y}-${String(M).padStart(2,"0")}-${String(d).padStart(2,"0")}`;if(s>t)break;n++;M++;if(M>12){M=1;Y++}}return n}
  let [Y,M]=c.issue.split("-").map(Number);const d=Math.min(28,N(c.payDay)||1);let n=0;M++;if(M>12){M=1;Y++}
  for(let i=0;i<240;i++){const s=`${Y}-${String(M).padStart(2,"0")}-${String(d).padStart(2,"0")}`;if(s>t)break;n++;M++;if(M>12){M=1;Y++}}return n}
function certTrend(c,share,monthly){const h=(c.brkHist||[]).filter(x=>N(x.v)>0&&x.d).slice().sort((a,b)=>String(a.d).localeCompare(String(b.d)));if(h.length<2)return null;
  const a=h[h.length-2],b=h[h.length-1];const gap=Math.max(7,daysBetween(a.d,b.d));const dropTotal=(N(a.v)-N(b.v))/(gap/30.4);const dropShare=dropTotal*share;
  return {h,dropTotal,dropShare,net:monthly-dropShare,gap,first:h[0],last:b}}
function effExp(){const man=N(S.income.expenses);if(S.settings.autoExp===false)return man;const a=window.HISN_EXT&&HISN_EXT.avgExp?HISN_EXT.avgExp():0;return a>0?a:man}
function calc(){
  const t=today();const sum=(a,k)=>a.reduce((s,x)=>s+N(x[k]),0);
  const gold=S.gold.map(g=>{const cost=N(g.grams)*N(g.ppg),val=N(g.grams)*goldPrice(g.karat);const days=Math.max(1,daysBetween(g.date,t)||1);
    const cagr=cost>0&&days>30?Math.pow(val/cost,365/days)-1:null;return {...g,cost,val,pnl:val-cost,ret:cost?val/cost-1:0,days,cagr}});
  const g24=gold.filter(g=>N(g.karat)===24),g21=gold.filter(g=>N(g.karat)!==24);
  const goldT={cost:sum(gold,"cost"),val:sum(gold,"val"),grams24:sum(g24,"grams"),grams21:sum(g21,"grams")};goldT.pnl=goldT.val-goldT.cost;
  const funds=S.funds.map(f=>{const bal=f.kind==="balance";const lots=(f.lots||[]).map(l=>({...l,cost:N(l.units)*(bal?1:N(l.price))}));const units=sum(lots,"units"),cost=sum(lots,"cost");const val=bal?N(f.nav):units*N(f.nav);
    const avg=units?cost/units:0;let w=0;lots.forEach(l=>{w+=N(l.cost)*Math.max(1,daysBetween(l.date,t)||1)});const days=cost?w/cost:0;
    const cagr=cost>0&&days>45&&val>0&&!bal?Math.pow(val/cost,365/days)-1:null;return {...f,lots,units,cost,val,avg,pnl:val-cost,ret:cost?val/cost-1:0,cagr,days}});
  const fundsT={cost:sum(funds,"cost"),val:sum(funds,"val")};fundsT.pnl=fundsT.val-fundsT.cost;
  const certs=S.certs.map(c=>{const mine=N(c.principal)*N(c.share||1);const monthly=N(c.monthly);const rate=mine?monthly*12/mine:0;
    const np=nextPay(c,t);const left=couponsBetween(np,c.maturity,c.payDay);const recv=c.issue?countPaid(c,t):null;
    const brk=N(c.breakTotal)?N(c.breakTotal)*N(c.share||1):null;const timeFr=c.issue&&c.maturity?clamp(daysBetween(c.issue,t)/Math.max(1,daysBetween(c.issue,c.maturity))):0;
    const trend=certTrend(c,N(c.share||1),monthly);return {...c,brk,trend,timeFr,mine,monthly,rate,nextPay:np,daysToPay:daysBetween(t,np),daysToMat:daysBetween(t,c.maturity),left,leftIncome:left*monthly,recv}});
  const certsT={val:sum(certs,"mine"),monthly:sum(certs,"monthly")};
  const cashT=S.cash.reduce((s,c)=>s+N(c.amount),0);
  const alloc={gold:goldT.val,fixed:certsT.val,liquid:cashT,growth:0};
  funds.forEach(f=>{const k=f.cls==="gold"?"gold":f.cls==="liquid"?"liquid":f.cls==="fixed"?"fixed":"growth";alloc[k]+=f.val});
  const debtT=(S.debts||[]).filter(d=>d.dir!=="owed").reduce((s,d)=>s+N(d.amount),0);const recvT=(S.debts||[]).filter(d=>d.dir==="owed").reduce((s,d)=>s+N(d.amount),0);
  const nw=alloc.gold+alloc.fixed+alloc.liquid+alloc.growth+recvT-debtT;
  const costBasis=goldT.cost+fundsT.cost+certsT.val+cashT;
  const yieldMonthly=funds.filter(f=>f.kind==="balance"&&f.yield).reduce((s,f)=>s+f.val*N(f.yield)/1200,0);
  const passive=certsT.monthly+yieldMonthly;
  const salary=N(S.income.salary),exp=effExp();const yr=t.slice(0,4);
  const extrasYr=(S.income.extras||[]).filter(e=>String(e.date||"").slice(0,4)===yr).reduce((s,e)=>s+N(e.amount),0);
  const inflow=salary+certsT.monthly;const surplus=exp>0?inflow-exp:null;
  const where={};const addW=(k,v)=>where[k]=(where[k]||0)+v;
  addW("الخزنة (ذهب عيني)",goldT.val);funds.forEach(f=>addW(f.custodian||"ثاندر",f.val));certs.forEach(c=>addW(c.bank||"بنك",c.mine));S.cash.forEach(c=>addW(c.label||"نقد",N(c.amount)));
  const shar={yes:0,no:0,contested:0,unknown:0};shar.yes+=goldT.val;funds.forEach(f=>shar[SH(f.shariah)]+=f.val);certs.forEach(c=>shar[SH(c.shariah||"contested")]+=c.mine);S.cash.forEach(c=>shar[SH(c.shariah??"yes")]+=N(c.amount));
  const G=goalCfg();const p21s=N(S.prices.k21.sell)||N(S.prices.k21.buy)||N(S.prices.k24.buy)*21/24;const shabkaV=N(G.shabka)*p21s;
  const goalSub=GOAL_ITEMS.reduce((s,[k])=>s+N(G.v[k]),0)+shabkaV;const goalT=Math.round(goalSub*(1+N(G.cont)/100));
  return {debtT,recvT,shar,goalT,goalSub,shabkaV,p21s,t,gold,goldT,funds,fundsT,certs,certsT,cashT,alloc,nw,costBasis,unreal:goldT.pnl+fundsT.pnl,salary,exp,inflow,surplus,extrasYr,passive,yieldMonthly,where};
}

/* health score */
function goalCfg(){const g=S.goal||{};if(g.scenario&&g.scenario!=="custom"&&SCEN[g.scenario])return {scenario:g.scenario,shabka:SCEN[g.scenario].shabka,v:{...SCEN[g.scenario].v},cont:g.cont??10};
  if(g.scenario==="custom")return {scenario:"custom",shabka:N(g.shabka),v:{...(g.v||{})},cont:g.cont??10};return {scenario:"mid",shabka:SCEN.mid.shabka,v:{...SCEN.mid.v},cont:10,implicit:true}}
function score(C){const nw=C.nw||1;const sh={};Object.keys(CLASS).forEach(k=>sh[k]=C.alloc[k]/nw);const tg=k=>N(S.targets[k])/100;
  const hhi=Object.values(sh).reduce((s,x)=>s+x*x,0);
  const invested=C.goldT.val+C.fundsT.val||1;
  const losers=[...C.gold.filter(g=>g.ret<-0.1).map(g=>g.val),...C.funds.filter(f=>f.ret<-0.1).map(f=>f.val)].reduce((s,x)=>s+x,0);
  const liq=C.alloc.liquid;
  const fresh=(ageH(S.prices.at)<24?5:ageH(S.prices.at)<72?2.5:0)+(C.funds.every(f=>!f.units&&!f.cost||f.navAt&&daysBetween(f.navAt,C.t)<=7)?5:2);
  const parts=[
    ["التنويع",25*clamp((1-hhi)/0.75)],
    ["محرك النمو",20*clamp(sh.growth/0.20)],
    ["توازن الذهب",15*clamp(1-(sh.gold>0.30?sh.gold-0.30:sh.gold<0.10?0.10-sh.gold:0)/0.25)],
    ["السيولة",C.exp>0?(()=>{const mo=liq/C.exp;return mo<6?15*mo/6:mo<=12?15:15*clamp(1-(mo-12)/24)})():10*clamp(sh.liquid/0.10)],
    ["جودة المراكز",15*clamp(1-losers/invested*5)],
    ["حداثة البيانات",fresh]];
  const max=[25,20,15,15,15,10];
  const total=Math.round(parts.reduce((s,p)=>s+p[1],0));
  const verdict=total>=85?"حصن منيع":total>=70?"حصن متماسك":total>=55?"أسوار فيها ثغرات":"تحت الحصار";
  return {total,verdict,parts:parts.map((p,i)=>({n:p[0],v:p[1],m:max[i]}))}}

/* advisor rules */
function rules(C){const A=[];const nw=C.nw||1;const p=S.prices;
  const goldShare=C.alloc.gold/nw,liq=C.alloc.liquid,growthShare=C.alloc.growth/nw;
  if(!C.nw){A.push({lv:"info",t:"ابدأ بتسجيل أصولك",b:"الحصن فاضي. أضف الذهب والصناديق والشهادات، والأرقام والتوصيات هتشتغل تلقائيًا."});return A}
  if(!N(p.k24.buy))A.push({lv:"critical",t:"مفيش سعر ذهب مسجّل",b:"قيمة الذهب العيني محسوبة بصفر.",a:"اضغط «تحديث أسعار الجلا»."});
  else if(ageH(p.at)>24)A.push({lv:"warn",t:"سعر الذهب قديم",b:`آخر تحديث من ${Math.max(1,Math.round(ageH(p.at)/24))} يوم.`,a:"حدّث السعر قبل أي قرار بيع أو شراء."});
  const stale=C.funds.filter(f=>f.cost>0&&(!f.navAt||daysBetween(f.navAt,C.t)>7));
  if(stale.length)A.push({lv:"warn",t:`محتاج تحديث سعر: ${stale.map(f=>f.name).join("، ")}`,b:"آخر سعر عمره أكتر من أسبوع، فالقيمة تقريبية.",a:"خد السعر من ثاندر وحدّثه في تبويب ثاندر."});
  const tgG=N(S.targets.gold)/100;
  if(goldShare>tgG+0.10){const excess=C.alloc.gold-tgG*nw;A.push({lv:goldShare>0.5?"critical":"warn",t:`تركّز في الذهب: ${(goldShare*100).toFixed(0)}% من الحصن`,b:`هدفك ${S.targets.gold}%. الفارق ${fmt(excess)} ج. الذهب تحوّط ضد الجنيه بس مش بيدّي دخل، وهبوط 15% فيه = خسارة ${fmt(C.alloc.gold*0.15)} ج.`,a:"وقّف أي شراء ذهب جديد لحد ما النسبة تنزل تحت "+(S.targets.gold+5)+"% بنمو باقي الأصول."})}
  if(N(p.k24.buy)&&N(p.k24.sell)){const sp=(p.k24.sell-p.k24.buy)/p.k24.sell;
    const under=C.gold.filter(g=>g.ret<0);
    if(under.length)A.push({lv:"warn",t:`قطع ذهب تحت سعر شرائها: ${under.map(g=>g.name).join("، ")}`,b:`خسارة دفترية ${fmt(under.reduce((s,g)=>s+g.pnl,0))} ج. اشتريت بسعر أعلى من سعر إعادة البيع الحالي (المصنعية + فرق ${(sp*100).toFixed(2)}% بين البيع والشراء).`,a:"الإضافات الصغيرة للذهب تبقى من صندوق الذهب، والسبائك للمبالغ الكبيرة بس."})}
  if(C.exp>0){const need=C.exp*6;if(liq<need)A.push({lv:"warn",t:"صندوق الطوارئ ناقص",b:`السيولة ${fmt(liq)} ج والمطلوب 6 شهور مصروف = ${fmt(need)} ج.`,a:`كمّل ${fmt(need-liq)} ج في أسواق النقد.`});
    else{const extra=liq-need*1.5;const gf=C.goalT&&(C.nw-C.certsT.val)>=C.goalT;if(!gf&&C.goalT){A.push({lv:"good",t:"السيولة دي فلوس مهمة الجواز، ومكانها صح",b:`السيولة تغطي ${(liq/C.exp).toFixed(1)} شهر مصروف، وأي فائض فوق الطوارئ محجوز للجواز اللي ممكن يتطلب خلال سنة.`,a:"متحوّلهاش لأسهم لحد ما مهمة الجواز تتموّل بالكامل."})}else A.push({lv:extra>50000?"warn":"good",t:extra>50000?`سيولة زيادة عن الحاجة: ${fmt(extra)} ج`:"خط الدفاع الأول مكتمل",b:`السيولة تغطي ${(liq/C.exp).toFixed(1)} شهر من مصروفك.`,a:extra>50000?"حوّل الفائض تدريجيًا لمحرّك النمو على 10–12 شهر.":""})}
    const rate=C.surplus/C.inflow;A.push(rate<0.2?{lv:"warn",t:`معدل الادخار ${(rate*100).toFixed(0)}%`,b:"أقل من 20% من دخلك بيتحول لاستثمار.",a:"تحويل تلقائي يوم القبض."}:{lv:"good",t:`معدل ادخار ${(rate*100).toFixed(0)}%`,b:`فايض شهري ${fmt(C.surplus)} ج.`})}
  else A.push({lv:"info",t:"سجّل مصروفك الشهري",b:"من غيره مش هقدر أحسب صندوق الطوارئ ولا الفائض ولا حجم السيولة الزيادة.",a:"الإعدادات ← المصروف الشهري."});
  C.certs.forEach(c=>{const m=Math.round(c.daysToMat/30.4);
    if(c.daysToMat<=0)A.push({lv:"critical",t:`${c.name} استحقت`,b:"الفلوس واقفة بدون عائد.",a:"قرّر مكانها فورًا."});
    else if(m<=6)A.push({lv:"warn",t:`${c.name} تستحق بعد ${m} شهور`,b:`${fmt(c.mine)} ج راجعة، وغالبًا بعائد أقل من ${(c.rate*100).toFixed(1)}%.`,a:"جهّز خطة إعادة الاستثمار."});
    else{if(c.brk!=null)A.push({lv:"good",t:`الاحتفاظ بالشهادة أفضل من كسرها بـ ${fmt(c.mine-c.brk+c.leftIncome)} ج`,b:`الكسر النهارده يرجّعلك ${fmt(c.brk)} بدل ${fmt(c.mine)} (خسارة ${fmt(c.mine-c.brk)})، وتخسر كمان ${c.left} صرفة متبقية (${fmt(c.leftIncome)}).`,a:"متكسرهاش إلا لضرورة قصوى؛ الأولوية للسحب من الكلاودز والذهب قبلها."});
    if(c.trend)A.push(c.trend.net>=0?{lv:"good",t:`${c.name}: الاحتفاظ بيكسب ${fmt(c.trend.net)} ج شهريًا فوق الكسر`,b:`العائد ${fmt(c.monthly)} ج، وقيمة الكسر نازلة ${fmt(Math.max(0,c.trend.dropShare))} ج شهريًا لنصيبك (من قراءتين: ${dLabel(c.trend.h[c.trend.h.length-2].d)} و${dLabel(c.trend.last.d)}).`,a:"سجّل قيمة الكسر كل شهر؛ لو النزول عدّى العائد، القرار هيتغير."}:{lv:"warn",t:`${c.name}: قيمة الكسر بتنزل أسرع من العائد`,b:`النزول ${fmt(c.trend.dropShare)} ج شهريًا مقابل عائد ${fmt(c.monthly)} ج، يعني كل شهر انتظار بيخسرك ${fmt(-c.trend.net)} ج.`,a:"اسأل البنك عن جدول القيم لحد الاستحقاق قبل أي قرار."});
    A.push({lv:"info",t:`عائد ${c.name}: ${fmt(c.monthly)} ج يوم ${c.payDay}`,b:`فعّال ${(c.rate*100).toFixed(2)}% (حقيقي ≈ ${((c.rate-N(S.assump.infl)/100)*100).toFixed(1)}% بعد التضخم). باقي ${c.left} صرفة = ${fmt(c.leftIncome)} ج لحد ${dLabel(c.maturity)}.`,a:"حوّل العائد يوم "+c.payDay+" لصندوق نمو، متسيبهوش في الحساب الجاري."})}});
  const goalOpen=C.goalT&&(C.nw-C.certsT.val)<C.goalT;
  if(growthShare<0.15)A.push({lv:goalOpen?"info":growthShare<0.05?"critical":"warn",t:`محرّك النمو ${(growthShare*100).toFixed(0)}% بس`,b:`هدفك ${S.targets.growth}%. أغلب الحصن في أصول بتحافظ على القيمة (ذهب، شهادة، أسواق نقد)، ومفيش جزء كافي بيكبّرها على المدى الطويل.`,a:goalOpen?"مؤجّل: النمو يبدأ من الفائض بعد ما مهمة الجواز تتموّل، أو من أصل الشهادة في 2028.":`ادخل بالتقسيط الشهري؛ الفارق للهدف ${fmt(N(S.targets.growth)/100*nw-C.alloc.growth)} ج.`});
  const losers=C.funds.filter(f=>f.ret<-0.1);losers.forEach(f=>A.push({lv:"warn",t:`${f.name}: ${(f.ret*100).toFixed(1)}%`,b:`خسارة ${fmt(-f.pnl)} ج على ${fmt(f.cost)}.`,a:"اسأل نفسك: لو معاك الفلوس دي كاش النهارده، هتشتريه بسعره الحالي؟ لو لأ، الانتظار لـ«نقطة التعادل» مش خطة."}));
  const pieces=[...C.gold.filter(g=>g.cagr!=null).map(g=>({n:g.name+" ("+dLabel(g.date)+")",c:g.cagr,r:g.ret})),...C.funds.filter(f=>f.cagr!=null).map(f=>({n:f.name,c:f.cagr,r:f.ret}))];
  if(pieces.length>1){pieces.sort((a,b)=>b.c-a.c);const b=pieces[0],w=pieces[pieces.length-1];A.push({lv:"good",t:`الأقوى: ${b.n}`,b:`عائد سنوي مركّب ${(b.c*100).toFixed(1)}%. الأضعف: ${w.n} بـ ${(w.c*100).toFixed(1)}%.`})}
  const mo=+C.t.slice(5,7);if(mo>=1&&mo<=3)A.push({lv:"info",t:"موسم المكافأة السنوية (مارس)",b:"قرّر توزيعها قبل ما تنزل.",a:"60% استثمار حسب أهدافك، 25% احتياطي، 15% لنفسك."});
  if(S.settings.streakStart)A.push({lv:"good",t:`${streak()} شهر استثمار متواصل`,b:"«أحبّ الأعمال إلى الله أدومها وإن قلّ». الاستمرارية أقوى أصل عندك."});
  (S.debts||[]).filter(d=>N(d.amount)>0&&d.dir!=="owed").forEach(d=>A.push({lv:N(d.rate)>0?"critical":"info",t:`${d.label}: ${fmt(d.amount)} ج مستحق`,b:N(d.rate)>0?`بفائدة ${d.rate}% شهريًا = ${fmt(N(d.amount)*N(d.rate)/100*12)} ج في السنة. ده أغلى من أي عائد عندك، وكمان ربا صريح.`:(N(d.limit)?`استخدام ${(N(d.amount)/N(d.limit)*100).toFixed(0)}% من الحد. `:"")+"بتسدده كامل قبل الاستحقاق، فمفيش فايدة. النقاط مكسب طالما السداد كامل دايمًا.",a:N(d.rate)>0?"سدّده فورًا من الكلاودز؛ ده أعلى عائد مضمون ممكن تاخده.":"افصل مدفوعات الشركة في سجل وتابع استردادها، عشان متتحسبش مصروف شخصي."}));
  const shBad=C.shar.contested+C.shar.unknown+C.shar.no;
  if(shBad>0){const parts=[];C.funds.filter(f=>SH(f.shariah)!=="yes").forEach(f=>parts.push(f.name+" ("+SHL[SH(f.shariah)]+")"));C.certs.filter(c=>SH(c.shariah||"contested")!=="yes").forEach(c=>parts.push(c.name+" ("+SHL[SH(c.shariah||"contested")]+")"));
    A.push({lv:"info",t:`التوافق الشرعي: ${(C.shar.yes/nw*100).toFixed(0)}% مؤكد`,b:"لسه محتاج حسم: "+parts.join("، ")+".",a:"الصناديق غير المحددة: اتأكد من نشرة الصندوق أو هيئته الشرعية، أو استبدلها ببديل شرعي معلن."})}
  const gt=N(S.settings.goldTarget);if(gt&&N(p.k24.buy)>=gt)A.push({lv:"critical",t:`سعر الذهب وصل هدفك: ${fmt(p.k24.buy)} ≥ ${fmt(gt)}`,b:`قيمة الذهب العيني الآن ${fmt(C.goldT.val)} ج.`,a:"لو قررت البيع: على دفعتين أو تلاتة، وابدأ بالقطع الأعلى ربحًا."});
  if(S.settings.goldSellBy){const dd=daysBetween(C.t,S.settings.goldSellBy);if(dd>=0&&dd<=45)A.push({lv:"warn",t:`موعد بيع الذهب المحتمل بعد ${dd} يوم`,b:"راقب السعر يوميًا من دلوقتي، وحدّد سعر أدنى مقبول.",a:"متبعش كله في يوم واحد."})}
  {const av=C.nw-C.certsT.val;if(C.goalT)A.push(av>=C.goalT?{lv:"good",t:"مهمة الجواز ممولة بالكامل",b:`المتاح ${fmt(av)} ج يغطي التكلفة التقديرية ${fmt(C.goalT)} ج (بدون الشقة) ${(av/C.goalT).toFixed(1)} مرة.`,a:"الفلوس دي لازم تفضل في أصول سهلة التسييل وقليلة التذبذب لحد ما التاريخ يتحدد."}:{lv:"info",t:`مهمة الجواز: ${(av/C.goalT*100).toFixed(0)}% جاهزة`,b:`فاضل ${fmt(C.goalT-av)} ج.`})}
  try{A.push(...((window.HISN_EXT&&HISN_EXT.rulesExtra&&HISN_EXT.rulesExtra())||[]))}catch(e){}
  const ord={critical:0,warn:1,info:2,good:3};A.sort((a,b)=>ord[a.lv]-ord[b.lv]);return A}

/* render */
let C=calc();
function render(){C=calc();renderTop();renderKpis();renderOps();renderGold();renderFunds();renderCerts();renderIncome();renderIntel();renderZakat();renderFuture();renderNasab();try{window.HISN_EXT&&HISN_EXT.onRender&&HISN_EXT.onRender()}catch(e){console.error(e)}}
function renderTop(){
  $("#nw").innerHTML=`${fmt(C.nw)}<small>EGP</small>`;
  const keys=Object.keys(HIST.snaps||{}).sort();const prevKey=keys.filter(k=>k<C.t).pop();
  $("#nwDelta").innerHTML=prevKey?`منذ ${dLabel(prevKey)}: ${sgn(C.nw-HIST.snaps[prevKey].nw)}`:"";
  const pill=(l,v)=>`<span class="pill">${l} <b>${v}</b></span>`;
  const brkLoss=C.certs.reduce((s,c)=>s+(c.brk!=null?c.mine-c.brk:0),0);
  $("#nwSub").innerHTML=(brkLoss?pill("لو كسرت الشهادة النهارده",fmt(C.nw-brkLoss)):"")+pill("ربح غير محقق",(C.unreal>=0?"+":"−")+fmt(Math.abs(C.unreal)))+pill("دخل سلبي/شهر",fmt(C.passive))+pill("ذهب",fmt(C.goldT.grams24+C.goldT.grams21,1)+" g")+(S.settings.streakStart?`<span class="pill">استثمار متواصل <b>${streak()}</b> شهر</span>`:"");
  const crit=rules(C).some(a=>a.lv==="critical");$("#flag").classList.toggle("distress",crit);$("#flagTxt").textContent=crit?"العلم مقلوب: فيه إنذار أحمر":"العلم مرفوع: لا إنذارات حمراء";
  const pc=$("#priceChip");const a=ageH(S.prices.at);pc.className="chip "+(a<6?"ok":a<48?"warn":"bad");
  pc.querySelector("span").textContent=S.prices.at?`ع24 ${fmt(S.prices.k24.buy)} · ${a<1?"الآن":a<24?Math.round(a)+" س":Math.round(a/24)+" يوم"}`:"لا يوجد سعر";
  renderGauge();
}
function renderGauge(){const sc=score(C);const v=sc.total;const R=90,cx=110,cy=104;
  const P=a=>[cx+R*Math.cos(a),cy+R*Math.sin(a)];const arc=(a0,a1,col,w)=>{const [x0,y0]=P(a0),[x1,y1]=P(a1);return `<path d="M${x0} ${y0}A${R} ${R} 0 0 1 ${x1} ${y1}" fill="none" stroke="${col}" stroke-width="${w}" stroke-linecap="round"/>`};
  const A0=Math.PI,A1=2*Math.PI;const av=A0+(A1-A0)*v/100;const [nx,ny]=[cx+(R-22)*Math.cos(av),cy+(R-22)*Math.sin(av)];
  let ticks="";for(let i=0;i<=10;i++){const a=A0+(A1-A0)*i/10;const [x0,y0]=[cx+(R+9)*Math.cos(a),cy+(R+9)*Math.sin(a)],[x1,y1]=[cx+(R+14)*Math.cos(a),cy+(R+14)*Math.sin(a)];ticks+=`<line x1="${x0}" y1="${y0}" x2="${x1}" y2="${y1}" stroke="#C9A24E" stroke-opacity="${i%5?.3:.7}"/>`}
  const col=v>=85?"#5CBF8D":v>=70?"#C9A24E":v>=55?"#E2A541":"#E06A5F";
  $("#gauge").innerHTML=`<div class="lbl">FORTRESS SCORE · درجة الحصن</div>
   <svg viewBox="0 0 220 128" role="img" aria-label="درجة الحصن ${v} من 100"><defs><linearGradient id="gg" x1="0" x2="1"><stop offset="0" stop-color="#E06A5F"/><stop offset=".55" stop-color="#E2A541"/><stop offset=".75" stop-color="#C9A24E"/><stop offset="1" stop-color="#5CBF8D"/></linearGradient></defs>
   ${ticks}${arc(A0+.001,A1-.001,"rgba(255,255,255,.06)",10)}${arc(A0+.001,Math.max(A0+.02,av),"url(#gg)",10)}
   <circle cx="${cx+R*Math.cos(av)}" cy="${cy+R*Math.sin(av)}" r="7.5" fill="#04060E" stroke="${col}" stroke-width="2.5"/>
   <text x="${cx}" y="${cy-10}" text-anchor="middle" style="font-family:'Cormorant Garamond',serif;font-size:52px;font-weight:600;fill:#F6E7BE">${v}</text>
   <text x="${cx}" y="${cy+12}" text-anchor="middle" style="font-size:9.5px">من 100</text></svg>
   <div class="verdict">${sc.verdict}</div>
   <div class="subs">${sc.parts.map(p=>{const r=p.v/p.m;return `<div class="sub" title="${esc(p.n)}: ${p.v.toFixed(1)} من ${p.m}"><div class="k">${esc(p.n)}</div><div class="t"><i style="width:${r*100}%;background:${r>.75?"#5CBF8D":r>.45?"#C9A24E":"#E06A5F"}"></i></div></div>`}).join("")}</div>`}
function renderKpis(){const k=(t,v,s)=>`<div class="kpi"><div class="k">${t}</div><div class="v">${v}</div><div class="s">${s||""}</div></div>`;
  const inv=C.goldT.cost+C.fundsT.cost||1;
  $("#kpis").innerHTML=k("صافي الثروة",fmt(C.nw),"ج.م · كل الأصول")+k("رأس المال المدفوع",fmt(C.costBasis),"تكلفة كل الأصول")+
   k("الربح غير المحقق",`<span class="${C.unreal>=0?"up":"down"}">${C.unreal>=0?"+":"−"}${fmt(Math.abs(C.unreal))}</span>`,(C.unreal/inv*100).toFixed(1)+"% على الذهب وثاندر")+
   k("الدخل السلبي الشهري",fmt(C.passive),`شهادة ${fmt(C.certsT.monthly)} + عائد سيولة ${fmt(C.yieldMonthly)}`)+k("التدفق الشهري",fmt(C.inflow),C.surplus!=null?`فائض ${fmt(C.surplus)} بعد المصروف`:"مرتب + عوائد الشهادة")}
function donut(parts,total){const R=78,r=54,cx=85,cy=85;let a0=-Math.PI/2;let out="";
  if(!total)return `<svg viewBox="0 0 170 170" class="ring"><circle cx="85" cy="85" r="66" fill="none" stroke="#1B2442" stroke-width="24"/></svg>`;
  parts.forEach(p=>{if(p.v<=0)return;const a=p.v/total*Math.PI*2;const a1=a0+a;const lg=a>Math.PI?1:0;const P=(rad,ang)=>`${cx+rad*Math.cos(ang)} ${cy+rad*Math.sin(ang)}`;
    out+=`<path d="M${P(R,a0)}A${R} ${R} 0 ${lg} 1 ${P(R,a1)}L${P(r,a1)}A${r} ${r} 0 ${lg} 0 ${P(r,a0)}Z" fill="${p.c}" stroke="#0B1124" stroke-width="2"/>`;a0=a1});
  return `<svg viewBox="0 0 170 170" class="ring" role="img" aria-label="توزيع الأصول">${out}<circle cx="85" cy="85" r="46" fill="none" stroke="#C9A24E" stroke-opacity=".25" stroke-dasharray="1 4"/><text x="85" y="80" text-anchor="middle" style="font-size:9.5px">الحصن</text><text x="85" y="100" text-anchor="middle" style="font-family:'Cormorant Garamond',serif;font-size:22px;font-weight:600;fill:#F6E7BE">${(total/1e6).toFixed(2)}M</text></svg>`}
function renderOps(){
  const parts=Object.keys(CLASS).map(k=>({k,v:C.alloc[k],c:CLASS[k].c}));
  const rows=parts.map(p=>{const cur=C.nw?p.v/C.nw:0,tg=N(S.targets[p.k])/100,diff=tg*C.nw-p.v;const ok=Math.abs(diff)<C.nw*0.03;
    return `<div class="alloc-row"><div><span class="dot" style="background:${p.c}"></span>${CLASS[p.k].n}</div>
    <div><div class="bar"><i style="width:${Math.min(100,cur*100)}%;background:${p.c}"></i><b style="right:${Math.min(100,tg*100)}%"></b></div>
    <div class="small faint" style="margin-top:4px">${(cur*100).toFixed(1)}% · الهدف ${S.targets[p.k]}%</div></div>
    <div class="small" style="text-align:left"><span class="num">${fmt(p.v)}</span><div class="${ok?"faint":diff>0?"up":"down"}">${ok?"في النطاق":(diff>0?"أضف ":"خفّف ")+fmt(Math.abs(diff))}</div></div></div>`}).join("");
  const W=Object.entries(C.where).filter(e=>e[1]>0).sort((a,b)=>b[1]-a[1]);const wc=["#C9A24E","#2F8F63","#6E8BD6","#9AA0B4","#B07CC6"];
  const sc=score(C);const A=rules(C).slice(0,5);
  $("#s-ops").innerHTML=`<div class="grid g-ov">
   <div class="grid">
    <div class="panel"><div class="ph"><h3>خريطة الانتشار</h3><span class="code">ALLOCATION</span></div>
     <div class="ov">${donut(parts,C.nw)}<div>${rows}</div></div>
     <p class="small faint" style="margin:10px 0 0">الخط الأبيض = هدفك. «أضف/خفّف» = المبلغ اللي يرجّعك للهدف. الأهداف من الإعدادات.</p></div>
    <div class="panel"><div class="ph"><h3>ثروتك عايشة فين</h3><span class="code">CUSTODY</span></div>
     <div class="stack">${W.map((w,i)=>`<i style="width:${w[1]/C.nw*100}%;background:${wc[i%wc.length]}" title="${esc(w[0])}"></i>`).join("")}</div>
     <div class="legend">${W.map((w,i)=>`<span><span class="dot" style="background:${wc[i%wc.length]}"></span>${esc(w[0])} <b>${(w[1]/C.nw*100).toFixed(0)}%</b></span>`).join("")}</div></div>
    <div class="panel"><div class="ph"><h3>التوافق الشرعي</h3><span class="code">SHARIAH ${(C.shar.yes/(C.nw||1)*100).toFixed(0)}%</span></div>
     <div class="stack">${Object.keys(SHL).filter(k=>C.shar[k]>0).map(k=>`<i style="width:${C.shar[k]/C.nw*100}%;background:${SHC[k]}" title="${SHL[k]}"></i>`).join("")}</div>
     <div class="legend">${Object.keys(SHL).filter(k=>C.shar[k]>0).map(k=>`<span><span class="dot" style="background:${SHC[k]}"></span>${SHL[k]} <b>${fmt(C.shar[k])}</b></span>`).join("")}</div></div>
    <div class="panel"><div class="ph"><h3>تفكيك درجة الحصن</h3><span class="code">SCORE ${sc.total}/100</span></div>
     <p class="small faint" style="margin:-6px 0 8px">الدرجة بتقيس بمعيار ثابت مش بأهدافك، عشان تغيير الأهداف ما يحسّنش الدرجة: معايرة لهدف متوسط المدى (جواز وشقة): نمو 20%، ذهب بين 10 و30%، سيولة من 6 لـ 12 شهر مصروف.</p>
     <div class="tw"><table><tbody>${sc.parts.map(p=>`<tr><td>${esc(p.n)}</td><td style="width:50%"><div class="bar"><i style="width:${p.v/p.m*100}%;background:${p.v/p.m>.75?"#5CBF8D":p.v/p.m>.45?"#C9A24E":"#E06A5F"}"></i></div></td><td class="num">${p.v.toFixed(1)} / ${p.m}</td></tr>`).join("")}</tbody></table></div></div>
   </div>
   <div class="grid" style="align-content:start">${planPanel()}
   <div class="panel"><div class="ph"><h3>التقرير الميداني</h3><span class="code">FIELD REPORT · ${C.t}</span></div><div class="alerts">${A.map(alertHtml).join("")}</div>
     <div style="margin-top:12px"><button class="btn sm" type="button" data-go="intel">كل الإشارات والمستشار ←</button></div></div></div>
  </div>
  <div class="panel" style="margin-top:16px"><div class="ph"><h3>منحنى الحصن</h3><span class="code">NET WORTH LOG</span></div>${histChart()}</div>`}
function planPanel(){const P=S.plan||[];if(!P.length)return "";const done=P.filter(x=>x.done).length;
  return `<div class="panel"><div class="ph"><h3>أوامر العمليات</h3><span class="code">ORDERS ${done}/${P.length}</span></div>
   <div class="bar" style="height:6px;margin-bottom:10px"><i style="width:${done/P.length*100}%;background:var(--ok)"></i></div>
   <div class="alerts">${P.map(x=>`<label class="alert ${x.done?"good":"warn"}" style="cursor:pointer;grid-template-columns:22px minmax(0,1fr)"><input type="checkbox" data-plan="${x.id}" id="pl-${x.id}" ${x.done?"checked":""} style="width:18px;height:18px;accent-color:#5CBF8D;margin-top:3px"><div><h4 style="${x.done?"text-decoration:line-through;opacity:.6":""}">${esc(x.t)}</h4>${x.d?`<p>${esc(x.d)}</p>`:""}</div></label>`).join("")}</div></div>`}
function alertHtml(a){const L={critical:"CRITICAL",warn:"WARNING",info:"INTEL",good:"SECURED"};return `<div class="alert ${a.lv}"><div class="stripe"></div><div><h4>${esc(a.t)}<span class="lv">${L[a.lv]}</span></h4><p>${esc(a.b)}</p>${a.a?`<div class="act">◆ ${esc(a.a)}</div>`:""}</div></div>`}
function histChart(){const pts=Object.entries(HIST.snaps||{}).sort((a,b)=>a[0]<b[0]?-1:1);
  if(pts.length<2)return `<div class="empty">المنحنى بيتبني لوحده: كل يوم تحدّث فيه الأسعار أو تعدّل حاجة بيتسجل نقطة. ${pts.length?"أول نقطة: "+dLabel(pts[0][0])+".":""}</div>`;
  const W=900,H=210,pl=8,pr=70,pt=14,pb=24;const ys=pts.map(p=>N(p[1].nw));let mn=Math.min(...ys),mx=Math.max(...ys);if(mx===mn){mx+=1;mn-=1}const pad=(mx-mn)*.15;mn-=pad;mx+=pad;
  const t0=dParse(pts[0][0]).getTime(),t1=dParse(pts[pts.length-1][0]).getTime();
  const X=d=>pl+(dParse(d).getTime()-t0)/((t1-t0)||1)*(W-pl-pr),Y=v=>pt+(1-(v-mn)/(mx-mn))*(H-pt-pb);
  const line=pts.map((p,i)=>(i?"L":"M")+X(p[0]).toFixed(1)+" "+Y(N(p[1].nw)).toFixed(1)).join("");
  let grid="";for(let i=0;i<=3;i++){const v=mn+(mx-mn)*i/3;grid+=`<line x1="${pl}" x2="${W-pr}" y1="${Y(v)}" y2="${Y(v)}" stroke="#1B2442"/><text x="${W-pr+6}" y="${Y(v)+3}">${fmt(v/1000)}k</text>`}
  const last=pts[pts.length-1];
  return `<div class="tw"><svg viewBox="0 0 ${W} ${H}" style="width:100%;min-width:520px;height:auto;direction:ltr"><defs><linearGradient id="ag" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#C9A24E" stop-opacity=".3"/><stop offset="1" stop-color="#C9A24E" stop-opacity="0"/></linearGradient></defs>${grid}<path d="${line}L${X(last[0])} ${H-pb}L${X(pts[0][0])} ${H-pb}Z" fill="url(#ag)"/><path d="${line}" fill="none" stroke="#EBD08C" stroke-width="2"/><circle cx="${X(last[0])}" cy="${Y(N(last[1].nw))}" r="4.5" fill="#F6E7BE"/><text x="${pl}" y="${H-6}">${pts[0][0]}</text><text x="${W-pr}" y="${H-6}" text-anchor="end">${last[0]}</text></svg></div>`}

function renderGold(){const p=S.prices;const sp24=N(p.k24.sell)&&N(p.k24.buy)?(p.k24.sell-p.k24.buy):0;const T=C.goldT;
  const rows=C.gold.map(g=>`<tr><td>${esc(g.name)}</td><td><span class="tag k${N(g.karat)===24?24:21}">ع${esc(g.karat)}</span></td><td class="num">${fmt(g.grams,2)}</td><td class="num">${fmt(g.ppg)}</td><td>${dLabel(g.date)}</td><td class="num">${fmt(g.cost)}</td><td class="num">${fmt(g.val)}</td><td class="num">${sgn(g.pnl)}</td><td class="num">${pct(g.ret,0)}</td><td class="num">${g.cagr==null?"—":pct(g.cagr)}</td>
   <td><div class="rowacts"><button class="btn sm ghost" data-edit="gold:${g.id}">تعديل</button><button class="btn sm ghost danger" data-del="gold:${g.id}">حذف</button></div></td></tr>`).join("");
  $("#s-gold").innerHTML=`<div class="panel"><div class="ph"><h3>خزنة الذهب العيني</h3><span class="code">OP-01 · BULLION VAULT</span>
   <div class="acts"><button class="btn sm" data-price-manual type="button">إدخال السعر يدوي</button><button class="btn gold sm" data-add="gold" type="button">+ قطعة ذهب</button></div></div>
   <div class="pstrip">
     <div class="pbox"><div class="k">ع24 · سعر بيعك للجلا</div><div class="v">${fmt(p.k24.buy)}</div><div class="s">الجلا تبيع بـ ${fmt(p.k24.sell)} · فرق ${fmt(sp24)}</div></div>
     <div class="pbox"><div class="k">ع21 · سعر بيعك للجلا</div><div class="v">${fmt(p.k21.buy)}</div><div class="s">الجلا تبيع بـ ${fmt(p.k21.sell)}</div></div>
     <div class="pbox"><div class="k">لو بعت كل الذهب النهارده</div><div class="v">${fmt(T.val)}</div><div class="s">${fmt(T.grams24,2)} جم ع24 + ${fmt(T.grams21,2)} جم ع21</div></div>
     <div class="pbox"><div class="k">ربحك الصافي على الذهب</div><div class="v ${T.pnl>=0?"up":"down"}">${T.pnl>=0?"+":"−"}${fmt(Math.abs(T.pnl))}</div><div class="s">${T.cost?((T.pnl/T.cost)*100).toFixed(1)+"% على "+fmt(T.cost)+" تكلفة":""}</div></div>
   </div>
   ${N(S.settings.goldTarget)||S.settings.goldSellBy?`<p class="small" style="margin:-2px 0 8px;color:var(--gold-hi)">◆ خطة البيع: ${N(S.settings.goldTarget)?"تنبيه عند ع24 ≥ "+fmt(S.settings.goldTarget)+(N(p.k24.buy)?" (باقي "+fmt(Math.max(0,N(S.settings.goldTarget)-N(p.k24.buy)))+" ج للجرام)":""):""}${S.settings.goldSellBy?" · الموعد المحتمل "+dLabel(S.settings.goldSellBy):""}</p>`:""}
   <p class="small faint" style="margin:-2px 0 12px">التقييم بسعر «Buy» على موقع الجلا، يعني المبلغ اللي هتقبضه فعلًا عند البيع. ${p.at?"آخر تحديث: "+new Date(p.at).toLocaleString("ar-EG-u-nu-latn",{timeZone:TZ,dateStyle:"medium",timeStyle:"short"})+(p.src?" · "+esc(p.src):""):""}</p>
   ${radarHtml()}
   ${C.gold.length?`<div class="tw"><table><thead><tr><th>القطعة</th><th>العيار</th><th>جرام</th><th>شراء/جم</th><th>التاريخ</th><th>التكلفة</th><th>القيمة الآن</th><th>الربح</th><th>العائد</th><th>سنوي مركّب</th><th></th></tr></thead><tbody>${rows}
   <tr class="tot"><td>الإجمالي</td><td></td><td class="num">${fmt(T.grams24+T.grams21,2)}</td><td></td><td></td><td class="num">${fmt(T.cost)}</td><td class="num">${fmt(T.val)}</td><td class="num">${sgn(T.pnl)}</td><td class="num">${T.cost?pct(T.pnl/T.cost,0):""}</td><td></td><td></td></tr></tbody></table></div>`:`<div class="empty">مفيش قطع ذهب مسجلة. اضغط «+ قطعة ذهب».</div>`}
  </div>`}
function renderNasab(){const L=S.lineage;const el=$("#s-nasab");
  if(!L||!L.chain){el.innerHTML=`<div class="panel"><div class="empty">سلسلة النسب بتتسجّل هنا.</div></div>`;return}
  el.innerHTML=`<div class="panel"><div class="ph"><h3>${esc(L.title||"النسب الشريف")}</h3><span class="code">LINEAGE · AL-HUSSAINI · AL-SHARQAWI</span></div>
   <p class="quote">﴿قل لا أسألكم عليه أجرا إلا المودة في القربى﴾<small>سورة الشورى · من الآية 23</small></p>
   <div class="chain">${L.chain.map(x=>x.gap?`<div class="gap" title="${esc(x.gap)}">· · ·</div>`:`<div class="node ${x.root?"root":""} ${x.me?"me":""} ${x.prophet?"prophet":""}"><div class="card"><div class="nm2">${esc(x.n)}${x.dec?' <span class="small faint">رحمه الله</span>':""}${x.ra?' <span class="small" style="color:var(--emerald-hi)">'+esc(x.ra===true?"رضي الله عنه":x.ra)+'</span>':""}</div>${x.role?`<div class="role">${esc(x.role)}</div>`:""}${x.yr?`<div class="yr">${esc(x.yr)}</div>`:""}${[...(x.branch?[x.branch]:[]),...(x.branches||[])].map(br=>`<div class="br"><div class="brt">${esc(br.t)}</div>${br.items.map(b=>`<div class="bri">◆ ${esc(b)}</div>`).join("")}</div>`).join("")}</div><div class="dia"></div><div class="sp"></div></div>`).join("")}</div>
   ${L.notes?`<div class="pstrip" style="margin-top:18px;grid-template-columns:repeat(auto-fit,minmax(170px,1fr))">${L.notes.map(n=>`<div class="pbox"><div class="k">${esc(n.k)}</div><div class="v" style="font-size:20px;font-family:var(--f-naskh);direction:rtl">${esc(n.v)}</div><div class="s">${esc(n.s||"")}</div></div>`).join("")}</div>`:""}
   ${L.story?`<div class="panel" style="margin-top:18px;background:rgba(4,6,14,.35)"><div class="ph"><h3>${esc(L.story.t)}</h3><span class="code">${esc(L.story.code||"")}</span></div>
     <div class="alerts">${L.story.items.map(it=>`<div class="alert info"><div class="stripe" style="background:var(--gold)"></div><div><h4><span class="mono" style="color:var(--gold-hi)">${esc(it.y)}</span> · ${esc(it.t)}</h4><p>${esc(it.d)}</p></div></div>`).join("")}</div>${L.story.src?`<p class="small faint" style="margin:10px 0 0">${esc(L.story.src)}</p>`:""}</div>`:""}
   <p class="quote" style="margin-top:16px">«إنك أن تذر ورثتك أغنياء خيرٌ من أن تذرهم عالةً يتكفّفون الناس»<small>متفق عليه · البخاري 1295 · مسلم 1628</small></p>
   <p class="small faint" style="text-align:center;margin:0">الحصن ده امتداد لوقفٍ عاش 176 سنة: الثروة اللي بتتبني النهارده جزء من نفس السلسلة.</p></div>`}
function radar(){const p=S.prices;const buy=N(p.k24.buy);const g=p.global||{};const sig=[];
  if(N(g.egp24)&&ageH(g.at)<72&&p.mode!=="est"&&p.mode!=="raw"){const prem=buy/g.egp24-1;sig.push({n:"العلاوة المحلية مقابل السعر العالمي",v:(prem>=0?"+":"")+(prem*100).toFixed(1)+"%",st:prem>=0.05?"sell":prem>=0?"hold":"hold",c:prem>=0.05?"علاوة عالية: البيع مستحب":prem>=0?"محايد":"المحلي أرخص من العالمي: احتفظ",d:`العالمي ${fmt(g.egp24)} ج/جم (أونصة × دولار)`,sellish:prem>=0.05})}
  else sig.push({n:"العلاوة المحلية مقابل السعر العالمي",v:"—",st:"na",c:"محتاج تحديث",d:"بتتسحب مع أسعار الجلا"});
  const series=Object.entries(HIST.snaps||{}).map(([d,v])=>N(v.p24)).filter(x=>x>0);series.push(buy);const peak=Math.max(...series);const dd=peak?buy/peak-1:0;
  sig.push({n:"البعد عن أعلى سعر مسجّل",v:(dd*100).toFixed(1)+"%",st:dd<=-0.08?"warn":"hold",c:dd<=-0.08?"حماية أرباح: فكّر في بيع جزئي":series.length<20?"السجل لسه بيتبني":"في نطاق القمة",d:`القمة ${fmt(peak)} · ${series.length} يوم مسجّل`,sellish:dd<=-0.08});
  const sh=C.alloc.gold/(C.nw||1);sig.push({n:"وزن الذهب في الحصن",v:(sh*100).toFixed(0)+"%",st:sh>0.35?"sell":sh>0.30?"warn":"hold",c:sh>0.35?"زيادة: خفّف جزء":sh>0.30?"على الحد":"متوازن",d:"المعيار 10–30%",sellish:sh>0.35});
  const by=S.settings.goldSellBy;const dd2=by?daysBetween(C.t,by):null;sig.push({n:"موعد البيع المحتمل",v:by?dd2+" يوم":"—",st:by&&dd2<=45?"warn":"hold",c:by?(dd2<=45?"اقترب الموعد":"بعيد"):"مش محدد",d:by?dLabel(by):"الإعدادات",sellish:by&&dd2<=45});
  const n=sig.filter(x=>x.sellish).length;const verdict=n>=3?"بيع":n>=1?"بيع جزئي (الثلث)":"احتفظ";return {sig,verdict,n}}
function radarHtml(){const r=radar();return `<div class="verdict-box"><div class="small faint" style="font-family:var(--f-mono);letter-spacing:2px">SELL RADAR</div><div class="vv">${r.verdict}</div><div class="muted small">${r.n} من 4 إشارات بتميل للبيع. القرار بالإشارات مش بالإحساس.</div></div>
  <div class="radar">${r.sig.map(x=>`<div class="sig ${x.st}"><div class="k">${esc(x.n)}</div><div class="v">${esc(x.v)}</div><span class="c">${esc(x.c)}</span><div class="small faint" style="margin-top:3px">${esc(x.d)}</div></div>`).join("")}</div>`}
function openNames(){const t=$("#nm").textContent;
  $("#modalRoot").innerHTML=`<div class="scrim" id="scrim"><div class="modal wide" role="dialog" aria-label="أسماء الله الحسنى"><div class="ph"><h3>أسماء الله الحسنى</h3><button class="btn sm ghost" type="button" id="mcancel">إغلاق</button></div>
   <p class="quote" style="font-size:16px">«إن لله تسعةً وتسعين اسمًا، مائةً إلا واحدًا، من أحصاها دخل الجنة»<small>متفق عليه · البخاري 2736 · مسلم 2677</small></p>
   <div class="names99">${NAMES99.map((n,i)=>`<button type="button" data-nm99="${esc(n)}" class="${n.replace(/ّ/g,"")===t.replace(/ّ/g,"")?"today":""}"><small>${i+1}</small>${esc(n)}</button>`).join("")}</div>
   <p class="small faint" style="margin:12px 0 0">الترتيب حسب رواية الترمذي. اضغط على أي اسم يظهر في النجمة.</p></div></div>`;
  $("#mcancel").onclick=()=>$("#modalRoot").innerHTML="";$("#scrim").onclick=e=>{if(e.target.id==="scrim")$("#modalRoot").innerHTML=""}}
function renderFunds(){
  const cards=C.funds.map(f=>{const bal=f.kind==="balance",stk=f.cls==="stock";return `<div class="fund"><div class="fund-h"><div><span class="t">${esc(f.name)}</span> <span class="tag">${FCLS[f.cls]||"—"}</span> <span class="tag" style="color:${SHC[SH(f.shariah)]};border-color:${SHC[SH(f.shariah)]}55">${SHL[SH(f.shariah)]}</span></div>
     <div class="rowacts"><button class="btn sm" data-nav="${f.id}" type="button">${bal?"تحديث الرصيد":stk?"تحديث سعر السهم":"تحديث سعر الوثيقة"}</button><button class="btn sm" data-addlot="${f.id}" type="button">${bal?"+ إيداع":"+ شراء"}</button><button class="btn sm ghost" data-edit="fund:${f.id}">تعديل</button><button class="btn sm ghost danger" data-del="fund:${f.id}">حذف</button></div></div>
     <div class="fund-stats">${bal?`<div><div class="k">صافي المودَع</div><div class="v">${fmt(f.cost)}</div></div><div><div class="k">العائد السنوي المعلن</div><div class="v">${f.yield?N(f.yield).toFixed(2)+"%":"—"}</div></div><div><div class="k">عائد شهري تقريبي</div><div class="v">${f.yield?fmt(f.val*N(f.yield)/1200):"—"}</div></div>`:`<div><div class="k">${stk?"الأسهم":"الوحدات"}</div><div class="v">${fmt(f.units,2)}</div></div><div><div class="k">متوسط الشراء</div><div class="v">${fmt(f.avg,3)}</div></div><div><div class="k">${stk?"سعر السهم":"سعر الوثيقة"}</div><div class="v">${fmt(f.nav,3)}</div></div>`}<div><div class="k">القيمة</div><div class="v">${fmt(f.val)}</div></div><div><div class="k">الربح</div><div class="v">${sgn(f.pnl)} ${f.cost?pct(f.ret,1):""}</div></div></div>
     <div class="small faint" style="margin-top:6px">${f.note?esc(f.note)+" · ":""}${f.navAt?(bal?"الرصيد":"السعر")+" بتاريخ "+dLabel(f.navAt):"لم يُسجّل سعر"}${f.cagr!=null?" · عائد سنوي مركّب "+(f.cagr*100).toFixed(1)+"%":""}</div>
     ${f.lots.length?`<details class="lots"><summary>${bal?"الإيداعات":"عمليات الشراء"} (${f.lots.length})</summary><div class="tw"><table><thead><tr><th>التاريخ</th><th>${bal?"المبلغ":"الوحدات"}</th><th>${bal?"":"السعر"}</th><th>التكلفة</th><th></th></tr></thead><tbody>${f.lots.slice().sort((a,b)=>String(a.date)<String(b.date)?-1:1).map(l=>`<tr><td>${dLabel(l.date)}</td><td class="num">${fmt(l.units,2)}</td><td class="num">${bal?"":fmt(l.price,3)}</td><td class="num">${fmt(l.cost)}</td><td><button class="btn sm ghost danger" data-dellot="${f.id}:${l.id}">حذف</button></td></tr>`).join("")}</tbody></table></div></details>`:""}
   </div>`}).join("");
  $("#s-funds").innerHTML=`<div class="panel"><div class="ph"><h3>محفظة ثاندر</h3><span class="code">OP-02 · FUND DESK</span><div class="acts"><button class="btn gold sm" data-add="fund" type="button">+ صندوق / سهم</button></div></div>
   <div class="pstrip" style="grid-template-columns:repeat(3,minmax(0,1fr))"><div class="pbox"><div class="k">القيمة</div><div class="v">${fmt(C.fundsT.val)}</div></div><div class="pbox"><div class="k">المدفوع</div><div class="v">${fmt(C.fundsT.cost)}</div></div><div class="pbox"><div class="k">الربح</div><div class="v ${C.fundsT.pnl>=0?"up":"down"}">${C.fundsT.pnl>=0?"+":"−"}${fmt(Math.abs(C.fundsT.pnl))}</div></div></div>
   ${cards||`<div class="empty">ضيف صناديقك من «+ صندوق / سهم».</div>`}
   <p class="small faint" style="margin:12px 0 0">ثاندر مالوش رابط عام للأسعار، فالسعر بيتحدّث من زرار التحديث في كل كارت.</p></div>`}
function renderCerts(){
  const cards=C.certs.map(c=>{const fr=c.timeFr;const L=2*Math.PI*58;
    return `<div class="panel"><div class="ph"><h3>${esc(c.name)}</h3><span class="code">OP-03 · ${esc(c.bank||"")}</span><div class="acts"><button class="btn sm ghost" data-edit="cert:${c.id}">تعديل</button><button class="btn sm ghost danger" data-del="cert:${c.id}">حذف</button></div></div>
    <div class="cert"><div>
      <div class="cd"><div><div class="v">${c.daysToPay}</div><div class="k">يوم للصرفة (${dLabel(c.nextPay)})</div></div><div><div class="v">${c.left}</div><div class="k">صرفة متبقية</div></div><div><div class="v">${Math.max(0,Math.round(c.daysToMat/30.4))}</div><div class="k">شهر للاستحقاق</div></div></div>
      <div class="tw" style="margin-top:12px"><table><tbody>
        <tr><td class="muted">إجمالي الشهادة</td><td class="num">${fmt(c.principal)}</td></tr>
        <tr><td class="muted">نصيبك (${Math.round(N(c.share)*100)}%)</td><td class="num">${fmt(c.mine)}</td></tr>
        <tr><td class="muted">عائدك الشهري · يوم ${c.payDay}</td><td class="num">${fmt(c.monthly)}</td></tr>
        <tr><td class="muted">العائد السنوي الفعّال</td><td class="num">${(c.rate*100).toFixed(2)}%</td></tr>
        <tr><td class="muted">العائد الحقيقي بعد التضخم (${N(S.assump.infl)}%)</td><td class="num">${((c.rate-N(S.assump.infl)/100)*100).toFixed(2)}%</td></tr>
        <tr><td class="muted">عوائد متبقية لحد الاستحقاق</td><td class="num">${fmt(c.leftIncome)}</td></tr>
        <tr><td class="muted">الاستحقاق</td><td>${dLabel(c.maturity)}</td></tr>
        ${c.recv!=null?`<tr><td class="muted">عوائد استلمتها${c.recvFrom?" (من "+dLabel(c.recvFrom)+")":""}</td><td class="num">${fmt(c.recv*c.monthly)}</td></tr>`:""}
        ${c.brk!=null?`<tr><td class="muted">قيمة الكسر لنصيبك${c.breakAt?" (بتاريخ "+dLabel(c.breakAt)+")":""}</td><td class="num">${fmt(c.brk)}</td></tr><tr><td class="muted">تكلفة الكسر الآن</td><td class="num down">−${fmt(c.mine-c.brk)} (${((1-c.brk/c.mine)*100).toFixed(1)}%)</td></tr><tr><td class="muted">الاحتفاظ للاستحقاق يكسبك فوق الكسر</td><td class="num up">+${fmt(c.mine-c.brk+c.leftIncome)}</td></tr>`:""}
        ${c.trend?`<tr><td class="muted">نزول قيمة الكسر شهريًا (نصيبك)</td><td class="num down">−${fmt(Math.max(0,c.trend.dropShare))}</td></tr><tr><td class="muted">صافي الاحتفاظ شهريًا (عائد − نزول)</td><td class="num ${c.trend.net>=0?"up":"down"}">${c.trend.net>=0?"+":"−"}${fmt(Math.abs(c.trend.net))}</td></tr><tr><td class="muted">قيمة الكسر المتوقعة بعد 6 شهور (لو النزول ثابت)</td><td class="num">${fmt(Math.max(0,c.brk-c.trend.dropShare*6))}</td></tr>`:""}
      </tbody></table></div></div>
      <div><svg viewBox="0 0 150 150" class="ring" role="img" aria-label="تقدّم مدة الشهادة"><circle cx="75" cy="75" r="58" fill="none" stroke="#1B2442" stroke-width="9"/><circle cx="75" cy="75" r="58" fill="none" stroke="#6E8BD6" stroke-width="9" stroke-dasharray="${L*fr} ${L}" transform="rotate(-90 75 75)" stroke-linecap="round"/><text x="75" y="76" text-anchor="middle" style="font-family:'Cormorant Garamond',serif;font-size:30px;font-weight:600;fill:#EFE8D8">${Math.round(fr*100)}%</text><text x="75" y="94" text-anchor="middle">من المدة</text></svg></div>
    </div>
    <div style="margin-top:14px"><div class="ph" style="margin-bottom:6px"><h3 style="font-size:15px">سجل قيمة الكسر</h3><div class="acts"><button class="btn sm gold" data-brk="${c.id}" type="button">+ تسجيل قيمة اليوم</button></div></div>
     ${(c.brkHist||[]).length?`<div class="tw"><table><thead><tr><th>التاريخ</th><th>للشهادة كلها</th><th>نصيبك</th><th>التغيير</th><th></th></tr></thead><tbody>${c.brkHist.map((h,i,a)=>{const dv=i?N(h.v)-N(a[i-1].v):null;return `<tr><td>${dLabel(h.d)}</td><td class="num">${fmt(h.v)}</td><td class="num">${fmt(N(h.v)*N(c.share||1))}</td><td class="num ${dv==null?"":dv<0?"down":"up"}">${dv==null?"—":(dv<0?"−":"+")+fmt(Math.abs(dv))}</td><td><button class="btn sm ghost danger" data-delbrk="${c.id}|${h.d}" type="button">حذف</button></td></tr>`}).join("")}</tbody></table></div>`:`<p class="small muted">سجّل قيمة الكسر اللي البنك يقولها كل شهر، وهحسب لك اتجاهها وهل الاحتفاظ أحسن من الكسر.</p>`}
     ${c.trend?`<p class="small faint" style="margin:8px 0 0">${c.trend.net>=0?"العائد الشهري أكبر من نزول قيمة الكسر، فالاحتفاظ أفضل من الكسر طول ما النزول ده ثابت.":"قيمة الكسر بتنزل أسرع من العائد: كل شهر انتظار بيخسرك."} المعدل محسوب من آخر قراءتين بس.</p>`:""}</div>
    </div>`}).join("");
  const cashRows=S.cash.map(c=>`<tr><td>${esc(c.label)}</td><td class="num">${fmt(c.amount)}</td><td><div class="rowacts"><button class="btn sm ghost" data-edit="cash:${c.id}">تعديل</button><button class="btn sm ghost danger" data-del="cash:${c.id}">حذف</button></div></td></tr>`).join("");
  $("#s-certs").innerHTML=`<div class="grid">${cards||`<div class="panel"><div class="empty">مفيش شهادات.</div></div>`}
   <div class="panel"><div class="ph"><h3>النقد والحسابات</h3><span class="code">OP-03B · CASH</span><div class="acts"><button class="btn sm" data-add="cert" type="button">+ شهادة</button><button class="btn gold sm" data-add="cash" type="button">+ رصيد نقدي</button></div></div>
   ${cashRows?`<div class="tw"><table><tbody>${cashRows}<tr class="tot"><td>الإجمالي</td><td class="num">${fmt(C.cashT)}</td><td></td></tr></tbody></table></div>`:`<div class="empty">سجّل أرصدة الحسابات أو الكاش عشان تكمل صورة السيولة.</div>`}</div></div>`}
function renderIncome(){const ex=(S.income.extras||[]).slice().sort((a,b)=>String(b.date).localeCompare(String(a.date)));
  const plan=C.surplus!=null&&C.surplus>0?Object.keys(CLASS).map(k=>`<tr><td><span class="dot" style="background:${CLASS[k].c}"></span>${CLASS[k].n}</td><td class="num">${S.targets[k]}%</td><td class="num">${fmt(C.surplus*N(S.targets[k])/100)}</td></tr>`).join(""):"";
  $("#s-income").innerHTML=`<div class="grid g2">
   <div class="panel" style="grid-column:1/-1">${goalPanel()}</div>
   <div class="panel"><div class="ph"><h3>التدفق الشهري</h3><span class="code">OP-04 · CASHFLOW</span><div class="acts"><button class="btn sm" data-settings type="button">تعديل المرتب والمصروف</button></div></div>
    <div class="tw"><table><tbody>
     <tr><td class="muted">المرتب الشهري</td><td class="num">${fmt(C.salary)}</td></tr>
     <tr><td class="muted">عوائد الشهادات</td><td class="num">${fmt(C.certsT.monthly)}</td></tr>
     <tr class="tot"><td>إجمالي الداخل النقدي</td><td class="num">${fmt(C.inflow)}</td></tr>
     <tr><td class="muted">عائد السيولة (بيتراكم داخل الصندوق)</td><td class="num">${fmt(C.yieldMonthly)}</td></tr>
     <tr><td class="muted">المصروف الشهري</td><td class="num">${C.exp?fmt(C.exp):"غير مسجّل"}</td></tr>
     <tr class="tot"><td>الفائض للاستثمار</td><td class="num">${C.surplus!=null?fmt(C.surplus):"—"}</td></tr>
     <tr><td class="muted">دخل إضافي ${C.t.slice(0,4)}</td><td class="num">${fmt(C.extrasYr)}</td></tr>
     <tr><td class="muted">الدخل السلبي ÷ المرتب</td><td class="num">${C.salary?(C.passive/C.salary*100).toFixed(0)+"%":"—"}</td></tr>
    </tbody></table></div>
    ${plan?`<h4 style="font-family:var(--f-kufi);font-weight:500;margin:16px 0 6px;color:var(--gold-hi)">أمر التوزيع الشهري للفائض</h4><div class="tw"><table><thead><tr><th>الوجهة</th><th>النسبة</th><th>المبلغ</th></tr></thead><tbody>${plan}</tbody></table></div>`:`<p class="small muted" style="margin-top:12px">سجّل مصروفك الشهري وهيطلع أمر توزيع شهري للفائض على أهدافك.</p>`}
   </div>
   <div class="panel"><div class="ph"><h3>الدخل الإضافي</h3><span class="code">BONUS · PROFIT SHARE</span><div class="acts"><button class="btn gold sm" data-add="extra" type="button">+ دخل إضافي</button></div></div>
    ${ex.length?`<div class="tw"><table><thead><tr><th>البيان</th><th>التاريخ</th><th>المبلغ</th><th></th></tr></thead><tbody>${ex.map(e=>`<tr><td>${esc(e.label)}</td><td>${dLabel(e.date)}</td><td class="num">${fmt(e.amount)}</td><td><div class="rowacts"><button class="btn sm ghost" data-edit="extra:${e.id}">تعديل</button><button class="btn sm ghost danger" data-del="extra:${e.id}">حذف</button></div></td></tr>`).join("")}</tbody></table></div>`:`<div class="empty">سجّل الأرباح السنوية والمكافأة (مارس) وأي دخل غير ثابت، عشان تعرف راح فين.</div>`}
    <div class="alert info" style="margin-top:12px"><div class="stripe"></div><div><h4>قاعدة الرزق غير المتوقع</h4><p>أي فلوس فوق المرتب: 60% استثمار حسب أهدافك، 25% احتياطي، 15% لنفسك. اللي بيتقسم قبل ما يوصل الحساب مبيضيعش.</p></div></div>
   </div></div>`}
function goalPanel(){const G=goalCfg();const T=C.goalT;
  const locked=C.certsT.val;const sources=[["نقد",C.cashT],["سيولة (كلاودز)",C.funds.filter(f=>f.cls==="liquid").reduce((s,f)=>s+f.val,0)],["ذهب عيني",C.goldT.val],["صناديق وأسهم",C.funds.filter(f=>f.cls!=="liquid").reduce((s,f)=>s+f.val,0)]];
  const avail=sources.reduce((s,x)=>s+x[1],0)-C.debtT;const pr=clamp(avail/(T||1));const pace=(C.surplus||0)+C.yieldMonthly;const gap=Math.max(0,T-avail);const months=pace>0?Math.ceil(gap/pace):null;
  let rem=T;const wf=sources.map(([n,v])=>{const use=Math.min(v,Math.max(0,rem));rem-=use;return [n,use,v]}).filter(x=>x[1]>0);const colors=["#9AA0B4","#6E8BD6","#C9A24E","#2F8F63"];
  const dm=n=>{const d=new Date(dParse(C.t));d.setUTCMonth(d.getUTCMonth()+n);return dLabel(d.toISOString().slice(0,10))};
  const c0=C.certs[0];const mMat=c0?Math.max(0,Math.round(c0.daysToMat/30.4)):0;const paths=[];
  if(T){paths.push(["من غير ما تلمس الشهادة",avail>=T?"جاهز الآن":(pace>0?dm(months)+" · بعد "+months+" شهر":"محتاج فائض شهري"),avail>=T?"بدون أي تكلفة":"بدون خسارة؛ الشهادة تكمل عوائدها",avail>=T||pace>0]);
    if(c0&&c0.brk!=null){const after=avail+c0.brk;const loss=c0.mine-c0.brk;const mB=after>=T?0:(pace>0?Math.ceil((T-after)/pace):null);paths.push(["لو كسرت الشهادة الآن",mB===0?"جاهز الآن":(mB!=null?dm(mB)+" · بعد "+mB+" شهر":"—"),"تكلفة "+fmt(loss)+" ج ("+((loss/c0.mine)*100).toFixed(0)+"% من نصيبك) وبتخسر "+fmt(c0.leftIncome)+" ج عوائد",true])}
    if(c0){const atMat=avail+(pace>0?pace*mMat:0)+c0.mine;paths.push(["الانتظار لاستحقاق الشهادة ("+dLabel(c0.maturity)+")",atMat>=T?"مغطّى · فايض "+fmt(atMat-T)+" ج":"ناقص "+fmt(T-atMat)+" ج",
      "بافتراض إن البنك يرجّع نصيبك "+fmt(c0.mine)+" ج + ادخارك "+fmt(pace>0?pace*mMat:0)+" ج",true])}}
  const mq=MARRIAGE[(+C.t.slice(8,10))%MARRIAGE.length];
  const seg=Object.entries(SCEN).map(([k,v])=>`<button type="button" data-scen="${k}" class="${G.scenario===k?"on":""}">${v.n}</button>`).join("")+`<button type="button" data-scen="custom" class="${G.scenario==="custom"?"on":""}">مخصص</button>`;
  return `<div class="ph"><h3>مهمة الجواز</h3><span class="code">MISSION · MARRIAGE (EXCL. APARTMENT)</span><div class="acts"><span class="seg">${seg}</span><button class="btn sm" data-goal type="button">تعديل البنود</button></div></div>
   <div class="quote">${mq.k==="v"?"﴿"+esc(mq.t)+"﴾":"«"+esc(mq.t)+"»"}<small>${esc(mq.a)} · ${esc(mq.b)}</small></div>
   <div class="verdict-box"><div class="vv">${pr>=1?"جاهز ماليًا الآن":pr>=0.75?"قريب جدًا":"في الطريق"}</div><div class="muted small">${pr>=1?`أصولك المتاحة (بدون الشهادة المقفولة) تغطي التكلفة التقديرية ${(avail/T).toFixed(1)} مرة.`:`فاضل ${fmt(gap)} ج، يعني حوالي ${months} شهر بمعدل ادخارك الحالي.`}</div></div>
   ${paths.length?`<div class="small muted" style="margin:10px 0 4px">طرق الوصول لتمويل الجواز:</div><div class="tw"><table><thead><tr><th>الطريق</th><th>متى أو كام</th><th>التكلفة والافتراض</th></tr></thead><tbody>${paths.map(x=>`<tr><td>${esc(x[0])}</td><td class="num">${esc(x[1])}</td><td class="small faint">${esc(x[2])}</td></tr>`).join("")}</tbody></table></div>`:""}
   <div class="pstrip"><div class="pbox"><div class="k">التكلفة التقديرية (${G.scenario==="custom"?"مخصص":SCEN[G.scenario].n})</div><div class="v">${fmt(T)}</div><div class="s">شامل احتياطي ${G.cont}%</div></div>
    <div class="pbox"><div class="k">الشبكة: ${fmt(G.shabka)} جم ع21</div><div class="v">${fmt(C.shabkaV)}</div><div class="s">بسعر الجلا اللحظي ${fmt(C.p21s)}/جم</div></div>
    <div class="pbox"><div class="k">المتاح بدون الشهادة</div><div class="v">${fmt(avail)}</div><div class="s">الشهادة ${fmt(locked)} مقفولة لحد ${C.certs[0]?dLabel(C.certs[0].maturity):"—"}</div></div>
    <div class="pbox"><div class="k">نسبة التغطية</div><div class="v">${(avail/(T||1)*100).toFixed(0)}%</div><div class="s">ادخار شهري ${fmt(pace)}</div></div></div>
   <div class="small muted" style="margin-bottom:4px">لو احتجت الفلوس النهارده، تتسحب منين وبالترتيب ده:</div>
   <div class="stack" style="height:16px">${wf.map((w,i)=>`<i style="width:${w[1]/T*100}%;background:${colors[sources.findIndex(x=>x[0]===w[0])]}" title="${esc(w[0])}"></i>`).join("")}</div>
   <div class="legend">${wf.map(w=>`<span><span class="dot" style="background:${colors[sources.findIndex(x=>x[0]===w[0])]}"></span>${esc(w[0])} <b>${fmt(w[1])}</b></span>`).join("")}</div>
   <div class="tw" style="margin-top:12px"><table><thead><tr><th>البند</th><th>التقدير</th><th>من الإجمالي</th></tr></thead><tbody>
    <tr><td>الشبكة (${fmt(G.shabka)} جم ع21 بالسعر اللحظي)</td><td class="num">${fmt(C.shabkaV)}</td><td class="num faint">${(C.shabkaV/T*100).toFixed(0)}%</td></tr>
    ${GOAL_ITEMS.filter(([k])=>N(G.v[k])).map(([k,l])=>`<tr><td>${l}</td><td class="num">${fmt(G.v[k])}</td><td class="num faint">${(N(G.v[k])/T*100).toFixed(0)}%</td></tr>`).join("")}
    <tr><td class="muted">احتياطي ${G.cont}%</td><td class="num">${fmt(T-C.goalSub)}</td><td></td></tr>
    <tr class="tot"><td>الإجمالي</td><td class="num">${fmt(T)}</td><td></td></tr></tbody></table></div>
   <p class="small faint" style="margin:8px 0 0">السيناريوهات تقديرات أسعار أكتوبر 2026 (أساسها تقارير السوق: أثاث من 90 ألف، أجهزة 60–120 ألف، شبكة 15 جم للحد الأدنى). الشقة نفسها مستبعدة. اختار «مخصص» وعدّل أي بند لما تبدأ تسأل على أسعار حقيقية.</p>`}
function renderIntel(){const A=rules(C);const el=$("#s-intel");
  el.innerHTML=`<div class="grid g-ov"><div class="panel"><div class="ph"><h3>كل الإشارات</h3><span class="code">SIGNALS</span></div><div class="alerts">${A.map(alertHtml).join("")}</div></div>
   <div class="panel"><div class="ph"><h3>التقرير الميداني</h3><span class="code">OP-05 · LOCAL ADVISOR</span><div class="acts"><button class="btn gold sm" id="btnBrief" type="button">اطلع التقرير</button></div></div>
    <div class="report" id="report"><span class="stamp">CLASSIFIED</span><p class="muted" style="margin-top:20px">تقرير بيتحسب على جهازك من أرقامك الحالية وقواعد الحصن (من غير إنترنت ولا ذكاء اصطناعي): الحكم، الخطر، الثغرات، ونقاط القوة.</p></div>
    <p class="small faint" style="margin:8px 0 0">تحليل مبني على قواعد ثابتة وأرقامك، مش توصية مرخّصة؛ القرار النهائي ليك.</p></div></div>`;
  $("#btnBrief").onclick=brief}
function brief(){const box=$("#report");const sc=score(C);const A=rules(C);
  const li=(a,k)=>a.map(x=>`<li><strong>${esc(x.t)}</strong> — ${esc(k?(x.a||x.b):x.b)}</li>`).join("");
  const crit=A.filter(a=>a.lv==="critical"),warn=A.filter(a=>a.lv==="warn"),good=A.filter(a=>a.lv==="good");
  const ext=(window.HISN_EXT&&HISN_EXT.briefHtml&&HISN_EXT.briefHtml())||"";
  box.innerHTML=`<span class="stamp">CLASSIFIED</span><h4>الحكم</h4><p>درجة الحصن <strong>${sc.total}/100</strong> (${sc.verdict}). صافي الثروة <strong>${fmt(C.nw)}</strong> ج، ودخلك السلبي <strong>${fmt(C.passive)}</strong> ج/شهر.</p>
   ${crit.length?`<h4>خطر الآن</h4><ul>${li(crit,1)}</ul>`:""}${warn.length?`<h4>ثغرات تحتاج تصرف</h4><ul>${li(warn,1)}</ul>`:""}${good.length?`<h4>نقاط القوة</h4><ul>${li(good,0)}</ul>`:""}${ext}`}

/* zakat — Dar al-Ifta al-Misriyya methodology */
const ZM={market:"القيمة السوقية × 2.5%",profit:"على الأرباح الموزعة فقط",none:"مستبعد"};
function zDefaults(){const z=S.zakat||{};return {hawlStart:z.hawlStart||"",debts:N(z.debts),certReturnsSpent:z.certReturnsSpent!==false,methods:z.methods||{},dividends:z.dividends||{},paid:z.paid||[],nisabKarat:z.nisabKarat||"21"}}
function addHijriYears(g,n){const d=dParse(g);if(!d)return null;d.setUTCDate(d.getUTCDate()+354*n);return d.toISOString().slice(0,10)}
function zakatCalc(){const Z=zDefaults();const rows=[];
  const p21=N(S.prices.k21.buy)||N(S.prices.k24.buy)*21/24;const nisab=85*p21;
  C.gold.forEach(g=>rows.push({grp:"ذهب الادخار",n:g.name+" · "+fmt(g.grams,2)+" جم ع"+g.karat,base:g.val,m:"market"}));
  C.funds.forEach(f=>{const def=f.cls==="stock"?"profit":"market";const m=Z.methods[f.id]||def;
    const base=m==="market"?f.val:m==="profit"?N(Z.dividends[f.id]):0;rows.push({grp:f.kind==="balance"?"سيولة":f.cls==="stock"?"أسهم":"صناديق",n:f.name,base,m,id:f.id,full:f.val})});
  C.certs.forEach(c=>rows.push({grp:"شهادات",n:c.name+" (نصيبك)",base:c.mine,m:"market"}));
  S.cash.forEach(c=>rows.push({grp:"نقد",n:c.label,base:N(c.amount),m:"market"}));
  const gross=rows.reduce((s,r)=>s+(r.m==="none"?0:r.base),0);Z.debts=N(Z.debts)+C.debtT;const net=Math.max(0,gross-Z.debts);
  const due=net>=nisab?net*0.025:0;
  let next=null,daysLeft=null;if(Z.hawlStart){let n=1;next=addHijriYears(Z.hawlStart,n);while(next&&next<C.t){n++;next=addHijriYears(Z.hawlStart,n)}daysLeft=daysBetween(C.t,next)}
  return {Z,rows,nisab,p21,gross,net,due,next,daysLeft}}
function renderZakat(){const q=zakatCalc();const Z=q.Z;
  const hj=d=>{try{return new Intl.DateTimeFormat("ar-SA-u-ca-islamic-umalqura-nu-latn",{timeZone:"UTC",day:"numeric",month:"long",year:"numeric"}).format(dParse(d))}catch(e){return ""}};
  const rows=q.rows.map(r=>`<tr><td class="muted">${esc(r.grp)}</td><td>${esc(r.n)}</td><td>${r.id?`<select data-zm="${r.id}" id="zm-${r.id}" aria-label="طريقة الاحتساب">${Object.entries(ZM).map(([k,v])=>`<option value="${k}" ${r.m===k?"selected":""}>${v}</option>`).join("")}</select>`:`<span class="small faint">${ZM.market}</span>`}</td>
   <td class="num">${r.m==="profit"?`<input type="number" step="any" data-zdiv="${r.id}" id="zd-${r.id}" value="${esc(Z.dividends[r.id]??"")}" placeholder="الأرباح المستلمة" style="max-width:130px">`:fmt(r.m==="none"?0:r.base)}</td><td class="num">${fmt((r.m==="none"?0:r.base)*0.025)}</td></tr>`).join("");
  const paid=(Z.paid||[]).slice().sort((a,b)=>String(b.date).localeCompare(String(a.date)));
  $("#s-zakat").innerHTML=`<div class="grid">
   <div class="panel"><div class="ph"><h3>زكاة المال</h3><span class="code">OP-07 · ZAKAT</span><div class="acts"><button class="btn sm" data-zset type="button">موعد الحول والديون</button><button class="btn gold sm" data-zpay type="button">+ سجّل إخراج زكاة</button></div></div>
    <div class="pstrip">
      <div class="pbox"><div class="k">النصاب (85 جم ذهب ع21)</div><div class="v">${fmt(q.nisab)}</div><div class="s">بسعر ع21 ${fmt(q.p21)} من الجلا</div></div>
      <div class="pbox"><div class="k">الوعاء الزكوي</div><div class="v">${fmt(q.net)}</div><div class="s">${Z.debts?"بعد خصم ديون "+fmt(Z.debts):"لا ديون مسجلة"}</div></div>
      <div class="pbox" style="border-color:var(--gold-dim)"><div class="k">الزكاة الواجبة (2.5%)</div><div class="v">${fmt(q.due)}</div><div class="s">${q.net>=q.nisab?"المال بلغ النصاب":"لم يبلغ النصاب"}</div></div>
      <div class="pbox"><div class="k">موعد الحول القادم</div><div class="v" style="font-size:22px">${q.next?q.daysLeft+" يوم":"—"}</div><div class="s">${q.next?hj(q.next)+" هـ · "+dLabel(q.next):"حدّد تاريخ بداية الحول"}</div></div>
    </div>
    <div class="tw"><table><thead><tr><th>البند</th><th>الأصل</th><th>طريقة الاحتساب</th><th>الوعاء</th><th>الزكاة</th></tr></thead><tbody>${rows}
     ${Z.debts?`<tr><td class="muted">خصم</td><td>ديون حالّة عليك</td><td></td><td class="num down">−${fmt(Z.debts)}</td><td></td></tr>`:""}
     <tr class="tot"><td>الإجمالي</td><td></td><td></td><td class="num">${fmt(q.net)}</td><td class="num">${fmt(q.due)}</td></tr></tbody></table></div>
    ${paid.length?`<h4 style="font-family:var(--f-kufi);font-weight:500;color:var(--gold-hi);margin:16px 0 6px">سجل الإخراج</h4><div class="tw"><table><tbody>${paid.map(p=>`<tr><td>${dLabel(p.date)} · ${hj(p.date)} هـ</td><td class="num">${fmt(p.amount)}</td><td>${esc(p.note||"")}</td><td><button class="btn sm ghost danger" data-zdel="${p.id}">حذف</button></td></tr>`).join("")}</tbody></table></div>`:""}
   </div>
   <div class="panel"><div class="ph"><h3>المنهج الشرعي المطبّق</h3><span class="code">DAR AL-IFTA · EGYPT</span></div>
    <div class="alerts">
     <div class="alert info"><div class="stripe"></div><div><h4>النصاب والنسبة</h4><p>قيمة 85 جرامًا من الذهب عيار 21، والزكاة ربع العُشر (2.5%) إذا بلغ المال النصاب وحال عليه الحول الهجري، وكان فائضًا عن الحاجات الأصلية وخاليًا من الدين.</p></div></div>
     <div class="alert info"><div class="stripe"></div><div><h4>الذهب</h4><p>السبائك والجنيهات المدّخرة تُزكّى بقيمتها يوم وجوب الزكاة (محسوبة هنا بسعر بيعك للجلا). ذهب الزينة المعتاد لا زكاة فيه، فلا تُدخله هنا.</p></div></div>
     <div class="alert info"><div class="stripe"></div><div><h4>الشهادات البنكية</h4><p>الزكاة على أصل الشهادة (نصيبك فقط) بنسبة 2.5%. العائد الذي تنفقه خلال العام لا زكاة فيه؛ وما تضمّه منه إلى مالك يُزكّى معه (وهو داخل تلقائيًا لو استثمرته في ثاندر).</p></div></div>
     <div class="alert info"><div class="stripe"></div><div><h4>الأسهم والصناديق</h4><p>أسهم الشركات التجارية وصناديق الاستثمار: بالقيمة السوقية مع الأرباح × 2.5%. أسهم الشركات الصناعية والإنتاجية (مثل سيدي كرير): الزكاة في أرباحها لا في أصلها. ومن يحتاج العائد لنفقته الضرورية يجوز له إخراج 10% من العائد عند قبضه.</p></div></div>
    </div>
    <p class="small faint" style="margin:12px 0 0">الحاسبة تطبّق فتاوى دار الإفتاء المصرية المنشورة. الحول يُحسب هنا بـ 354 يومًا (سنة قمرية تقريبية)، فراجِع اليوم الهجري الدقيق. للحالات الخاصة اسأل دار الإفتاء مباشرة (الخط الساخن 107).</p>
   </div></div>`;
  $("#s-zakat").querySelectorAll("[data-zm]").forEach(el=>el.onchange=()=>{S.zakat=Object.assign(zDefaults(),S.zakat||{});S.zakat.methods={...(S.zakat.methods||{}),[el.dataset.zm]:el.value};commit()});
  $("#s-zakat").querySelectorAll("[data-zdiv]").forEach(el=>el.onchange=()=>{S.zakat=Object.assign(zDefaults(),S.zakat||{});S.zakat.dividends={...(S.zakat.dividends||{}),[el.dataset.zdiv]:N(el.value)};commit()})}

/* projection */
function project(){const A=S.assump;const yrs=Math.max(1,Math.min(25,N(A.years)));const m=N(A.monthly);const bal={...C.alloc};const tg=S.targets;const tsum=Object.values(tg).reduce((s,x)=>s+N(x),0)||1;
  const certMat=C.certs.length?Math.max(0,Math.round(Math.min(...C.certs.map(c=>c.daysToMat))/30.4)):0;const rate=k=>N(A[k])/100/12;const infl=N(A.infl)/100/12;const pts=[{m:0,nom:C.nw,real:C.nw}];
  for(let i=1;i<=yrs*12;i++){Object.keys(bal).forEach(k=>{if(!(k==="fixed"&&i<=certMat&&C.certs.length))bal[k]*=1+rate(k)});
    if(i===certMat+1&&C.certs.length){bal.fixed-=C.certsT.val;bal.liquid+=C.certsT.val}
    const contrib=m+(i<=certMat?C.certsT.monthly:0);Object.keys(bal).forEach(k=>bal[k]+=contrib*N(tg[k])/tsum);
    const nom=Object.values(bal).reduce((s,x)=>s+x,0);pts.push({m:i,nom,real:nom/Math.pow(1+infl,i)})}return pts}
function renderFuture(){const A=S.assump;const pts=project();const last=pts[pts.length-1];
  const W=900,H=240,pl=8,pr=74,pt=12,pb=26;const mx=Math.max(...pts.map(p=>p.nom))*1.05;const X=m=>pl+m/(pts.length-1)*(W-pl-pr),Y=v=>pt+(1-v/mx)*(H-pt-pb);
  const path=k=>pts.map((p,i)=>(i?"L":"M")+X(p.m).toFixed(1)+" "+Y(p[k]).toFixed(1)).join("");
  let grid="";for(let i=0;i<=4;i++){const v=mx*i/4;grid+=`<line x1="${pl}" x2="${W-pr}" y1="${Y(v)}" y2="${Y(v)}" stroke="#1B2442"/><text x="${W-pr+6}" y="${Y(v)+3}">${(v/1e6).toFixed(1)}M</text>`}
  let xt="";const yrs=(pts.length-1)/12;for(let y=0;y<=yrs;y+=yrs>10?5:yrs>5?2:1)xt+=`<text x="${X(y*12)}" y="${H-8}" text-anchor="middle">${+C.t.slice(0,4)+y}</text>`;
  const miles=[2e6,3e6,5e6,10e6].filter(v=>v>C.nw).map(v=>{const p=pts.find(p=>p.nom>=v);if(!p)return "";const d=dParse(C.t);d.setUTCMonth(d.getUTCMonth()+p.m);return `<tr><td>${fmt(v/1e6)} مليون</td><td>${d.toLocaleDateString("ar-EG-u-nu-latn",{timeZone:"UTC",month:"long",year:"numeric"})}</td><td class="num">${(p.m/12).toFixed(1)} سنة</td></tr>`}).join("");
  const inp=(k,l)=>`<label><span>${l}</span><input type="number" step="any" data-as="${k}" id="as-${k}" value="${esc(A[k])}"></label>`;
  $("#s-future").innerHTML=`<div class="grid g-ov">
   <div class="panel"><div class="ph"><h3>افتراضات الخريطة</h3><span class="code">ASSUMPTIONS</span></div>
    <div class="fields">${inp("monthly","استثمار شهري إضافي (ج)")}${inp("years","عدد السنين")}${inp("gold","عائد الذهب السنوي %")}${inp("growth","عائد الأسهم السنوي %")}${inp("liquid","عائد أسواق النقد %")}${inp("fixed","عائد الدخل الثابت بعد الشهادة %")}${inp("infl","التضخم السنوي %")}</div>
    <p class="small faint" style="margin:10px 0 0">افتراضات مش توقعات. عوائد الشهادة بتتضاف للاستثمار الشهري لحد استحقاقها، وبعدها أصلها بيتحوّل لسيولة. المساهمات بتتوزع على أهدافك.</p></div>
   <div class="panel"><div class="ph"><h3>خريطة النمو</h3><span class="code">TRAJECTORY · ${yrs} YRS</span></div>
    <div class="pstrip" style="grid-template-columns:repeat(2,minmax(0,1fr))"><div class="pbox"><div class="k">بعد ${yrs} سنة (اسمي)</div><div class="v">${fmt(last.nom)}</div></div><div class="pbox"><div class="k">بقوة شراء النهارده</div><div class="v">${fmt(last.real)}</div></div></div>
    <div class="tw"><svg viewBox="0 0 ${W} ${H}" style="width:100%;min-width:520px;height:auto;direction:ltr">${grid}${xt}<path d="${path("nom")}" fill="none" stroke="#EBD08C" stroke-width="2.2"/><path d="${path("real")}" fill="none" stroke="#62C597" stroke-width="2" stroke-dasharray="5 4"/><circle cx="${X(last.m)}" cy="${Y(last.nom)}" r="4.5" fill="#F6E7BE"/></svg></div>
    <div class="legend" style="margin-top:8px"><span><span class="dot" style="background:#EBD08C"></span>القيمة الاسمية</span><span><span class="dot" style="background:#62C597"></span>بعد خصم التضخم</span></div>
    ${miles?`<h4 style="font-family:var(--f-kufi);font-weight:500;color:var(--gold-hi);margin:14px 0 6px">محطات الطريق</h4><div class="tw"><table><tbody>${miles}</tbody></table></div>`:""}
   </div></div>`;
  $("#s-future").querySelectorAll("[data-as]").forEach(i=>i.onchange=()=>{S.assump[i.dataset.as]=N(i.value);commit(false);renderFuture()})}

/* modal editor */
const FORMS={
 gold:{t:"قطعة ذهب",f:[["name","الوصف (سبيكة 10 جم، جنيه…)","text",1],["karat","العيار","select",0,[["24","24"],["21","21"],["18","18"]]],["grams","الوزن بالجرام","number"],["ppg","سعر الشراء للجرام (شامل المصنعية)","number"],["date","تاريخ الشراء","date"],["note","ملاحظة","text",1]]},
 fund:{t:"صندوق / سهم",f:[["name","الاسم","text",1],["cls","النوع","select",0,Object.entries(FCLS)],["shariah","التوافق الشرعي","select",0,Object.entries(SHL)],["kind","طريقة التتبع","select",0,[["","وثائق/أسهم بسعر"],["balance","رصيد (زي كلاودز)"]]],["yield","العائد السنوي المعلن % (للرصيد)","number"],["nav","السعر / الرصيد الحالي","number"],["navAt","تاريخ السعر","date"],["custodian","مكانه (ثاندر، بنك…)","text"],["note","ملاحظة","text",1]]},
 lot:{t:"عملية شراء",f:[["units","عدد الوحدات / مبلغ الإيداع","number"],["price","سعر الوحدة عند الشراء (1 للإيداع)","number"],["date","التاريخ","date"]]},
 cert:{t:"شهادة",f:[["name","اسم الشهادة","text"],["bank","البنك","text"],["principal","إجمالي المبلغ","number"],["share","نصيبك (1 = كاملة، 0.5 = النص)","number"],["monthly","عائدك الشهري","number"],["payDay","يوم الصرف من الشهر","number"],["issue","تاريخ الإصدار","date"],["maturity","تاريخ الاستحقاق","date"],["recvFrom","بداية استلامك للعائد","date"],["breakTotal","قيمة الكسر الإجمالية (لو اتكسرت)","number"],["breakAt","تاريخ عرض الكسر","date"],["shariah","التوافق الشرعي","select",0,Object.entries(SHL)]]},
 brk:{t:"تسجيل قيمة كسر جديدة",f:[["d","التاريخ","date"],["v","قيمة الكسر للشهادة كلها (الرقم اللي البنك قاله)","number"]]},
 goal:{t:"بنود مهمة الجواز",f:[["shabka","وزن الشبكة (جرام ع21)","number"],...GOAL_ITEMS.map(([k,l])=>[k,l,"number"]),["cont","نسبة الاحتياطي %","number"]]},
 debt:{t:"دين / التزام",f:[["label","الاسم أو البيان","text",1],["dir","النوع","select",0,[["me","عليّ (التزام)"],["owed","ليّ (مستحق عند حد)"]]],["amount","المبلغ المتبقي","number"],["due","موعد السداد","date"],["rate","الفائدة الشهرية % (لو فيه)","number"],["limit","الحد الائتماني (للكروت)","number"],["note","ملاحظة","text",1]]},
 cash:{t:"حساب",f:[["label","اسم الحساب","text",1],["type","النوع","select",0,[["cash","كاش"],["bank","حساب بنكي"],["wallet","محفظة إلكترونية"],["savings","مدخرات"]]],["amount","الرصيد الحالي","number"]]},
 extra:{t:"دخل إضافي",f:[["label","البيان (أرباح، مكافأة…)","text",1],["amount","المبلغ","number"],["date","التاريخ","date"]]},
 nav:{t:"تحديث السعر",f:[["nav","السعر / الرصيد","number"],["navAt","بتاريخ","date"]]},
 price:{t:"سعر الذهب يدوي",f:[["k24buy","ع24 · سعر بيعك (Buy)","number"],["k24sell","ع24 · سعر الجلا للبيع (Sell)","number"],["k21buy","ع21 · سعر بيعك (Buy)","number"],["k21sell","ع21 · سعر الجلا للبيع (Sell)","number"]]},
 zset:{t:"إعدادات الزكاة",f:[["hawlStart","تاريخ بداية الحول (ميلادي)","date"],["debts","ديون حالّة عليك (ج)","number"]]},
 zpay:{t:"إخراج زكاة",f:[["amount","المبلغ","number"],["date","التاريخ","date"],["note","ملاحظة (الجهة…)","text",1]]},
 settings:{t:"الإعدادات",f:[["salary","المرتب الشهري","number"],["expenses","المصروف الشهري (يدوي، يُستخدم لو مفيش معاملات كفاية)","number"],["tgold","هدف الذهب %","number"],["tfixed","هدف الدخل الثابت %","number"],["tliquid","هدف السيولة %","number"],["tgrowth","هدف النمو (أسهم) %","number"],["infl","التضخم السنوي %","number"],["streak","بداية سلسلة الاستثمار (YYYY-MM)","text"],["goldSellBy","موعد البيع المحتمل للذهب","date"],["auto","تحديث سعر الذهب تلقائيًا","select",1,[["1","نعم (لو آخر سعر أقدم من ساعة)"],["","لا"]]],["autoexp","مصدر المصروف الشهري","select",1,[["1","تلقائي من متوسط معاملاتك (لو متاح)"],["","الرقم اليدوي بس"]]]]}
};
function openForm(kind,vals,onSave,title){const F=FORMS[kind];
  $("#modalRoot").innerHTML=`<div class="scrim" id="scrim"><form class="modal" id="mform"><h3>${esc(title||F.t)}</h3><div class="fields">${F.f.map(([k,l,t,full,opts])=>`<label class="${full?"full":""}"><span>${l}</span>${t==="select"?`<select id="f-${k}" name="${k}">${opts.map(([v,n])=>`<option value="${esc(v)}" ${String(vals[k]??"")===String(v)?"selected":""}>${esc(n)}</option>`).join("")}</select>`:`<input id="f-${k}" name="${k}" type="${t}" ${t==="number"?'step="any"':""} value="${esc(vals[k]??"")}">`}</label>`).join("")}</div>
   <div class="mfoot"><button class="btn gold" type="submit">حفظ</button><button class="btn ghost" type="button" id="mcancel">إلغاء</button><span class="small down" id="merr"></span></div></form></div>`;
  const close=()=>$("#modalRoot").innerHTML="";$("#mcancel").onclick=close;$("#scrim").onclick=e=>{if(e.target.id==="scrim")close()};
  $("#mform").onsubmit=e=>{e.preventDefault();const o={};F.f.forEach(([k,,t])=>{const v=$("#f-"+k).value;o[k]=t==="number"?(v===""?"":N(v)):v});const err=onSave(o);if(err){$("#merr").textContent=err;return}close()};
  setTimeout(()=>$("#mform input,#mform select")?.focus(),30)}
const LIST={gold:"gold",fund:"funds",cert:"certs",cash:"cash",debt:"debts"};
function listFor(kind){if(kind==="extra")return S.income.extras;if(kind==="debt"&&!Array.isArray(S.debts))S.debts=[];return S[LIST[kind]]}
function add(kind){const t=today();const defs={gold:{karat:"24",date:t},fund:{cls:"growth",navAt:t,custodian:"ثاندر"},cert:{share:1,payDay:1},cash:{type:"cash"},debt:{dir:"me"},extra:{date:t}}[kind];
  openForm(kind,defs,o=>{if((kind==="gold"||kind==="fund")&&!String(o.name||"").trim())return "اكتب الاسم";const item={id:uid(),...o};if(kind==="fund"){item.lots=[]}listFor(kind).push(item);commit()})}
function edit(kind,id){const it=listFor(kind).find(x=>x.id===id);if(!it)return;const vals={...it};if(kind==="fund")vals.shariah=SH(it.shariah);if(kind==="cert")vals.shariah=SH(it.shariah||"contested");
  openForm(kind,vals,o=>{Object.assign(it,o);if(kind==="cert"){it.issueEst=false;if(N(it.breakTotal)&&it.breakAt){it.brkHist=(it.brkHist||[]).filter(h=>h.d!==it.breakAt);it.brkHist.push({d:it.breakAt,v:N(it.breakTotal)});it.brkHist.sort((a,b)=>String(a.d).localeCompare(String(b.d)))}}commit()},"تعديل: "+FORMS[kind].t)}
let armed=null;
function arm(btn){if(armed!==btn){if(armed)armed.textContent="حذف";armed=btn;btn.textContent="تأكيد؟";setTimeout(()=>{if(armed===btn){btn.textContent="حذف";armed=null}},3000);return false}armed=null;return true}
function del(kind,id,btn){if(!arm(btn))return;const L=listFor(kind);const i=L.findIndex(x=>x.id===id);if(i>=0)L.splice(i,1);commit()}

/* persistence */
function setSync(cls,t){const c=$("#syncChip");if(!c)return;c.className="chip "+cls;c.querySelector("span").textContent=t}
function snapshot(){const d=C.t;const v={p24:N(S.prices.k24.buy),nw:Math.round(C.nw),gold:Math.round(C.alloc.gold),fixed:Math.round(C.alloc.fixed),liquid:Math.round(C.alloc.liquid),growth:Math.round(C.alloc.growth)};
  const prev=HIST.snaps[d];if(prev&&prev.nw===v.nw&&prev.gold===v.gold&&prev.p24===v.p24)return false;HIST.snaps[d]=v;const keys=Object.keys(HIST.snaps).sort();while(keys.length>730)delete HIST.snaps[keys.shift()];return true}
function commit(rerender=true){S.updatedAt=new Date().toISOString();if(rerender)render();else C=calc();const hc=C.nw>0&&snapshot();const ok=LS.set("state",S);if(hc)LS.set("hist",HIST);setSync(ok?"ok":"bad",ok?"محفوظ على جهازك":"تعذّر الحفظ: المساحة ممتلئة؟");if(!ok)toast("تعذّر الحفظ على الجهاز. اعمل نسخة احتياطية الآن.")}
async function boot(){render();setSync("ok",cached||SEED_AT?"محفوظ على جهازك":"جهاز جديد");maybeAuto();try{navigator.storage&&navigator.storage.persist&&navigator.storage.persist()}catch(e){}}

/* gold price: public CORS APIs give the world price in EGP/gram; the local market (El Galla) carries a premium,
   so the app calibrates against the last price the user typed in and applies the same ratio to fresh fetches */
let fetching=false;
const OZ=31.1034768;
async function jget(url,ms=9000){const c=new AbortController();const t=setTimeout(()=>c.abort(),ms);try{const r=await fetch(url,{cache:"no-store",signal:c.signal});if(!r.ok)throw new Error("http "+r.status);return await r.json()}finally{clearTimeout(t)}}
async function globalGram(){
  const tries=[
    async()=>{const [g,fx]=await Promise.all([jget("https://api.gold-api.com/price/XAU"),jget("https://open.er-api.com/v6/latest/USD")]);return N(g.price)/OZ*N(fx.rates&&fx.rates.EGP)},
    async()=>{const j=await jget("https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/xau.json");return N(j.xau&&j.xau.egp)/OZ},
    async()=>{const j=await jget("https://latest.currency-api.pages.dev/v1/currencies/xau.json");return N(j.xau&&j.xau.egp)/OZ}];
  for(const f of tries){try{const v=await f();if(v>500&&v<100000)return v}catch(e){}}return null}
function applyGlobal(g){const p=S.prices;const ref=p.ref;const now=new Date().toISOString();let r=null,mode="raw";
  if(ref&&N(ref.k24buy)){if(!N(ref.global)&&ageH(ref.at)<72)ref.global=g;if(N(ref.global)){r=ref.k24buy/ref.global;mode="est"}}
  const b24=Math.round(g*(r||1)),sp=ref&&N(ref.k24buy)&&N(ref.k24sell)?ref.k24sell/ref.k24buy:1.01;
  const k21r=ref&&N(ref.k24buy)&&N(ref.k21buy)?ref.k21buy/ref.k24buy:21/24,k21s=ref&&N(ref.k21buy)&&N(ref.k21sell)?ref.k21sell/ref.k21buy:sp;
  const b21=Math.round(b24*k21r);
  S.prices={...p,k24:{buy:b24,sell:Math.round(b24*sp)},k21:{buy:b21,sell:Math.round(b21*k21s)},global:{egp24:Math.round(g),at:now,src:"api"},at:now,mode,ref,
    src:mode==="est"?"تقدير من السعر العالمي (معايَر على آخر إدخال يدوي)":"السعر العالمي بدون علاوة السوق المحلي"};return mode}
async function fetchGalla(manual){if(fetching)return;fetching=true;const btn=$("#btnPrices");if(btn){btn.disabled=true;btn.textContent="جارِ التحديث…"}
  try{const g=await globalGram();
    if(!g){toast(navigator.onLine?"تعذّر سحب السعر الآن. جرّب بعد شوية أو أدخله يدوي.":"مفيش إنترنت. أدخل السعر يدوي.");if(manual)manualPrice();return}
    const mode=applyGlobal(g);commit();
    toast(mode==="est"?`تم: ع24 ${fmt(S.prices.k24.buy)} · ع21 ${fmt(S.prices.k21.buy)}`:`تم السعر العالمي: ع24 ${fmt(S.prices.k24.buy)}. أدخل سعر الجلا يدوي مرة لمعايرته على السوق المحلي.`)}
  catch(e){toast("تعذّر تحديث السعر الآن.");if(manual)manualPrice()}
  finally{fetching=false;if(btn){btn.disabled=false;btn.textContent="تحديث سعر الذهب"}}}
function manualPrice(){const p=S.prices;openForm("price",{k24buy:p.k24.buy||"",k24sell:p.k24.sell||"",k21buy:p.k21.buy||"",k21sell:p.k21.sell||""},o=>{if(!N(o.k24buy))return "سعر ع24 مطلوب";
  const now=new Date().toISOString();S.prices={k24:{buy:N(o.k24buy),sell:N(o.k24sell)},k21:{buy:N(o.k21buy),sell:N(o.k21sell)},global:S.prices.global||null,at:now,src:"إدخال يدوي",mode:"manual",ref:{k24buy:N(o.k24buy),k24sell:N(o.k24sell),k21buy:N(o.k21buy),k21sell:N(o.k21sell),global:null,at:now}};commit();
  globalGram().then(g=>{if(!g)return;S.prices.ref.global=g;S.prices.global={egp24:Math.round(g),at:new Date().toISOString(),src:"api"};commit(false);render()}).catch(()=>{})})}
function maybeAuto(){if(S.settings.autoGalla&&ageH(S.prices.at)>1&&S.gold.length&&navigator.onLine)fetchGalla(false)}
function openSettings(){const t=S.targets;openForm("settings",{salary:S.income.salary,expenses:S.income.expenses,tgold:t.gold,tfixed:t.fixed,tliquid:t.liquid,tgrowth:t.growth,infl:S.assump.infl,streak:S.settings.streakStart||"",goldSellBy:S.settings.goldSellBy||"",auto:S.settings.autoGalla?"1":"",autoexp:S.settings.autoExp===false?"":"1"},o=>{
  const sum=N(o.tgold)+N(o.tfixed)+N(o.tliquid)+N(o.tgrowth);if(Math.abs(sum-100)>0.5)return `مجموع الأهداف ${sum}% لازم يبقى 100%`;
  if(o.streak&&!/^\d{4}-\d{2}$/.test(o.streak))return "بداية السلسلة بالشكل 2025-05";
  S.income.salary=N(o.salary);S.income.expenses=N(o.expenses);S.targets={gold:N(o.tgold),fixed:N(o.tfixed),liquid:N(o.tliquid),growth:N(o.tgrowth)};S.assump.infl=N(o.infl)||S.assump.infl;S.settings.streakStart=o.streak||"";S.settings.goldSellBy=o.goldSellBy||"";S.settings.autoGalla=!!o.auto;S.settings.autoExp=!!o.autoexp;commit()})}

/* events */
document.addEventListener("click",e=>{const b=e.target.closest("button");if(!b)return;const d=b.dataset;
  if(d.t){document.querySelectorAll(".tab").forEach(x=>x.setAttribute("aria-selected",x===b?"true":"false"));document.querySelectorAll(".sector").forEach(s=>s.classList.toggle("on",s.id==="s-"+d.t));LS.set("tab",d.t);return}
  if(d.go){document.querySelector(`.tab[data-t="${d.go}"]`)?.click();return}
  if(d.h){showHadith(hIdx+N(d.h),true);return}
  if(d.add){add(d.add);return}
  if(d.edit){const [k,id]=d.edit.split(":");edit(k,id);return}
  if(d.del){const [k,id]=d.del.split(":");del(k,id,b);return}
  if(d.brk){const c=S.certs.find(x=>x.id===d.brk);if(!c)return;openForm("brk",{d:today(),v:c.breakTotal||""},o=>{if(!N(o.v)||!o.d)return "التاريخ والقيمة مطلوبين";c.brkHist=(c.brkHist||[]).filter(h=>h.d!==o.d);c.brkHist.push({d:o.d,v:N(o.v)});c.brkHist.sort((a,b)=>String(a.d).localeCompare(String(b.d)));const last=c.brkHist[c.brkHist.length-1];c.breakTotal=last.v;c.breakAt=last.d;commit()},"قيمة كسر: "+c.name);return}
  if(d.delbrk){const [cid,dt]=d.delbrk.split("|");const c=S.certs.find(x=>x.id===cid);if(!c||!arm(b))return;c.brkHist=(c.brkHist||[]).filter(h=>h.d!==dt);const last=c.brkHist[c.brkHist.length-1];c.breakTotal=last?last.v:"";c.breakAt=last?last.d:"";commit();return}
  if(d.addlot){const f=S.funds.find(x=>x.id===d.addlot);openForm("lot",{date:today(),price:f?.kind==="balance"?1:(f?.nav||"")},o=>{if(!N(o.units))return "الكمية مطلوبة";(f.lots=f.lots||[]).push({id:uid(),units:N(o.units),price:N(o.price)||1,date:o.date});commit()},(f?.kind==="balance"?"إيداع في ":"شراء في ")+(f?.name||""));return}
  if(d.dellot){const [fid,lid]=d.dellot.split(":");const f=S.funds.find(x=>x.id===fid);if(!arm(b))return;f.lots=f.lots.filter(l=>l.id!==lid);commit();return}
  if(d.nav){const f=S.funds.find(x=>x.id===d.nav);openForm("nav",{nav:f.nav,navAt:today()},o=>{if(!N(o.nav))return "القيمة مطلوبة";f.nav=N(o.nav);f.navAt=o.navAt;commit()},(f.kind==="balance"?"الرصيد الحالي في ":"السعر الحالي لـ ")+f.name);return}
  if("goal" in d){const G=goalCfg();openForm("goal",{shabka:G.shabka,...G.v,cont:G.cont},o=>{const v={};GOAL_ITEMS.forEach(([k])=>v[k]=N(o[k]));S.goal={scenario:"custom",shabka:N(o.shabka),v,cont:N(o.cont)};commit()});return}
  if(d.scen){const G=goalCfg();S.goal=d.scen==="custom"?{scenario:"custom",shabka:G.shabka,v:G.v,cont:G.cont}:{scenario:d.scen,cont:G.cont};commit();return}
  if("names" in d){openNames();return}
  if(d.nm99){$("#nm").textContent=d.nm99;$("#mean").textContent=nmMean(d.nm99);$("#modalRoot").innerHTML="";return}
  if("zset" in d){const Z=zDefaults();openForm("zset",{hawlStart:Z.hawlStart,debts:Z.debts||""},o=>{S.zakat=Object.assign(Z,S.zakat||{},{hawlStart:o.hawlStart,debts:N(o.debts)});commit()});return}
  if("zpay" in d){const q=zakatCalc();openForm("zpay",{amount:Math.round(q.due)||"",date:today()},o=>{if(!N(o.amount))return "المبلغ مطلوب";S.zakat=Object.assign(zDefaults(),S.zakat||{});(S.zakat.paid=S.zakat.paid||[]).push({id:uid(),amount:N(o.amount),date:o.date,note:o.note});commit()});return}
  if(d.zdel){if(!arm(b))return;S.zakat.paid=(S.zakat.paid||[]).filter(p=>p.id!==d.zdel);commit();return}
  if("priceManual" in d){manualPrice();return}
  if("settings" in d){openSettings();return}
});
$("#btnPrices").onclick=()=>fetchGalla(true);
$("#btnSettings").onclick=()=>HISN_EXT.openMenu();
document.addEventListener("change",e=>{const id=e.target?.dataset?.plan;if(!id)return;const it=(S.plan||[]).find(x=>x.id===id);if(it){it.done=e.target.checked;it.doneAt=it.done?today():null;commit()}});
document.addEventListener("keydown",e=>{if(e.key==="Escape")$("#modalRoot").innerHTML=""});

/* hadith rotator */
let hIdx=0,hTimer=null;const RED=matchMedia("(prefers-reduced-motion: reduce)").matches;
function showHadith(i,user){hIdx=(i+SACRED.length)%SACRED.length;const it=SACRED[hIdx];const el=$("#hadith");
  const put=()=>{const v=it.k==="v";$("#hIntro").textContent=v?"قال الله تعالى":it.k==="d"?"من دعاء النبي ﷺ":"قال رسول الله ﷺ";$("#hTxt").textContent=v?"﴿"+it.t+"﴾":"«"+it.t+"»";$("#hSrc").innerHTML=`<b>${esc(it.a)}</b> · ${esc(it.b)}`;
    const W=9,st=Math.floor(hIdx/W)*W;$("#hDots").innerHTML=SACRED.slice(st,st+W).map((_,j)=>`<i class="${st+j===hIdx?"on":""}"></i>`).join("");el.classList.remove("fade")};
  if(RED||!$("#hTxt").textContent){put()}else{el.classList.add("fade");setTimeout(put,450)}
  clearInterval(hTimer);hTimer=setInterval(()=>{if(!el.matches(":hover"))showHadith(hIdx+1)},16000)}

/* clock, name, stars */
function tick(){const d=new Date();
  $("#dates").innerHTML=`<span><b>${d.toLocaleDateString("ar-EG-u-nu-latn",{timeZone:TZ,weekday:"long",day:"numeric",month:"long",year:"numeric"})}</b></span><span class="hj">${hijri(d)} هـ</span><span class="clock">${d.toLocaleTimeString("en-GB",{timeZone:TZ,hour:"2-digit",minute:"2-digit",second:"2-digit"})}</span>`}
tick();setInterval(tick,1000);
(()=>{const t=today();const doy=Math.floor((dParse(t)-Date.UTC(+t.slice(0,4),0,1))/DAY);const [n,m]=NAMES[doy%NAMES.length];$("#nm").textContent=n;$("#mean").textContent=m;
  $("#doctrine").innerHTML=`عقيدة الحصن: <b>${DOCTRINE[doy%DOCTRINE.length]}</b>`;showHadith((doy*3)%SACRED.length)})();
(()=>{const cv=$("#stars");const ctx=cv.getContext("2d");let st=[],cons=[];
  function size(){const r=cv.getBoundingClientRect();const dpr=devicePixelRatio||1;cv.width=r.width*dpr;cv.height=r.height*dpr;
    st=Array.from({length:Math.round(r.width/4)},()=>({x:Math.random()*cv.width,y:Math.random()*cv.height*.75,r:(Math.random()*1.2+.2)*dpr,p:Math.random()*6}));
    const pick=()=>st[Math.floor(Math.random()*st.length)];cons=Array.from({length:6},()=>[pick(),pick()]).filter(([a,b])=>a&&b&&Math.hypot(a.x-b.x,a.y-b.y)<160*dpr)}
  function draw(t){if(!cv.offsetParent){if(!RED)requestAnimationFrame(draw);return}ctx.clearRect(0,0,cv.width,cv.height);ctx.strokeStyle="rgba(235,208,140,.08)";ctx.lineWidth=1;cons.forEach(([a,b])=>{ctx.beginPath();ctx.moveTo(a.x,a.y);ctx.lineTo(b.x,b.y);ctx.stroke()});
    st.forEach(s=>{const a=RED?.55:.3+.5*Math.abs(Math.sin(t/1600+s.p));ctx.fillStyle=`rgba(246,231,190,${a})`;ctx.beginPath();ctx.arc(s.x,s.y,s.r,0,7);ctx.fill()});if(!RED)requestAnimationFrame(draw)}
  size();addEventListener("resize",size);requestAnimationFrame(draw)})();

const savedTab=LS.get("tab");if(savedTab&&savedTab!=="ops")document.querySelector(`.tab[data-t="${savedTab}"]`)?.click();
window.HISN={get S(){return S},get C(){return C},get HIST(){return HIST},setState(s,h){S=merge(s);if(h&&h.snaps)HIST=h;commit()},cached:!!cached,
  commit,render,calc,fmt,N,esc,uid,today,dLabel,dParse,daysBetween,toast,openForm,arm,FORMS,CLASS,LS,sgn,pct,TZ,rules,alertHtml,openSettings,manualPrice,fetchGalla,merge,SACRED,ageH,effExp,hijri};
try{HISN_EXT.init&&HISN_EXT.init()}catch(e){console.error(e)}
boot();
})();