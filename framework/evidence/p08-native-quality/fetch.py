import urllib.request,hashlib,re,pathlib,subprocess,json
b=pathlib.Path(__file__).parent
out=[]
for name in ['openfoam','libopenfoam']:
 u=f'https://packages.debian.org/trixie/amd64/{name}/download'
 html=urllib.request.urlopen(u,timeout=40).read().decode()
 (b/'evidence'/f'{name}-download.html').write_text(html)
 sha=re.search(r'SHA256 checksum.*?([a-f0-9]{64})',html,re.S).group(1)
 fn=f'{name}_1912.200626-3+b1_amd64.deb'
 data=urllib.request.urlopen('https://deb.debian.org/debian/pool/main/o/openfoam/'+fn,timeout=60).read()
 assert hashlib.sha256(data).hexdigest()==sha
 p=b/'packages'/fn;p.write_bytes(data)
 subprocess.run(['dpkg-deb','-x',str(p),str(b/'root')],check=True)
 out.append({'file':fn,'bytes':len(data),'sha256':sha,'source':u}); print(out[-1],flush=True)
(b/'evidence/packages.json').write_text(json.dumps(out,indent=2))
