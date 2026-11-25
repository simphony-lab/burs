# Lira 7.5.1: own confirm dialog instead of the system "JavaScript" box, operations of a
# category on tap, category filter in history.
# usage: python3 ui_patch_76.py app75.html app76.html
import sys
src, dst = sys.argv[1], sys.argv[2]
s = open(src, encoding='utf-8').read()


def once(old, new, count=1):
    global s
    n = s.count(old)
    assert n == count, (old[:70], n)
    s = s.replace(old, new)


def skip_string(t, i):
    q = t[i]
    i += 1
    while i < len(t) and t[i] != q:
        i += 2 if t[i] == '\\' else 1
    return i + 1


def match_paren(t, i):
    """t[i] == '(' -> index of the matching ')'."""
    depth = 0
    while i < len(t):
        c = t[i]
        if c in '"\'`':
            i = skip_string(t, i)
            continue
        if c == '(':
            depth += 1
        elif c == ')':
            depth -= 1
            if depth == 0:
                return i
        i += 1
    raise ValueError('unbalanced')


def block_end(t, i):
    """Index of the '}' that closes the block containing position i (strings/regex aware)."""
    depth, prev = 0, ';'
    while i < len(t):
        c = t[i]
        if c in '"\'`':
            i = skip_string(t, i)
            prev = 'q'
            continue
        if c == '/' and t[i + 1] == '/':
            i = t.index('\n', i)
            continue
        if c == '/' and t[i + 1] == '*':
            i = t.index('*/', i) + 2
            continue
        if c == '/' and prev in '(,=:[!&|?{};+-*%<>~^':
            i += 1
            cls = False
            while True:
                d = t[i]
                if d == '\\':
                    i += 2
                    continue
                if d == '[':
                    cls = True
                elif d == ']':
                    cls = False
                elif d == '/' and not cls:
                    break
                i += 1
            i += 1
            while t[i].isalpha():
                i += 1
            prev = '/'
            continue
        if c == '{':
            depth += 1
        elif c == '}':
            if depth == 0:
                return i
            depth -= 1
        if not c.isspace():
            prev = c
        i += 1
    raise ValueError('no block end')


# --- 1. every confirm() becomes liraAsk(message, then) ------------------------------------
once("if(!editingNoteId||!confirm('Удалить заметку и её текст?'))return;",
     "if(!editingNoteId)return;if(!confirm('Удалить заметку и её текст?'))return;")
once("var r=rpGet(b.dataset.id);if(r&&confirm('Удалить повтор «'+r.title+'»? Выполненные дела останутся в архиве.')){rpRemove(r.id,v6DateKey(Date.now()));if(save()){render();toast('Повтор удалён')}}return}",
     "var r=rpGet(b.dataset.id);if(r)liraAsk('Удалить повтор «'+r.title+'»? Выполненные дела останутся в архиве.',function(){rpRemove(r.id,v6DateKey(Date.now()));if(save()){render();toast('Повтор удалён')}});return}")
done = 0
while True:
    i = s.find('if(!confirm(')
    if i < 0:
        break
    p = i + len('if(!confirm')
    q = match_paren(s, p)
    arg = s[p + 1:q]
    tail = '))return;'
    assert s[q:q + len(tail)] == tail, s[q:q + 40]
    body_start = q + len(tail)
    end = block_end(s, body_start)
    body = s[body_start:end]
    s = s[:i] + 'liraAsk(' + arg + ',function(){' + body + '});' + s[end:]
    done += 1
    print('confirm ->', arg[:50], '| body:', body[:40].replace('\n', ' '), '...', body[-30:].replace('\n', ' '))
assert 'confirm(' not in s, 'confirm left'
print('rewritten', done)

once("v8Version='7.5.0'", "v8Version='7.5.1'")

