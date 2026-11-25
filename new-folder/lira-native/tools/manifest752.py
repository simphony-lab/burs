"""7.5.2: adds the optional accessibility service that hosts the island over system Settings.
usage: python3 manifest752.py in.xml out.xml versionCode versionName"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import axml
LABEL, NAME, PERM, EXPORTED, PROCESS = 0x01010001, 0x01010003, 0x01010006, 0x01010010, 0x01010011
src, dst, code, name = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
d = axml.Doc(open(src, 'rb').read())
for n, r in (('label', LABEL), ('name', NAME), ('permission', PERM), ('exported', EXPORTED), ('process', PROCESS)):
    d.attr_name(n, r)
man = d.nodes[d.find('manifest')]
vc, vn = d.attr(man, 'versionCode'), d.attr(man, 'versionName')
assert code > vc.data
vc.data = code
vn.raw = vn.data = d.string(name)
assert 'IslandAccessibility' not in d.dump()
app = d.find('application')
end = d.end_of(app)
svc = d.element('service', [('label', LABEL, 'Лира · Динамический остров'),
                            ('name', NAME, 'com.local.simple.notes.IslandAccessibility'),
                            ('permission', PERM, 'android.permission.BIND_ACCESSIBILITY_SERVICE'),
                            ('exported', EXPORTED, True), ('process', PROCESS, ':screen')],
                [d.element('intent-filter', [], [d.element('action', [('name', NAME, 'android.accessibilityservice.AccessibilityService')])])])
d.insert(end, svc)
open(dst, 'wb').write(d.serialize())
print(axml.Doc(open(dst, 'rb').read()).dump())
