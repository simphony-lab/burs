# Lira 7.5: dynamic island + curfew settings, tasks for the island, plan repeats,
# habits with streak tiers and 66-day formation, motion and visual polish, icon pack.
# usage: python3 ui_patch_75.py app74.html app75.html
import sys
src, dst = sys.argv[1], sys.argv[2]
s = open(src, encoding='utf-8').read()


def once(old, new, count=1):
    global s
    n = s.count(old)
    assert n == count, (old[:70], n)
    s = s.replace(old, new)


CSS = r'''
/* ===== Lira 7.5 ===== */
/* logo glow follows the theme instead of always blue */
.about img{filter:drop-shadow(0 8px 18px rgba(0,0,0,.35));filter:drop-shadow(0 8px 20px color-mix(in srgb,var(--accent) 42%,transparent))}
/* motion: pages only animate when you switch sections, not on every update */
.page{animation:none}
.page.enter{--dx:calc(var(--nav-dir,1) * 16px)}
.page.enter>*{animation:v75Up .56s cubic-bezier(.2,.8,.2,1) both}
.page.enter>*:nth-child(2){animation-delay:.03s}.page.enter>*:nth-child(3){animation-delay:.06s}.page.enter>*:nth-child(4){animation-delay:.09s}
.page.enter>*:nth-child(5){animation-delay:.12s}.page.enter>*:nth-child(6){animation-delay:.15s}.page.enter>*:nth-child(7){animation-delay:.18s}
.page.enter>*:nth-child(8){animation-delay:.21s}.page.enter>*:nth-child(9){animation-delay:.24s}.page.enter>*:nth-child(n+10){animation-delay:.27s}
@keyframes v75Up{from{opacity:0;transform:translate3d(var(--dx),10px,0) scale(.985)}to{opacity:1;transform:none}}
.overlay.open{animation:v75Fade .28s ease both}
.overlay.open .sheet{animation:v75SheetIn .52s cubic-bezier(.16,1.12,.3,1) both}
@keyframes v75Fade{from{opacity:0}to{opacity:1}}
@keyframes v75SheetIn{from{transform:translateY(60%);opacity:.4}to{transform:none;opacity:1}}
.v75-ghost{position:fixed;z-index:40;pointer-events:none;margin:0}
.v75-ghost .sheet{animation:v75SheetOut .3s cubic-bezier(.4,0,.8,.6) both;margin:0;max-height:none}
.v75-ghost-bg{position:fixed;inset:0;z-index:39;pointer-events:none;background:rgba(0,0,0,.58);animation:v75FadeOut .3s ease both}
@keyframes v75SheetOut{to{transform:translateY(46%);opacity:0}}
@keyframes v75FadeOut{to{opacity:0}}
.toast{transition:transform .5s cubic-bezier(.2,1.35,.3,1),opacity .25s ease}
.nav-item.pop .nav-ico{animation:v75NavPop .5s cubic-bezier(.2,1.4,.3,1)}
@keyframes v75NavPop{0%{transform:translateY(0) scale(.8)}60%{transform:translateY(-3px) scale(1.08)}100%{transform:translateY(-2px) scale(1)}}
.mini-btn,.primary,.quick-btn,.lim-cta,.theme-option,.st-chip,.seg button,.daily-entry,.plan-today,.plan-archive-row,.weekday-preset button,.hb-chip,.hb-card,.plan-task-mark,.v75-card{transition:transform .2s cubic-bezier(.2,.8,.2,1),filter .2s,background .2s,border-color .2s}
.mini-btn:active,.primary:active,.quick-btn:active,.lim-cta:active,.theme-option:active,.st-chip:active,.seg button:active,.daily-entry:active,.plan-today:active,.plan-archive-row:active,.hb-chip:active,.v75-card:active{transform:scale(.965)}
.plan-task-mark.just{animation:v75Pop .55s cubic-bezier(.2,1.5,.3,1)}
.plan-task-mark.just svg path,.plan-task-mark.just svg polyline{stroke-dasharray:30;stroke-dashoffset:30;animation:v75Draw .45s .08s cubic-bezier(.3,.7,.2,1) forwards}
.plan-task.completed .plan-task-mark{background:var(--accent);color:var(--onaccent);border-color:var(--accent)}
.plan-task{transition:opacity .3s,background .3s}
@keyframes v75Pop{0%{transform:scale(.7)}55%{transform:scale(1.15)}100%{transform:scale(1)}}
@keyframes v75Draw{to{stroke-dashoffset:0}}
.glass{transition:border-color .25s,background .25s}
@media (prefers-reduced-motion:reduce){.page.enter>*,.overlay.open,.overlay.open .sheet,.plan-task-mark.just,.nav-item.pop .nav-ico{animation:none!important}.v75-ghost,.v75-ghost-bg{display:none}}

/* island preview + cards on the screen-time page */
.v75-card{display:flex;align-items:center;gap:13px;width:100%;text-align:left;color:var(--fg);border-radius:22px;padding:15px 16px;margin:0 0 12px}
.v75-card>span:nth-child(2){flex:1;min-width:0;display:grid;gap:3px}
.v75-card strong{font-size:15px;font-weight:720}
.v75-card small{font-size:11.5px;color:var(--sub);line-height:1.45}
.v75-card .st-sw{flex:none}
.v75-card .mini-btn{margin:0;flex:none}
.v75-moon{color:#b9a8ff}
.v75-moon:before{background:#b9a8ff!important}
.v75-cf-state{display:inline-block;margin-top:3px;font-size:11.5px;font-weight:700;color:var(--accent)}
.ip-phone{position:relative;height:148px;border-radius:22px;overflow:hidden;background:radial-gradient(120% 90% at 50% 0%,#2a3346,#0d1118 70%);margin:2px 0 14px;border:1px solid var(--line)}
.ip-sb{position:absolute;top:0;left:0;right:0;height:26px;display:flex;justify-content:space-between;align-items:center;padding:0 16px;color:#fff;font:650 11px Roboto,Inter,Arial,sans-serif;z-index:3}
.ip-sb i{display:inline-block;width:12px;height:6px;margin-left:3px;border-radius:2px;background:#fff;opacity:.85}
.ip-island{position:absolute;left:50%;top:4px;transform:translateX(-50%);background:#000;width:86px;height:20px;border-radius:11px;overflow:hidden;z-index:2;animation:ipShape 12s infinite}
.ip-cam{position:absolute;left:50%;top:9px;width:9px;height:9px;margin-left:-4.5px;border-radius:50%;background:#0a0d13;box-shadow:inset 0 0 0 2px #030406,0 0 0 1px #111;z-index:4}
.ip-app{position:absolute;left:12px;right:12px;top:78px;height:20px;border-radius:9px;background:rgba(255,255,255,.07);box-shadow:0 30px 0 rgba(255,255,255,.05)}
@keyframes ipShape{0%,7%{width:86px;height:20px;border-radius:11px;animation-timing-function:cubic-bezier(.25,1.45,.55,1)}14%,84%{width:236px;height:58px;border-radius:24px;animation-timing-function:cubic-bezier(.45,0,.2,1)}92%,100%{width:86px;height:20px;border-radius:11px}}
.ip-l{position:absolute;left:15px;right:15px;bottom:8px;height:22px;display:flex;align-items:center;gap:8px;color:#fff;font:600 12px Roboto,Inter,Arial,sans-serif;opacity:0;white-space:nowrap}
.ip-l b{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;font-weight:600}
.ip-l em{font-style:normal;font-weight:700;font-variant-numeric:tabular-nums;color:#ffb340}
.ip-l .ip-plus{color:#fff;background:#2c2c2e;border-radius:9px;padding:2px 7px;font-size:11px}
.ip-ring{width:18px;height:18px;border-radius:50%;flex:none;background:conic-gradient(var(--c) 0 var(--p),#2c2c2e var(--p) 100%);display:grid;place-items:center}
.ip-ring:after{content:'';width:12px;height:12px;border-radius:50%;background:#000}
.ip-ring.dot:after{width:12px;height:12px;background:radial-gradient(circle,var(--c) 0 3px,#000 3.5px)}
.ip-ring.moon:after{background:radial-gradient(circle at 70% 30%,#000 0 4px,#b9a8ff 4.5px 6px,#000 6.5px)}
.ip-task{animation:ipA 12s infinite}.ip-cur{animation:ipB 12s infinite}.ip-lim{animation:ipC 12s infinite}
@keyframes ipA{0%,12%{opacity:0;transform:scale(.9);filter:blur(4px)}18%,30%{opacity:1;transform:none;filter:none}35%,100%{opacity:0;transform:translateY(-6px);filter:blur(3px)}}
@keyframes ipB{0%,34%{opacity:0;transform:translateY(6px)}39%,56%{opacity:1;transform:none}61%,100%{opacity:0;transform:translateY(-6px)}}
@keyframes ipC{0%,60%{opacity:0;transform:translateY(6px)}65%,81%{opacity:1;transform:none}86%,100%{opacity:0;transform:scale(.92);filter:blur(3px)}}
@media (prefers-reduced-motion:reduce){.ip-island,.ip-l{animation:none}.ip-island{width:236px;height:58px;border-radius:24px}.ip-task{opacity:1}}

/* plan repeats */
.rp-badge{display:inline-flex;align-items:center;gap:3px;font-style:normal;color:var(--accent);font-weight:650}
.rp-badge svg{width:12px!important;height:12px!important}
.rp-days[hidden]{display:none}
.rp-scope{display:flex;align-items:center;gap:10px;margin:-4px 0 16px;font-size:12.5px;color:var(--sub);cursor:pointer}
.rp-scope input{position:static!important;opacity:1!important;width:18px!important;height:18px!important;pointer-events:auto!important;clip-path:none!important;accent-color:var(--accent)}
.rp-list{padding:4px 14px}
.rp-row{display:flex;align-items:center;gap:11px;padding:11px 0}
.rp-row+.rp-row{border-top:1px solid var(--line)}
.rp-row>span:nth-child(2){flex:1;min-width:0;display:grid;gap:2px}
.rp-row strong{font-size:13.5px;font-weight:660;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.rp-row small{font-size:11px;color:var(--sub)}
.rp-row .mini-btn{margin:0;padding:8px 10px}

/* habits */
.hb-hero{display:flex;align-items:center;gap:16px;border-radius:26px;padding:18px;margin:4px 0 20px}
.hb-ring{--p:0;position:relative;width:86px;height:86px;flex:none;border-radius:50%;background:conic-gradient(var(--accent) calc(var(--p)*1%),var(--glass2) 0);display:grid;place-items:center;transition:--p .6s}
.hb-ring:before{content:'';position:absolute;inset:7px;border-radius:50%;background:var(--base2,var(--bg))}
.hb-ring b{position:relative;font-size:22px;font-weight:800;letter-spacing:-.6px;font-variant-numeric:tabular-nums}
.hb-ring b small{font-size:12px;color:var(--sub);font-weight:650}
.hb-hero-main{flex:1;min-width:0;display:grid;gap:4px}
.hb-hero-main strong{font-size:17px;font-weight:760;letter-spacing:-.3px}
.hb-hero-main span{font-size:12px;color:var(--sub);line-height:1.5}
.hb-best{display:flex;align-items:center;gap:8px;margin-top:4px;font-size:12px;color:var(--sub)}
.hb-best b{color:var(--fg)}
.hb-list{display:grid;gap:10px}
.hb-card{display:flex;align-items:center;gap:13px;border-radius:22px;padding:13px 13px 13px 12px;color:var(--fg);text-align:left;width:100%;cursor:pointer}
.hb-card.is-done{background:linear-gradient(120deg,color-mix(in srgb,var(--accent) 12%,transparent),transparent 60%),var(--glass)}
.hb-main{flex:1;min-width:0;display:grid;gap:5px}
.hb-title{font-size:15px;font-weight:700;letter-spacing:-.2px;line-height:1.3;overflow-wrap:anywhere}
.hb-sub{font-size:11.5px;color:var(--sub);line-height:1.4}
.hb-sub b{color:var(--fg);font-weight:700}
.hb-bars{display:grid;grid-template-columns:1fr auto;align-items:center;gap:8px}
.hb-bar{height:5px;border-radius:99px;background:var(--glass2);overflow:hidden}
.hb-bar i{display:block;height:100%;border-radius:inherit;background:linear-gradient(90deg,var(--ta,var(--accent)),var(--tb,var(--accent)));transition:width .6s cubic-bezier(.2,.8,.2,1)}
.hb-bars small{font-size:10.5px;color:var(--sub);font-variant-numeric:tabular-nums;white-space:nowrap}
.hb-week{display:flex;gap:4px;margin-top:1px}
.hb-week i{width:14px;height:5px;border-radius:3px;background:var(--glass2)}
.hb-week i.done{background:var(--accent)}
.hb-week i.missed{background:var(--neg)}
.hb-week i.off{opacity:.35}
.hb-week i.today{box-shadow:0 0 0 1.5px var(--fg)}
.hb-check{position:relative;width:46px;height:46px;flex:none;border-radius:50%;border:2px solid var(--line);background:var(--glass);display:grid;place-items:center;color:var(--onaccent)}
.hb-check svg{width:22px;height:22px;stroke:currentColor;stroke-width:3;fill:none;stroke-linecap:round;stroke-linejoin:round;opacity:0}
.hb-check.on{background:var(--accent);border-color:var(--accent);box-shadow:0 6px 18px color-mix(in srgb,var(--accent) 35%,transparent)}
.hb-check.on svg{opacity:1}
.hb-check.just{animation:v75Pop .55s cubic-bezier(.2,1.5,.3,1)}
.hb-check.just svg path{stroke-dasharray:24;stroke-dashoffset:24;animation:v75Draw .42s .1s cubic-bezier(.3,.7,.2,1) forwards}
.hb-check.just:after{content:'';position:absolute;inset:-2px;border-radius:50%;border:2px solid var(--accent);animation:hbRing .7s ease-out forwards}
@keyframes hbRing{from{transform:scale(1);opacity:.9}to{transform:scale(1.7);opacity:0}}
.hb-check:disabled{opacity:.35}
.hb-add{display:flex;gap:10px;margin:18px 0 6px}
.hb-add .primary{flex:1}
.hb-chips{display:flex;flex-wrap:wrap;gap:7px;margin:-4px 0 16px}
.hb-chip{border:1px solid var(--line);background:var(--glass);color:var(--fg);border-radius:99px;padding:8px 12px;font-size:12px;font-weight:650}
.hb-emb{display:inline-grid;place-items:center;flex:none;filter:drop-shadow(0 4px 10px var(--glow,transparent))}
.hb-emb svg{width:100%;height:100%;overflow:visible}
.hb-emb.locked{filter:grayscale(1);opacity:.32}
.hb-emb.b2 .hb-shine,.hb-emb.b3 .hb-shine{animation:hbShine 3.2s ease-in-out infinite;transform-origin:32px 32px}
.hb-emb.b3 .hb-orbit{animation:hbSpin 9s linear infinite;transform-origin:32px 32px}
@keyframes hbShine{0%,100%{opacity:.15}50%{opacity:.5}}
@keyframes hbSpin{to{transform:rotate(360deg)}}
.hb-d-top{display:flex;align-items:center;gap:16px;margin:0 0 16px}
.hb-d-top h3{margin:2px 0 4px;font-size:22px;font-weight:800;letter-spacing:-.5px}
.hb-d-top p{margin:0;font-size:12.5px;color:var(--sub)}
.hb-box{border-radius:18px;padding:14px;background:var(--glass);border:1px solid var(--line);margin:0 0 12px}
.hb-box-head{display:flex;justify-content:space-between;align-items:baseline;gap:10px;margin-bottom:9px}
.hb-box-head b{font-size:13.5px}
.hb-box-head span{font-size:12px;color:var(--sub);font-variant-numeric:tabular-nums}
.hb-box p{margin:9px 0 0;font-size:11.5px;line-height:1.5;color:var(--sub)}
.hb-66{display:flex;align-items:center;gap:14px}
.hb-66 .hb-ring{width:70px;height:70px}
.hb-66 .hb-ring b{font-size:16px}
.hb-ladder{display:grid;grid-template-columns:repeat(auto-fill,minmax(54px,1fr));gap:8px;margin:0 0 14px}
.hb-step{display:grid;justify-items:center;gap:3px;font-size:10.5px;color:var(--sub);font-variant-numeric:tabular-nums}
.hb-step.cur{color:var(--fg);font-weight:800}
.hb-step.next .hb-emb{outline:2px dashed var(--line);outline-offset:2px;border-radius:50%}
.hb-cele{position:fixed;inset:0;z-index:60;display:grid;place-items:center;background:rgba(3,5,10,.93);background:radial-gradient(circle at 50% 40%,color-mix(in srgb,var(--cb,#fff) 26%,rgba(3,5,10,.93)),rgba(3,5,10,.95) 60%);-webkit-backdrop-filter:blur(14px);backdrop-filter:blur(14px);animation:v75Fade .3s ease both;padding:24px}
.hb-cele-card{position:relative;text-align:center;display:grid;justify-items:center;gap:8px;max-width:320px;animation:hbCeleIn .7s cubic-bezier(.2,1.3,.3,1) both}
.hb-cele-card .hb-emb{animation:hbFloat 3s ease-in-out .7s infinite}
.hb-cele-card h2{margin:6px 0 0;font-size:30px;font-weight:850;letter-spacing:-1px;color:#fff}
.hb-cele-card p{margin:0 0 12px;color:rgba(255,255,255,.75);font-size:14px;line-height:1.5}
.hb-cele-card .kicker{color:rgba(255,255,255,.8)}
.hb-cele-card .primary{min-width:200px}
.hb-spark{position:absolute;left:50%;top:38%;width:8px;height:8px;border-radius:50%;background:var(--c);animation:hbBurst 1.1s cubic-bezier(.1,.8,.3,1) forwards;pointer-events:none}
@keyframes hbBurst{from{transform:translate(-50%,-50%) scale(1);opacity:1}to{transform:translate(calc(-50% + var(--x)),calc(-50% + var(--y))) scale(.2);opacity:0}}
@keyframes hbCeleIn{from{transform:scale(.6) translateY(30px);opacity:0}to{transform:none;opacity:1}}
@keyframes hbFloat{0%,100%{transform:translateY(0)}50%{transform:translateY(-6px)}}
@media (prefers-reduced-motion:reduce){.hb-cele,.hb-cele-card,.hb-spark,.hb-check.just,.hb-emb *{animation:none!important}}
'''