CSS = r'''
/* ===== Lira 7.5.1 ===== */
.la-over{position:fixed;inset:0;z-index:70;display:grid;place-items:center;padding:24px;background:rgba(2,4,10,.58);-webkit-backdrop-filter:blur(9px);backdrop-filter:blur(9px);animation:v75Fade .22s ease both}
.la-over.out{animation:v75FadeOut .22s ease both}
.la-card{width:min(340px,100%);background:var(--base2,#141a2b);border:1px solid var(--line);border-radius:28px;padding:24px 20px 18px;text-align:center;box-shadow:0 30px 80px rgba(0,0,0,.5);animation:laIn .46s cubic-bezier(.2,1.25,.3,1) both}
.la-over.out .la-card{animation:laOut .2s ease both}
@keyframes laIn{from{transform:scale(.86) translateY(16px);opacity:0}to{transform:none;opacity:1}}
@keyframes laOut{to{transform:scale(.94);opacity:0}}
.la-ico{width:56px;height:56px;border-radius:19px;display:grid;place-items:center;margin:0 auto 14px;background:var(--glass2);color:var(--accent)}
.la-ico.danger{background:rgba(255,92,116,.14);color:#ff6b81}
.la-ico svg{width:26px;height:26px}
.la-card h3{margin:0;font-size:18px;font-weight:760;line-height:1.35;letter-spacing:-.2px;overflow-wrap:anywhere}
.la-card p{margin:8px 0 0;font-size:13px;line-height:1.55;color:var(--sub)}
.la-btns{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:22px}
.la-btns button{min-height:50px;border-radius:16px;font-size:14.5px;font-weight:720;border:1px solid var(--line);background:var(--glass2);color:var(--fg);transition:transform .18s cubic-bezier(.2,.8,.2,1),filter .18s}
.la-btns button:active{transform:scale(.95)}
.la-yes{background:var(--accent)!important;color:var(--onaccent)!important;border-color:transparent!important}
.la-yes.danger{background:#ff5c74!important;color:#fff!important}
@media (prefers-reduced-motion:reduce){.la-over,.la-card{animation:none!important}}
.v76-tap{position:relative;padding-right:24px!important;cursor:pointer;border-radius:12px;transition:background .2s,transform .18s cubic-bezier(.2,.8,.2,1)}
.v76-tap:after{content:'';position:absolute;right:6px;top:50%;width:7px;height:7px;border-right:2px solid var(--sub);border-top:2px solid var(--sub);transform:translateY(-50%) rotate(45deg);opacity:.55}
.v76-tap:active{transform:scale(.985);background:var(--glass)}
.set-row.v76-tap:after{right:58px}
.set-row.v76-tap{padding-right:0!important}
.v76-head{display:flex;align-items:center;gap:14px;margin:0 0 16px}
.v76-head .cat-ico{width:54px;height:54px;border-radius:18px;flex:none}
.v76-head .cat-ico svg{width:25px;height:25px}
.v76-big{font-size:28px;font-weight:820;letter-spacing:-.8px;line-height:1.15;font-variant-numeric:tabular-nums;margin-top:3px}
.v76-big small{font-size:14px;color:var(--sub);font-weight:650;letter-spacing:0}
.v76-big.pos{color:var(--pos)}
.v76-sub{font-size:12px;color:var(--sub);margin-top:4px}
.v76-bars{display:grid;grid-template-columns:repeat(6,1fr);gap:8px;height:110px;padding:12px 12px 0;margin:0 0 12px;border-radius:18px;background:var(--glass);border:1px solid var(--line)}
.v76-bar{display:grid;grid-template-rows:1fr auto;gap:6px;height:100%;border:0;background:none;color:var(--sub);font-size:10.5px;font-weight:650;padding:0 0 9px;min-width:0}
.v76-bar span{display:flex;align-items:flex-end;justify-content:center;height:100%;min-height:0}
.v76-bar i{display:block;width:100%;max-width:28px;border-radius:8px 8px 3px 3px;background:var(--c,var(--accent));opacity:.4;min-height:3px;animation:v76Grow .6s cubic-bezier(.2,.8,.2,1) both;transform-origin:bottom}
.v76-bar.cur i{opacity:.75}.v76-bar.on i{opacity:1}.v76-bar.on{color:var(--fg)}
@keyframes v76Grow{from{transform:scaleY(0)}to{transform:none}}
.v76-chips{margin:0 0 10px}
.v76-chips .chip-btn{flex:0 0 auto}
.v76-hcats{margin-top:8px}
.v76-hcats[hidden]{display:none}
.v76-hcats .chip-btn{flex:0 0 auto;display:inline-flex;align-items:center;gap:6px}
.v76-hcats .chip-btn svg{width:14px;height:14px;color:var(--c)}
.v76-hcats .chip-btn[aria-pressed="true"] svg{color:inherit}
.v76-hcats small{font-size:10px;opacity:.7;font-weight:600}
#v76CatList .op-day:first-child{margin-top:0}
'''

