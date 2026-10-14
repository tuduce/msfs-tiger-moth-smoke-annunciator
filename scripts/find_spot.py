"""Map the free wood area of the Ants rear panel and search for box placements (stdlib only).
python -I scripts/find_spot.py [L_mm W_mm]   -> ascii map + feasible (angle, cx, cy) placements"""
import json, math, struct, sys
G='_reference/AntsTigerMoth_int_LOD00'
g=json.load(open(G+'.gltf')); b=open(G+'.bin','rb').read(); A=g['accessors']; bvs=g['bufferViews']
n=[x for x in g['nodes'] if x.get('name')=='panel_rear'][0]; tris=[]
for p in g['meshes'][n['mesh']]['primitives']:
    pa=A[p['attributes']['POSITION']]; bv=bvs[pa['bufferView']]; st=bv.get('byteStride',12); off=bv.get('byteOffset',0)+pa.get('byteOffset',0)
    P=[struct.unpack_from('<3f',b,off+i*st) for i in range(pa['count'])]
    ia=A[p['indices']]; ib=bvs[ia['bufferView']]; io=ib.get('byteOffset',0)+ia.get('byteOffset',0)
    idx=struct.unpack_from(f"<{ia['count']}H",b,io)
    for t in range(0,len(idx),3):
        v=[P[i] for i in idx[t:t+3]]
        if all(-0.8005<q[2]<-0.7955 for q in v): tris.append([(q[0],q[1]) for q in v])
def inside(x,y):
    for a,b_,c in tris:
        d1=(x-b_[0])*(a[1]-b_[1])-(a[0]-b_[0])*(y-b_[1]); d2=(x-c[0])*(b_[1]-c[1])-(b_[0]-c[0])*(y-c[1]); d3=(x-a[0])*(c[1]-a[1])-(c[0]-a[0])*(y-a[1])
        if not ((d1<0 or d2<0 or d3<0) and (d1>0 or d2>0 or d3>0)): return True
    return False
SIDE='left' if 'left' in sys.argv else 'right'      # pilot's right = -X, pilot's left = +X
# obstacles: circles (cx,cy,r), rectangles (x0,x1,y0,y1) on the panel face
if SIDE=='right':
    CIRCLES=[(-0.127,0.235,0.0685)]; RECTS=[(-0.246,-0.177,0.137,0.186)]           # rpm plate, warning placard
    STEP=0.002; X0,X1,Y0,Y1=-0.30,-0.10,0.10,0.33
else:
    CIRCLES=[]                                                                         # airspeed: square plate + magneto switches + placards
    RECTS=[(0.107,0.200,0.194,0.287),(0.184,0.242,0.128,0.184),(0.176,0.250,0.170,0.192),(0.106,0.144,0.286,0.310),(0.058,0.105,0.185,0.305)]
    STEP=0.002; X0,X1,Y0,Y1=0.10,0.30,0.10,0.33
nx=int((X1-X0)/STEP)+1; ny=int((Y1-Y0)/STEP)+1
mask=[[0]*nx for _ in range(ny)]; cls=[['.']*nx for _ in range(ny)]
for j in range(ny):
    y=Y0+j*STEP
    for i in range(nx):
        x=X0+i*STEP
        if not inside(x,y): c='.'
        elif any(math.hypot(x-a,y-b_)<r for a,b_,r in CIRCLES): c='O'
        elif any(r[0]<x<r[1] and r[2]<y<r[3] for r in RECTS): c='P'
        else: c='#'; mask[j][i]=1
        cls[j][i]=c
def free(x,y,m=0.003):          # point + margin ring all on free wood
    r=int(m/STEP)
    i=round((x-X0)/STEP); j=round((y-Y0)/STEP)
    for dj in range(-r,r+1):
        for di in range(-r,r+1):
            jj,ii=j+dj,i+di
            if not(0<=jj<ny and 0<=ii<nx) or not mask[jj][ii]: return False
    return True
def fits(cx,cy,phi,L,W):
    ph=math.radians(phi); u=(math.cos(ph),math.sin(ph)); v=(-math.sin(ph),math.cos(ph))
    for i in range(-6,7):
        for j in range(-3,4):
            a=i/6*L/2; c=j/3*W/2
            if not free(cx+u[0]*a+v[0]*c, cy+u[1]*a+v[1]*c): return False
    return True
if __name__=='__main__':
    nums=[a for a in sys.argv[1:] if a.replace('.','').isdigit()]
    L=float(nums[0])/1000 if len(nums)>0 else 0.060; W=float(nums[1])/1000 if len(nums)>1 else 0.030
    print(f'side={SIDE}: map x from {X0} to {X1}, y 0.33 (top) to 0.10. #=free wood  O=circular obstacle  P=placard/obstacle rect  .=no panel')
    for j in range(ny-1,-1,-3): print(f'{Y0+j*STEP:.3f} '+''.join(cls[j][i] for i in range(0,nx,2)))
    res=[]
    for phi in range(0,181,5):
        for cxi in (range(-290,-150,3) if SIDE=='right' else range(150,290,3)):
            for cyi in range(120,310,3):
                if fits(cxi/1000,cyi/1000,phi,L,W): res.append((phi,cxi/1000,cyi/1000))
    print(f'feasible {L*1000:.0f}x{W*1000:.0f} mm placements:',len(res))
    by={}
    for phi,cx,cy in res: by.setdefault(phi,[]).append((cx,cy))
    for phi,v in sorted(by.items()): print(f'  angle {phi:3d}: {len(v)} spots, e.g. {v[len(v)//2]}')
