# 4-qubit ZZFeatureMap circuit (same pattern as project dataset generation)
import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit.library import zz_feature_map
num_qubits = 4
thetas = np.array([0.3, 0.7, 1.1, 0.5])  # one angle per qubit / feature
# feature_dimension: number of qubits (feature variables)
# reps: how many times the feature-map block is repeated (circuit depth)
# entanglement: 'full' | 'linear' | 'circular' | explicit pair list
feature_map = zz_feature_map(
    feature_dimension=num_qubits,
    reps=2,
    entanglement="full",)
qc = QuantumCircuit(num_qubits, num_qubits)
# bind angles and insert the feature-map sub-circuit
qc.compose(feature_map.assign_parameters(thetas), inplace=True)
qc.measure(range(num_qubits), range(num_qubits))
# qc is ready for ideal or noisy simulation (NoiseModel on AerSimulator)