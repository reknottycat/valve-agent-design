import math
ARCS=[[0.008889005948377998, 1.0383085452482557], [1.056086557145, 2.085506096445], [2.1032841083416143, 3.132703647641416], [3.1504816595379994, 4.179901198838001], [4.197679210734727, 5.227098750035001], [5.244876761930999, 6.2742963012312085]]
R=112.5
Z0,Z1=21.95,22.0
H0,SLOPE,MAX_SIZE=.25,.8,25.
CUTOFF=(MAX_SIZE-H0)/SLOPE
def distance(x,y,z):
 rho=math.hypot(x-300,y);theta=math.atan2(y,x-300);dz=max(Z0-z,z-Z1,0.);best=float('inf')
 for lo,hi in ARCS:
  angle=lo+(theta-lo)%(2*math.pi)
  radial=abs(rho-R) if angle<=hi else min(math.hypot(x-300-R*math.cos(t),y-R*math.sin(t)) for t in (lo,hi))
  best=min(best,math.hypot(radial,dz))
 return best
def apply(dim,tag,x,y,z,existing_lc):
 # Proposed 2D comparison only. Existing lc means after all earlier constraints.
 if dim not in (1,2):return existing_lc
 d=distance(x,y,z)
 if d>=CUTOFF:return existing_lc
 return min(existing_lc,H0+SLOPE*d)
