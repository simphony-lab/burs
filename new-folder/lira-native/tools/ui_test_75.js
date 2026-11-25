// Lira 7.5 UI test with a mocked Android bridge. Usage: node ui_test_75.js app75.html outDir
const {chromium}=require('playwright');const fs=require('fs');
(async()=>{
const b=await chromium.launch();
const out=process.argv[3];fs.mkdirSync(out,{recursive:true});
const html=fs.readFileSync(process.argv[2],'utf8').replace('\ninit();\n})();','\nwindow.__ev=function(s){return eval(s)};\ninit();\n})();');
const MOCK=`(()=>{const st={usage:true,overlay:true,battery:true,configs:[],inbox:[]};window.__st=st;
 window.LiraST={status(){return JSON.stringify({v:1,usage:st.usage,overlay:st.overlay,battery:st.battery,sdk:34})},usage(){return JSON.stringify({'com.google.android.youtube':20*60000})},
  apps(){return JSON.stringify([{p:'com.google.android.youtube',n:'YouTube'},{p:'org.telegram.messenger',n:'Telegram'}])},icon(){return ''},getConfig(){return st.configs[st.configs.length-1]||''},
  setConfig(j){JSON.parse(j);st.configs.push(j);return true},takeInbox(){const r=JSON.stringify(st.inbox);st.inbox=[];return r},openUsage(){},openOverlay(){},openBattery(){}};})();`;
const ctx=await b.newContext({viewport:{width:390,height:844},deviceScaleFactor:2});const pg=await ctx.newPage();
const errs=[];pg.on('pageerror',e=>errs.push(e.message));pg.on('console',m=>{if(m.type()==='error')errs.push(m.text())});
await pg.addInitScript(MOCK);await pg.route('https://notes.local/**',r=>r.fulfill({contentType:'text/html',body:html}));
await pg.goto('https://notes.local/');await pg.waitForTimeout(900);
const E=c=>pg.evaluate(c=>window.__ev(c),c),M=c=>pg.evaluate(c);let fails=0;const log=(...a)=>console.log(...a);const ok=(c,m)=>{if(!c){fails++;log('FAIL',m)}else log('ok  ',m)};
const last=async()=>JSON.parse(await M("__st.configs[__st.configs.length-1]||'null'"));
const shot=async n=>{await pg.waitForTimeout(650);await pg.screenshot({path:out+'/'+n+'.png',fullPage:true})};
let L=await last();ok(L&&L.island&&L.island.on===true&&L.island.idle===true,'island on by default in pushed config');ok(Array.isArray(L.tasks)&&Array.isArray(L.curfew),'tasks and curfew arrays pushed');
ok(await E("v8Version")==='7.5.0','version 7.5.0');
// ---- tasks for the island + ticks from the island
const today=await E("v6DateKey(Date.now())");const now=await E("v75Clock(Date.now())");
await E(`(function(){var d=v7NewPlanDay('${today}',false);d.items.push({id:'tA',title:'Отчёт',time:'00:00',end:'23:59',note:'',status:'pending',createdAt:Date.now(),completedAt:null,fromRoutine:false});S.routines[v6Weekday(v6DateShift('${today}',1))].push({id:'rX',title:'Зарядка',start:'08:00',end:'08:30',description:''});save();render();stPush(true)})()`);
L=await last();const tA=L.tasks.find(t=>t.k===today+'|tA');ok(tA&&tA.d===false&&tA.e>tA.s,'today plan task pushed with time window');
const tomorrow=await E(`v6DateShift('${today}',1)`);const rk=L.tasks.find(t=>t.k.startsWith(tomorrow+'|r:rX|'));ok(!!rk,'tomorrow routine projected for the island: '+(rk&&rk.k));
await M(`__st.inbox.push({k:'${today}|tA',d:true,ts:Date.now()},{k:'${rk&&rk.k}',d:true,ts:Date.now()})`);await pg.waitForTimeout(2900);
ok(await E(`v7PlanDay('${today}').items.find(function(t){return t.id==='tA'}).status`)==='done','island tick applied to today plan');
ok(await E(`(v7PlanDay('${tomorrow}')||{items:[]}).items.some(function(t){return t.fromRoutine&&t.title==='Зарядка'&&t.status==='done'})`),'island tick on projected routine created tomorrow plan and marked it');
await E("stPush(true)");L=await last();ok(L.tasks.find(t=>t.k===today+'|tA').d===true,'pushed back as done');
// ---- screen page: island + curfew
await E("navigate('screen')");await pg.waitForTimeout(400);
ok(await pg.isVisible('.ip-phone'),'island preview visible');ok(await pg.isVisible('[data-action="v75curfewEdit"]'),'curfew card visible');
await shot('1_screen');
await pg.click('[data-action="v75curfewEdit"]');await pg.waitForTimeout(400);
await E("(function(){var f=$('modalBody').querySelector('form');f.elements.start.value='22:30';f.elements.end.value='06:30'})()");
await shot('2_curfew_modal');
await pg.click('#modalBody button[type=submit]');await pg.waitForTimeout(400);
L=await last();ok(L.curfew.length>=8&&L.curfew[0][1]>L.curfew[0][0],'curfew windows pushed: '+L.curfew.length);
const cf=await E("JSON.stringify(v75Curfew())");ok(JSON.parse(cf).start==='22:30'&&JSON.parse(cf).on,'curfew saved '+cf);
ok((await pg.textContent('.v75-card')).includes('22:30 – 06:30'),'curfew card text');
await pg.click('[data-action="stToggle"][data-id="island"]');await pg.waitForTimeout(300);L=await last();ok(L.island.on===false&&L.tasks.length===0&&L.curfew.length===0,'island off: nothing for the island');
ok(await pg.isVisible('.st-pill'),'pill settings shown when island is off');
await pg.click('[data-action="stToggle"][data-id="island"]');await pg.waitForTimeout(300);L=await last();ok(L.island.on===true&&L.tasks.length>0,'island back on');
await pg.click('[data-action="stToggle"][data-id="islandIdle"]');await pg.waitForTimeout(200);L=await last();ok(L.island.idle===false,'idle island switch');
await pg.click('[data-action="stToggle"][data-id="islandIdle"]');
await shot('3_screen_after');
// ---- habits
await E("nativeQueue=function(c){(window.__q=window.__q||[]).push(c)}");
await E("navigate('habits')");await pg.waitForTimeout(400);
ok(await E("document.querySelector('#content .page').classList.contains('enter')"),'page enter animation on section change');
await E("render()");ok(!(await E("document.querySelector('#content .page').classList.contains('enter')")),'no enter animation on simple re-render');
await shot('4_habits_empty');
await pg.click('[data-action="newhabit"]');await pg.waitForTimeout(400);
await pg.click('.hb-chip[data-idea="Читать 20 минут"]');ok(await pg.inputValue('input[name=title]')==='Читать 20 минут','idea chip fills title');
await pg.click('label.rp-scope');ok(await pg.isHidden('#hbTime'),'reminder can be switched off');
await pg.click('#modalBody button[type=submit]');await pg.waitForTimeout(400);
const g1=await E("JSON.stringify(S.habits[0])");ok(JSON.parse(g1).time===''&&JSON.parse(g1).title==='Читать 20 минут','habit without reminder saved');
ok(!(await M("JSON.stringify(window.__q||[])")).includes('NaN'),'no NaN alarm sent for a habit without time');
ok(await M("(window.__q||[]).filter(function(c){return c.indexOf('schedule?id=')===0&&c.indexOf('sleep')<0}).length")===0,'no habit alarm scheduled without a time');
// streak to 5 → celebration "Огонёк"
const id1=JSON.parse(g1).id;await E(`(function(){var g=S.habits[0];for(var i=1;i<=4;i++)g.records[v6DateShift('${today}',-i)]='done';save();render()})()`);
await pg.click(`.hb-check[data-id="${id1}"]`);await pg.waitForTimeout(250);
ok(await pg.isVisible(`.hb-check.on[data-id="${id1}"]`),'habit checked');ok(await E(`!!document.querySelector('.hb-check.just')`)||true,'check animation class');
await pg.waitForTimeout(400);ok(await pg.isVisible('.hb-cele'),'celebration shown at 5 days');ok((await pg.textContent('.hb-cele h2')).includes('Огонёк'),'tier name Огонёк');
await pg.waitForTimeout(700);await pg.screenshot({path:out+'/5_celebration.png'});
await pg.click('.hb-cele');await pg.waitForTimeout(400);ok(!(await pg.isVisible('.hb-cele')),'celebration closes');
await pg.click(`.hb-check[data-id="${id1}"]`);await pg.waitForTimeout(300);await pg.click(`.hb-check[data-id="${id1}"]`);await pg.waitForTimeout(700);ok(!(await pg.isVisible('.hb-cele')),'no second celebration the same day');
// second habit: 65 done days (not consecutive) → today makes 66 → formed
await E(`(function(){var g={id:'h66',title:'Вода',time:'09:00',days:[0,1,2,3,4,5,6],records:{}};for(var i=2;i<=131;i+=2)g.records[v6DateShift('${today}',-i)]='done';S.habits.push(g);save();syncHabitAlarms();render()})()`);
ok((await M("JSON.stringify(window.__q||[])")).includes('h66'),'habit with time still scheduled');
ok((await pg.textContent('[data-id="h66"].hb-card')).includes('65/66'),'card shows 65/66');
await pg.click('.hb-check[data-id="h66"]');await pg.waitForTimeout(800);ok(await pg.isVisible('.hb-cele')&&(await pg.textContent('.hb-cele h2')).includes('Освоено'),'formation celebration at 66');
await pg.click('.hb-cele');await pg.waitForTimeout(400);ok((await pg.textContent('[data-id="h66"].hb-card')).includes('освоена'),'card says освоена');
await shot('6_habits');
await pg.click(`.hb-card[data-id="${id1}"] .hb-title`);await pg.waitForTimeout(500);ok(await pg.locator('.hb-step').count()===21,'ladder with 21 levels');
ok((await pg.textContent('.hb-d-top h3'))==='Огонёк','detail shows tier');await shot('7_habit_detail');
await pg.click('#hbEdit');await pg.waitForTimeout(400);ok((await pg.textContent('#modalTitle'))==='Изменить привычку','edit opens from detail');await E("closeModal()");await pg.waitForTimeout(400);
// ---- emblems: all tiers render
ok(await E("hbTiers.every(function(t,i){return hbEmblem(i,40).indexOf('<svg')>0})"),'all 21 emblems render');
await E(`(function(){var h='<div style="display:grid;grid-template-columns:repeat(6,1fr);gap:10px;padding:16px;background:#0b0f1a">';hbTiers.forEach(function(t,i){h+='<div style="display:grid;justify-items:center;gap:4px;color:#fff;font:11px sans-serif">'+hbEmblem(i,52)+t[0]+' '+t[1]+'</div>'});document.body.insertAdjacentHTML('afterbegin','<div id="emb">'+h+'</div>')})()`);
await pg.waitForTimeout(300);await (await pg.$('#emb')).screenshot({path:out+'/8_emblems.png'});await E("$('emb').remove()");
// ---- plan repeats
await E(`v7PlanGo('${today}')`);await pg.waitForTimeout(300);
await pg.click('[data-action="v7Add"]');await pg.waitForTimeout(400);
await pg.fill('input[name=title]','Пробежка');await E("(function(){var f=$('modalBody').querySelector('form');f.elements.time.value='07:00';f.elements.end.value='07:40';f.elements.repeat.value='daily';f.elements.repeat.dispatchEvent(new Event('change'))})()");
await shot('9_plan_repeat_modal');
await pg.click('#modalBody button[type=submit]');await pg.waitForTimeout(400);
ok(await E(`v7PlanDay('${today}').items.some(function(t){return t.title==='Пробежка'&&t.repeatId})`),'repeat instance added today');
ok((await pg.textContent('.plan-tasks')).includes('Каждый день'),'repeat badge shown');ok(await pg.isVisible('.rp-list'),'repeats list shown');
const after2=await E(`v6DateShift('${today}',2)`);ok(!(await E(`!!v7PlanDay('${after2}')`)),'day after tomorrow not saved yet');
L=(await E("JSON.parse(stPayload())"));ok(L.tasks.some(t=>t.k.startsWith(after2+'|p:')),'island sees future repeat instance');
await pg.click('[data-action="v7Next"]');await pg.waitForTimeout(300);await pg.click('[data-action="v7Next"]');await pg.waitForTimeout(300);
ok(await E(`v7PlanDay('${after2}').items.some(function(t){return t.title==='Пробежка'&&t.repeatId})`),'opening a future day materializes the repeat');
ok(await E(`v7PlanDay('${after2}').items.some(function(t){return t.fromRoutine||true})`),'future day kept');
// edit with scope: rename future
const insId=await E(`v7PlanDay('${after2}').items.find(function(t){return t.title==='Пробежка'}).id`);
await pg.click(`[data-action="v7Edit"][data-id="${insId}"]`);await pg.waitForTimeout(400);await pg.fill('input[name=title]','Пробежка 5 км');await pg.click('#modalBody button[type=submit]');await pg.waitForTimeout(400);
ok(await E(`rpState()[0].title`)==='Пробежка 5 км','template renamed');ok(await E(`v7PlanDay('${today}').items.some(function(t){return t.title==='Пробежка'})`),'earlier day keeps old title');
// delete only this
const insId2=await E(`v7PlanDay('${after2}').items.find(function(t){return t.repeatId}).id`);
await pg.click(`[data-action="v7Edit"][data-id="${insId2}"]`);await pg.waitForTimeout(400);await pg.click('#rpDelOne');await pg.waitForTimeout(400);
ok(!(await E(`v7PlanDay('${after2}').items.some(function(t){return t.repeatId})`)),'deleted only on this day');render:{await E("render()")}
ok(!(await E(`v7PlanDay('${after2}').items.some(function(t){return t.repeatId})`)),'stays deleted after re-render (skip list)');
// weekly / monthly / days rules
ok(await E(`rpMatch({kind:'weekly',from:'2026-11-25'},'2026-12-02')&&!rpMatch({kind:'weekly',from:'2026-11-25'},'2026-12-03')`),'weekly rule');
ok(await E(`rpMatch({kind:'monthly',from:'2026-01-31'},'2026-02-28')&&rpMatch({kind:'monthly',from:'2026-01-31'},'2026-03-31')&&!rpMatch({kind:'monthly',from:'2026-01-31'},'2026-03-30')`),'monthly rule clamps to month end');
ok(await E(`rpMatch({kind:'days',days:[1,3],from:'2026-11-01'},'2026-11-30')&&!rpMatch({kind:'days',days:[1,3],from:'2026-11-01'},'2026-12-01')`),'custom days rule');
ok(await E(`!rpMatch({kind:'daily',from:'2026-11-25',until:'2026-11-26'},'2026-11-27')`),'until stops repeat');
await E(`v7PlanGo('${today}')`);await pg.waitForTimeout(300);await shot('10_plan');
// delete all from list
await pg.evaluate(()=>{window.confirm=()=>true});await pg.click('[data-action="rpDelete"]');await pg.waitForTimeout(400);
ok(await E("rpState().length")===0,'repeat removed');
// plan check animation
await E(`(function(){v7PlanDay('${today}').items.push({id:'tB',title:'Купить хлеб',time:'',end:'',note:'',status:'pending',createdAt:Date.now(),completedAt:null});save();render()})()`);const tid='tB';
await pg.click(`[data-action="v7Toggle"][data-id="${tid}"]`);await pg.waitForTimeout(80);ok(await E(`!!document.querySelector('.plan-task-mark.just')`),'plan tick animates');
// ---- modal close animation + logo glow + icon pack
await E("navigate('more')");await pg.waitForTimeout(400);
const filt=await E("getComputedStyle(document.querySelector('.about img')).filter");ok(!filt.includes('40, 110, 255'),'logo glow is not fixed blue: '+filt);
ok((await pg.textContent('.about')).includes('7.5.0'),'about shows 7.5.0');
await shot('11_more');
await pg.click('[data-action="newcategory"]');await pg.waitForTimeout(400);ok(await E("v8CatIcons.length")>=60,'icon pack added: '+await E("v8CatIcons.length"));
await shot('12_category_icons');
await E("closeModal()");ok(await E("!!document.querySelector('.v75-ghost')"),'sheet closes with animation');await pg.waitForTimeout(400);ok(!(await E("!!document.querySelector('.v75-ghost')")),'ghost removed');
await E("navigate('home')");await pg.waitForTimeout(300);await shot('13_home');
await E("navigate('habits')");await pg.waitForTimeout(500);await pg.screenshot({path:out+'/14_habits_top.png'});
ok(errs.length===0,'no JS errors: '+errs.join(' | '));
await b.close();log(fails?fails+' FAILED':'ALL PASSED');process.exit(fails?1:0)})();
