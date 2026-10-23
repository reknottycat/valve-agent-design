import math
H0=math.pi/24
SLOPE=.8
CUTOFF=(25-H0)/SLOPE
ARCS=((110.74996624095,79.25,.25,2.722713633111,4.712388980385),(105.25003375904,79.25,.25,-math.pi/2,.418879020458))
def arc_distance(rho,z,arc):
 R,Z,a,lo,hi=arc
 dr=rho-R;dz=z-Z;theta=math.atan2(dz,dr)
 theta=lo+(theta-lo)%(2*math.pi)
 if theta<=hi:return abs(math.hypot(dr,dz)-a)
 return min(math.hypot(rho-(R+a*math.cos(t)),z-(Z+a*math.sin(t))) for t in (lo,hi))
def distance(x,y,z):
 rho=math.hypot(x-300,y)
 return min(arc_distance(rho,z,a) for a in ARCS)
def apply(dim,tag,x,y,z,lc):
 if dim!=3 or tag!=1:return lc
 d=distance(x,y,z)
 if d>=CUTOFF:return lc
 return min(lc,H0+SLOPE*d)
