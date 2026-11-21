import math
Z0=79.351684160769
Z1=82.093263356924
L=3.0010320485073683
HB=math.pi/24
HT=math.pi/6
TARGETS={120:{283,285,286},124:{291,292,293}}
def slant(z):return min(L,max(0.,(z-Z0)*L/(Z1-Z0)))
def size(z):
 s=slant(z)
 return min(HB+.8*s,HT+.8*(L-s))
def applies(d,t):return (d==2 and t in TARGETS) or (d==1 and t in set.union(*TARGETS.values()))
