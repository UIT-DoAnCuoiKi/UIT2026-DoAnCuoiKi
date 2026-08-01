#!/usr/bin/env python3
"""Inspect a dataset dir: structure, file types, image dims, annotation format, classes."""
import os, sys, json, collections, random
from pathlib import Path
try:
    from PIL import Image
except Exception:
    Image = None

IMG_EXT = {'.jpg','.jpeg','.png','.bmp','.webp'}

def human(n):
    for u in ['B','K','M','G']:
        if n<1024: return f"{n:.0f}{u}"
        n/=1024
    return f"{n:.0f}T"

def tree(root, maxdepth=2):
    root=Path(root); out=[]
    for dp,dns,fns in os.walk(root):
        depth=len(Path(dp).relative_to(root).parts)
        if depth>maxdepth:
            dns[:]=[]; continue
        rel=Path(dp).relative_to(root)
        ind='  '*depth
        out.append(f"{ind}{rel if str(rel)!='.' else '.'}/ ({len(fns)}f,{len(dns)}d)")
        if depth==maxdepth and dns:
            out[-1]+=" ..."
    return '\n'.join(out[:40])

def inspect(root):
    root=Path(root)
    print("="*70); print("DATASET:", root.name); print("="*70)
    ext=collections.Counter(); imgs=[]; txts=[]; xmls=[]; jsons=[]; yamls=[]
    top_dirs=collections.Counter()
    for dp,dns,fns in os.walk(root):
        for f in fns:
            p=Path(dp)/f; e=p.suffix.lower(); ext[e]+=1
            rel=p.relative_to(root)
            if len(rel.parts)>1: top_dirs[rel.parts[0]]+=1
            if e in IMG_EXT: imgs.append(p)
            elif e=='.txt': txts.append(p)
            elif e=='.xml': xmls.append(p)
            elif e=='.json': jsons.append(p)
            elif e in ('.yaml','.yml'): yamls.append(p)
    print("\n[TREE]"); print(tree(root))
    print("\n[EXT COUNTS]", dict(ext.most_common(12)))
    print("[TOP-LEVEL SUBDIR file counts]", dict(top_dirs.most_common(12)))
    print(f"\nIMAGES={len(imgs)}  TXT={len(txts)}  XML={len(xmls)}  JSON={len(jsons)}  YAML={len(yamls)}")

    # annotation format guess
    fmt=[]
    if yamls or (txts and any('labels' in str(t).lower() or 'label' in str(t.parent).lower() for t in txts[:50])): fmt.append("YOLO")
    if xmls: fmt.append("VOC-XML")
    if jsons: fmt.append("COCO/JSON?")
    # classification = images grouped in class subdirs, no annotation
    if not txts and not xmls and not jsons and top_dirs:
        fmt.append("CLASSIFICATION(folder=class)")
    print("ANNOTATION FORMAT GUESS:", fmt or ["unknown/plain-images"])

    # image dims sample
    if Image and imgs:
        s=random.sample(imgs, min(40,len(imgs)))
        dims=[]
        for p in s:
            try:
                with Image.open(p) as im: dims.append(im.size)
            except Exception: pass
        if dims:
            ws=[d[0] for d in dims]; hs=[d[1] for d in dims]
            print(f"IMG DIMS (n={len(dims)}): W[min={min(ws)} max={max(ws)} avg={sum(ws)//len(ws)}]  H[min={min(hs)} max={max(hs)} avg={sum(hs)//len(hs)}]")
            print("  sample names:", [p.name for p in s[:4]])

    # YAML content (YOLO data.yaml -> classes)
    for y in yamls[:3]:
        print(f"\n[YAML {y.relative_to(root)}]")
        try: print("  "+y.read_text()[:400].replace('\n','\n  '))
        except Exception as e: print("  err",e)

    # YOLO label class distribution
    if txts:
        cls=collections.Counter(); nlab=0; empty=0
        for t in txts:
            try:
                lines=[l for l in t.read_text().splitlines() if l.strip()]
                if not lines: empty+=1
                for l in lines:
                    parts=l.split()
                    if parts and parts[0].lstrip('-').isdigit():
                        cls[parts[0]]+=1; nlab+=1
            except Exception: pass
        if nlab:
            print(f"\n[YOLO LABELS] total_boxes={nlab} empty_txt={empty} classes={dict(cls.most_common(20))}")
        else:
            # maybe txt are OCR strings (plate text) not YOLO
            samp=[]
            for t in txts[:5]:
                try: samp.append((t.name, t.read_text()[:60].replace('\n','|')))
                except Exception: pass
            print("\n[TXT not-YOLO sample]", samp)

    # VOC sample
    if xmls:
        x=xmls[0]
        try:
            import re
            c=x.read_text()
            names=re.findall(r'<name>(.*?)</name>', c)
            print(f"\n[VOC sample {x.name}] object names:", collections.Counter(names))
        except Exception as e: print("voc err",e)

    # JSON (COCO?) sample
    if jsons:
        j=jsons[0]
        try:
            d=json.loads(j.read_text())
            if isinstance(d,dict):
                print(f"\n[JSON {j.name}] keys:", list(d.keys())[:10])
                if 'categories' in d: print("  categories:", [c.get('name') for c in d['categories']][:20])
                if 'images' in d: print("  #images:", len(d['images']))
                if 'annotations' in d: print("  #annotations:", len(d['annotations']))
        except Exception as e: print("json err",e)

    # license
    lic=[p for p in root.rglob('*') if p.is_file() and p.name.lower() in ('license','license.txt','license.md','licence','licence.txt')]
    print("\n[LICENSE FILE]", [str(l.relative_to(root)) for l in lic] or "none in archive")

if __name__=='__main__':
    for d in sys.argv[1:]:
        if os.path.isdir(d): inspect(d)
        print()
