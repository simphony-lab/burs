"""Adds the screen-time pieces to Lira's binary AndroidManifest.xml and sets the version.

usage: python3 manifest74.py in.xml out.xml versionCode versionName
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import axml

NAME, EXPORTED, PROCESS = 0x01010003, 0x01010010, 0x01010011
VCODE, VNAME = 0x0101021b, 0x0101021c

src, dst, code, name = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
d = axml.Doc(open(src, 'rb').read())
# All attribute names first: adding one shifts string indices.
for n, r in (('name', NAME), ('exported', EXPORTED), ('process', PROCESS)):
    d.attr_name(n, r)

man = d.nodes[d.find('manifest')]
vc, vn = d.attr(man, 'versionCode'), d.attr(man, 'versionName')
assert code > vc.data, 'versionCode must grow'
vc.data = code
vn.raw = vn.data = d.string(name)

have = {d.s(d.attr(d.nodes[i], 'name').raw) for i, n in enumerate(d.nodes)
        if n.kind == 'start' and d.s(n.name) == 'uses-permission'}
perms = ['android.permission.PACKAGE_USAGE_STATS', 'android.permission.SYSTEM_ALERT_WINDOW',
         'android.permission.FOREGROUND_SERVICE', 'android.permission.RECEIVE_BOOT_COMPLETED',
         'android.permission.REQUEST_IGNORE_BATTERY_OPTIMIZATIONS']
new_perms = []
for p in perms:
    if p not in have:
        new_perms += d.element('uses-permission', [('name', NAME, p)])
app = d.find('application')
d.insert(app, new_perms)

app = d.find('application')
end = d.end_of(app)
service = d.element('service', [('name', NAME, 'com.local.simple.notes.ScreenTimeService'),
                                ('exported', EXPORTED, False), ('process', PROCESS, ':screen')])
receiver = d.element('receiver', [('name', NAME, 'com.local.simple.notes.ScreenTimeBoot'),
                                  ('exported', EXPORTED, True), ('process', PROCESS, ':screen')],
                     [d.element('intent-filter', [], [
                         d.element('action', [('name', NAME, 'android.intent.action.BOOT_COMPLETED')]),
                         d.element('action', [('name', NAME, 'android.intent.action.MY_PACKAGE_REPLACED')])])])
d.insert(end, service + receiver)
open(dst, 'wb').write(d.serialize())
print(axml.Doc(open(dst, 'rb').read()).dump())
