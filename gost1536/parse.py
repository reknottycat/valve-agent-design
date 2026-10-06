import re, sys, html, io

p = r"F:\设计探索\gost1536\gost1536.htm"
raw = open(p, "rb").read()
try:
    txt = raw.decode("utf-8")
except UnicodeDecodeError:
    txt = raw.decode("cp1251")

# isolate the standard body
start = txt.find("ГОСТ 1536-76")
body = txt[start:]

def cell_text(c):
    c = re.sub(r"<[^>]+>", " ", c)
    c = html.unescape(c)
    return re.sub(r"\s+", " ", c).strip()

out = []
pos = 0
tbl = re.compile(r"<table\b.*?</table>", re.S | re.I)
for m in tbl.finditer(body):
    between = body[pos:m.start()]
    plain = re.sub(r"<[^>]+>", " ", between)
    plain = re.sub(r"\s+", " ", html.unescape(plain)).strip()
    if plain:
        out.append("TEXT: " + plain)
    pos = m.end()
    rows = re.findall(r"<tr\b.*?</tr>", m.group(0), re.S | re.I)
    out.append("=== TABLE (%d rows) ===" % len(rows))
    for r in rows:
        cells = re.findall(r"<t[dh]\b.*?</t[dh]>", r, re.S | re.I)
        vals = [cell_text(c) for c in cells]
        out.append(" | ".join(vals))
    out.append("=== END TABLE ===")

tail = body[pos:]
plain = re.sub(r"<[^>]+>", " ", tail)
plain = re.sub(r"\s+", " ", html.unescape(plain)).strip()
if plain:
    out.append("TEXT: " + plain)

open(r"F:\设计探索\gost1536\gost1536.txt", "w", encoding="utf-8").write("\n".join(out))
print("lines:", len(out))