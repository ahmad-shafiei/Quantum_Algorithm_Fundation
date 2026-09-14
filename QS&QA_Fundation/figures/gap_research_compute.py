"""Reproduce the adiabatic-gap figures. Requires Python 3 and NumPy.
Run from any directory: python gap_research_compute.py
Units: local J=1, hbar=1. Outputs are written next to this script.
No experimental data or fitted claims of quantum advantage are used.
"""
from pathlib import Path
import numpy as np
import json
ROOT=Path(__file__).resolve().parent
X=np.array([[0.,1.],[1.,0.]])
Z=np.diag([1.,-1.])
I=np.eye(2)
HB=-np.kron(X,I)-np.kron(I,X)
HP=-np.kron(Z,Z)-.25*(np.kron(Z,I)+np.kron(I,Z))
D=HP-HB
def spectrum(s):
    return np.linalg.eigh(HB+s*D)
def gap(s):
    e,_=spectrum(s)
    return float(e[1]-e[0])
# Global screening first; bounded refinement of its isolated minimum.
ss=np.linspace(0,1,2001)
ee,vv=np.linalg.eigh(HB[None,:,:]+ss[:,None,None]*D)
gg=ee[:,1]-ee[:,0]
i=int(gg.argmin())
a,b=ss[i-1],ss[i+1]
for _ in range(60):
    c=a+(b-a)*.3819660112501051
    d=a+(b-a)*.6180339887498949
    if gap(c)<gap(d): b=d
    else: a=c
sstar=(a+b)/2
e,v=spectrum(sstar)
M=abs(v[:,1:].conj().T@D@v[:,0])
ks=[]
for energies,vecs in zip(ee,vv):
    mm=abs(vecs[:,1:].conj().T@D@vecs[:,0])
    ks.append(float(np.max(mm/(energies[1:]-energies[0])**2)))
ks=np.array(ks)
weight=np.maximum(ks,.05*ks.max())
cum=np.concatenate(([0.],np.cumsum((weight[:-1]+weight[1:])*np.diff(ss)/2)))
uu=cum/cum[-1]
def success(T,local,steps):
    u=(np.arange(steps)+.5)/steps
    s=np.interp(u,uu,ss) if local else u
    ew,ev=np.linalg.eigh(HB[None,:,:]+s[:,None,None]*D)
    psi=np.ones(4,dtype=complex)/2
    dt=T/steps
    for E,V in zip(ew,ev):
        psi=V@(np.exp(-1j*E*dt)*(V.conj().T@psi))
    return float(abs(psi[0])**2)
times=np.array([1,2,3,4,5,7,10,15,20,30,40,60,80,120.])
coarse=np.array([[success(t,local,2000) for local in [False,True]] for t in times])
fine=np.array([[success(t,local,4000) for local in [False,True]] for t in times])
diff=float(abs(fine-coarse).max())
assert diff<2e-5, diff
# Open TFIM exact free-fermion spectrum. Cross-check using full spin matrices.
def ff_gap(n,g):
    B=g*np.eye(n)-np.eye(n,k=-1)
    return float(2*np.linalg.svd(B,compute_uv=False)[-1])
def kronlist(ops):
    out=np.ones((1,1))
    for op in ops: out=np.kron(out,op)
    return out
def dense_gap(n,g):
    H=np.zeros((2**n,2**n))
    for j in range(n):
        ops=[I]*n;ops[j]=X;H-=g*kronlist(ops)
    for j in range(n-1):
        ops=[I]*n;ops[j]=Z;ops[j+1]=Z;H-=kronlist(ops)
    ev=np.linalg.eigvalsh(H)
    return float(ev[1]-ev[0])