JS = r'''
/* ===================================================================================== */
/* Lira 7.5 — dynamic island & curfew, tasks for the island, plan repeats, habit streaks, */
/* motion. Everything stays on the phone: no network of any kind.                         */
/* ===================================================================================== */
function v75Reduce(){try{return window.matchMedia('(prefers-reduced-motion: reduce)').matches}catch(e){return false}}
var v75After=[];
function v75Island(){var c=stCfg(),is=c.island;if(!is||typeof is!=='object'||Array.isArray(is))is=c.island={};if(typeof is.on!=='boolean')is.on=true;if(typeof is.idle!=='boolean')is.idle=true;return is}
function v75Curfew(){var c=stCfg(),f=c.curfew;if(!f||typeof f!=='object'||Array.isArray(f))f=c.curfew={};if(typeof f.on!=='boolean')f.on=false;
 if(!dtTimeOk(f.start))f.start=S.sleep&&dtTimeOk(S.sleep.time)?S.sleep.time:'23:00';if(!dtTimeOk(f.end))f.end='07:00';
 if(!Array.isArray(f.days)||!f.days.length)f.days=[0,1,2,3,4,5,6];f.days=f.days.map(Number).filter(function(d){return d>=0&&d<=6});if(!f.days.length)f.days=[0,1,2,3,4,5,6];return f}
function v75CurfewWindows(){var f=v75Curfew();if(!f.on||f.start===f.end)return [];var out=[],today=v6DateKey(Date.now());
 for(var i=-1;i<=7;i++){var k=v6DateShift(today,i);if(f.days.indexOf(v6Weekday(k))<0)continue;var st=v6WallMillis(k,f.start),en=v6WallMillis(f.end<=f.start?v6DateShift(k,1):k,f.end);if(isFinite(st)&&isFinite(en)&&en>st)out.push([st,en])}return out}
function v75Clock(ts){var p=v6Parts(ts);return v6Pad(p.hour)+':'+v6Pad(p.minute)}
function v75In(ms){var m=Math.max(1,Math.round(ms/60000)),hh=Math.floor(m/60),mm=m%60;return hh?hh+' ч'+(mm?' '+mm+' мин':''):mm+' мин'}
function v75CurfewState(){var w=v75CurfewWindows(),now=Date.now();for(var i=0;i<w.length;i++){if(w[i][1]<=now)continue;if(now>=w[i][0])return {on:true,s:w[i][0],e:w[i][1]};return {on:false,s:w[i][0],e:w[i][1]}}return null}
function v75Win(k,a,b){var st=v6WallMillis(k,a),en=dtTimeOk(b)?v6WallMillis(b<=a?v6DateShift(k,1):k,b):st+30*60000;return isFinite(st)&&isFinite(en)&&en>st?[st,en]:null}
// Tasks for the island: plan days of the coming week, or the weekly routine (and repeats) for days not planned yet.
function v75Tasks(){var out=[],today=v6DateKey(Date.now());
 for(var i=0;i<7;i++){var k=v6DateShift(today,i),day=S.planDays&&S.planDays[k];
  if(day&&Array.isArray(day.items))day.items.forEach(function(t){if(!dtTimeOk(t.time)||t.status==='missed')return;var w=v75Win(k,t.time,t.end);if(w)out.push({k:k+'|'+t.id,t:String(t.title||'Дело').slice(0,140),s:w[0],e:w[1],d:t.status==='done'})});
  else v6RoutineList(v6Weekday(k)).forEach(function(r){if(!dtTimeOk(r.start))return;var w=v75Win(k,r.start,r.end);if(w)out.push({k:k+'|r:'+r.id+'|'+r.start,t:String(r.title||'Дело').slice(0,140),s:w[0],e:w[1],d:false})});
  rpVirtual(k,day).forEach(function(r){if(!dtTimeOk(r.time))return;var w=v75Win(k,r.time,r.end);if(w)out.push({k:k+'|p:'+r.id,t:String(r.title||'Дело').slice(0,140),s:w[0],e:w[1],d:false})})}
 return out.slice(0,400)}
var v75OldPayload=stPayload;stPayload=function(){var o=JSON.parse(v75OldPayload()),is=v75Island();o.island={on:is.on,idle:is.idle};o.curfew=is.on?v75CurfewWindows():[];o.tasks=is.on?v75Tasks():[];return JSON.stringify(o)};
// Ticks made on the island: applied to the plan when Lira is open.
function v75TakeInbox(){if(!ST||typeof ST.takeInbox!=='function'||!S)return 0;var list=stCall('takeInbox',[]);if(!Array.isArray(list)||!list.length)return 0;var n=0;
 list.forEach(function(ev){if(!ev||typeof ev.k!=='string')return;var parts=ev.k.split('|'),k=parts[0],id=parts[1]||'';if(!v7PlanDateOk(k))return;var day=v7PlanDay(k),item=null;
  if(id.indexOf('r:')===0){var rid=id.slice(2),start=parts[2]||'',r=(S.routines[v6Weekday(k)]||[]).find(function(x){return x.id===rid});if(!day)day=v7NewPlanDay(k,true);
   item=day.items.find(function(t){return t.fromRoutine&&r&&t.title===String(r.title||'')&&t.time===String(r.start||'')})||day.items.find(function(t){return t.fromRoutine&&t.time===start})}
  else if(id.indexOf('p:')===0){var pid=id.slice(2);if(!day)day=v7NewPlanDay(k,true);rpEnsure(k,day);item=day.items.find(function(t){return t.repeatId===pid})}
  else if(day)item=day.items.find(function(t){return t.id===id});
  if(!item)return;var st=ev.d?'done':'pending';if(item.status!==st){item.status=st;item.completedAt=ev.d?(Number(ev.ts)||Date.now()):null;day.updatedAt=Date.now();n++}});
 if(n&&save()){render();toast(n===1?'Отметка с острова сохранена':'Отметки с острова сохранены: '+n)}return n}

/* ---------- plan repeats ---------- */
var rpKinds=[['none','Не повторять'],['daily','Каждый день'],['weekdays','По будням'],['weekends','По выходным'],['weekly','Каждую неделю'],['monthly','Каждый месяц'],['days','В выбранные дни недели']];
function rpState(){if(!Array.isArray(S.planRepeats))S.planRepeats=[];return S.planRepeats}
function rpGet(id){return rpState().find(function(r){return r.id===id})||null}
function rpMatch(r,key){if(!r||!v7PlanDateOk(key)||key<r.from||(r.until&&key>r.until))return false;var wd=v6Weekday(key);
 if(r.kind==='daily')return true;if(r.kind==='weekdays')return wd>=1&&wd<=5;if(r.kind==='weekends')return wd===0||wd===6;if(r.kind==='weekly')return wd===v6Weekday(r.from);
 if(r.kind==='monthly'){var d=+r.from.slice(8,10),dim=new Date(Date.UTC(+key.slice(0,4),+key.slice(5,7),0)).getUTCDate();return +key.slice(8,10)===Math.min(d,dim)}
 if(r.kind==='days')return (r.days||[]).indexOf(wd)>=0;return false}
var rpWd=['воскресеньям','понедельникам','вторникам','средам','четвергам','пятницам','субботам'];
function rpLabel(r){if(!r)return 'Повтор';if(r.kind==='daily')return 'Каждый день';if(r.kind==='weekdays')return 'По будням';if(r.kind==='weekends')return 'По выходным';if(r.kind==='weekly')return 'По '+rpWd[v6Weekday(r.from)];
 if(r.kind==='monthly')return 'Каждый месяц, '+(+r.from.slice(8,10))+'-го';if(r.kind==='days')return (r.days||[]).slice().sort(function(a,b){return (a+6)%7-(b+6)%7}).map(function(d){return weekNames[d]}).join(', ');return 'Повтор'}
function rpEnsure(key,day){if(!day||!Array.isArray(day.items))return 0;var skip=day.skipRepeats||[],n=0;
 rpState().forEach(function(r){if(!rpMatch(r,key)||skip.indexOf(r.id)>=0||day.items.some(function(t){return t.repeatId===r.id}))return;
  day.items.push({id:uid(),title:r.title,time:r.time||'',end:r.end||'',note:r.note||'',status:'pending',createdAt:Date.now(),completedAt:null,fromRoutine:false,repeatId:r.id});n++});
 if(n)day.updatedAt=Date.now();return n}
function rpVirtual(key,day){var skip=day&&day.skipRepeats||[];return rpState().filter(function(r){return rpMatch(r,key)&&skip.indexOf(r.id)<0&&!(day&&Array.isArray(day.items)&&day.items.some(function(t){return t.repeatId===r.id}))})}
// Days already saved after `key` (and not in the past): bring their copies of repeat r in line.
function rpSyncFuture(r,key,remove){var today=v6DateKey(Date.now());Object.keys(v7PlanState()).forEach(function(k){if(k<=key||k<today)return;var d=v7PlanDay(k);if(!d||!Array.isArray(d.items))return;
 d.items=d.items.filter(function(t){if(t.repeatId!==r.id||t.status!=='pending')return true;if(remove||!rpMatch(r,k))return false;t.title=r.title;t.time=r.time;t.end=r.end;t.note=r.note;return true});
 if(!remove)rpEnsure(k,d);d.updatedAt=Date.now()})}
var rpOldNewPlanDay=v7NewPlanDay;v7NewPlanDay=function(key,withRoutine){var existed=!!v7PlanDay(key),d=rpOldNewPlanDay(key,withRoutine);if(!existed)rpEnsure(key,d);return d};
var rpOldTaskView=v7PlanTaskView;v7PlanTaskView=function(task){var html=rpOldTaskView(task);if(!task.repeatId)return html;var r=rpGet(task.repeatId);
 return html.replace('</span>',' · <em class="rp-badge">'+ico('refresh',true)+' '+h(r?rpLabel(r):'Повтор')+'</em></span>')};
var rpOldPlanPage=v7PlanPage;v7PlanPage=function(){var html=rpOldPlanPage(),list=rpState().filter(function(r){return !r.until||r.until>=v6DateKey(Date.now())});
 if(!list.length)return html;var block='<div class="daily-section-title"><h2>Повторяющиеся дела</h2><span>'+list.length+'</span></div><div class="panel glass rp-list">'+list.map(function(r){return '<div class="rp-row"><span class="tint" style="width:34px;height:34px;border-radius:11px">'+ico('refresh',true)+'</span><span><strong>'+h(r.title)+'</strong><small>'+h(rpLabel(r))+(r.time?' · '+h(r.time)+(r.end?'–'+h(r.end):''):'')+'</small></span><button type="button" class="mini-btn danger" data-action="rpDelete" data-id="'+h(r.id)+'" aria-label="Удалить повтор">'+ico('trash',true)+'</button></div>'}).join('')+'</div>';
 var mark='<p class="plan-help">';return html.indexOf(mark)<0?html+block:html.replace(mark,block+mark)};
v7PlanAdd=function(id){var key=v7SelectedDate||v6DateKey(Date.now()),day=v7PlanDay(key),item=id&&day&&day.items.find(function(t){return t.id===id}),rep=item&&item.repeatId?rpGet(item.repeatId):null;
 var kind=rep?rep.kind:'none',days=rep&&Array.isArray(rep.days)&&rep.days.length?rep.days:[v6Weekday(key)];
 var wdAcc=['воскресенье','понедельник','вторник','среду','четверг','пятницу','субботу'][v6Weekday(key)],named={weekly:'Каждую неделю — в '+wdAcc,monthly:'Каждый месяц — '+(+key.slice(8,10))+'-го числа'};
 var body='<form>'+field('Что нужно сделать','title','text','maxlength="130" placeholder="Например: Подготовить презентацию" value="'+h(item?item.title:'')+'" required')+'<div class="form-pair">'+field('Начало · необязательно','time','time','value="'+h(item?item.time:'')+'"')+field('Окончание · необязательно','end','time','value="'+h(item?item.end:'')+'"')+'</div>'+
  '<label class="field"><span>Повтор</span><select name="repeat">'+rpKinds.map(function(k){return '<option value="'+k[0]+'"'+(k[0]===kind?' selected':'')+'>'+h(named[k[0]]||k[1])+'</option>'}).join('')+'</select></label>'+
  '<div class="rp-days field" id="rpDays"'+(kind==='days'?'':' hidden')+'>'+weekdaySelector(days)+'</div>'+
  (rep?'<label class="rp-scope"><input type="checkbox" name="scope" checked><span>Изменить и будущие повторы</span></label>':'')+
  '<label class="field"><span>Подробности · необязательно</span><textarea name="note" maxlength="1000" placeholder="Что важно не забыть…">'+h(item?item.note:'')+'</textarea></label>'+buttonSave(item?'Сохранить изменения':'Добавить в план')+'</form>'+
  (item?'<div class="sheet-actions">'+(rep?'<button type="button" class="mini-btn danger" id="rpDelOne">'+ico('trash',true)+' Только это</button><button type="button" class="mini-btn danger" id="rpDelAll">'+ico('refresh',true)+' Весь повтор</button>':'<button type="button" class="mini-btn danger" id="v7RemoveTask">'+ico('trash',true)+' Удалить дело</button>')+'</div>':'');
 openModal(item?'Изменить дело':'Новое дело · '+key,body,function(fd){var title=String(fd.get('title')||'').trim(),time=String(fd.get('time')||''),end=String(fd.get('end')||''),note=String(fd.get('note')||'').trim();
  if(!title){toast('Введите название дела');return}if(end&&!time){toast('Для окончания укажите начало');return}if(time&&end&&end<=time){toast('Окончание должно быть позже начала');return}
  var kNew=String(fd.get('repeat')||'none'),dNew=fd.getAll('day').map(Number);if(kNew==='days'&&!dNew.length){toast('Выберите дни для повтора');return}
  var target=v7NewPlanDay(key,false),fields={title:title,time:time,end:end,note:note};
  if(item){Object.assign(item,fields);
   if(rep){if(kNew==='none'){rep.until=v6DateShift(key,-1);delete item.repeatId;rpSyncFuture(rep,key,true)}
    else if(fd.get('scope')){var changed=kNew!==rep.kind||(kNew==='days'&&dNew.join(',')!==(rep.days||[]).join(','));Object.assign(rep,fields);if(changed){rep.kind=kNew;rep.days=dNew;rep.from=key}rpSyncFuture(rep,key,false)}}
   else if(kNew!=='none'){var nr={id:uid(),kind:kNew,days:dNew,from:key,until:'',createdAt:Date.now()};Object.assign(nr,fields);rpState().push(nr);item.repeatId=nr.id;rpSyncFuture(nr,key,false)}}
  else if(kNew!=='none'){var r={id:uid(),kind:kNew,days:dNew,from:key,until:'',createdAt:Date.now()};Object.assign(r,fields);rpState().push(r);rpEnsure(key,target)}
  else target.items.push({id:uid(),title:title,time:time,end:end,note:note,status:'pending',createdAt:Date.now(),completedAt:null,fromRoutine:false});
  target.updatedAt=Date.now();goSuccess(item?'Дело изменено':kNew!=='none'?'Повтор создан: '+rpLabel(rpState()[rpState().length-1]).toLowerCase():'Дело добавлено')});
 var form=$('modalBody').querySelector('form');bindWeekdaySelector();form.elements.repeat.addEventListener('change',function(){$('rpDays').hidden=form.elements.repeat.value!=='days'});
 if(item&&!rep)$('v7RemoveTask').onclick=function(){if(!confirm('Удалить дело из архива выбранного дня?'))return;day.items=day.items.filter(function(t){return t.id!==id});day.updatedAt=Date.now();goSuccess('Дело удалено')};
 if(rep){$('rpDelOne').onclick=function(){day.items=day.items.filter(function(t){return t.id!==id});day.skipRepeats=(day.skipRepeats||[]).concat(rep.id);day.updatedAt=Date.now();goSuccess('Удалено только на этот день')};
  $('rpDelAll').onclick=function(){if(!confirm('Удалить повтор «'+rep.title+'»? Выполненные дела останутся в архиве.'))return;rpRemove(rep.id,key);goSuccess('Повтор удалён')}}};
function rpRemove(rid,fromKey){var today=v6DateKey(Date.now());S.planRepeats=rpState().filter(function(r){return r.id!==rid});
 Object.keys(v7PlanState()).forEach(function(k){var d=v7PlanDay(k);if(!d||!Array.isArray(d.items))return;d.items=d.items.filter(function(t){if(t.repeatId!==rid)return true;if(t.status==='pending'&&k>=fromKey&&k>=today)return false;delete t.repeatId;return true})})}

/* ---------- habits: streak tiers every 5 days and 66 days to form a habit ---------- */
var hbFormDays=66;
var hbTiers=[[3,'Искра','spark','#ffd36b','#ff9f1c'],[5,'Огонёк','flame','#ffb347','#ff6a00'],[10,'Пламя','flame2','#ff8a3d','#ff2e2e'],[15,'Жар','flame3','#ff6f7d','#d01a5c'],[20,'Факел','torch','#ff5fae','#a8239c'],
 [25,'Комета','comet','#c79bff','#6a3dff'],[30,'Звезда','star','#b9a2ff','#5b2bd8'],[35,'Созвездие','stars','#95a7ff','#3b3fd6'],[40,'Луна','moon','#8dcbff','#2f6bff'],[45,'Прилив','wave','#6ee9ff','#0b84d8'],
 [50,'Кристалл','crystal','#6ff3df','#0a9c8c'],[55,'Изумруд','gem1','#6ef5aa','#0f9d58'],[60,'Сапфир','gem2','#7cb2ff','#1546c9'],[65,'Рубин','gem3','#ff7d91','#c2002f'],[70,'Аметист','gem4','#d79bff','#7b1fd1'],
 [75,'Алмаз','diamond','#f2fdff','#79c6f2'],[80,'Корона','crown','#ffea8a','#d99a00'],[85,'Феникс','phoenix','#ffd36b','#ff4d1f'],[90,'Солнце','sun','#fff3b0','#ffa600'],[95,'Сверхновая','nova','#ffd6f3','#ff3fd2'],[100,'Легенда','laurel','#fff6c4','#ff9d00']];
var hbUid=0;
function hbStarPath(cx,cy,ro,ri,n){var p='';for(var i=0;i<n*2;i++){var a=Math.PI*i/n-Math.PI/2,r=i%2?ri:ro;p+=(i?'L':'M')+(cx+r*Math.cos(a)).toFixed(2)+' '+(cy+r*Math.sin(a)).toFixed(2)}return p+'Z'}
function hbGlyph(kind,b){var W='#fff';switch(kind){
 case 'spark':return '<path d="'+hbStarPath(32,32,19,5,4)+'" fill="'+W+'"/>';
 case 'flame':return '<path d="M32 12c4 9 13 13 13 24a13 13 0 0 1-26 0c0-7 4-10 7-16 1 5 3 7 6 7-2-6-1-11 0-15z" fill="'+W+'"/>';
 case 'flame2':return hbGlyph('flame',b)+'<path d="M32 31c2.5 4 7 6.5 7 11a7 7 0 0 1-14 0c0-3.5 2-5.5 3.5-8 1 2 2.2 3 3.5 3-.5-2-.4-4 0-6z" fill="'+b+'" opacity=".55"/>';
 case 'flame3':return hbGlyph('flame2',b)+'<circle cx="18" cy="21" r="2.4" fill="'+W+'"/><circle cx="47" cy="17" r="2" fill="'+W+'"/><circle cx="50" cy="31" r="1.5" fill="'+W+'" opacity=".8"/>';
 case 'torch':return '<path d="M32 10c3 6 9 9 9 16a9 9 0 0 1-18 0c0-5 3-7 5-11 1 3 2 5 4 5-1-4 0-7 0-10z" fill="'+W+'"/><path d="M25 37h14l-3 17h-8z" fill="'+W+'" opacity=".85"/>';
 case 'comet':return '<circle cx="41" cy="23" r="8.5" fill="'+W+'"/><path d="M35 29L15 49M38.5 33L23 48.5M31 26L16 41" stroke="'+W+'" stroke-width="3.4" stroke-linecap="round" opacity=".8"/>';
 case 'star':return '<path d="'+hbStarPath(32,33,20,8.5,5)+'" fill="'+W+'"/>';
 case 'stars':return '<path d="M20 38L33 22 46 34" stroke="'+W+'" stroke-width="1.6" fill="none" opacity=".55"/><path d="'+hbStarPath(20,38,8,3.2,5)+'" fill="'+W+'"/><path d="'+hbStarPath(33,22,10,4,5)+'" fill="'+W+'"/><path d="'+hbStarPath(46,34,7,2.8,5)+'" fill="'+W+'"/>';
 case 'moon':return '<path d="M37 12a20 20 0 1 0 14 31 17 17 0 0 1-14-31z" fill="'+W+'"/><path d="'+hbStarPath(46,19,5,1.8,4)+'" fill="'+W+'"/>';
 case 'wave':return '<path d="M12 27c5-6 10-6 15 0s10 6 15 0 7-5 10-3M12 38c5-6 10-6 15 0s10 6 15 0 7-5 10-3" stroke="'+W+'" stroke-width="4.2" stroke-linecap="round" fill="none"/>';
 case 'crystal':return '<path d="M32 11l13 9v24l-13 9-13-9V20z" fill="'+W+'"/><path d="M32 29v24M19 20l13 9 13-9" stroke="'+b+'" stroke-width="1.8" fill="none" opacity=".55"/>';
 case 'gem1':return '<path d="M24 14h16l7 7v22l-7 7H24l-7-7V21z" fill="'+W+'"/><path d="M27 20h10l4 4v16l-4 4H27l-4-4V24z" fill="'+b+'" opacity=".35"/>';
 case 'gem2':return '<ellipse cx="32" cy="32" rx="15" ry="19.5" fill="'+W+'"/><path d="M32 13v38M17 32h30M21 18l22 28M43 18L21 46" stroke="'+b+'" stroke-width="1.4" opacity=".45"/>';
 case 'gem3':return '<path d="M32 50L15 32a9.5 9.5 0 0 1 17-11 9.5 9.5 0 0 1 17 11z" fill="'+W+'"/><path d="M32 22v28M15.5 32h33" stroke="'+b+'" stroke-width="1.5" opacity=".45"/>';
 case 'gem4':return '<path d="M32 9l7.5 16L32 53l-7.5-28z" fill="'+W+'"/><path d="M20 22l5 9-5 17-5-17zM44 22l5 9-5 17-5-17z" fill="'+W+'" opacity=".72"/>';
 case 'diamond':return '<path d="M17 25l8-11h14l8 11-15 26z" fill="'+W+'"/><path d="M17 25h30M25 14l7 11 7-11M32 25v26M25 25l7 26 7-26" stroke="'+b+'" stroke-width="1.4" fill="none" opacity=".6"/>';
 case 'crown':return '<path d="M14 43l3-24 9 10 6-16 6 16 9-10 3 24z" fill="'+W+'"/><rect x="14" y="46" width="36" height="5" rx="2.5" fill="'+W+'"/><circle cx="32" cy="35" r="3.2" fill="'+b+'"/>';
 case 'phoenix':return '<path d="M32 47c-7-7-17-6-22-17 9 1 15 4 22 11 7-7 13-10 22-11-5 11-15 10-22 17z" fill="'+W+'"/><path d="M32 11c3 6 7 8 7 14a7 7 0 0 1-14 0c0-4 3-6 4-10 1 2 2 3 3 3-.5-3 0-5 0-7z" fill="'+W+'"/>';
 case 'sun':return '<circle cx="32" cy="32" r="9.5" fill="'+W+'"/><path d="M32 11v7M32 46v7M11 32h7M46 32h7M17.2 17.2l5 5M41.8 41.8l5 5M17.2 46.8l5-5M41.8 22.2l5-5" stroke="'+W+'" stroke-width="3.4" stroke-linecap="round"/>';
 case 'nova':return '<path d="'+hbStarPath(32,32,22,7,12)+'" fill="'+W+'"/><circle cx="32" cy="32" r="5" fill="'+b+'" opacity=".6"/>';
 case 'laurel':var l='';for(var i=0;i<6;i++){[115+i*24,65-i*24].forEach(function(deg){var a=deg*Math.PI/180,x=32+20*Math.cos(a),y=32+20*Math.sin(a);l+='<ellipse cx="'+x.toFixed(1)+'" cy="'+y.toFixed(1)+'" rx="2.4" ry="5" transform="rotate('+deg+' '+x.toFixed(1)+' '+y.toFixed(1)+')" fill="'+W+'" opacity="'+(1-i*0.08).toFixed(2)+'"/>'})}
  return l+'<text x="32" y="39" text-anchor="middle" font-size="15" font-weight="900" fill="'+W+'" font-family="Inter,Roboto,Arial,sans-serif">100</text>';
 default:return '<path d="M32 44c0-8 0-12-6-16 6 0 6 4 6 8 0-6 3-11 9-11-3 4-9 7-9 19z" fill="'+W+'" opacity=".9"/>'}}
function hbTierIndex(n){var i=-1;for(var j=0;j<hbTiers.length;j++)if(n>=hbTiers[j][0])i=j;return i}
function hbEmblem(i,size,locked){var t=i>=0?hbTiers[i]:[0,'Росток','seed','#9aa7b8','#5b6778'],a=t[3],b=t[4],id='hbg'+(++hbUid),band=i<0?0:i<10?1:i<16?2:i<20?3:4;
 var shape=band<=1?'<circle cx="32" cy="32" r="28"/>':band===2?'<path d="M32 3l25 14.5v29L32 61 7 46.5v-29z"/>':band===3?'<path d="'+hbStarPath(32,32,30,25.5,8)+'"/>':'<circle cx="32" cy="32" r="29"/>';
 var frame='<g fill="url(#'+id+')">'+shape+'</g>'+(band===4?'<circle class="hb-orbit" cx="32" cy="32" r="31.5" fill="none" stroke="'+a+'" stroke-width="1.4" stroke-dasharray="3 5"/>':'');
 var rings=band>=2?'<circle cx="32" cy="32" r="22" fill="none" stroke="#fff" stroke-opacity=".28" stroke-width="1"/>':'';
 return '<span class="hb-emb b'+(band>=3?3:band>=2?2:1)+(locked?' locked':'')+'" style="width:'+size+'px;height:'+size+'px;--glow:'+b+'66"><svg viewBox="0 0 64 64" aria-hidden="true"><defs><linearGradient id="'+id+'" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="'+a+'"/><stop offset="1" stop-color="'+b+'"/></linearGradient><clipPath id="'+id+'c">'+shape+'</clipPath></defs>'+frame+rings+
  '<g clip-path="url(#'+id+'c)"><ellipse class="hb-shine" cx="24" cy="18" rx="15" ry="8" fill="#fff" opacity=".22" transform="rotate(-25 24 18)"/></g>'+'<g transform="translate(32 32) scale(.72) translate(-32 -32)">'+hbGlyph(t[2],b)+'</g></svg></span>'}
function hbStreak(g){return habitStats(g,30).streak}
function hbDone(g){var n=0,r=g.records||{};for(var k in r)if(r[k]==='done')n++;return n}
function hbBest(g){var keys=Object.keys(g.records||{}).filter(v7PlanDateOk).sort(),today=dateKey(new Date()),best=0,cur=0;if(!keys.length)return 0;var k=keys[0],guard=0;
 while(k<=today&&guard++<1200){if(habitOnDay(g,fromDateKey(k))){var st=habitStatus(g,k);if(st==='done'){cur++;if(cur>best)best=cur}else if(st==='missed'||k<today)cur=0}k=v6DateShift(k,1)}return Math.max(best,hbStreak(g))}
function hbNext(n){for(var j=0;j<hbTiers.length;j++)if(hbTiers[j][0]>n)return hbTiers[j];return null}
function hbDayWord(n){n=Math.abs(n);var a=n%10,b=n%100;return a===1&&b!==11?'день':a>=2&&a<=4&&(b<12||b>14)?'дня':'дней'}
var hbJust='';
function hbCard(g){var today=dateKey(new Date()),st=habitStatus(g,today),sched=habitOnDay(g,fromDateKey(today)),streak=hbStreak(g),ti=hbTierIndex(streak),nx=hbNext(streak),done=hbDone(g),form=Math.min(hbFormDays,done);
 var prev=ti>=0?hbTiers[ti][0]:0,pct=nx?Math.round((streak-prev)/(nx[0]-prev)*100):100,tier=ti>=0?hbTiers[ti]:null;
 var week='';for(var i=6;i>=0;i--){var k=v6DateShift(today,-i),on=habitOnDay(g,fromDateKey(k)),s2=habitStatus(g,k);week+='<i class="'+(!on?'off':s2==='done'?'done':s2==='missed'?'missed':'')+(i===0?' today':'')+'"></i>'}
 var sub=streak?'Серия <b>'+streak+' '+hbDayWord(streak)+'</b>'+(tier?' · '+h(tier[1]):''):(done?'Серия начнётся с ближайшей отметки':'Отметьте первый день');
 return '<article class="hb-card glass'+(st==='done'?' is-done':'')+'" data-action="hbOpen" data-id="'+h(g.id)+'" style="--ta:'+(tier?tier[3]:'var(--accent)')+';--tb:'+(tier?tier[4]:'var(--accent)')+'">'+hbEmblem(ti,52)+
  '<div class="hb-main"><div class="hb-title">'+h(g.title)+'</div><div class="hb-sub">'+sub+(nx?' · до «'+h(nx[1])+'» '+(nx[0]-streak)+' '+hbDayWord(nx[0]-streak):'')+'</div>'+
  '<div class="hb-bars"><div class="hb-bar"><i style="width:'+Math.round(form/hbFormDays*100)+'%"></i></div><small>'+(form>=hbFormDays?'освоена ✓':form+'/'+hbFormDays+' дн.')+'</small></div><div class="hb-week" aria-hidden="true">'+week+'</div></div>'+
  '<button type="button" class="hb-check'+(st==='done'?' on':'')+(hbJust===g.id?' just':'')+'" data-action="hbToggle" data-id="'+h(g.id)+'" aria-pressed="'+(st==='done')+'"'+(sched?'':' disabled')+' aria-label="'+(st==='done'?'Снять отметку':'Отметить выполненной')+'"><svg viewBox="0 0 24 24"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg></button></article>'}
habitsPage=function(){var today=dateKey(new Date()),list=todayHabits(),done=list.filter(function(g){return habitStatus(g,today)==='done'}).length,pct=list.length?Math.round(done/list.length*100):0,others=S.habits.filter(function(g){return list.indexOf(g)<0});
 var best=null,bestN=0;S.habits.forEach(function(g){var n=hbStreak(g);if(n>bestN){bestN=n;best=g}});
 var html='<div class="kicker">Ваш ритм</div><h1 class="heading">Привычки</h1><p class="page-sub">Отмечайте одним касанием. Серия растёт каждый день и меняет уровень на 3, 5, 10 и дальше каждые 5 дней до 100. Около '+hbFormDays+' дней — и действие становится привычкой.</p>'+
  '<section class="hb-hero glass"><div class="hb-ring" style="--p:'+pct+'"><b>'+done+'<small>/'+list.length+'</small></b></div><div class="hb-hero-main"><strong>'+(list.length?(done===list.length?'Всё на сегодня сделано':'Сегодня осталось: '+(list.length-done)):'Сегодня отдыхаем')+'</strong><span>'+(list.length?pct+'% привычек по расписанию':'По расписанию на сегодня ничего нет')+'</span>'+
  (best?'<div class="hb-best">'+hbEmblem(hbTierIndex(bestN),22)+'<span>Лучшая серия: <b>'+bestN+' '+hbDayWord(bestN)+'</b> · '+h(best.title)+'</span></div>':'')+'</div></section>';
 if(!S.habits.length)return html+'<button type="button" class="lim-cta glass" data-action="newhabit"><span class="lim-cta-ico tint">'+ico('habit')+'</span><span><strong>Первая привычка</strong><small>Вода, чтение, спорт, ранний подъём — что угодно. Напоминание по желанию.</small></span>'+ico('plus',true)+'</button>';
 html+=(list.length?topSection('Сегодня',null,null)+'<div class="hb-list">'+list.map(hbCard).join('')+'</div>':'')+(others.length?topSection('В другие дни',null,null)+'<div class="hb-list">'+others.map(hbCard).join('')+'</div>':'');
 return html+'<div class="hb-add"><button type="button" class="primary" data-action="newhabit">'+ico('plus',true)+' Новая привычка</button></div><p class="sidenote">Нажмите на карточку, чтобы увидеть все уровни серии, историю и прогресс освоения. Напоминания работают локально через Android.</p>'};
function hbSeen(g,n){var k=dateKey(new Date()),m={};try{m=JSON.parse(localStorage.getItem('lira_streak_seen_v1')||'{}')||{}}catch(e){}var key=g.id+':'+n;if(m[key]===k)return false;m[key]=k;try{localStorage.setItem('lira_streak_seen_v1',JSON.stringify(m))}catch(e){}return true}
function hbToggle(id){var g=S.habits.find(function(x){return x.id===id});if(!g)return;var k=dateKey(new Date());if(!habitOnDay(g,fromDateKey(k))){toast('Сегодня эта привычка не по расписанию');return}
 var before=hbStreak(g),beforeDone=hbDone(g);g.records=g.records||{};var on=g.records[k]!=='done';if(on)g.records[k]='done';else delete g.records[k];if(!save())return;
 hbJust=on?id:'';render();hbJust='';if(!on)return;var after=hbStreak(g),t=hbTiers.find(function(x){return x[0]===after});
 if(t&&after>before&&hbSeen(g,after))setTimeout(function(){hbCelebrate(g,hbTiers.indexOf(t),after+' '+hbDayWord(after)+' подряд: «'+g.title+'»','Новый уровень серии',t[1])},380);
 else if(beforeDone<hbFormDays&&hbDone(g)===hbFormDays&&hbSeen(g,'form'))setTimeout(function(){hbCelebrate(g,hbTierIndex(after),hbFormDays+' дней выполнено. «'+g.title+'» теперь часть вас.','Привычка освоена','Освоено!')},380)}
function hbCelebrate(g,ti,text,kicker,title){var t=ti>=0?hbTiers[ti]:hbTiers[0],el=document.createElement('div');el.className='hb-cele';el.setAttribute('role','dialog');el.style.setProperty('--cb',t[4]);
 var sp='';for(var i=0;i<28;i++){var a=Math.random()*Math.PI*2,d=110+Math.random()*130;sp+='<i class="hb-spark" style="--c:'+(i%3?t[3]:t[4])+';--x:'+Math.round(Math.cos(a)*d)+'px;--y:'+Math.round(Math.sin(a)*d)+'px;animation-delay:'+(Math.random()*.15).toFixed(2)+'s;width:'+(4+Math.random()*7).toFixed(0)+'px;height:'+(4+Math.random()*7).toFixed(0)+'px"></i>'}
 el.innerHTML=sp+'<div class="hb-cele-card">'+hbEmblem(ti,148)+'<div class="kicker">'+h(kicker)+'</div><h2>'+h(title)+'</h2><p>'+h(text)+'</p><button type="button" class="primary">Продолжаем</button></div>';
 document.body.appendChild(el);function close(){el.style.transition='opacity .25s';el.style.opacity='0';setTimeout(function(){el.remove()},260)}el.addEventListener('click',close)}
function hbOpen(id){var g=S.habits.find(function(x){return x.id===id});if(!g)return;var streak=hbStreak(g),ti=hbTierIndex(streak),nx=hbNext(streak),best=hbBest(g),done=hbDone(g),form=Math.min(hbFormDays,done),prev=ti>=0?hbTiers[ti][0]:0;
 var key=dateKey(new Date()),tiles=[];for(var i=13;i>=0;i--){var d=fromDateKey(key);d.setDate(d.getDate()-i);var ds=dateKey(d),is=habitOnDay(g,d),status=habitStatus(g,ds);
  tiles.push('<button type="button" '+(!is?'disabled':'data-action="habitdate" data-id="'+h(g.id)+'" data-date="'+ds+'"')+' class="habit-day '+(!is?'off':status==='done'?'done':status==='missed'?'missed':'pending')+'"><span>'+weekShort[(v6Weekday(ds)+6)%7]+'</span><b>'+Number(ds.slice(8,10))+'</b></button>')}
 var html='<div class="hb-d-top">'+hbEmblem(ti,96)+'<div><div class="kicker">Уровень серии</div><h3>'+h(ti>=0?hbTiers[ti][1]:'Росток')+'</h3><p>Серия '+streak+' '+hbDayWord(streak)+' · рекорд '+best+' '+hbDayWord(best)+'</p></div></div>'+
  '<div class="hb-box hb-66"><div class="hb-ring" style="--p:'+Math.round(form/hbFormDays*100)+'"><b>'+form+'<small>/'+hbFormDays+'</small></b></div><div><div class="hb-box-head"><b>'+(form>=hbFormDays?'Привычка освоена':'Освоение привычки')+'</b></div><p style="margin:0">'+(form>=hbFormDays?'Вы выполнили её '+done+' '+hbDayWord(done)+'. Отличная работа!':'Ещё '+(hbFormDays-form)+' '+hbDayWord(hbFormDays-form)+' выполнения. В среднем около 66 дней нужно, чтобы действие стало автоматическим. Пропуск не обнуляет этот прогресс.')+'</p></div></div>'+
  (nx?'<div class="hb-box" style="--ta:'+(ti>=0?hbTiers[ti][3]:'var(--accent)')+';--tb:'+nx[4]+'"><div class="hb-box-head"><b>До уровня «'+h(nx[1])+'»</b><span>'+streak+' / '+nx[0]+'</span></div><div class="hb-bar"><i style="width:'+Math.round((streak-prev)/(nx[0]-prev)*100)+'%"></i></div></div>':'<div class="hb-box"><div class="hb-box-head"><b>Максимальный уровень</b><span>'+streak+' '+hbDayWord(streak)+'</span></div></div>')+
  '<div class="hb-ladder">'+hbTiers.map(function(t,j){return '<div class="hb-step'+(j===ti?' cur':'')+(nx&&t===nx?' next':'')+'" title="'+h(t[1])+'">'+hbEmblem(j,44,streak<t[0])+'<span>'+t[0]+'</span></div>'}).join('')+'</div>'+
  '<div class="habit-timeline">'+tiles.join('')+'</div><div class="habit-actions"><button type="button" class="habit-mark no" id="hbMiss">'+ico('close',true)+' Не выполнено сегодня</button><button type="button" class="habit-mark" id="hbEdit">'+ico('edit',true)+' Изменить</button></div>';
 openModal(g.title,html,null);$('hbMiss').onclick=function(){if(!habitOnDay(g,fromDateKey(key))){toast('Сегодня эта привычка не по расписанию');return}g.records=g.records||{};if(g.records[key]==='missed')delete g.records[key];else g.records[key]='missed';save();closeModal();render()};
 $('hbEdit').onclick=function(){habitModal(id)}}
habitModal=function(id){var g=id?S.habits.find(function(x){return x.id===id}):null,days=g?g.days:[1,2,3,4,5,6,0],remind=!!(g&&g.time)||!g,time=g&&g.time?g.time:'09:00';
 var ideas=['Пить воду','Читать 20 минут','Тренировка','Медитация','Ранний подъём','Без сладкого','10 000 шагов','Без телефона перед сном'];
 var html='<form>'+field('Что хотите делать?','title','text','maxlength="75" placeholder="Например: Читать 20 минут" value="'+h(g?g.title:'')+'" required')+(g?'':'<div class="hb-chips">'+ideas.map(function(x){return '<button type="button" class="hb-chip" data-idea="'+h(x)+'">'+h(x)+'</button>'}).join('')+'</div>')+
  '<div class="field"><span>Дни недели</span>'+weekdaySelector(days)+'</div><label class="rp-scope"><input type="checkbox" name="remind"'+(remind?' checked':'')+'><span>Напоминать</span></label><div id="hbTime"'+(remind?'':' hidden')+'>'+field('Время напоминания','time','time','value="'+h(time)+'"')+'</div>'+
  '<div class="info-box">Серия считается по дням из расписания. На '+hbFormDays+'-й выполненный день привычка считается освоенной.</div>'+buttonSave(g?'Сохранить изменения':'Создать привычку')+'</form>'+(g?'<div class="sheet-actions"><button class="mini-btn danger" id="deleteHabit">'+ico('trash',true)+' Удалить привычку</button></div>':'');
 openModal(g?'Изменить привычку':'Новая привычка',html,function(fd){var title=String(fd.get('title')||'').trim(),on=!!fd.get('remind'),tm=String(fd.get('time')||''),dd=fd.getAll('day').map(Number);
  if(!title){toast('Как назовём привычку?');return}if(!dd.length){toast('Выберите хотя бы один день');return}if(on&&!/^(?:[01]\d|2[0-3]):[0-5]\d$/.test(tm)){toast('Укажите время напоминания');return}
  if(g){g.title=title;g.time=on?tm:'';g.days=dd}else{g={id:uid(),title:title,time:on?tm:'',days:dd,records:{},createdAt:Date.now()};S.habits.push(g)}save();closeModal();render();syncHabitAlarms();toast(id?'Привычка сохранена':'Привычка создана — удачной серии!')});
 bindWeekdaySelector();var form=$('modalBody').querySelector('form');form.elements.remind.addEventListener('change',function(){$('hbTime').hidden=!form.elements.remind.checked});
 Array.prototype.forEach.call(form.querySelectorAll('[data-idea]'),function(b){b.addEventListener('click',function(e){e.preventDefault();form.elements.title.value=b.dataset.idea;form.elements.title.focus()})});
 if(g)$('deleteHabit').onclick=function(){if(!confirm('Удалить привычку и историю её выполнения?'))return;S.habits=S.habits.filter(function(x){return x.id!==g.id});save();closeModal();render();syncHabitAlarms();toast('Привычка удалена')}};
// Habits without a reminder time must never reach the native alarm scheduler.
var hbOldSync=syncHabitAlarms;syncHabitAlarms=function(){if(!S||!Array.isArray(S.habits))return hbOldSync();var all=S.habits;S.habits=all.filter(function(g){return /^(?:[01]\d|2[0-3]):[0-5]\d$/.test(String(g.time||''))});try{hbOldSync()}finally{S.habits=all}};

/* ---------- icon pack (drawn here, nothing is downloaded) ---------- */
Object.assign(paths,{plane:'<path d="M3 11.5l18-7.5-7.5 18-2.5-7.5z"/><path d="M11 14.5l3.5-3.5"/>',train:'<rect x="5" y="3" width="14" height="14" rx="3"/><path d="M5 11h14M8 17l-2 4M16 17l2 4"/><circle cx="9" cy="14" r=".7"/><circle cx="15" cy="14" r=".7"/>',
 bike:'<circle cx="6" cy="16" r="3.5"/><circle cx="18" cy="16" r="3.5"/><path d="M6 16l4-7h5l3 7M10 9l3 7h-2M14 6h2"/>',bag:'<path d="M5 8h14l-1 12H6z"/><path d="M9 8V6a3 3 0 0 1 6 0v2"/>',
 scissors:'<circle cx="6" cy="6" r="2.5"/><circle cx="6" cy="18" r="2.5"/><path d="M8 7.5L20 18M8 16.5L20 6"/>',tooth:'<path d="M7 3c-2 0-3.5 2-3 5s2 4 2 7 1 6 2.5 6 1.5-3 2.5-5c1 2 1 5 2.5 5s2.5-3 2.5-6 1.5-4 2-7-1-5-3-5-3 1.5-5 1.5S9 3 7 3z"/>',
 cake:'<path d="M4 21h16v-8H4zM4 16c2 1.5 4 1.5 6 0s4-1.5 6 0 4 1.5 4 0"/><path d="M8 13V9M12 13V9M16 13V9M8 6v.5M12 6v.5M16 6v.5"/>',pizza:'<path d="M12 22L3 6a14 14 0 0 1 18 0z"/><path d="M4.8 9.2a11 11 0 0 1 14.4 0"/><circle cx="10" cy="11" r="1"/><circle cx="14" cy="14" r="1"/>',
 apple:'<path d="M12 7c-2-1.5-6-1-6 4s3 9 5 9c.5 0 .8-.3 1-.3s.5.3 1 .3c2 0 5-4 5-9s-4-5.5-6-4z"/><path d="M12 7c0-2 1-3.5 3-4"/>',leaf:'<path d="M5 19c0-9 6-14 15-14 0 9-5 15-14 15"/><path d="M5 19l8-8"/>',
 flower:'<path d="M12 14c-3 0-5-2-5-5V5l2.5 2L12 4l2.5 3L17 5v4c0 3-2 5-5 5z"/><path d="M12 14v7M12 18c-2-2-4-2-5-2M12 19c2-2 4-2 5-2"/>',camera:'<rect x="3" y="7" width="18" height="13" rx="3"/><circle cx="12" cy="13.5" r="3.5"/><path d="M8.5 7l1.5-3h4l1.5 3"/>',
 headphones:'<path d="M4 15v-3a8 8 0 0 1 16 0v3"/><rect x="3" y="14" width="4" height="7" rx="1.5"/><rect x="17" y="14" width="4" height="7" rx="1.5"/>',tv:'<rect x="3" y="6" width="18" height="12" rx="2.5"/><path d="M8 21h8M9 3l3 3 3-3"/>',
 laptop:'<rect x="5" y="5" width="14" height="10" rx="1.5"/><path d="M2.5 19h19l-2-4h-15z"/>',wrench:'<path d="M15 4a5 5 0 0 0-4.7 6.6L4 17v3h3l6.4-6.3A5 5 0 0 0 20 9l-3 1-2-2 1-3z"/>',
 key:'<circle cx="8" cy="15" r="4"/><path d="M11 12l9-9M17 6l2 2M15 8l2 2"/>',graduation:'<path d="M2 9l10-5 10 5-10 5z"/><path d="M6 11v5c3 2 9 2 12 0v-5M22 9v6"/>',
 trophy:'<path d="M8 4h8v5a4 4 0 0 1-8 0z"/><path d="M8 6H5a3 3 0 0 0 3 4M16 6h3a3 3 0 0 1-3 4M12 13v4M9 17h6v4H9z"/>',rocket:'<path d="M12 3c4 2 6 6 6 10l-3 3H9l-3-3c0-4 2-8 6-10z"/><circle cx="12" cy="10" r="2"/><path d="M9 16l-2 4 3-1M15 16l2 4-3-1"/>',
 piggy:'<path d="M5 11a6 5 0 0 1 11-3h2l-1 2.5a5 5 0 0 1 2 2.5h1.5v3H19a6 6 0 0 1-2 2v3h-3v-2h-4v2H7v-3a5 5 0 0 1-2-4z"/><circle cx="15" cy="11" r=".7"/><path d="M9 7.5h3"/>',receipt:'<path d="M6 3h12v18l-2-1.5-2 1.5-2-1.5-2 1.5-2-1.5L6 21z"/><path d="M9 8h6M9 12h6M9 16h3"/>',
 umbrella:'<path d="M3 12a9 9 0 0 1 18 0z"/><path d="M12 12v7a2 2 0 0 1-4 0"/>',sun:'<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
 drop:'<path d="M12 3c3 4 6 7 6 11a6 6 0 0 1-12 0c0-4 3-7 6-11z"/>',fire:'<path d="M12 3c1 3 6 5 6 11a6 6 0 0 1-12 0c0-3 2-5 3-7 0 2 1 3 2.5 3C11 8 11 5.5 12 3z"/>',
 ticket:'<path d="M3 8a2 2 0 0 0 2-2h14a2 2 0 0 0 2 2v3a2 2 0 0 0 0 2v3a2 2 0 0 0-2 2H5a2 2 0 0 0-2-2v-3a2 2 0 0 0 0-2z"/><path d="M14 7v2M14 11v2M14 15v2"/>',palette:'<path d="M12 3a9 9 0 0 0 0 18c1.5 0 2-1 2-2s-1-1.5-1-2.5 1-1.5 2-1.5h2a4 4 0 0 0 4-4c0-4.5-4-8-9-8z"/><circle cx="7.5" cy="11" r="1"/><circle cx="10" cy="7" r="1"/><circle cx="15" cy="7.5" r="1"/>',
 pin:'<path d="M12 21s-6-6-6-11a6 6 0 0 1 12 0c0 5-6 11-6 11z"/><circle cx="12" cy="10" r="2.2"/>',ball:'<circle cx="12" cy="12" r="9"/><path d="M12 3a14 14 0 0 1 0 18M3 12h18M5 6c4 2 10 2 14 0M5 18c4-2 10-2 14 0"/>'});
if(typeof v8CatIcons!=='undefined'&&Array.isArray(v8CatIcons))[['plane','Авиа'],['train','Поезд'],['bike','Велосипед'],['bag','Шопинг'],['scissors','Красота'],['tooth','Стоматолог'],['cake','Праздники'],['pizza','Фастфуд'],['apple','Продукты'],['leaf','Растения'],['flower','Цветы'],['camera','Фото'],['headphones','Подписки'],['tv','ТВ'],['laptop','Техника'],['wrench','Ремонт'],['key','Аренда'],['graduation','Образование'],['trophy','Награды'],['rocket','Проекты'],['piggy','Копилка'],['receipt','Счета'],['umbrella','Страховка'],['sun','Отдых'],['drop','Вода'],['fire','Отопление'],['ticket','Билеты'],['palette','Хобби'],['pin','Места'],['ball','Спорт и игры']].forEach(function(x){if(!v8CatIcons.some(function(y){return y[0]===x[0]}))v8CatIcons.splice(Math.max(0,v8CatIcons.length-1),0,x)});

/* ---------- screen page: island and curfew ---------- */
function v75IslandPreview(){return '<div class="ip-phone" aria-hidden="true"><div class="ip-sb"><span>9:41</span><span><i></i><i></i><i></i></span></div><div class="ip-island"><div class="ip-l ip-task"><span class="ip-ring dot" style="--c:var(--accent);--p:40%"></span><b>Подготовить отчёт</b><em class="ip-plus">+2</em></div><div class="ip-l ip-cur"><span class="ip-ring moon" style="--c:#ffb340;--p:18%"></span><b>Комендантский час</b><em>24:37</em></div><div class="ip-l ip-lim"><span class="ip-ring" style="--c:#ffd27a;--p:80%"></span><b>YouTube</b><em style="color:#ffd27a">24/30</em></div></div><div class="ip-cam"></div><div class="ip-app"></div></div>'}
function v75CurfewText(){var f=v75Curfew(),days=f.days.length===7?'каждый день':f.days.slice().sort(function(a,b){return (a+6)%7-(b+6)%7}).map(function(d){return weekNames[d]}).join(', ');return f.start+' – '+f.end+' · '+days}
function v75CurfewCard(){var f=v75Curfew(),st=f.on?v75CurfewState():null,now=Date.now();
 var line=!f.on?'Выключен. Днём ничего не беспокоит.':st?(st.on?'Идёт сейчас — до '+v75Clock(st.e):'Начнётся через '+v75In(st.s-now)+(st.s-now<=30*60000?' · идёт отсчёт на острове':'')):'';
 return '<section class="v75-card glass"><span class="tint v75-moon" style="width:42px;height:42px;border-radius:14px;flex:none">'+ico('moon')+'</span><span><strong>Комендантский час</strong><small>'+h(v75CurfewText())+'</small>'+(line?'<span class="v75-cf-state">'+h(line)+'</span>':'')+'</span><button type="button" class="mini-btn" data-action="v75curfewEdit" aria-label="Настроить комендантский час">'+ico('edit',true)+'</button>'+
  '<button type="button" class="st-sw-row" role="switch" aria-checked="'+f.on+'" data-action="v75curfewToggle" style="width:auto;padding:0;border:0" aria-label="Комендантский час"><span class="st-sw" aria-hidden="true"><i></i></span></button></section>'}
function v75CurfewModal(){var f=v75Curfew();
 var html='<form><div class="form-pair">'+field('Начало','start','time','value="'+h(f.start)+'" required')+field('Конец','end','time','value="'+h(f.end)+'" required')+'</div><div class="field"><span>Дни</span>'+weekdaySelector(f.days)+'</div>'+
  '<div class="info-box">За 30 минут до начала на динамическом острове пойдёт красивый обратный отсчёт. Во время комендантского часа остров мягко напомнит, что пора отдыхать. Днём он не беспокоит. Ничего не блокируется.</div>'+buttonSave('Сохранить и включить')+'</form>'+(S.sleep&&S.sleep.enabled&&dtTimeOk(S.sleep.time)?'<div class="sheet-actions"><button type="button" class="mini-btn" id="v75FromSleep">'+ico('moon',true)+' Как время сна · '+h(S.sleep.time)+'</button></div>':'');
 openModal('Комендантский час',html,function(fd){var a=String(fd.get('start')||''),b=String(fd.get('end')||''),dd=fd.getAll('day').map(Number);if(!dtTimeOk(a)||!dtTimeOk(b)){toast('Укажите начало и конец');return}if(a===b){toast('Начало и конец не должны совпадать');return}if(!dd.length){toast('Выберите хотя бы один день');return}
  f.start=a;f.end=b;f.days=dd;f.on=true;if(!save())return;stPush();closeModal();render();toast('Комендантский час: '+a+' – '+b)});
 bindWeekdaySelector();var fs=$('v75FromSleep');if(fs)fs.onclick=function(){var form=$('modalBody').querySelector('form');form.elements.start.value=S.sleep.time}}
function v75Setup(){var u=!!stStatus.usage,o=!!stStatus.overlay,b=!!stStatus.battery,is=v75Island().on,needU=!!Object.keys(stCfg().limits).length||!is;if(o&&(u||!needU)&&b)return '';
 function step(done,n,title,text,id,btn,opt){return '<div class="st-step'+(done?' done':'')+'"><span class="st-num">'+(done?ico('check',true):n)+'</span><div class="st-step-main"><b>'+title+(opt?'<span class="st-opt">'+opt+'</span>':'')+'</b><small>'+text+'</small></div>'+(done?'<span class="st-ok">Готово</span>':'<button type="button" class="mini-btn" data-action="stPerm" data-id="'+id+'">'+btn+'</button>')+'</div>'}
 return '<section class="st-setup glass"><h3>'+(o?'Почти всё готово':'Одно разрешение — и остров заработает')+'</h3><p>Android спросит один раз. Всё считается на телефоне, без интернета.</p>'+
  step(o,1,'Поверх других приложений','Чтобы показывать динамический остров и плашку.','overlay','Разрешить')+
  step(u,2,'Доступ к истории использования','Чтобы считать минуты в приложениях с лимитом. Выберите «Лира · Финансы».','usage','Открыть',needU?'':'для лимитов')+
  step(b,3,'Работа в фоне без ограничений','Чтобы Android не выключал остров и подсчёт.','battery','Настроить','по желанию')+
  (o&&u?'':'<div class="st-note">Если Android пишет «Настройка ограничена», откройте Настройки → Приложения → Лира · Финансы → ⋮ → «Разрешить ограниченные настройки» и попробуйте ещё раз. На Xiaomi также включите «Всплывающие окна в фоне».</div>')+'</section>'}
function v75IslandSettings(){var c=stCfg(),is=v75Island();
 return topSection('Динамический остров',null,null)+'<div class="panel glass st-set">'+v75IslandPreview()+
  stSwitch('island',is.on,'Динамический остров','Чёрный остров у камеры: текущие дела, лимиты и отсчёт комендантского часа. Нажмите на него, чтобы отметить дело.')+
  stSwitch('islandIdle',is.idle,'Показывать остров всегда','Когда нечего показывать, он остаётся маленькой чёрной капсулой вокруг камеры',!is.on)+
  stSwitch('hideFull',c.hideFull,'Прятать в полноэкранном режиме','Видео и игры на весь экран — без острова',!is.on)+
  stSwitch('enabled',c.enabled,'Лимиты приложений на острове','Время в приложении и сколько осталось',!is.on)+'</div>'}
stPage=function(){var c=stCfg(),is=v75Island(),head='<button type="button" class="st-back" data-page="more">'+ico('back',true)+' Настройки</button><div class="kicker">Цифровой баланс</div><h1 class="heading">Экранное время</h1><p class="page-sub">Динамический остров, дневные лимиты для приложений и комендантский час. Остров показывает текущие дела из План-листа — их можно отметить прямо на нём.</p>';
 if(!ST)return head+'<div class="info-box">Экранное время и динамический остров работают в приложении Лира на Android 6 и новее.</div>';
 stRefresh();stLoadApps();var keys=Object.keys(c.limits).sort(function(a,b){return stState(b).pct-stState(a).pct});
 return head+v75Setup()+(is.on?v75IslandSettings():'')+v75CurfewCard()+stHero()+topSection('Лимиты на день',keys.length?'Добавить':null,'stAdd')+
  (keys.length?'<div class="panel glass lim-list">'+keys.map(stRow).join('')+'</div>':v9Cta('stAdd','clock','Добавить приложение','Например, не больше 30 минут в день в YouTube','plus'))+stToday()+
  (is.on?'':topSection('Динамический остров',null,null)+'<div class="panel glass st-set">'+stSwitch('island',false,'Динамический остров','Включите, чтобы вместо плашки был остров с делами и комендантским часом')+'</div>'+stSettings())+
  '<p class="sidenote">Минуты считаются по истории использования Android с полуночи. Остров и плашка ничего не блокируют. Всё остаётся на телефоне — Лира не выходит в интернет. Если Android остановит остров, просто откройте Лиру.</p>'};
stEntry=function(){var n=S&&S.screenTime&&S.screenTime.limits?Object.keys(S.screenTime.limits).length:0;
 return '<button type="button" class="lim-cta glass" data-action="stOpen" style="margin:0 0 18px"><span class="lim-cta-ico tint">'+ico('clock')+'</span><span><strong>Экранное время и остров</strong><small>Динамический остров, комендантский час'+(n?' и лимиты для '+n+' '+(n%10===1&&n%100!==11?'приложения':'приложений'):' и лимиты приложений')+'</small></span>'+ico('arrow',true)+'</button>'};

/* ---------- wiring ---------- */
var v75LastPage=null,v75LastNav=null;
var v75Order=['home','wallets','limits','goals','habits','sleep','routine','plan','daily','notes','more','screen'];
var v75OldRender=render;render=function(){
 if(S&&page==='plan'){var today=v6DateKey(Date.now()),key=v7SelectedDate||today;if(v7PlanDateOk(key)&&key>=today){var d=v7PlanDay(key);if(d){if(rpEnsure(key,d))save()}else if(rpVirtual(key,null).length){v7NewPlanDay(key,true);save()}}}
 var changed=v75LastPage!==null&&v75LastPage!==page;if(changed){var a=v75Order.indexOf(v75LastPage),b=v75Order.indexOf(page);document.documentElement.style.setProperty('--nav-dir',b>=a?'1':'-1')}
 v75OldRender();var sec=$('content')&&$('content').firstElementChild;if(sec&&changed&&!v75Reduce())sec.classList.add('enter');v75LastPage=page;
 var fns=v75After;v75After=[];fns.forEach(function(f){try{f()}catch(e){}})};
var v75OldRenderNav=renderNav;renderNav=function(){v75OldRenderNav();if(v75LastNav!==page){var cur=$('navigation').querySelector('[aria-current="page"]');if(cur&&v75LastNav!==null)cur.classList.add('pop');v75LastNav=page}};
var v75OldToggle=v7PlanToggle;v7PlanToggle=function(id,missed){var day=v7PlanDay(v7SelectedDate),t=day&&day.items.find(function(x){return x.id===id}),was=t&&t.status;
 if(!missed&&was!=='done')v75After.push(function(){var b=document.querySelector('.plan-task-mark[data-id="'+(window.CSS&&CSS.escape?CSS.escape(id):id)+'"]');if(b)b.classList.add('just')});v75OldToggle(id,missed)};
var v75OldClose=closeModal;closeModal=function(){var ov=$('overlay'),sh=ov&&ov.classList.contains('open')?ov.querySelector('.sheet'):null;
 if(sh&&!v75Reduce()){try{var r=sh.getBoundingClientRect(),g=sh.cloneNode(true);Array.prototype.forEach.call(g.querySelectorAll('[id]'),function(e){e.removeAttribute('id')});g.removeAttribute('id');
  var wrap=document.createElement('div');wrap.className='v75-ghost';wrap.style.left=r.left+'px';wrap.style.top=r.top+'px';wrap.style.width=r.width+'px';wrap.style.height=r.height+'px';g.style.height='100%';g.scrollTop=sh.scrollTop;wrap.appendChild(g);
  var bg=document.createElement('div');bg.className='v75-ghost-bg';document.body.appendChild(bg);document.body.appendChild(wrap);setTimeout(function(){wrap.remove();bg.remove()},340)}catch(e){}}
 v75OldClose()};
var v75OldHandle=handleAction;handleAction=function(e){var b=e.target.closest('[data-page],[data-action]'),a=b&&b.dataset.action;
 if(a==='hbToggle'){if(!b.disabled)hbToggle(b.dataset.id);return}
 if(a==='hbOpen'){hbOpen(b.dataset.id);return}
 if(a==='rpDelete'){var r=rpGet(b.dataset.id);if(r&&confirm('Удалить повтор «'+r.title+'»? Выполненные дела останутся в архиве.')){rpRemove(r.id,v6DateKey(Date.now()));if(save()){render();toast('Повтор удалён')}}return}
 if(a==='v75curfewEdit'){v75CurfewModal();return}
 if(a==='v75curfewToggle'){var f=v75Curfew();f.on=!f.on;if(save()){stPush();render();toast(f.on?'Комендантский час включён: '+f.start+' – '+f.end:'Комендантский час выключен')}return}
 if(a==='stToggle'&&(b.dataset.id==='island'||b.dataset.id==='islandIdle')){if(b.disabled)return;var is=v75Island();if(b.dataset.id==='island')is.on=!is.on;else is.idle=!is.idle;if(save()){stPush();render()}return}
 v75OldHandle(e)};
var v75OldInit=init;init=function(){v75OldInit();try{v75TakeInbox()}catch(e){}stPush();
 var ticks=0;setInterval(function(){if(document.hidden||!S)return;if(!modal)v75TakeInbox();if(++ticks%12===0)stPush()},2500);
 document.addEventListener('visibilitychange',function(){if(!document.hidden&&S){v75TakeInbox();stPush()}})};
'''

once('</style>\n</head>', CSS + '</style>\n</head>')
once("v8Version='7.2.1'", "v8Version='7.5.0'")
once('\ninit();\n})();', '\n' + JS + '\ninit();\n})();')
open(dst, 'w', encoding='utf-8').write(s)
print('ok', len(s))
