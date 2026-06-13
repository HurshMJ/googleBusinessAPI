import os, re, shutil
OUT = "/home/venom/Documents/googleBusinessAPI/pavis-demo/pavis-clean"
H_IN = "/home/venom/Documents/googleBusinessAPI/pavis-demo/site/www.pavis-engineering.de/en/index.html"

def clean_name(fn): return fn.split("%3F")[0].split("?")[0]
EXT_DIR = {".css":"css",".js":"js",".png":"img",".jpg":"img",".jpeg":"img",
    ".gif":"img",".svg":"img",".webp":"img",".ico":"img",
    ".woff":"fonts",".woff2":"fonts",".ttf":"fonts",".eot":"fonts",".otf":"fonts"}
FONT_SVG=("fontawesome","linea-icons","elegant")
def target_dir(name):
    base,ext=os.path.splitext(name); ext=ext.lower()
    if ext==".svg" and any(k in base.lower() for k in FONT_SVG): return "fonts"
    return EXT_DIR.get(ext)

# build basename->flat map from what we copied
name_to_flat={}
for d in ["css","js","img","fonts"]:
    for f in os.listdir(os.path.join(OUT,d)):
        name_to_flat[f]=(d,f)

def map_url(u):
    u=u.strip()
    if not u or u.startswith(("data:","http://","https://","#","mailto:","tel:","javascript:")):
        return None
    base=clean_name(os.path.basename(u))
    td=target_dir(base)
    if not td: return None
    # try exact, then collision-prefixed variants present in dir
    if base in name_to_flat: return "%s/%s" % name_to_flat[base]
    return None

txt=open(H_IN,encoding="utf-8",errors="ignore").read()

def attr_repl(m):
    attr,q,val=m.group(1),m.group(2),m.group(3)
    nv=map_url(val)
    return '%s=%s%s%s' % (attr,q,nv,q) if nv else m.group(0)
txt=re.sub(r'(href|src)=(["\'])([^"\']+)\2', attr_repl, txt)

def srcset_repl(m):
    q=m.group(1); parts=[]
    for item in m.group(2).split(","):
        item=item.strip()
        if not item: continue
        seg=item.split()
        nv=map_url(seg[0])
        seg[0]=nv if nv else seg[0]
        parts.append(" ".join(seg))
    return 'srcset=%s%s%s' % (q,", ".join(parts),q)
txt=re.sub(r'srcset=(["\'])([^"\']+)\1', srcset_repl, txt)

def style_url(m):
    raw=m.group(1).strip("'\"")
    nv=map_url(raw)
    return "url(%s)"%nv if nv else m.group(0)
txt=re.sub(r"url\(([^)]+)\)", style_url, txt)

open(os.path.join(OUT,"index.html"),"w",encoding="utf-8").write(txt)
# report any unmapped local asset refs
leftover=set(re.findall(r'(?:href|src)=["\']((?:\.\./|/)[^"\']+)["\']', txt))
print("index.html written")
print("remaining relative refs:", len(leftover))
for x in sorted(leftover)[:20]: print("  ?", x)
