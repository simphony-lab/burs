# Lira 7.4: screen time page (limits for other apps + the pill on top of them).
import sys
src, dst = sys.argv[1], sys.argv[2]
s = open(src, encoding='utf-8').read()

def once(old, new, count=1):
    global s
    n = s.count(old)
    assert n == count, (old[:60], n)
    s = s.replace(old, new)

CSS = r'''
/* Lira 7.4 — screen time */
.st-back{display:inline-flex;align-items:center;gap:6px;border:0;background:none;color:var(--sub);font-size:13px;font-weight:650;padding:4px 0;margin:0 0 10px}
.st-back svg{width:16px;height:16px}
.st-ico{width:38px;height:38px;border-radius:11px;flex:none;object-fit:cover;display:grid;place-items:center;background:var(--glass2);color:var(--sub);font-size:15px;font-weight:760}
.st-ico.sm{width:30px;height:30px;border-radius:9px;font-size:13px}
.st-ico.xs{width:16px;height:16px;border-radius:5px;font-size:9px}
.st-setup{border-radius:24px;padding:16px;margin:0 0 18px}
.st-setup h3{margin:0 0 4px;font-size:16px;font-weight:760;letter-spacing:-.2px}
.st-setup>p{margin:0 0 10px;font-size:12px;line-height:1.55;color:var(--sub)}
.st-step{display:flex;align-items:center;gap:12px;padding:11px 0}
.st-step+.st-step{border-top:1px solid var(--line)}
.st-num{width:30px;height:30px;border-radius:50%;flex:none;display:grid;place-items:center;font-size:13px;font-weight:780;color:var(--onaccent);background:var(--accent)}
.st-step.done .st-num{background:var(--glass2);color:var(--pos)}
.st-step.done .st-num svg{width:15px;height:15px}
.st-step-main{flex:1;min-width:0}
.st-step-main b{display:block;font-size:13.5px;font-weight:680;line-height:1.35}
.st-step-main small{display:block;font-size:11.5px;color:var(--sub);line-height:1.45;margin-top:2px}
.st-step .mini-btn{margin:0;flex:none}
.st-step.done .st-step-main b{color:var(--sub)}
.st-ok{font-size:11.5px;font-weight:700;color:var(--pos);flex:none}
.st-opt{display:inline-block;margin-left:6px;padding:1px 7px;border-radius:99px;background:var(--glass2);color:var(--sub);font-size:10px;font-weight:700;vertical-align:1px}
.st-note{margin:10px 0 0;padding:10px 12px;border-radius:14px;background:var(--glass);border:1px solid var(--line);font-size:11px;line-height:1.55;color:var(--sub)}
.st-hero .lim-big{margin:8px 0 6px}
.st-hero-sub{font-size:12.5px;color:var(--sub);line-height:1.5}
.st-hero-sub b{color:var(--fg);font-weight:700}
.st-hero-sub .bad{color:var(--neg)}
.lim-row .st-ico{width:38px;height:38px}
.st-gone{opacity:.55}
.st-today{padding:4px 16px}
.st-trow{display:flex;align-items:center;gap:12px;padding:11px 0}
.st-trow+.st-trow{border-top:1px solid var(--line)}
.st-tmain{flex:1;min-width:0}
.st-tline{display:flex;justify-content:space-between;align-items:baseline;gap:10px}
.st-tline span{font-size:13.5px;font-weight:650;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;min-width:0}
.st-tline b{font-size:12.5px;font-weight:720;white-space:nowrap;font-variant-numeric:tabular-nums;color:var(--sub)}
.st-tbar{height:4px;border-radius:99px;background:var(--glass2);margin-top:7px;overflow:hidden}
.st-tbar i{display:block;height:100%;border-radius:inherit;background:var(--accent2,var(--accent));opacity:.75}
.st-trow .mini-btn{margin:0;padding:8px 10px;flex:none}
.st-set{padding:4px 16px 16px}
.st-sw-row{display:flex;align-items:center;gap:14px;width:100%;text-align:left;border:0;background:none;color:var(--fg);padding:13px 0}
.st-sw-row+.st-sw-row{border-top:1px solid var(--line)}
.st-sw-text{flex:1;min-width:0}
.st-sw-text b{display:block;font-size:13.5px;font-weight:660;line-height:1.35}
.st-sw-text small{display:block;font-size:11.5px;color:var(--sub);line-height:1.45;margin-top:2px}
.st-sw{position:relative;width:46px;height:28px;border-radius:99px;background:var(--glass2);border:1px solid var(--line);flex:none;transition:background .2s}
.st-sw i{position:absolute;top:3px;left:3px;width:20px;height:20px;border-radius:50%;background:var(--sub);transition:transform .22s cubic-bezier(.2,.8,.2,1),background .2s}
.st-sw-row[aria-checked="true"] .st-sw{background:var(--accent);border-color:transparent}
.st-sw-row[aria-checked="true"] .st-sw i{transform:translateX(18px);background:var(--onaccent)}
.st-sw-row:disabled{opacity:.45}
.st-pos{border-top:1px solid var(--line);padding-top:13px}
.st-pos>span{display:block;font-size:12px;font-weight:680;color:var(--sub);margin-bottom:8px}
.st-preview{position:relative;height:122px;margin-top:14px;border-radius:18px;overflow:hidden;background:#f4f6f8;border:1px solid var(--line)}
.st-sb{position:absolute;left:0;right:0;top:0;height:24px;display:flex;align-items:center;justify-content:space-between;padding:0 14px;font-size:10.5px;font-weight:700;color:#1b1f24}
.st-sb i{display:inline-block;width:14px;height:7px;margin-left:4px;border-radius:2px;background:#1b1f24;opacity:.75}
.st-fake{position:absolute;left:12px;right:12px;height:22px;border-radius:9px;background:#e3e8ee}
.st-pill{position:absolute;top:30px;left:50%;transform:translateX(-50%);opacity:.8;padding:7px 12px 8px;border-radius:19px;background:rgba(15,23,36,.98);border:1px solid rgba(255,255,255,.16);box-shadow:0 6px 18px rgba(0,0,0,.3);color:#f3f8ff;white-space:nowrap;font-family:Roboto,Inter,Arial,sans-serif}
.st-pill[data-pos="1"]{left:12px;transform:none}
.st-pill[data-pos="2"]{left:auto;right:12px;transform:none}
.st-pr{display:flex;align-items:center;font-size:12.5px;line-height:1.25}
.st-pr .st-ico{margin-right:7px}
.st-pn{display:inline-block;overflow:hidden;max-width:120px;margin-right:10px;font-weight:560}
.st-pv{font-weight:760;font-variant-numeric:tabular-nums}
.st-pv em{font-style:normal;color:#a7bad0;display:inline-block;overflow:hidden;vertical-align:bottom}
.st-pv .st-short{max-width:0;opacity:0}
.st-pb{height:3px;border-radius:99px;background:rgba(255,255,255,.18);margin-top:6px;overflow:hidden}
.st-pb i{display:block;width:40%;height:100%;border-radius:inherit;background:var(--accent)}
.st-pill.anim .st-pn{animation:stName 7s ease-in-out infinite}
.st-pill.anim .st-full{animation:stFull 7s ease-in-out infinite}
.st-pill.anim .st-short{animation:stShort 7s ease-in-out infinite}
@keyframes stName{0%,42%{max-width:120px;opacity:1;margin-right:10px}50%,92%{max-width:0;opacity:0;margin-right:0}100%{max-width:120px;opacity:1;margin-right:10px}}
@keyframes stFull{0%,42%{max-width:80px;opacity:1}50%,92%{max-width:0;opacity:0}100%{max-width:80px;opacity:1}}
@keyframes stShort{0%,42%{max-width:0;opacity:0}50%,92%{max-width:40px;opacity:1}100%{max-width:0;opacity:0}}
.st-pill.off{opacity:.25;filter:grayscale(1)}
@media (prefers-reduced-motion:reduce){.st-pill.anim .st-pn,.st-pill.anim .st-full,.st-pill.anim .st-short{animation:none}}
.st-search{margin-bottom:10px}
.st-pick{display:grid;gap:6px;max-height:min(46vh,360px);overflow:auto;padding:2px;margin:0 -2px;overscroll-behavior:contain}
.st-app{position:relative;display:block;cursor:pointer}
.st-app input{position:absolute!important;left:0;top:0;opacity:0!important;width:1px!important;height:1px!important;min-height:0!important;margin:0!important;padding:0!important;border:0!important;pointer-events:none}
.st-app-in{display:flex;align-items:center;gap:12px;padding:9px 11px;border-radius:15px;border:1px solid var(--line);background:var(--inputbg);transition:border-color .15s,background .15s}
.st-app input:checked+.st-app-in{border-color:var(--accent);background:var(--glass2);box-shadow:inset 0 0 0 1px var(--accent)}
.st-app-name{flex:1;min-width:0;font-size:13.5px;font-weight:620;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.st-app small{font-size:11px;color:var(--sub);white-space:nowrap;font-variant-numeric:tabular-nums}
.st-app[hidden]{display:none}
.st-empty{padding:16px;text-align:center;font-size:12.5px;color:var(--sub)}
.st-chips{display:flex;flex-wrap:wrap;gap:7px;margin-bottom:10px}
.st-chip{border:1px solid var(--line);background:var(--inputbg);color:var(--fg);border-radius:99px;padding:8px 13px;font-size:12.5px;font-weight:680}
.st-chip[aria-pressed="true"]{background:var(--accent);color:var(--onaccent);border-color:transparent}
.st-min{display:flex;align-items:center;gap:10px}
.st-min input{flex:1}
.st-min span{font-size:13px;color:var(--sub);font-weight:650}
'''