check=max(abs(dense_gap(n,g)-ff_gap(n,g)) for n in range(2,8) for g in [.5,1,1.5])
assert check<1e-10,check
ns=np.arange(2,33)
scales=np.array([[ff_gap(int(n),g) for g in [1.5,1,.5]] for n in ns])
assert np.max(abs(scales[:,1]-4*np.sin(np.pi/(4*ns+2))))<1e-12
np.savetxt(ROOT/'gap_spectrum.csv',np.column_stack([ss,ee,gg,ks]),delimiter=',',header='s,E0,E1,E2,E3,gap,K',comments='')
np.savetxt(ROOT/'gap_schedule.csv',np.column_stack([times,fine]),delimiter=',',header='T,P_linear,P_local',comments='')
np.savetxt(ROOT/'gap_scaling.csv',np.column_stack([ns,scales]),delimiter=',',header='n,gap_g1p5,gap_g1,gap_g0p5',comments='')
report={'s_min':sstar,'gap_min':gap(sstar),'energies':e.tolist(),
        'M_m0':M.tolist(),'norm_Hprime':float(np.linalg.norm(D,2)),
        'K_max':float(ks.max()),'K_integral_with_floor':float(cum[-1]),
        'time_step_convergence_max_probability_difference':diff,
        'dense_vs_free_fermion_max_gap_difference':check,
        'residual_ground':float(np.linalg.norm((HB+sstar*D)@v[:,0]-e[0]*v[:,0])),
        'times':times.tolist(),'success_probabilities_linear_local':fine.tolist()}
