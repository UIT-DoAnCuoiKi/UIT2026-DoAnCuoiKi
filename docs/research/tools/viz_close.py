#!/usr/bin/env python3
"""Draw YOLO boxes, montage images split by dominant-box area band (near vs far)."""
import sys, glob, random
from pathlib import Path
import cv2, numpy as np

root=Path(sys.argv[1]); out=sys.argv[2]; band=sys.argv[3]  # 'near' or 'far' or 'all'
IMG={'.jpg','.jpeg','.png'}
imgs=[p for p in root.rglob('*') if p.suffix.lower() in IMG]

def lbl_for(img):
    # try labels dir sibling
    cands=[img.with_suffix('.txt'),
           Path(str(img).replace('/images/','/labels/')).with_suffix('.txt'),
           img.parent.parent/'labels'/(img.stem+'.txt')]
    for c in cands:
        if c.exists(): return c
    return None

items=[]
for img in imgs:
    lp=lbl_for(img)
    if not lp: continue
    mx=0
    for l in lp.read_text().splitlines():
        p=l.split()
        if len(p)>=5 and p[0].lstrip('-').isdigit():
            try:
                a=float(p[3])*float(p[4])
                if 0<a<=1: mx=max(mx,a)
            except: pass
    if mx>0: items.append((mx,img,lp))
if not items:
    print("no labeled imgs"); sys.exit(0)
items.sort()
if band=='near': sel=items[-16:]
elif band=='far': sel=items[:16]
else:
    random.seed(1); sel=random.sample(items,min(16,len(items)))
cell=320; cols=4; rows=(len(sel)+cols-1)//cols
canvas=np.full((rows*cell,cols*cell,3),30,np.uint8)
for i,(mx,img,lp) in enumerate(sel):
    im=cv2.imread(str(img))
    if im is None: continue
    h,w=im.shape[:2]
    for l in lp.read_text().splitlines():
        p=l.split()
        if len(p)>=5 and p[0].lstrip('-').isdigit():
            cx,cy,bw,bh=[float(x) for x in p[1:5]]
            x1=int((cx-bw/2)*w); y1=int((cy-bh/2)*h); x2=int((cx+bw/2)*w); y2=int((cy+bh/2)*h)
            cv2.rectangle(im,(x1,y1),(x2,y2),(0,255,0),3)
    im=cv2.resize(im,(cell-4,cell-22))
    r,c=divmod(i,cols); y,x=r*cell,c*cell
    canvas[y+2:y+2+im.shape[0],x+2:x+2+im.shape[1]]=im
    cv2.putText(canvas,f"domArea={mx*100:.1f}%",(x+4,y+cell-6),cv2.FONT_HERSHEY_SIMPLEX,0.6,(0,255,120),2)
cv2.imwrite(out,canvas); print("SAVED",out,"n=",len(sel))
