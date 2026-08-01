#!/usr/bin/env python3
"""Estimate VN plate background color distribution on real cropped plates via HSV.
Masks dark text pixels, classifies dominant bright-background hue."""
import sys, glob, random, collections
import numpy as np, cv2

files=[]
for g in sys.argv[1:]:
    files+=glob.glob(g, recursive=True)
files=[f for f in files if f.lower().endswith(('.jpg','.jpeg','.png'))]
random.seed(3); random.shuffle(files); files=files[:600]

def classify(img):
    h,w=img.shape[:2]
    if h<8 or w<8: return None
    hsv=cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    H,S,V=hsv[:,:,0].astype(int),hsv[:,:,1],hsv[:,:,2]
    # background = brighter pixels (text is dark). keep top 60% by V
    thr=np.percentile(V,45)
    m=V>=thr
    if m.sum()<20: m=np.ones_like(V,bool)
    hs=H[m]; ss=S[m]; vs=V[m]
    mS=np.median(ss); mV=np.median(vs); mH=np.median(hs)
    # white: low saturation, high value
    if mS<55 and mV>110: return 'white'
    # by hue (OpenCV H 0-179)
    if mS>=55:
        if mH<12 or mH>=160: return 'red'
        if 12<=mH<35: return 'yellow'
        if 35<=mH<85: return 'green'
        if 85<=mH<140: return 'blue'
    return 'white' if mV>110 else 'other/dark'

cnt=collections.Counter(); ok=0
for f in files:
    im=cv2.imread(f)
    if im is None: continue
    c=classify(im)
    if c: cnt[c]+=1; ok+=1
print(f"analyzed {ok} crops")
for k,v in cnt.most_common():
    print(f"  {k:12s} {v:4d}  {100*v/ok:5.1f}%")