JS = r'''
/* Lira 7.4 — screen time. Daily limits for other apps. The Android side (window.LiraST, only in
   the app) counts minutes from the system usage history and draws a small pill on top of an app
   with a limit. Settings are kept in S.screenTime, so they are part of backups, and are mirrored
   to the Android side. Nothing here touches finance data. */
var ST=window.LiraST||null,stApps=null,stIcons={},stUsage={},stStatus={},stTimer=null,stTick=0,stPushed=null;
function stCfg(){var c=S.screenTime;if(!c||typeof c!=='object'||Array.isArray(c))c=S.screenTime={};
 if(!c.limits||typeof c.limits!=='object'||Array.isArray(c.limits))c.limits={};if(!c.names||typeof c.names!=='object'||Array.isArray(c.names))c.names={};
 if(typeof c.enabled!=='boolean')c.enabled=true;if(typeof c.compact!=='boolean')c.compact=true;if(typeof c.hideFull!=='boolean')c.hideFull=true;if([0,1,2].indexOf(c.pos)<0)c.pos=0;
 Object.keys(c.limits).forEach(function(p){var m=Math.round(Number(c.limits[p]));if(!(m>=1&&m<=1440))delete c.limits[p];else c.limits[p]=m});return c}
function stAccent(){try{var v=getComputedStyle(document.documentElement).getPropertyValue('--accent').trim();return /^#[0-9a-f]{6}$/i.test(v)?v.toLowerCase():''}catch(e){return ''}}
function stPayload(){var c=stCfg();return JSON.stringify({enabled:c.enabled,compact:c.compact,hideFull:c.hideFull,pos:c.pos,accent:stAccent(),limits:c.limits})}
function stPush(force){if(!ST||!S)return;var p=stPayload();if(!force&&p===stPushed)return;try{if(ST.setConfig(p)!==false)stPushed=p}catch(e){}}
function stCall(fn,fallback){try{var v=ST&&typeof ST[fn]==='function'?ST[fn]():null;return v==null||v===''?fallback:JSON.parse(v)}catch(e){return fallback}}
function stRefresh(){stStatus=stCall('status',{})||{};stUsage=stStatus.usage?stCall('usage',{})||{}:{}}
function stLoadApps(){if(stApps===null){var a=stCall('apps',[]);stApps=Array.isArray(a)?a.filter(function(x){return x&&typeof x.p==='string'&&typeof x.n==='string'}):[];
 var c=stCfg();stApps.forEach(function(x){if(c.limits[x.p])c.names[x.p]=x.n})}return stApps}
function stKnown(p){return (stLoadApps()).some(function(x){return x.p===p})}
function stName(p){var a=stLoadApps().find(function(x){return x.p===p});return a?a.n:(stCfg().names[p]||p)}
function stIconUrl(p){if(!(p in stIcons)){var v='';try{v=ST&&ST.icon?String(ST.icon(p)||''):''}catch(e){}stIcons[p]=/^data:image\/png;base64,[A-Za-z0-9+\/=]+$/.test(v)?v:''}return stIcons[p]}
// Icons are fetched after the page is drawn, a few per frame, so long app lists open instantly.
function stIco(p,cls){var have=stIcons[p];if(have)return '<img class="st-ico '+(cls||'')+'" src="'+have+'" alt="">';
 return '<span class="st-ico '+(cls||'')+'" data-st-icon="'+h(p)+'">'+h((stName(p)||'?').trim().slice(0,1).toUpperCase())+'</span>'}
function stFillIcons(root){var list=Array.prototype.slice.call((root||document).querySelectorAll('[data-st-icon]'));
 (function step(){var batch=list.splice(0,6);batch.forEach(function(el){if(!el.isConnected)return;var url=stIconUrl(el.dataset.stIcon);if(url){var img=document.createElement('img');img.className=el.className;img.src=url;img.alt='';el.replaceWith(img)}else el.removeAttribute('data-st-icon')});if(list.length)setTimeout(step,16)})()}
function stMin(ms){return Math.floor((Number(ms)||0)/60000)}
function stDur(ms){var m=Math.floor((Number(ms)||0)/60000);if(m<1)return 'меньше минуты';var hh=Math.floor(m/60),mm=m%60;return hh?hh+' ч'+(mm?' '+mm+' мин':''):mm+' мин'}
function stLimText(m){m=Number(m)||0;var hh=Math.floor(m/60),mm=m%60;return hh?hh+' ч'+(mm?' '+mm+' мин':''):mm+' мин'}
function stState(p){var lim=stCfg().limits[p]*60000,used=Number(stUsage[p])||0,pct=lim>0?used/lim*100:0;return {used:used,lim:lim,pct:pct,level:pct>=100?'over':pct>=80?'warn':'ok'}}
function stSetup(){var u=!!stStatus.usage,o=!!stStatus.overlay,b=!!stStatus.battery;if(u&&o&&b)return '';
 function step(done,n,title,text,id,btn,opt){return '<div class="st-step'+(done?' done':'')+'"><span class="st-num">'+(done?ico('check',true):n)+'</span><div class="st-step-main"><b>'+title+(opt?'<span class="st-opt">по желанию</span>':'')+'</b><small>'+text+'</small></div>'+(done?'<span class="st-ok">Готово</span>':'<button type="button" class="mini-btn" data-action="stPerm" data-id="'+id+'">'+btn+'</button>')+'</div>'}
 var main=u&&o;
 return '<section class="st-setup glass"><h3>'+(main?'Почти всё готово':'Два разрешения — и всё заработает')+'</h3><p>'+(main?'Плашка уже работает. Чтобы Android не выключал подсчёт в фоне, снимите для Лиры ограничение батареи.':'Android спросит их один раз. Лира ничего не отправляет в интернет: минуты считаются на телефоне.')+'</p>'+
  step(u,1,'Доступ к истории использования','Чтобы считать минуты. В списке выберите «Лира · Финансы» и включите доступ.','usage','Открыть')+
  step(o,2,'Поверх других приложений','Чтобы показывать плашку сверху экрана.','overlay','Разрешить')+
  step(b,3,'Работа в фоне без ограничений','Чтобы Android не останавливал подсчёт.','battery','Настроить',true)+
  (main?'':'<div class="st-note">Если Android пишет «Настройка ограничена», откройте Настройки → Приложения → Лира · Финансы → ⋮ → «Разрешить ограниченные настройки» и попробуйте ещё раз. На Xiaomi также включите «Всплывающие окна в фоне» в разрешениях Лиры.</div>')+'</section>'}
function stHero(){if(!stStatus.usage)return '';var c=stCfg(),total=0;stLoadApps().forEach(function(a){total+=Number(stUsage[a.p])||0});
 var keys=Object.keys(c.limits),over=keys.filter(function(p){return stState(p).level==='over'}).length;
 return '<section class="lim-hero glass st-hero"><div class="kicker">Сегодня в приложениях</div><div class="lim-big">'+h(total<60000?'0 мин':stDur(total))+'</div><div class="st-hero-sub">'+(keys.length?'С лимитом: <b>'+keys.length+'</b>'+(over?' · <span class="bad">превышено: '+over+'</span>':' · всё в рамках'):'Лимитов пока нет — добавьте первое приложение')+'</div></section>'}
function stRow(p){var st=stState(p),gone=stApps&&stApps.length&&!stKnown(p),left=st.lim-st.used;
 var meta=gone?'Приложение не найдено на телефоне':!stStatus.usage?'Нужен доступ к истории использования':st.level==='over'?'<b>Превышен на '+h(stDur(-left))+'</b>':'Осталось <b>'+h(stDur(left))+'</b>';
 return '<div class="lim-row lvl-'+st.level+(gone?' st-gone':'')+'">'+stIco(p)+'<div class="lim-main"><div class="lim-line"><span class="lim-name">'+h(stName(p))+'</span><b>'+stMin(st.used)+' <em>/ '+stCfg().limits[p]+' мин</em></b></div><div class="lim-bar sm"><i style="width:'+Math.min(100,st.pct).toFixed(2)+'%"></i></div><div class="lim-meta">'+meta+'</div></div><button type="button" class="mini-btn" data-action="stEdit" data-id="'+h(p)+'" aria-label="Изменить лимит">'+ico('edit',true)+'</button></div>'}
function stToday(){if(!stStatus.usage)return '';var c=stCfg(),apps=stLoadApps().filter(function(a){return !c.limits[a.p]&&(Number(stUsage[a.p])||0)>=60000}).sort(function(a,b){return stUsage[b.p]-stUsage[a.p]}).slice(0,5);
 if(!apps.length)return '';var max=Number(stUsage[apps[0].p])||1;
 return topSection('Сегодня без лимита',null,null)+'<div class="panel glass st-today">'+apps.map(function(a){var u=Number(stUsage[a.p])||0;return '<div class="st-trow">'+stIco(a.p,'sm')+'<div class="st-tmain"><div class="st-tline"><span>'+h(a.n)+'</span><b>'+h(stDur(u))+'</b></div><div class="st-tbar"><i style="width:'+Math.max(4,u/max*100).toFixed(1)+'%"></i></div></div><button type="button" class="mini-btn" data-action="stAddFor" data-id="'+h(a.p)+'" aria-label="Лимит для '+h(a.n)+'">'+ico('plus',true)+'</button></div>'}).join('')+'</div>'}
function stSwitch(id,on,title,text,disabled){return '<button type="button" class="st-sw-row" role="switch" aria-checked="'+(on?'true':'false')+'" data-action="stToggle" data-id="'+id+'"'+(disabled?' disabled':'')+'><span class="st-sw-text"><b>'+title+'</b><small>'+text+'</small></span><span class="st-sw" aria-hidden="true"><i></i></span></button>'}
function stPreview(){var c=stCfg();return '<div class="st-preview" aria-hidden="true"><div class="st-sb"><span>9:41</span><span><i></i><i></i><i></i></span></div><span class="st-fake" style="top:60px"></span><span class="st-fake" style="top:90px"></span>'+
 '<div class="st-pill'+(c.compact?' anim':'')+(c.enabled?'':' off')+'" data-pos="'+c.pos+'"><div class="st-pr"><span class="st-ico xs" style="background:#ff0033;color:#fff">▶</span><span class="st-pn">YouTube</span><span class="st-pv">12<em class="st-full">&nbsp;/ 30 мин</em><em class="st-short">/30</em></span></div><div class="st-pb"><i></i></div></div></div>'}
function stSettings(){var c=stCfg();
 return topSection('Плашка',null,null)+'<div class="panel glass st-set">'+
  stSwitch('enabled',c.enabled,'Показывать плашку','Сверху экрана, когда открыто приложение с лимитом')+
  stSwitch('compact',c.compact,'Сворачивать через 4 секунды','Потом остаются только минуты и шкала. При 80% и 100% плашка снова раскроется',!c.enabled)+
  stSwitch('hideFull',c.hideFull,'Прятать в полноэкранном режиме','Видео и игры на весь экран — без плашки',!c.enabled)+
  '<div class="st-pos"><span>Где показывать</span><div class="seg seg3">'+[[1,'Слева'],[0,'По центру'],[2,'Справа']].map(function(x){return '<button type="button" data-action="stPos" data-id="'+x[0]+'" aria-pressed="'+(c.pos===x[0]?'true':'false')+'">'+x[1]+'</button>'}).join('')+'</div>'+stPreview()+'</div></div>'}
function stPage(){var c=stCfg(),head='<button type="button" class="st-back" data-page="more">'+ico('back',true)+' Настройки</button><div class="kicker">Цифровой баланс</div><h1 class="heading">Экранное время</h1><p class="page-sub">Дневные лимиты для приложений. Когда вы открываете такое приложение, сверху появляется небольшая плашка: сколько минут уже прошло из разрешённых.</p>';
 if(!ST)return head+'<div class="info-box">Экранное время работает в приложении Лира на Android 6 и новее.</div>';
 stRefresh();stLoadApps();var keys=Object.keys(c.limits).sort(function(a,b){return stState(b).pct-stState(a).pct});
 return head+stSetup()+stHero()+topSection('Лимиты на день',keys.length?'Добавить':null,'stAdd')+
  (keys.length?'<div class="panel glass lim-list">'+keys.map(stRow).join('')+'</div>':v9Cta('stAdd','clock','Добавить приложение','Например, не больше 30 минут в день в YouTube','plus'))+
  stToday()+stSettings()+
  '<p class="sidenote">Минуты считаются по истории использования Android — так же, как в «Цифровом благополучии», с полуночи по времени телефона. Плашка ничего не блокирует и не мешает нажатиям: она только показывает, сколько осталось. Всё остаётся на телефоне. Если Android всё же остановит подсчёт, просто откройте Лиру — минуты не потеряются.</p>'}
function stEntry(){var n=S&&S.screenTime&&S.screenTime.limits?Object.keys(S.screenTime.limits).length:0;
 return '<button type="button" class="lim-cta glass" data-action="stOpen" style="margin:0 0 18px"><span class="lim-cta-ico tint">'+ico('clock')+'</span><span><strong>Экранное время</strong><small>'+(n?'Лимиты для '+n+' '+(n%10===1&&n%100!==11?'приложения':'приложений')+' · плашка поверх них':'Дневные лимиты для приложений и плашка поверх них')+'</small></span>'+ico('arrow',true)+'</button>'}
function stPerm(k){try{if(k==='usage')ST.openUsage();else if(k==='overlay')ST.openOverlay();else ST.openBattery()}catch(e){toast('Не удалось открыть настройки Android')}}
// pkg: null = choose an app; preset: open the picker result directly as a new limit.
function stLimitModal(pkg){var c=stCfg(),old=pkg&&c.limits[pkg]?c.limits[pkg]:0,isNew=!old,apps=stLoadApps();
 if(!pkg&&!apps.length){toast('Не удалось получить список приложений');return}
 var free=apps.filter(function(a){return !c.limits[a.p]}).sort(function(a,b){return (Number(stUsage[b.p])||0)-(Number(stUsage[a.p])||0)});
 if(!pkg&&!free.length){toast('У всех приложений уже есть лимит');return}
 var head=pkg?'<div class="cat-preview">'+stIco(pkg)+'<strong>'+h(stName(pkg))+'</strong></div>':
  '<div class="field"><span>Приложение</span><input type="search" class="st-search" placeholder="Найти приложение" autocomplete="off" aria-label="Найти приложение"><div class="st-pick" role="radiogroup" aria-label="Приложения">'+free.map(function(a){var u=Number(stUsage[a.p])||0;
   return '<label class="st-app" data-name="'+h(a.n.toLowerCase())+'"><input type="radio" name="app" value="'+h(a.p)+'"><span class="st-app-in">'+stIco(a.p,'sm')+'<span class="st-app-name">'+h(a.n)+'</span>'+(u>=60000?'<small>'+h(stDur(u))+' сегодня</small>':'')+'</span></label>'}).join('')+'<div class="st-empty" hidden>Ничего не найдено</div></div></div>';
 var minutes=old||30;
 var html='<form>'+head+'<div class="field"><span>Сколько можно в день</span><div class="st-chips">'+[15,30,45,60,90,120].map(function(m){return '<button type="button" class="st-chip" data-m="'+m+'" aria-pressed="'+(m===minutes?'true':'false')+'">'+stLimText(m)+'</button>'}).join('')+'</div>'+
  '<label class="st-min"><input name="minutes" type="text" inputmode="numeric" maxlength="4" autocomplete="off" value="'+minutes+'" aria-label="Минут в день"><span>мин в день</span></label></div>'+
  '<div class="info-box" id="stPreviewText"></div>'+buttonSave(isNew?'Установить лимит':'Сохранить лимит')+'</form>'+(old?'<div class="sheet-actions"><button type="button" class="mini-btn danger" id="stLimitDelete">'+ico('trash',true)+' Удалить лимит</button></div>':'');
 openModal(isNew?'Лимит для приложения':'Лимит приложения',html,function(fd){
  var p=pkg||String(fd.get('app')||''),m=Number(String(fd.get('minutes')||'').replace(/\s/g,''));
  if(!p){toast('Выберите приложение');return}
  if(!(Math.round(m)===m&&m>=1&&m<=1440)){toast('Укажите от 1 до 1440 минут');return}
  c.limits[p]=m;c.names[p]=stName(p);c.updated=Date.now();
  if(!save())return;stPush();closeModal();render();toast(old?'Лимит обновлён':'Лимит установлен: '+stLimText(m)+' в день')});
 var body=$('modalBody'),form=body.querySelector('form');stFillIcons(body);
 function current(){return pkg||(form.querySelector('input[name=app]:checked')||{}).value||''}
 function preview(){var m=Number(form.elements.minutes.value),p=current();Array.prototype.forEach.call(form.querySelectorAll('.st-chip'),function(b){b.setAttribute('aria-pressed',String(Number(b.dataset.m)===m))});
  var box=$('stPreviewText');if(!p){box.textContent='Выберите приложение из списка.';return}if(!(m>=1&&m<=1440)){box.textContent='Лимит — от 1 минуты до 24 часов в день.';return}
  var used=Number(stUsage[p])||0,left=m*60000-used;box.innerHTML=stStatus.usage?(used<60000?'Сегодня в «'+h(stName(p))+'» ещё меньше минуты. ':'Сегодня в «'+h(stName(p))+'» уже '+h(stDur(used))+'. ')+(left>=0?'Останется <b>'+h(stDur(left))+'</b>.':'Лимит на сегодня уже превышен на <b>'+h(stDur(-left))+'</b> — плашка сразу будет красной.'):'Минуты появятся, когда вы дадите доступ к истории использования.'}
 form.addEventListener('click',function(e){var b=e.target.closest('.st-chip');if(!b)return;e.preventDefault();form.elements.minutes.value=b.dataset.m;preview()});
 form.addEventListener('input',function(e){if(e.target.name==='minutes'){var v=e.target.value.replace(/\D/g,'').slice(0,4);if(v!==e.target.value)e.target.value=v}if(e.target.classList.contains('st-search')){var q=e.target.value.trim().toLowerCase(),shown=0;Array.prototype.forEach.call(form.querySelectorAll('.st-app'),function(l){var ok=!q||l.dataset.name.indexOf(q)>=0;l.hidden=!ok;if(ok)shown++});form.querySelector('.st-empty').hidden=shown>0}preview()});
 form.addEventListener('change',preview);preview();
 var search=form.querySelector('.st-search');if(search)search.addEventListener('keydown',function(e){if(e.key==='Enter')e.preventDefault()});
 var del=$('stLimitDelete');if(del)del.onclick=function(){delete c.limits[pkg];if(!save())return;stPush();closeModal();render();toast('Лимит удалён')}}
// While the page is open: notice permissions granted in Android settings and refresh minutes.
function stWatch(){if(stTimer||!ST)return;stTimer=setInterval(function(){if(page!=='screen'){stUnwatch();return}if(modal||dtSheet)return;stTick++;
 var before=JSON.stringify(stStatus),now=stCall('status',{})||{};if(JSON.stringify(now)!==before){stPush(true);render();return}if(stTick%15===0)render()},2000)}
function stUnwatch(){if(stTimer){clearInterval(stTimer);stTimer=null}}
var stOldRender=render;render=function(){if(S)stCfg();if(page==='screen'&&S){renderNav();$('content').innerHTML='<section class="page">'+stPage()+'</section>';try{v8TopBar()}catch(e){}stFillIcons($('content'));stWatch()}else{stUnwatch();stOldRender()}if(S)stPush()};
var stOldRenderNav=renderNav;renderNav=function(){stOldRenderNav();if(page==='screen'){var m=$('navigation').querySelector('[data-page="more"]');if(m)m.setAttribute('aria-current','page')}};
var stOldMorePage=morePage;morePage=function(){var html=stOldMorePage(),i=html.indexOf('</p>');return i<0?stEntry()+html:html.slice(0,i+4)+stEntry()+html.slice(i+4)};
var stOldSetTheme=setTheme;setTheme=function(key){stOldSetTheme(key);if(S)stPush()};
var stOldHandleAction=handleAction;handleAction=function(e){var b=e.target.closest('[data-page],[data-action]'),a=b&&b.dataset.action;
 if(a==='stOpen'){navigate('screen');return}
 if(a==='stAdd'){stLimitModal(null);return}
 if(a==='stAddFor'||a==='stEdit'){stLimitModal(b.dataset.id);return}
 if(a==='stPerm'){stPerm(b.dataset.id);return}
 if(a==='stToggle'){if(b.disabled)return;var c=stCfg(),k=b.dataset.id;if(['enabled','compact','hideFull'].indexOf(k)>=0){c[k]=!c[k];if(save()){stPush();render()}}return}
 if(a==='stPos'){var c2=stCfg();c2.pos=Number(b.dataset.id)||0;if(save()){stPush();render()}return}
 stOldHandleAction(e)};
'''

once('</style>\n</head>', CSS + '</style>\n</head>')
once("Без интернета · разрешение только на уведомления", "Без интернета · разрешения только для уведомлений и экранного времени", 2)
once('\ninit();\n})();', '\n' + JS + '\ninit();\n})();')
open(dst, 'w', encoding='utf-8').write(s)
print('ok', len(s))
