# Heuristic T from spectral norm of dH/ds and Delta_min (pedagogical excerpt)
import numpy as np
from qiskit.quantum_info import Operator, SparsePauliOp

hx, J, hz = 1.0, 1.0, 0.25
eps = 1e-2
Delta_min = 0.65886072  # from the gap scan / analytic example
HB = SparsePauliOp.from_list([("IX", -hx), ("XI", -hx)])
HP = SparsePauliOp.from_list([("ZZ", -J), ("IZ", -hz), ("ZI", -hz)])
norm = float(np.linalg.norm((Operator(HP) - Operator(HB)).data, ord=2))
T_heur = norm / (Delta_min**2 * eps)
print(norm, T_heur)
