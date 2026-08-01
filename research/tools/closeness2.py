#!/usr/bin/env python3
"""Closeness (bbox area frac) with AUTO polygon-vs-bbox detection.
 - 5 tokens  -> YOLO bbox: class cx cy w h ; area=w*h ; aspect=w/h
 - >=9 odd   -> YOLO-SEG polygon: class x1 y1 x2 y2 ...; area=bbox-extent ; aspect from extent
Reports per-image dominant-box area band + per-class median area & aspect."""
import sys, collections
from pathlib import Path
import numpy as np

def parse(txt):
    boxes=[]  # (cls, area, aspect)
    try:
        for l in txt.read_text().splitlines():
            p=l.split()
            if not p or not p[0].lstrip('-').isdigit(): continue
            c=int(p[0]); vals=[float(x) for x in p[1:]]
            if len(vals)==4:
                w,h=vals[2],vals[3]
            elif len(vals)>=6 and len(vals)%2==0:
                xs=vals[0::2]; ys=vals[1::2]
                w=max(xs)-min(xs); h=max(ys)-min(ys)
            else:
                continue
            if 0<w<=1.01 and 0<h<=1.01:
                boxes.append((c, w*h, (w/h if h>0 else 0)))
    except: pass
    return boxes

def report(name, root):
    root=Path(root)
    labels=[p for p in root.rglob('*.txt') if p.name.lower() not in ('classes.txt','readme.txt')]
    per_box=[]; dom=[]; per_cls=collections.defaultdict(list); per_cls_asp=collections.defaultdict(list); n=0
    for t in labels:
        bs=parse(t)
        if not bs: continue
        n+=1; areas=[a for _,a,_ in bs]
        per_box+=areas; dom.append(max(areas))
        for c,a,asp in bs: per_cls[c].append(a); per_cls_asp[c].append(asp)
    if not per_box:
        print(f"\n### {name}: no boxes"); return
    pb=np.array(per_box); dm=np.array(dom)
    tiny=(dm<0.02).mean(); small=((dm>=0.02)&(dm<0.08)).mean()
    med=((dm>=0.08)&(dm<0.25)).mean(); large=(dm>=0.25).mean()
    close=med+large
    v="CLOSE ✅" if close>0.6 else ("MIXED ⚠️" if close>0.3 else "FAR ❌")
    print(f"\n### {name}  (imgs={n}, boxes={len(pb)})")
    print(f"  box area: median={np.median(pb):.3f} p90={np.percentile(pb,90):.3f}")
    print(f"  dominant area band: tiny={tiny*100:.1f}% small={small*100:.1f}% med={med*100:.1f}% LARGE={large*100:.1f}%")
    print(f"  close-share(med+large)={close*100:.1f}%  {v}")
    for c in sorted(per_cls):
        print(f"    class {c}: n={len(per_cls[c])} med_area={np.median(per_cls[c]):.3f} med_aspect(w/h)={np.median(per_cls_asp[c]):.2f}")

if __name__=='__main__':
    a=sys.argv[1:]
    for i in range(0,len(a),2): report(a[i],a[i+1])