(ROOT/'gap_validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
# Standard vector scientific plots using TikZ, no extra package or style change.
def begin():
    return [r'\begin{tikzpicture}[x=1cm,y=1cm,font=\scriptsize]']
def axis(out,x0,y0,w,h,xlim,ylim,xt,yt,xlabel,title):
    def f(x,y):
        return (x0+w*(x-xlim[0])/(xlim[1]-xlim[0]),y0+h*(y-ylim[0])/(ylim[1]-ylim[0]))
    out.append(r'\draw[->] (%.4f,%.4f)--(%.4f,%.4f);'%(x0,y0,x0+w+.15,y0))
    out.append(r'\draw[->] (%.4f,%.4f)--(%.4f,%.4f);'%(x0,y0,x0,y0+h+.15))
    for val,lab in xt:
        xx,yy=f(val,ylim[0]);out.append(r'\draw (%.4f,%.4f)--+(0,-.07) node[below] {%s};'%(xx,yy,lab))
    for val,lab in yt:
        xx,yy=f(xlim[0],val)
        out.append(r'\draw[gray!20] (%.4f,%.4f)--+(%.4f,0);'%(xx,yy,w))
        out.append(r'\node[left] at (%.4f,%.4f) {%s};'%(xx,yy,lab))
    out.append(r'\node at (%.4f,%.4f) {%s};'%(x0+w/2,y0-.65,xlabel))
    out.append(r'\node at (%.4f,%.4f) {%s};'%(x0+w/2,y0+h+.5,title))
    return f
def line(out,f,x,y,color,style=''):
    pts=' '.join('(%.5f,%.5f)'%f(float(a),float(b)) for a,b in zip(x,y))
    out.append(r'\draw[%s,thick,%s] plot coordinates {%s};'%(color,style,pts))
def save(name,out):
    out.append(r'\end{tikzpicture}')
    (ROOT/name).write_text('\n'.join(out),encoding='utf-8')
o=begin()
f=axis(o,0,0,5.3,4.2,(0,1),(-2.1,2.1),[(0,'$0$'),(.5,'$0.5$'),(1,'$1$')],[(-2,'$-2$'),(0,'$0$'),(2,'$2$')],'$s$',r'\lr{Energy} $E/J$')
colors=['blue!75!black','orange!90!black','gray','green!50!black']
for j,col in enumerate(colors):
    line(o,f,ss[::10],ee[::10,j],col)
    o.append(r'\node[text=%s] at (%.2f,5.3) {$E_%d$};'%(col,.5+j*1.2,j))
f2=axis(o,7,0,5.3,4.2,(0,1),(0,2.1),[(0,'$0$'),(.5,'$0.5$'),(1,'$1$')],[(0,'$0$'),(1,'$1$'),(2,'$2$')],'$s$',r'\lr{Gap} $\Delta/J$')
line(o,f2,ss[::10],gg[::10],'blue!75!black')
x,y=f2(sstar,gap(sstar));o.append(r'\draw[dashed] (%.4f,0)--(%.4f,4.2); \fill (%.4f,%.4f) circle (1.5pt);'%(x,x,x,y))
o.append(r'\node[above left,fill=white,inner sep=1.5pt] at (%.4f,%.4f) {$\Delta_{\min}=0.658861$};'%(x,y))
save('gap_spectrum.tex',o)
o=begin()
f=axis(o,0,0,5.3,4.2,(0,1),(0,1),[(0,'$0$'),(.5,'$0.5$'),(1,'$1$')],[(0,'$0$'),(.5,'$0.5$'),(1,'$1$')],'$u=t/T$',r'\lr{Schedule} $s(u)$')
line(o,f,[0,1],[0,1],'gray','dashed')
line(o,f,uu[::10],ss[::10],'blue!75!black')
f=axis(o,7,0,5.3,4.2,(0,np.log10(120)),(-7,0),[(0,'$1$'),(1,'$10$'),(2,'$100$')],[(-6,'$10^{-6}$'),(-4,'$10^{-4}$'),(-2,'$10^{-2}$'),(0,'$1$')],r'$T\,J/\hbar$',r'\lr{Failure} $1-P_{\mathrm{succ}}$')
for j,col,sty in [(0,'gray','dashed'),(1,'blue!75!black','')]:
    line(o,f,np.log10(times),np.log10(np.maximum(1-fine[:,j],1e-7)),col,sty)
o.append(r'\node[text=gray] at (3,5.05) {\lr{Dashed: linear}};')
o.append(r'\node[text=blue!75!black] at (9,5.05) {\lr{Blue: local schedule}};')
save('gap_schedule.tex',o)
o=begin()
f=axis(o,0,0,11.4,5,(2,32),(-10,1),[(2,'$2$'),(10,'$10$'),(20,'$20$'),(32,'$32$')],[(-10,'$10^{-10}$'),(-8,'$10^{-8}$'),(-6,'$10^{-6}$'),(-4,'$10^{-4}$'),(-2,'$10^{-2}$'),(0,'$1$')],r'\lr{Number of spins} $n$',r'\lr{Open TFIM: full spectral gap} $\Delta/J$')
for j,col in enumerate(['green!50!black','blue!75!black','orange!90!black']):
    line(o,f,ns,np.log10(scales[:,j]),col)
    o.append(r'\node[text=%s] at (%.2f,5.95) {$g=%s$};'%(col,2+j*3.6,['1.5','1','0.5'][j]))
save('gap_scaling.tex',o)
(ROOT/'gap_workflow.tex').write_text(r'''
\begin{tikzpicture}[node distance=7mm,>=Latex,
 every node/.style={font=\small},
 gapbox/.style={draw,rounded corners,align=center,text width=10.6cm,minimum height=10mm,fill=blue!5}]
\node[gapbox] (a) {\RL{مدل، واحد انرژی، اندازه، تقارن و تعریف گاف}};
\node[gapbox,below=of a] (b) {\RL{محاسبهٔ چند تراز یا طیف‌سنجی با مشاهده‌پذیر مناسب}};
\node[gapbox,below=of b] (c) {\RL{کنترل خطا و جست‌وجوی تطبیقی کمینه در مسیر}};
\node[gapbox,below=of c] (d) {\RL{طراحی زمان‌بندی با گاف و عناصر ماتریسی گذار}};
\node[gapbox,below=of d] (e) {\RL{آزمون موفقیت و منابع؛ مقایسه در اندازه‌های مختلف}};
\draw[->] (a)--(b);
\draw[->] (b)--(c);
\draw[->] (c)--(d);
\draw[->] (d)--(e);
\draw[->] (e.east)--++(.65,0)|-(c.east);
\end{tikzpicture}
''',encoding='utf-8')
print(json.dumps(report,indent=2))
