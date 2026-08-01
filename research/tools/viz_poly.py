#!/usr/bin/env python3
"""Draw YOLO-SEG polygons for duydieu; montage by plate-area band."""
import sys, random
from pathlib import Path
import cv2, numpy as np
root=Path(sys.argv[1]); out=sys.argv[2]; band=sys.argv[3]
IMG={'.jpg','.jpeg','.png'}
imgs=[p for p in root.rglob('*') if p.suffix.lower() in IMG]
def lbl(img):
    c=Path(str(img).replace('/images/','/labels/')).with_suffix('.txt')
    return c if c.exists() else None
items=[]
for img in imgs:
    lp=lbl(img)
    if not lp: continue
    mx=0; polys=[]
    for l in lp.read_text().splitlines():
        p=l.split()
        if len(p)>=9:
            v=[float(x) for x in p[1:]]
            xs=v[0::2]; ys=v[1::2]
            a=(max(xs)-min(xs))*(max(ys)-min(ys)); mx=max(mx,a)
            polys.append((int(p[0]),list(zip(xs,ys))))
    if polys: items.append((mx,img,polys))
items.sort()
if not items:
    print("no labeled imgs"); sys.exit(0)
k = min(10, len(items))
sel = items[-k:] if band=='near' else items[:k] if band=='far' else random.sample(items, k)
cell=320; cols=5; rows=2
canvas=np.full((rows*cell,cols*cell,3),30,np.uint8)
for i,(mx,img,polys) in enumerate(sel):
    im=cv2.imread(str(img))
    if im is None: continue
    h,w=im.shape[:2]
    for c,pts in polys:
        arr=np.array([[int(x*w),int(y*h)] for x,y in pts],np.int32)
        col=(0,200,255) if c==0 else (0,255,120)  # BSD orange, BSV green
        cv2.polylines(im,[arr],True,col,3)
    im=cv2.resize(im,(cell-4,cell-22))
    r,cc=divmod(i,cols); y,x=r*cell,cc*cell
    canvas[y+2:y+2+im.shape[0],x+2:x+2+im.shape[1]]=im
    cv2.putText(canvas,f"plate={mx*100:.1f}%",(x+4,y+cell-6),cv2.FONT_HERSHEY_SIMPLEX,0.55,(0,255,120),2)
cv2.imwrite(out,canvas); print("SAVED",out)
