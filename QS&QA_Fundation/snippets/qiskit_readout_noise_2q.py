# Minimal 2-qubit example: independent per-qubit readout noise via Qiskit Aer
import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, ReadoutError
# Row-stochastic assignment matrix: A[i,j] = P(measured=j | prepared=i)
A_q0 = np.array([[0.92, 0.08],   # prepared |0>
                 [0.11, 0.89]])  # prepared |1>
A_q1 = np.array([[0.90, 0.10],
                 [0.12, 0.88]])
noise_model = NoiseModel()
noise_model.add_readout_error(ReadoutError(A_q0), [0])  # attach to qubit 0
noise_model.add_readout_error(ReadoutError(A_q1), [1])  # attach to qubit 1
# Simple entangled circuit
qc = QuantumCircuit(2, 2)
qc.h(0)
qc.cx(0, 1)
qc.measure([0, 1], [0, 1])
# Noisy simulation: readout errors applied at measurement time
sim = AerSimulator(noise_model=noise_model)
tqc = transpile(qc, sim)
result = sim.run(tqc, shots=4096).result()
counts = result.get_counts()  # bitstring -> shot count