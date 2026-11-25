"""Minimal reader/writer for Android binary XML (AndroidManifest.xml inside an APK).

Keeps every original string index; new attribute names that need a resource id are inserted
at the end of the resource-mapped part of the string pool (all later indices are shifted),
other new strings are appended. Round-trips the original file byte for byte.
"""
import struct

NONE = 0xFFFFFFFF
T_STRING, T_INT_DEC, T_INT_BOOL = 0x03, 0x10, 0x12


def _u8len(b, p):
    n = b[p]
    if n & 0x80:
        return ((n & 0x7F) << 8) | b[p + 1], p + 2
    return n, p + 1


def _u16len(b, p):
    n = struct.unpack_from('<H', b, p)[0]
    if n & 0x8000:
        return ((n & 0x7FFF) << 16) | struct.unpack_from('<H', b, p + 2)[0], p + 4
    return n, p + 2


class Attr:
    def __init__(self, ns, name, raw, dtype, data):
        self.ns, self.name, self.raw, self.dtype, self.data = ns, name, raw, dtype, data


class Node:
    """kind: ns_start, ns_end, start, end, cdata, raw"""

    def __init__(self, kind, **kw):
        self.kind = kind
        self.line = kw.get('line', 1)
        self.comment = kw.get('comment', NONE)
        self.__dict__.update(kw)


