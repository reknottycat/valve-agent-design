"""Set geometric patch types after gmshToFoam and before checkMesh."""
from pathlib import Path
import re
import sys


def convert(text):
    wanted={'inlet':'patch','outlet':'patch','walls':'wall','wedgeMinus':'wedge','wedgePlus':'wedge'}
    seen=set()
    def change(m):
        name=m['name']; body=m['body']
        if not re.search(r'\bnFaces\b',body): return m[0]
        if name not in wanted or name in seen: raise ValueError('unexpected patch: '+name)
        if not re.search(r'\bnFaces\s+[1-9]\d*\s*;',body): raise ValueError('empty patch: '+name)
        seen.add(name)
        body,n=re.subn(r'(?m)^(\s*type\s+)\w+(\s*;)',lambda t:t[1]+wanted[name]+t[2],body)
        if n!=1: raise ValueError('missing or repeated patch type: '+name)
        return m['prefix']+body+'}'
    result=re.sub(r'(?P<prefix>(?P<name>\w+)\s*\{)(?P<body>[^{}]*)\}',change,text)
    if seen!=set(wanted): raise ValueError('missing patches: '+str(set(wanted)-seen))
    return result

if __name__=='__main__':
    p=Path(sys.argv[1]); p.write_text(convert(p.read_text()))
