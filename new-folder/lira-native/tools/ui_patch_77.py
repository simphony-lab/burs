# Lira 7.5.2: "island over everything" switch (accessibility window) in the island settings.
import sys
src, dst = sys.argv[1], sys.argv[2]
s = open(src, encoding='utf-8').read()
def once(old, new):
    global s
    assert s.count(old) == 1, (old[:60], s.count(old))
    s = s.replace(old, new)
once("v8Version='7.5.1'", "v8Version='7.5.2'")
once("""  stSwitch('enabled',c.enabled,'Лимиты приложений на острове','Время в приложении и сколько осталось',!is.on)+'</div>'}""",
"""  stSwitch('enabled',c.enabled,'Лимиты приложений на острове','Время в приложении и сколько осталось',!is.on)+v77A11yRow()+'</div>'}""")
CSS = r'''
/* Lira 7.5.2 */
.v77-a11y{display:flex;align-items:center;gap:13px;padding:14px 0 2px;border-top:1px solid var(--line)}
.v77-a11y>span:nth-child(2){flex:1;min-width:0}
.v77-a11y b{display:block;font-size:13.5px;font-weight:660;line-height:1.35}
.v77-a11y small{display:block;font-size:11.5px;color:var(--sub);line-height:1.45;margin-top:3px}
.v77-a11y .mini-btn{margin:0;flex:none}
.v77-a11y .st-ok{flex:none}
'''
JS = r'''
/* Lira 7.5.2 — island over everything: Android hides ordinary overlays inside system Settings;
   a window of Lira's accessibility service is not hidden and can be tapped even over the status bar. */
function v77A11yRow(){var on=!!stStatus.a11y;
 return '<div class="v77-a11y"><span class="tint" style="width:38px;height:38px;border-radius:12px;flex:none">'+ico('shield',true)+'</span><span><b>Поверх всего, даже в Настройках</b><small>'+(on?'Включено: остров виден везде и нажимается целиком, даже в строке состояния.':'Android прячет обычные наложения в системных Настройках. Включите «Лира · Динамический остров» в Специальных возможностях — остров будет виден везде и нажиматься целиком. Служба ничего не читает с экрана.')+'</small></span>'+
  (on?'<span class="st-ok">Готово</span>':'<button type="button" class="mini-btn" data-action="stPerm" data-id="a11y">Включить</button>')+'</div>'}
var v77OldPerm=stPerm;stPerm=function(k){if(k==='a11y'){try{ST.openA11y()}catch(e){toast('Не удалось открыть настройки Android')}return}v77OldPerm(k)};
var v77OldSetup=v75Setup;v75Setup=function(){var o=stStatus.overlay;if(stStatus.a11y&&v75Island().on)stStatus.overlay=true;try{return v77OldSetup()}finally{stStatus.overlay=o}};
'''
once('</style>\n</head>', CSS + '</style>\n</head>')
once('\ninit();\n})();', '\n' + JS + '\ninit();\n})();')
open(dst, 'w', encoding='utf-8').write(s)
print('ok', len(s))
