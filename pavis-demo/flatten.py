import os, re, shutil
SRC = "/home/venom/Documents/googleBusinessAPI/pavis-demo/site/www.pavis-engineering.de"
OUT = "/home/venom/Documents/googleBusinessAPI/pavis-demo/pavis-clean"

if os.path.isdir(OUT): shutil.rmtree(OUT)
for d in ["css","js","img","fonts"]:
    os.makedirs(os.path.join(OUT,d), exist_ok=True)

def clean_name(fn):
    return fn.split("%3F")[0].split("?")[0]

EXT_DIR = {".css":"css",".js":"js",".png":"img",".jpg":"img",".jpeg":"img",
    ".gif":"img",".svg":"img",".webp":"img",".ico":"img",
    ".woff":"fonts",".woff2":"fonts",".ttf":"fonts",".eot":"fonts",".otf":"fonts"}
FONT_SVG = ("fontawesome","linea-icons","elegant")
def target_dir(name):
    base, ext = os.path.splitext(name); ext = ext.lower()
    if ext == ".svg" and any(k in base.lower() for k in FONT_SVG): return "fonts"
    return EXT_DIR.get(ext)

# map: original-relative-srcpath -> flat name ; plus basename->flatname for css url()
path_map = {}      # full src abspath -> (subdir, flatname)
name_to_flat = {}  # cleaned basename -> flatname (last wins ok for url)
used = {}          # (subdir, flatname) used

for root,_,files in os.walk(SRC):
    for f in files:
        if f.endswith(".html"): continue
        src = os.path.join(root,f)
        cn = clean_name(f)
        td = target_dir(cn)
        if not td: continue
        flat = cn
        dst = os.path.join(OUT,td,flat)
        # collision w/ different file? prefix parent dir
        if os.path.exists(dst) and os.path.getsize(dst)!=os.path.getsize(src):
            parent = os.path.basename(root)
            base,ext = os.path.splitext(cn)
            flat = "%s_%s%s" % (base, parent.lower(), ext)
            dst = os.path.join(OUT,td,flat)
        shutil.copyfile(src,dst)
        path_map[src] = (td,flat)
        name_to_flat[cn] = flat

# rewrite css url()
for cf in os.listdir(os.path.join(OUT,"css")):
    p = os.path.join(OUT,"css",cf)
    txt = open(p,encoding="utf-8",errors="ignore").read()
    def repl(m):
        raw = m.group(1).strip("'\"")
        if raw.startswith("data:"): return m.group(0)
        base = clean_name(os.path.basename(raw))
        td = target_dir(base)
        if td and base in name_to_flat:
            return "url(../%s/%s)" % (td, name_to_flat[base])
        return m.group(0)
    txt = re.sub(r"url\(([^)]+)\)", repl, txt)
    open(p,"w",encoding="utf-8").write(txt)

print("flattened:", len(path_map))
for d in ["css","js","img","fonts"]:
    print(d, len(os.listdir(OUT+"/"+d)))
