# One Trotter slice of the digital adiabatic path (pedagogical excerpt)
from qiskit import QuantumCircuit

hx, J, hz = 1.0, 1.0, 0.25


def trotter_slice(s: float, dt: float) -> QuantumCircuit:
    qc = QuantumCircuit(2)
    ax = (1.0 - s) * hx * dt
    azz = s * J * dt
    az = s * hz * dt
    qc.rx(-2.0 * ax, 0)
    qc.rx(-2.0 * ax, 1)
    qc.rzz(-2.0 * azz, 0, 1)
    qc.rz(-2.0 * az, 0)
    qc.rz(-2.0 * az, 1)
    return qc