JS = r'''
/* ============ Lira 7.5.1 — own confirm dialog, category operations, history filter ============ */
function liraAsk(message,yes){var m=String(message||''),parts=/^(.*?[?!])\s+(.+)$/.exec(m),title=parts?parts[1]:m,sub=parts?parts[2]:'';
 var verb=/^Удалить/.test(m)?'Удалить':/^Заменить/.test(m)?'Заменить':'Да',danger=verb!=='Да';
 var el=document.createElement('div');el.className='la-over';el.setAttribute('role','alertdialog');el.setAttribute('aria-modal','true');
 el.innerHTML='<div class="la-card"><span class="la-ico'+(danger?' danger':'')+'">'+ico(verb==='Удалить'?'trash':verb==='Заменить'?'refresh':'info')+'</span><h3>'+h(title)+'</h3>'+(sub?'<p>'+h(sub)+'</p>':'')+'<div class="la-btns"><button type="button" class="la-no">Отмена</button><button type="button" class="la-yes'+(danger?' danger':'')+'">'+verb+'</button></div></div>';
 document.body.appendChild(el);var closed=false;
 function close(ok){if(closed)return;closed=true;document.removeEventListener('keydown',key,true);el.classList.add('out');setTimeout(function(){el.remove()},230);if(ok)yes()}
 function key(e){if(e.key==='Escape'){e.preventDefault();e.stopPropagation();close(false)}else if(e.key==='Enter'){e.preventDefault();e.stopPropagation();close(true)}}
 document.addEventListener('keydown',key,true);el.addEventListener('click',function(e){if(e.target===el)close(false)});
 el.querySelector('.la-no').onclick=function(){close(false)};el.querySelector('.la-yes').onclick=function(){close(true)};setTimeout(function(){var b=el.querySelector('.la-no');if(b)b.focus()},40)}
window.confirm=function(){return false}; // nothing may open the system box any more

// Category entries now remember which category (and currency) they are.
v8Entries=function(list,type,inAZN){var cats=type==='income'?S.incomeCategories:S.categories,grouped={},order=[],curs={};
 list.forEach(function(o){if(o.type!==type)return;var id=o.category||'none',v=Number(o.amount)||0;curs[o.currency]=1;if(inAZN)v=toAZN(v,o.currency);if(!grouped[id]){grouped[id]={amount:0,count:0};order.push(id)}grouped[id].amount+=v;grouped[id].count++});
 var keys=Object.keys(curs),one=!inAZN&&keys.length===1?keys[0]:'';
 return order.map(function(id){var cat=cats.find(function(c){return c.id===id});return {id:id,type:type,cur:one,name:cat?cat.name:(type==='income'?'Без категории':'Категория удалена'),icon:cat?cat.icon:'tag',color:v8Hex(cat&&cat.color),amount:grouped[id].amount,count:grouped[id].count}}).filter(function(e){return e.amount>0}).sort(function(a,b){return b.amount-a.amount})};
var v76OldCatList=v8CatList;v8CatList=function(entries,total,unit,fmt){var html=v76OldCatList(entries,total,unit,fmt),i=0;
 return html.replace(/<div class="cat-row">/g,function(){var e=entries[i++];return e&&e.id?'<div class="cat-row v76-tap" role="button" tabindex="0" data-action="v76cat" data-type="'+h(e.type)+'" data-cat="'+h(e.id)+'" data-cur="'+h(e.cur||'')+'" aria-label="Операции категории '+h(e.name)+'">':'<div class="cat-row">'})};
// Settings: the category rows are built inside morePage, so mark them in its output.
var v76OldMore=morePage;morePage=function(){var parts=v76OldMore().split('<div class="set-row">');
 for(var i=1;i<parts.length;i++){var m=/data-action="(editcategory|editincomecategory)" data-id="([^"]*)"/.exec(parts[i].split('</div>')[0]+parts[i].slice(0,600));
  parts[i]=(m?'<div class="set-row v76-tap" role="button" tabindex="0" data-action="v76cat" data-type="'+(m[1]==='editincomecategory'?'income':'expense')+'" data-cat="'+m[2]+'">':'<div class="set-row">')+parts[i]}return parts.join('')};

var v76C={type:'expense',id:'none',cur:'',period:'all',limit:80};
function v76Meta(type,id){var c=(type==='income'?S.incomeCategories:S.categories).find(function(x){return x.id===id});return {cat:c||null,name:c?c.name:(id==='none'?'Без категории':'Удалённая категория'),icon:c?c.icon:'tag',color:c?(v8Hex(c.color)||'var(--accent)'):'var(--sub)'}}
function v76Key(o){return v6DateKey(Number(o.date)||0)}
function v76InPeriod(o){var p=v76C.period,k=v76Key(o),today=v6DateKey(Date.now());if(p==='month')return k.slice(0,7)===today.slice(0,7);if(p==='d30')return k>v6DateShift(today,-30);if(p==='year')return k.slice(0,4)===today.slice(0,4);if(p.indexOf('m:')===0)return k.slice(0,7)===p.slice(2);return true}
function v76CatOpen(type,id,curId){v76C={type:type==='income'?'income':'expense',id:String(id||'none'),cur:curId&&S.currencies.some(function(c){return c.id===curId})?curId:'',period:'all',limit:80};
 openModal(v76Meta(v76C.type,v76C.id).name,'<div id="v76Cat"></div>',null);v76CatDraw()}
function v76CatDraw(){var box=$('v76Cat');if(!box)return;var m=v76Meta(v76C.type,v76C.id),isIn=v76C.type==='income';
 var all=S.ops.filter(function(o){return o.type===v76C.type&&(o.category||'none')===v76C.id}),usedCurs=[];all.forEach(function(o){if(usedCurs.indexOf(o.currency)<0)usedCurs.push(o.currency)});
 if(v76C.cur&&usedCurs.indexOf(v76C.cur)<0)v76C.cur='';var mine=all.filter(function(o){return !v76C.cur||o.currency===v76C.cur}),list=mine.filter(v76InPeriod);
 var sums={};list.forEach(function(o){sums[o.currency]=(sums[o.currency]||0)+(Number(o.amount)||0)});var codes=Object.keys(sums),inAZN=list.reduce(function(a,o){return a+toAZN(Number(o.amount)||0,o.currency)},0);
 var big=codes.length===1?money(sums[codes[0]])+' <small>'+h(cur(codes[0]).code)+'</small>':codes.length?'≈ '+money(inAZN)+' <small>AZN</small>':'0 <small>'+h(v76C.cur?cur(v76C.cur).code:'AZN')+'</small>';
 var avg=list.length?(codes.length===1?money(sums[codes[0]]/list.length)+' '+cur(codes[0]).code:'≈ '+money(inAZN/list.length)+' AZN'):'';
 var today=v6DateKey(Date.now()),months=[];for(var i=5;i>=0;i--)months.push(new Date(Date.UTC(+today.slice(0,4),+today.slice(5,7)-1-i,15)).toISOString().slice(0,7));
 var val=months.map(function(ym){return mine.filter(function(o){return v76Key(o).slice(0,7)===ym}).reduce(function(a,o){return a+(v76C.cur?Number(o.amount)||0:toAZN(Number(o.amount)||0,o.currency))},0)}),mx=Math.max.apply(null,val.concat([0]));
 var mn=['янв','фев','мар','апр','май','июн','июл','авг','сен','окт','ноя','дек'];
 var bars='<div class="v76-bars" role="group" aria-label="По месяцам" style="--c:'+h(m.color)+'">'+months.map(function(ym,i){var pc=mx>0?Math.max(3,val[i]/mx*100):3;return '<button type="button" class="v76-bar'+(ym===today.slice(0,7)?' cur':'')+(v76C.period==='m:'+ym?' on':'')+'" data-ym="'+ym+'" aria-label="'+mn[+ym.slice(5,7)-1]+': '+h(money(val[i]))+'"><span><i style="height:'+pc.toFixed(1)+'%"></i></span>'+mn[+ym.slice(5,7)-1]+'</button>'}).join('')+'</div>';
 var periods=[['all','Всё время'],['month','Этот месяц'],['d30','30 дней'],['year','Этот год']];
 var chips='<div class="chips v76-chips" role="group" aria-label="Период">'+periods.map(function(p){return '<button type="button" class="chip-btn" data-per="'+p[0]+'" aria-pressed="'+(v76C.period===p[0])+'">'+p[1]+'</button>'}).join('')+(v76C.period.indexOf('m:')===0?'<button type="button" class="chip-btn" data-per="'+v76C.period+'" aria-pressed="true">'+mn[+v76C.period.slice(7,9)-1]+' '+v76C.period.slice(2,6)+'</button>':'')+'</div>';
 var curChips=usedCurs.length>1?'<div class="chips v76-chips" role="group" aria-label="Валюта"><button type="button" class="chip-btn" data-cur="" aria-pressed="'+(!v76C.cur)+'">Все валюты</button>'+usedCurs.map(function(id){return '<button type="button" class="chip-btn" data-cur="'+h(id)+'" aria-pressed="'+(v76C.cur===id)+'">'+h(cur(id).code)+'</button>'}).join('')+'</div>':'';
 var shown=list.slice(0,v76C.limit);
 box.innerHTML='<div class="v76-head"><span class="cat-ico tint" style="--c:'+h(m.color)+'">'+ico(m.icon)+'</span><div style="min-width:0"><div class="kicker">'+(isIn?'Доходы':'Расходы')+' · '+h(v76C.period==='all'?'всё время':v76C.period==='month'?'этот месяц':v76C.period==='d30'?'30 дней':v76C.period==='year'?'этот год':mn[+v76C.period.slice(7,9)-1]+' '+v76C.period.slice(2,6))+'</div><div class="v76-big'+(isIn?' pos':'')+'">'+big+'</div><div class="v76-sub">'+list.length+' '+v8Plural(list.length,['операция','операции','операций'])+(avg?' · в среднем '+h(avg):'')+'</div></div></div>'+
  bars+chips+curChips+'<div id="v76CatList">'+(shown.length?v8OpsByDay(shown)+(list.length>shown.length?'<button type="button" class="mini-btn hist-more" id="v76More">Показать ещё · '+(list.length-shown.length)+'</button>':''):'<div class="hist-none">'+ico('search')+(all.length?'За этот период операций нет.':'В этой категории пока нет операций.')+'</div>')+'</div>'+
  '<div class="sheet-actions">'+(m.cat?'<button type="button" class="mini-btn" id="v76Edit">'+ico('edit',true)+' Категория</button>':'')+'<button type="button" class="mini-btn" id="v76Hist">'+ico('chart',true)+' В истории</button></div>';
 Array.prototype.forEach.call(box.querySelectorAll('[data-per]'),function(b){b.onclick=function(){v76C.period=b.dataset.per;v76C.limit=80;v76CatDraw()}});
 Array.prototype.forEach.call(box.querySelectorAll('[data-ym]'),function(b){b.onclick=function(){v76C.period=v76C.period==='m:'+b.dataset.ym?'all':'m:'+b.dataset.ym;v76C.limit=80;v76CatDraw()}});
 Array.prototype.forEach.call(box.querySelectorAll('[data-cur]'),function(b){b.onclick=function(){v76C.cur=b.dataset.cur;v76C.limit=80;v76CatDraw()}});
 var more=$('v76More');if(more)more.onclick=function(){v76C.limit+=120;v76CatDraw()};
 var ed=$('v76Edit');if(ed)ed.onclick=function(){categoryModal(m.cat.id,isIn?'income':'expense')};
 $('v76Hist').onclick=function(){v8HistFilter=v76C.type;v76HistCat=v76C.type+':'+v76C.id;v8HistQuery='';historyModal(true)}}

var v76HistCat='';
var v76OldHistMatches=v8HistMatches;v8HistMatches=function(o){if(!v76OldHistMatches(o))return false;if(!v76HistCat)return true;var p=v76HistCat.split(':');return o.type===p[0]&&(o.category||'none')===p.slice(1).join(':')};
var v76OldHistory=historyModal;historyModal=function(keep){if(keep!==true)v76HistCat='';v76OldHistory();var tools=$('modalBody')&&$('modalBody').querySelector('.hist-tools');if(!tools)return;
 tools.insertAdjacentHTML('beforeend','<div class="chips v76-hcats" id="v76HCats" role="group" aria-label="Категория"></div>');v76HCats();v8HistDraw();
 Array.prototype.forEach.call(tools.querySelectorAll('[data-v8filter]'),function(b){b.addEventListener('click',function(){if(v76HistCat&&v76HistCat.split(':')[0]!==v8HistFilter){v76HistCat='';v8HistDraw()}v76HCats()})})};
function v76HCats(){var box=$('v76HCats');if(!box)return;var f=v8HistFilter;if(f!=='all'&&f!=='expense'&&f!=='income'){box.hidden=true;return}box.hidden=false;var left=box.scrollLeft;
 var list=[];if(f!=='income')S.categories.forEach(function(c){list.push(['expense',c])});if(f!=='expense')S.incomeCategories.forEach(function(c){list.push(['income',c])});
 box.innerHTML='<button type="button" class="chip-btn" data-hcat="" aria-pressed="'+(!v76HistCat)+'">Все категории</button>'+list.map(function(x){var key=x[0]+':'+x[1].id;return '<button type="button" class="chip-btn" data-hcat="'+h(key)+'" aria-pressed="'+(v76HistCat===key)+'" style="--c:'+h(v8Hex(x[1].color)||'var(--accent)')+'">'+ico(x[1].icon,true)+h(x[1].name)+(f==='all'&&x[0]==='income'?' <small>доход</small>':'')+'</button>'}).join('');
 box.scrollLeft=left;
 Array.prototype.forEach.call(box.querySelectorAll('[data-hcat]'),function(b){b.onclick=function(){v76HistCat=b.dataset.hcat;if(v76HistCat){var t=v76HistCat.split(':')[0];if(v8HistFilter!==t&&v8HistFilter!=='all'){v8HistFilter=t}}
  Array.prototype.forEach.call($('modalBody').querySelectorAll('[data-v8filter]'),function(x){x.setAttribute('aria-pressed',String(x.dataset.v8filter===v8HistFilter))});v8HistLimit=150;v76HCats();v8HistDraw()}})}
var v76OldHandle=handleAction;handleAction=function(e){var b=e.target.closest('[data-page],[data-action]'),a=b&&b.dataset.action;
 if(a==='v76cat'){v76CatOpen(b.dataset.type,b.dataset.cat,b.dataset.cur||'');return}
 v76OldHandle(e)};
document.addEventListener('keydown',function(e){if((e.key==='Enter'||e.key===' ')&&e.target&&e.target.classList&&e.target.classList.contains('v76-tap')){e.preventDefault();e.target.click()}});
'''

once('</style>\n</head>', CSS + '</style>\n</head>')
once('\ninit();\n})();', '\n' + JS + '\ninit();\n})();')
open(dst, 'w', encoding='utf-8').write(s)
print('ok', len(s))
