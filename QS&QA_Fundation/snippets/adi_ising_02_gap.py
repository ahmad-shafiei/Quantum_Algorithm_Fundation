# Scan Delta(s)=E1(s)-E0(s) and locate the minimum (pedagogical excerpt)
import numpy as np
from qiskit.quantum_info import Operator, SparsePauliOp

hx, J, hz = 1.0, 1.0, 0.25
HB = SparsePauliOp.from_list([("IX", -hx), ("XI", -hx)])
HP = SparsePauliOp.from_list([("ZZ", -J), ("IZ", -hz), ("ZI", -hz)])

ss = np.linspace(0.0, 1.0, 2001)
gaps = []
for s in ss:
    H = (1.0 - s) * HB + s * HP
    e0, e1 = np.linalg.eigvalsh(Operator(H).data)[:2]
    gaps.append(e1 - e0)

i = int(np.argmin(gaps))
s_star, Delta_min = float(ss[i]), float(gaps[i])
print(s_star, Delta_min)