class Doc:
    def __init__(self, data):
        b = bytes(data)
        t, hs, size = struct.unpack_from('<HHI', b, 0)
        assert t == 0x0003 and size == len(b), 'not binary xml'
        p = hs
        self.nodes = []
        self.resmap = []
        while p < len(b):
            t, hs, size = struct.unpack_from('<HHI', b, p)
            c = b[p:p + size]
            if t == 0x0001:
                self._read_pool(c)
            elif t == 0x0180:
                self.resmap = list(struct.unpack_from('<%dI' % ((size - 8) // 4), c, 8))
            elif t in (0x0100, 0x0101):
                line, com, prefix, uri = struct.unpack_from('<IIII', c, 8)
                self.nodes.append(Node('ns_start' if t == 0x0100 else 'ns_end', line=line, comment=com, prefix=prefix, uri=uri))
            elif t == 0x0102:
                line, com, ns, name, ast, asz, acnt, idi, cli, sti = struct.unpack_from('<IIIIHHHHHH', c, 8)
                attrs = []
                for i in range(acnt):
                    a_ns, a_name, a_raw, _sz, _r0, dt, dd = struct.unpack_from('<IIIHBBI', c, 16 + ast + i * asz)
                    attrs.append(Attr(a_ns, a_name, a_raw, dt, dd))
                self.nodes.append(Node('start', line=line, comment=com, ns=ns, name=name, attrs=attrs, idi=idi, cli=cli, sti=sti))
            elif t == 0x0103:
                line, com, ns, name = struct.unpack_from('<IIII', c, 8)
                self.nodes.append(Node('end', line=line, comment=com, ns=ns, name=name))
            elif t == 0x0104:
                line, com, data, _sz, _r0, dt, dd = struct.unpack_from('<IIIHBBI', c, 8)
                self.nodes.append(Node('cdata', line=line, comment=com, data=data, dtype=dt, ddata=dd))
            else:
                self.nodes.append(Node('raw', bytes=c))
            p += size

    def _read_pool(self, c):
        cnt, scnt, flags, sstart, ststart = struct.unpack_from('<IIIII', c, 8)
        assert scnt == 0, 'styled strings not supported'
        self.utf8 = bool(flags & 0x100)
        self.pool_flags = flags
        offs = struct.unpack_from('<%dI' % cnt, c, 28)
        self.strings = []
        for o in offs:
            p = sstart + o
            if self.utf8:
                _, p = _u8len(c, p)
                n, p = _u8len(c, p)
                self.strings.append(c[p:p + n].decode('utf-8'))
            else:
                n, p = _u16len(c, p)
                self.strings.append(c[p:p + n * 2].decode('utf-16-le'))
        self._pool_bytes = c  # for exact round trip when untouched
        self._pool_dirty = False

    # ---- strings -------------------------------------------------------------------------
    def s(self, i):
        return None if i == NONE else self.strings[i]

    def string(self, value):
        """Index of a plain string, appended if missing."""
        for i, v in enumerate(self.strings):
            if v == value:
                return i
        self.strings.append(value)
        self._pool_dirty = True
        return len(self.strings) - 1

    def attr_name(self, value, resid):
        """Index of an attribute-name string bound to a resource id, inserting it if missing."""
        for i, r in enumerate(self.resmap):
            if r == resid and self.strings[i] == value:
                return i
        k = len(self.resmap)
        self._shift(k)
        self.strings.insert(k, value)
        self.resmap.append(resid)
        self._pool_dirty = True
        return k

    def _shift(self, k):
        f = lambda i: i + 1 if i != NONE and i >= k else i
        for n in self.nodes:
            n.comment = f(n.comment)
            if n.kind in ('ns_start', 'ns_end'):
                n.prefix, n.uri = f(n.prefix), f(n.uri)
            elif n.kind in ('start', 'end'):
                n.ns, n.name = f(n.ns), f(n.name)
                for a in getattr(n, 'attrs', []):
                    a.ns, a.name, a.raw = f(a.ns), f(a.name), f(a.raw)
                    if a.dtype == T_STRING:
                        a.data = f(a.data)
            elif n.kind == 'cdata':
                n.data = f(n.data)
                if n.dtype == T_STRING:
                    n.ddata = f(n.ddata)

    # ---- tree helpers --------------------------------------------------------------------
    def find(self, tag, start=0):
        for i in range(start, len(self.nodes)):
            n = self.nodes[i]
            if n.kind == 'start' and self.s(n.name) == tag:
                return i
        return -1

    def end_of(self, i):
        depth = 0
        for j in range(i, len(self.nodes)):
            k = self.nodes[j].kind
            if k == 'start':
                depth += 1
            elif k == 'end':
                depth -= 1
                if depth == 0:
                    return j
        raise ValueError('unclosed element')

    def attr(self, node, name):
        for a in node.attrs:
            if self.s(a.name) == name:
                return a
        return None

    def element(self, tag, attrs, children=()):
        """attrs: list of (name, resid, value); value str -> string, bool -> boolean, int -> int.

        Attribute names must already be in the pool (call attr_name() for all of them before
        building any element), because inserting one shifts indices of nodes not yet inserted.
        """
        mapped = len(self.resmap)
        names = [(self.attr_name(n, r), v) for n, r, v in sorted(attrs, key=lambda a: a[1])]
        assert len(self.resmap) == mapped, 'call attr_name() for every attribute first'
        ns = self.string('http://schemas.android.com/apk/res/android')
        out = []
        for ni, value in names:
            if isinstance(value, bool):
                out.append(Attr(ns, ni, NONE, T_INT_BOOL, 0xFFFFFFFF if value else 0))
            elif isinstance(value, int):
                out.append(Attr(ns, ni, NONE, T_INT_DEC, value))
            else:
                vi = self.string(value)
                out.append(Attr(ns, ni, vi, T_STRING, vi))
        t = self.string(tag)
        nodes = [Node('start', line=1, ns=NONE, name=t, attrs=out, idi=0, cli=0, sti=0)]
        for ch in children:
            nodes.extend(ch)
        nodes.append(Node('end', line=1, ns=NONE, name=self.string(tag)))
        return nodes

    def insert(self, pos, nodes):
        self.nodes[pos:pos] = nodes

    # ---- writing -------------------------------------------------------------------------
    def _pool(self):
        if not self._pool_dirty:
            return self._pool_bytes
        data = bytearray()
        offs = []
        for v in self.strings:
            offs.append(len(data))
            if self.utf8:
                e = v.encode('utf-8')
                for n in (len(v.encode('utf-16-le')) // 2, len(e)):
                    data += bytes([0x80 | (n >> 8), n & 0xFF]) if n > 0x7F else bytes([n])
                data += e + b'\x00'
            else:
                n = len(v.encode('utf-16-le')) // 2
                data += struct.pack('<H', n) if n <= 0x7FFF else struct.pack('<HH', 0x8000 | (n >> 16), n & 0xFFFF)
                data += v.encode('utf-16-le') + b'\x00\x00'
        while len(data) % 4:
            data += b'\x00'
        sstart = 28 + 4 * len(offs)
        hdr = struct.pack('<HHIIIIII', 0x0001, 28, sstart + len(data), len(offs), 0, self.pool_flags, sstart, 0)
        return hdr + struct.pack('<%dI' % len(offs), *offs) + bytes(data)

    def serialize(self):
        body = bytearray(self._pool())
        body += struct.pack('<HHI', 0x0180, 8, 8 + 4 * len(self.resmap)) + struct.pack('<%dI' % len(self.resmap), *self.resmap)
        for n in self.nodes:
            if n.kind in ('ns_start', 'ns_end'):
                body += struct.pack('<HHIIIII', 0x0100 if n.kind == 'ns_start' else 0x0101, 16, 24, n.line, n.comment, n.prefix, n.uri)
            elif n.kind == 'start':
                c = struct.pack('<IIIIHHHHHH', n.line, n.comment, n.ns, n.name, 20, 20, len(n.attrs), n.idi, n.cli, n.sti)
                for a in n.attrs:
                    c += struct.pack('<IIIHBBI', a.ns, a.name, a.raw, 8, 0, a.dtype, a.data)
                body += struct.pack('<HHI', 0x0102, 16, 8 + len(c)) + c
            elif n.kind == 'end':
                body += struct.pack('<HHIIIII', 0x0103, 16, 24, n.line, n.comment, n.ns, n.name)
            elif n.kind == 'cdata':
                body += struct.pack('<HHIIIIHBBI', 0x0104, 16, 28, n.line, n.comment, n.data, 8, 0, n.dtype, n.ddata)
            else:
                body += n.bytes
        return struct.pack('<HHI', 0x0003, 8, 8 + len(body)) + bytes(body)

    def dump(self):
        out, depth = [], 0
        for n in self.nodes:
            if n.kind == 'start':
                at = ' '.join('%s=%r' % (self.s(a.name), self.s(a.raw) if a.raw != NONE else
                              (bool(a.data) if a.dtype == T_INT_BOOL else a.data)) for a in n.attrs)
                out.append('  ' * depth + '<%s %s>' % (self.s(n.name), at))
                depth += 1
            elif n.kind == 'end':
                depth -= 1
        return '\n'.join(out)
