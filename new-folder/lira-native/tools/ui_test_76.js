// Lira 7.5.1 UI test: own confirm dialog, category operations, category filter in history.
const {chromium}=require('playwright');const fs=require('fs');
(async()=>{
const b=await chromium.launch();const out=process.argv[3];fs.mkdirSync(out,{recursive:true});
const html=fs.readFileSync(process.argv[2],'utf8').replace('\ninit();\n})();','\nwindow.__ev=function(s){return eval(s)};\ninit();\n})();');
const ctx=await b.newContext({viewport:{width:390,height:844},deviceScaleFactor:2});const pg=await ctx.newPage();
const errs=[],dialogs=[];pg.on('pageerror',e=>errs.push(e.message));pg.on('console',m=>{if(m.type()==='error')errs.push(m.text())});pg.on('dialog',d=>{dialogs.push(d.message());d.dismiss()});
await pg.route('https://notes.local/**',r=>r.fulfill({contentType:'text/html',body:html}));await pg.goto('https://notes.local/');await pg.waitForTimeout(800);
const E=c=>pg.evaluate(c=>window.__ev(c),c);let fails=0;const log=(...a)=>console.log(...a);const ok=(c,m)=>{if(!c){fails++;log('FAIL',m)}else log('ok  ',m)};
const shot=async n=>{await pg.waitForTimeout(600);await pg.screenshot({path:out+'/'+n+'.png'})};
// seed: USD currency, ops over several months in two categories and an income
await E(`(function(){if(!S.currencies.some(function(c){return c.id==='USD'}))S.currencies.push({id:'USD',name:'Доллар США',code:'USD',rate:1.7});S.balances.USD=500;S.balances.AZN=2000;
 var food=S.categories[0].id,cart=S.categories[1].id,sal=S.incomeCategories[0].id,now=Date.now(),D=86400000;
 for(var i=0;i<40;i++)S.ops.push({id:'e'+i,type:'expense',currency:i%5?'AZN':'USD',amount:10+i,date:now-i*4*D,category:i%3?food:cart,note:i===3?'Кафе с друзьями':''});
 for(var j=0;j<6;j++)S.ops.push({id:'in'+j,type:'income',currency:'AZN',amount:1500,date:now-j*30*D,category:sal});
 S.ops.sort(function(a,b){return b.date-a.date});save();render()})()`);
ok(await E("v8Version")==='7.5.1','version 7.5.1');
// ---- wallet breakdown rows open the category
await E("navigate('wallets')");await pg.waitForTimeout(400);
const rows=await pg.locator('.cat-row.v76-tap').count();ok(rows>=2,'category rows are tappable: '+rows);
const foodName=await E("S.categories[0].name"),foodId=await E("S.categories[0].id");
await pg.locator(`.cat-row.v76-tap[data-cat="${foodId}"]`).first().click();await pg.waitForTimeout(500);
ok(await pg.isVisible('#v76Cat'),'category sheet opened');ok((await pg.textContent('#modalTitle'))===foodName,'title is the category');
const azn=await E(`S.ops.filter(function(o){return o.type==='expense'&&o.category==='${foodId}'&&o.currency==='AZN'}).length`);
const curAttr=await E(`document.querySelector('.cat-row.v76-tap[data-cat="${foodId}"]').dataset.cur`);
const expectN=curAttr?azn:await E(`S.ops.filter(function(o){return o.type==='expense'&&o.category==='${foodId}'}).length`);
ok((await pg.locator('#v76CatList .op-list > *').count())===expectN,'lists all operations of the category ('+expectN+', currency '+(curAttr||'all')+')');
ok(await pg.locator('.v76-bar').count()===6,'six month bars');
await shot('1_category');
await pg.click('[data-per="month"]');await pg.waitForTimeout(300);
const inMonth=await E(`(function(){var m=v6DateKey(Date.now()).slice(0,7);return S.ops.filter(function(o){return o.type==='expense'&&o.category==='${foodId}'&&(!'${curAttr}'||o.currency==='${curAttr}')&&v6DateKey(o.date).slice(0,7)===m}).length})()`);
ok((await pg.locator('#v76CatList .op-list > *').count())===inMonth,'period: this month = '+inMonth);
await pg.locator('.v76-bar').nth(4).click();await pg.waitForTimeout(300);ok(await E("v76C.period.indexOf('m:')===0"),'tap on a month bar filters by that month');
await pg.click('[data-per="all"]');await pg.waitForTimeout(200);
if(await pg.locator('[data-cur=""]').count()){await pg.click('[data-cur=""]');await pg.waitForTimeout(200);ok((await pg.locator('#v76CatList .op-list > *').count())===await E(`S.ops.filter(function(o){return o.type==='expense'&&o.category==='${foodId}'}).length`),'all currencies')}
await pg.click('#v76Hist');await pg.waitForTimeout(500);
ok(await pg.isVisible('#v8HistList'),'opens history');ok(await E("v76HistCat")==='expense:'+foodId,'history keeps the category');
ok((await pg.getAttribute(`[data-hcat="expense:${foodId}"]`,'aria-pressed'))==='true','category chip pressed');
const histN=await pg.locator('#v8HistList .op-list > *').count();ok(histN===Math.min(150,await E(`S.ops.filter(function(o){return o.type==='expense'&&o.category==='${foodId}'}).length`)),'history filtered by category: '+histN);
await shot('2_history_category');
await pg.click('[data-v8filter="income"]');await pg.waitForTimeout(300);ok(await E("v76HistCat")==='','switching to income clears the expense category');
ok(await pg.locator('#v76HCats [data-hcat^="income:"]').count()===await E("S.incomeCategories.length"),'income categories listed');
await pg.click('[data-v8filter="exchange"]');await pg.waitForTimeout(200);ok(await pg.isHidden('#v76HCats'),'no category chips for exchanges');
await pg.click('[data-v8filter="all"]');await pg.waitForTimeout(200);await pg.click(`[data-hcat="income:${await E("S.incomeCategories[0].id")}"]`);await pg.waitForTimeout(300);
ok((await pg.locator('#v8HistList .op-list > *').count())===6,'income category in "all" shows 6');
await E("closeModal()");await pg.waitForTimeout(400);
await E("historyModal()");await pg.waitForTimeout(300);ok(await E("v76HistCat")==='','history opened normally starts without category');await E("closeModal()");await pg.waitForTimeout(400);
// ---- settings category rows
await E("navigate('more')");await pg.waitForTimeout(400);
const setRows=await pg.locator('.set-row.v76-tap').count();ok(setRows===await E("S.categories.length+S.incomeCategories.length"),'settings category rows tappable: '+setRows);
await pg.locator('.set-row.v76-tap').nth(1).locator('.set-name').click();await pg.waitForTimeout(400);ok(await pg.isVisible('#v76Cat'),'settings row opens operations');
await pg.click('#v76Edit');await pg.waitForTimeout(400);ok(await pg.isVisible('#modalBody form'),'"Категория" opens the category editor');await E("closeModal()");await pg.waitForTimeout(400);
await pg.locator('.set-row.v76-tap').nth(1).locator('.mini-btn').click();await pg.waitForTimeout(400);ok(!(await pg.isVisible('#v76Cat'))&&await pg.isVisible('#modalBody form'),'edit button still edits');
// ---- own confirm dialog: delete category (cancel, escape, then delete)
const n0=await E("S.categories.length");const delBtn=await pg.$('#deleteCategory');ok(!!delBtn,'delete category button present');
await pg.click('#deleteCategory');await pg.waitForTimeout(450);ok(await pg.isVisible('.la-over'),'Lira dialog shown');ok((await pg.textContent('.la-card h3'))==='Удалить категорию?','dialog title');ok((await pg.textContent('.la-card p'))==='Старые операции сохранятся.','dialog subtitle');
ok((await pg.textContent('.la-yes')).trim()==='Удалить','danger button text');await shot('3_confirm');
await pg.click('.la-no');await pg.waitForTimeout(350);ok(!(await pg.isVisible('.la-over'))&&await E("S.categories.length")===n0,'cancel keeps category');
await pg.click('#deleteCategory');await pg.waitForTimeout(300);await pg.keyboard.press('Escape');await pg.waitForTimeout(350);ok(!(await pg.isVisible('.la-over'))&&await E("S.categories.length")===n0&&await pg.isVisible('#modalBody form'),'Escape cancels and keeps the sheet');
await pg.click('#deleteCategory');await pg.waitForTimeout(300);await pg.click('.la-yes');await pg.waitForTimeout(500);ok(await E("S.categories.length")===n0-1,'delete works after confirming');
// habit delete through the dialog
await E("(function(){S.habits.push({id:'hx',title:'Тест',time:'',days:[1,2,3,4,5,6,0],records:{}});save();navigate('habits')})()");await pg.waitForTimeout(400);
await E("habitModal('hx')");await pg.waitForTimeout(400);await pg.click('#deleteHabit');await pg.waitForTimeout(300);await pg.click('.la-yes');await pg.waitForTimeout(500);ok(!(await E("S.habits.some(function(g){return g.id==='hx'})")),'habit deleted via Lira dialog');
// backup restore uses "Заменить"
ok(await E("typeof liraAsk")==='function','liraAsk available');await E("liraAsk('Заменить ВСЕ данные из этой копии?',function(){window.__yes=1})");await pg.waitForTimeout(300);ok((await pg.textContent('.la-yes')).trim()==='Заменить','replace wording');await pg.click('.la-yes');await pg.waitForTimeout(300);ok(await E("window.__yes===1"),'callback runs');
ok(await E("window.confirm('x')===false"),'system confirm disabled');
ok(dialogs.length===0,'no system dialogs at all: '+dialogs.join(' | '));
ok(errs.length===0,'no JS errors: '+errs.join(' | '));
await b.close();log(fails?fails+' FAILED':'ALL PASSED');process.exit(fails?1:0)})();
