# Build H_B, H_P and the linear path H(s) (pedagogical excerpt)
from qiskit.quantum_info import SparsePauliOp

hx, J, hz = 1.0, 1.0, 0.25
HB = SparsePauliOp.from_list([("IX", -hx), ("XI", -hx)])
HP = SparsePauliOp.from_list([("ZZ", -J), ("IZ", -hz), ("ZI", -hz)])


def H_of_s(s: float) -> SparsePauliOp:
    return ((1.0 - s) * HB + s * HP).simplify()
