# Assemble the digital adiabatic circuit and read P(|00>) (pedagogical excerpt)
import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector

hx, J, hz = 1.0, 1.0, 0.25
T, n_steps = 40.0, 200
dt = T / n_steps


def trotter_slice(s, dt):
    qc = QuantumCircuit(2)
    ax, azz, az = (1 - s) * hx * dt, s * J * dt, s * hz * dt
    qc.rx(-2 * ax, 0)
    qc.rx(-2 * ax, 1)
    qc.rzz(-2 * azz, 0, 1)
    qc.rz(-2 * az, 0)
    qc.rz(-2 * az, 1)
    return qc


qc = QuantumCircuit(2)
qc.h([0, 1])
for k in range(n_steps):
    qc.compose(trotter_slice((k + 0.5) / n_steps, dt), inplace=True)
probs = Statevector.from_instruction(qc).probabilities()
print(np.round(probs, 4), float(probs[0]))
