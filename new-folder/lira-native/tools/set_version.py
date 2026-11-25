import sys
sys.path.insert(0,'/home/user/burs/new-folder/lira-native/tools')
import axml
src,dst,code,name=sys.argv[1],sys.argv[2],int(sys.argv[3]),sys.argv[4]
d=axml.Doc(open(src,'rb').read())
m=d.nodes[d.find('manifest')]
vc,vn=d.attr(m,'versionCode'),d.attr(m,'versionName')
assert code>vc.data
vc.data=code
vn.raw=vn.data=d.string(name)
open(dst,'wb').write(d.serialize())
print(axml.Doc(open(dst,'rb').read()).dump().split('\n')[0])
