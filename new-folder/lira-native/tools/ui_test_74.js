// Screen-time UI test with a mocked window.LiraST. Usage: node test3.js app.html outDir
const {chromium}=require('playwright');const fs=require('fs');
(async()=>{
const b=await chromium.launch();
const html0=fs.readFileSync(process.argv[2],'utf8');const out=process.argv[3];fs.mkdirSync(out,{recursive:true});
const o='\ninit();\n})();';const html=html0.replace(o,'\nwindow.__ev=function(s){return eval(s)};'+o);
const MOCK=`(()=>{const st={usage:false,overlay:false,battery:false,calls:[],configs:[]};window.__st=st;
 const apps=[['com.google.android.youtube','YouTube','#ff0033'],['org.telegram.messenger','Telegram','#2aabee'],['com.zhiliaoapp.musically','TikTok','#111111'],['com.instagram.android','Instagram','#d6249f'],['com.android.chrome','Chrome','#4285f4'],['ru.yandex.music','Яндекс Музыка','#ffcc00'],['com.whatsapp','WhatsApp','#25d366'],['com.vk.vkclient','VK','#0077ff'],['com.spotify.music','Spotify','#1db954']];
 const usage={'com.google.android.youtube':47*60000+12000,'org.telegram.messenger':83*60000,'com.zhiliaoapp.musically':25*60000,'com.instagram.android':12*60000,'com.android.chrome':6*60000,'ru.yandex.music':30000,'com.android.launcher':99*60000};
 function icon(c){const cv=document.createElement('canvas');cv.width=cv.height=96;const x=cv.getContext('2d');x.fillStyle=c;x.beginPath();x.roundRect(0,0,96,96,26);x.fill();x.fillStyle='#fff';x.beginPath();x.arc(48,48,20,0,7);x.fill();return cv.toDataURL('image/png')}
 window.LiraST={status(){st.calls.push('status');return JSON.stringify({v:1,usage:st.usage,overlay:st.overlay,battery:st.battery,sdk:34})},
  usage(){st.calls.push('usage');return st.usage?JSON.stringify(usage):'{}'},
  apps(){st.calls.push('apps');return JSON.stringify(apps.map(a=>({p:a[0],n:a[1]})).sort((a,b)=>a.n.localeCompare(b.n,'ru')))},
  icon(p){st.calls.push('icon');const a=apps.find(x=>x[0]===p);return a?icon(a[2]):''},
  getConfig(){return st.configs.length?st.configs[st.configs.length-1]:''},
  setConfig(j){JSON.parse(j);st.configs.push(j);return true},
  openUsage(){st.calls.push('openUsage');setTimeout(()=>st.usage=true,300)},
  openOverlay(){st.calls.push('openOverlay');setTimeout(()=>st.overlay=true,300)},
  openBattery(){st.calls.push('openBattery');setTimeout(()=>st.battery=true,300)}};})();`;
async function open(native){const ctx=await b.newContext({viewport:{width:390,height:844},deviceScaleFactor:2});const pg=await ctx.newPage();
 const errs=[];pg.on('pageerror',e=>errs.push(e.message));pg.on('console',m=>{if(m.type()==='error')errs.push(m.text())});
 if(native)await pg.addInitScript(MOCK);
 await pg.route('https://notes.local/**',r=>r.fulfill({contentType:'text/html',body:html}));
 await pg.goto('https://notes.local/');await pg.waitForTimeout(900);return {pg,errs,ctx}}
const log=(...a)=>console.log(...a);let fails=0;const ok=(c,m)=>{if(!c){fails++;log('FAIL',m)}else log('ok  ',m)};
let {pg,errs,ctx}=await open(true);const E=c=>pg.evaluate(c=>window.__ev(c),c);const M=c=>pg.evaluate(c);
const last=async()=>JSON.parse(await M("window.__st.configs[window.__st.configs.length-1]||'null'"));
ok(await last()!==null,'config pushed on start');
ok(JSON.stringify((await last()).limits)==='{}','no limits at first');
ok(/^#[0-9a-f]{6}$/.test((await last()).accent),'accent pushed: '+(await last()).accent);
await E("navigate('more')");await pg.waitForTimeout(300);
ok(await pg.isVisible('[data-action="stOpen"]'),'entry card in Настройки');
ok((await pg.textContent('#content')).includes('уведомлений и экранного времени'),'offline text updated');
await pg.screenshot({path:out+'/1_more.png'});
await pg.click('[data-action="stOpen"]');await pg.waitForTimeout(400);
ok(await E("page")==='screen','screen page opened');
ok(await pg.isVisible('.st-setup'),'setup card shown without permissions');
ok(await E("document.querySelector('[data-page=\"more\"].nav-item').getAttribute('aria-current')")==='page','nav highlights Ещё');
await pg.screenshot({path:out+'/2_setup.png',fullPage:true});
await pg.click('[data-action="stPerm"][data-id="usage"]');await pg.waitForTimeout(2600);
ok(await M("window.__st.calls.includes('openUsage')"),'usage settings requested');
ok(await pg.isVisible('.st-hero'),'hero after usage access (auto refresh)');
await pg.click('[data-action="stPerm"][data-id="overlay"]');await pg.waitForTimeout(2600);
ok((await pg.textContent('.st-setup h3')).includes('Почти'),'only battery step left');
await pg.screenshot({path:out+'/3_almost.png',fullPage:true});
await pg.click('[data-action="stPerm"][data-id="battery"]');await pg.waitForTimeout(2600);
ok(!(await pg.isVisible('.st-setup')),'setup card gone when all granted');
ok((await pg.textContent('.st-hero .lim-big'))==='2 ч 53 мин','total today 2 ч 53 мин (launcher excluded): '+await pg.textContent('.st-hero .lim-big'));
ok(await pg.locator('.st-trow').count()===5,'today list top 5');
await pg.waitForTimeout(500);
ok(await pg.locator('.st-today img.st-ico').count()===5,'icons loaded lazily');
await pg.screenshot({path:out+'/4_empty_limits.png',fullPage:true});
// add YouTube via picker
await pg.click('.lim-cta[data-action="stAdd"]');await pg.waitForTimeout(400);
ok(await pg.locator('.st-app').count()===9,'picker lists 9 apps');
ok((await pg.textContent('.st-app:first-child .st-app-name'))==='Telegram','picker sorted by usage today');
await pg.waitForTimeout(400);await pg.screenshot({path:out+'/5_picker.png'});
await pg.fill('.st-search','you');await pg.waitForTimeout(100);
ok(await pg.locator('.st-app:not([hidden])').count()===1,'search filters to 1');
await pg.press('.st-search','Enter');await pg.waitForTimeout(100);
ok(await E("!!modal"),'Enter in search does not submit');
await pg.click('.st-app:not([hidden])');await pg.click('.st-chip[data-m="30"]');await pg.waitForTimeout(100);
ok((await pg.textContent('#stPreviewText')).includes('превышен на 17 мин'),'preview shows over: '+await pg.textContent('#stPreviewText'));
await pg.screenshot({path:out+'/6_picker_chosen.png'});
await pg.click('#modalBody button[type=submit]');await pg.waitForTimeout(400);
ok(JSON.stringify((await last()).limits)==='{"com.google.android.youtube":30}','limit pushed to native');
ok(await pg.locator('.lim-row').count()===1,'one limit row');
ok((await pg.textContent('.lim-row .lim-line b')).replace(/\s+/g,' ')==='47 / 30 мин','row shows 47 / 30 мин');
ok(await pg.locator('.lim-row.lvl-over').count()===1,'row is over');
// add Telegram from today list with typed minutes
await pg.click('.st-trow [data-action="stAddFor"][data-id="org.telegram.messenger"]');await pg.waitForTimeout(300);
ok(await pg.isVisible('.cat-preview'),'preset app modal');
await pg.fill('input[name=minutes]','12x0');ok(await pg.inputValue('input[name=minutes]')==='120','digits only');
ok(await pg.getAttribute('.st-chip[data-m="120"]','aria-pressed')==='true','chip 2 ч follows input');
await pg.click('#modalBody button[type=submit]');await pg.waitForTimeout(400);
// TikTok 30 → warn (25/30)
await pg.click('.st-trow [data-action="stAddFor"][data-id="com.zhiliaoapp.musically"]');await pg.waitForTimeout(200);await pg.click('.st-chip[data-m="30"]');await pg.click('#modalBody button[type=submit]');await pg.waitForTimeout(400);
ok(await pg.locator('.lim-row').count()===3,'three limits');
ok(await pg.locator('.lim-row.lvl-warn').count()===1,'tiktok warn');
const L=(await last()).limits;ok(L['org.telegram.messenger']===120&&L['com.zhiliaoapp.musically']===30,'all limits pushed');
await pg.waitForTimeout(500);await pg.screenshot({path:out+'/7_limits.png',fullPage:true});
// bad input
await pg.click('[data-action="stEdit"][data-id="org.telegram.messenger"]');await pg.waitForTimeout(300);
await pg.fill('input[name=minutes]','0');await pg.click('#modalBody button[type=submit]');await pg.waitForTimeout(200);
ok(await E("!!modal"),'0 minutes rejected');
await pg.fill('input[name=minutes]','2000');await pg.click('#modalBody button[type=submit]');await pg.waitForTimeout(200);
ok(await E("!!modal"),'2000 minutes rejected');
await pg.click('#stLimitDelete');await pg.waitForTimeout(400);
ok(!(await last()).limits['org.telegram.messenger'],'delete pushed');
ok(await pg.locator('.lim-row').count()===2,'two limits after delete');
// settings
await pg.click('[data-action="stToggle"][data-id="compact"]');await pg.waitForTimeout(200);
ok((await last()).compact===false,'compact off pushed');ok(!(await pg.locator('.st-pill.anim').count()),'preview stops collapsing');
await pg.click('[data-action="stPos"][data-id="1"]');await pg.waitForTimeout(200);
ok((await last()).pos===1&&await pg.getAttribute('.st-pill','data-pos')==='1','position left');
await pg.click('[data-action="stToggle"][data-id="enabled"]');await pg.waitForTimeout(200);
ok((await last()).enabled===false&&await pg.isDisabled('[data-action="stToggle"][data-id="compact"]'),'master switch off disables others');
await pg.click('[data-action="stToggle"][data-id="enabled"]');await pg.click('[data-action="stToggle"][data-id="compact"]');await pg.click('[data-action="stPos"][data-id="0"]');await pg.waitForTimeout(300);
await pg.locator('.st-set').scrollIntoViewIfNeeded();await pg.waitForTimeout(500);await pg.screenshot({path:out+'/8_settings.png'});
await pg.waitForTimeout(3200);await pg.screenshot({path:out+'/8b_settings_collapsed.png'});
// theme change pushes accent
const acc=(await last()).accent;await E("setTheme('amethyst');save();render()");await pg.waitForTimeout(200);
ok((await last()).accent!==acc,'theme accent pushed '+acc+' -> '+(await last()).accent);
await pg.screenshot({path:out+'/9_amethyst.png',fullPage:true});
await E("setTheme('base');save();render()");
// persisted in Lira data (backup)
const saved=JSON.parse(await M("localStorage.getItem('lira_offline_finance_v1')"));
ok(saved.screenTime&&saved.screenTime.limits['com.google.android.youtube']===30,'stored in Lira data');
ok(saved.ops&&saved.currencies,'finance data intact');
// back
await pg.click('.st-back');await pg.waitForTimeout(200);ok(await E("page")==='more','back to Настройки');
ok((await pg.textContent('[data-action="stOpen"] small')).includes('Лимиты для 2 приложений'),'entry shows count');
// reload: limits restored and pushed again
const n=await M("window.__st.configs.length");await pg.reload();await pg.waitForTimeout(900);
ok(JSON.parse(await M("window.__st.configs[window.__st.configs.length-1]")).limits['com.zhiliaoapp.musically']===30,'pushed after restart');
ok(errs.length===0,'no JS errors: '+errs.join(' | '));
await ctx.close();
// without the Android bridge (old WebView / browser)
({pg,errs,ctx}=await open(false));
await pg.evaluate(()=>window.__ev("navigate('screen')"));await pg.waitForTimeout(300);
ok((await pg.textContent('#content')).includes('работает в приложении Лира'),'no-bridge message');
ok(errs.length===0,'no JS errors without bridge: '+errs.join(' | '));
await pg.screenshot({path:out+'/10_nobridge.png'});
await b.close();log(fails?fails+' FAILED':'ALL PASSED');process.exit(fails?1:0)})();
