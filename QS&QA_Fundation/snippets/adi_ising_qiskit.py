# --- Adiabatic 2-qubit Ising (sec:adi-ising-example), Qiskit 1.x ---
# Run:  python adi_ising_qiskit.py
# Needs: qiskit, numpy; optional: qiskit-aer, matplotlib
from __future__ import annotations

import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.quantum_info import SparsePauliOp, Operator, Statevector

HX, J, HZ = 1.0, 1.0, 0.25
EPS = 1e-2
T_DEMO = 40.0
N_STEPS = 200


def build_hamiltonians():
    # Little-endian Pauli labels: rightmost letter acts on qubit 0.
    hb = SparsePauliOp.from_list([("IX", -HX), ("XI", -HX)])
    hp = SparsePauliOp.from_list([("ZZ", -J), ("IZ", -HZ), ("ZI", -HZ)])
    return hb, hp


def H_of_s(hb, hp, s: float) -> SparsePauliOp:
    return ((1.0 - s) * hb + s * hp).simplify()


def scan_gap(hb, hp, n: int = 2001):
    ss = np.linspace(0.0, 1.0, n)
    gaps = np.empty(n)
    e0 = np.empty(n)
    e1 = np.empty(n)
    for i, s in enumerate(ss):
        ev = np.linalg.eigvalsh(Operator(H_of_s(hb, hp, s)).data)
        e0[i], e1[i] = ev[0], ev[1]
        gaps[i] = ev[1] - ev[0]
    i = int(np.argmin(gaps))
    return ss, e0, e1, gaps, float(ss[i]), float(gaps[i]), float(e0[i]), float(e1[i])


def heuristic_T(hb, hp, delta_min: float) -> tuple[float, float]:
    norm = float(np.linalg.norm((Operator(hp) - Operator(hb)).data, ord=2))
    return norm, norm / (delta_min**2 * EPS)


def trotter_slice(s: float, dt: float) -> QuantumCircuit:
    """First-order product formula for exp(-i H(s) dt)."""
    qc = QuantumCircuit(2)
    ax = (1.0 - s) * HX * dt
    azz = s * J * dt
    az = s * HZ * dt
    qc.rx(-2.0 * ax, 0)
    qc.rx(-2.0 * ax, 1)
    qc.rzz(-2.0 * azz, 0, 1)
    qc.rz(-2.0 * az, 0)
    qc.rz(-2.0 * az, 1)
    return qc


def digital_adiabatic_sv(T: float = T_DEMO, n_steps: int = N_STEPS) -> QuantumCircuit:
    dt = T / n_steps
    qc = QuantumCircuit(2)
    qc.h([0, 1])
    for k in range(n_steps):
        qc.compose(trotter_slice((k + 0.5) / n_steps, dt), inplace=True)
    return qc


def digital_adiabatic_shots(T: float = T_DEMO, n_steps: int = N_STEPS) -> QuantumCircuit:
    qc = digital_adiabatic_sv(T, n_steps)
    qcm = QuantumCircuit(2, 2)
    qcm.compose(qc, inplace=True)
    qcm.measure([0, 1], [0, 1])
    return qcm


def main():
    hb, hp = build_hamiltonians()
    print("H_B:", hb)
    print("H_P:", hp)

    ss, e0, e1, gaps, s_star, dmin, e0s, e1s = scan_gap(hb, hp)
    print(f"s* ≈ {s_star:.4f},  Delta_min ≈ {dmin:.8f}")
    print(f"E0(s*) ≈ {e0s:.8f},  E1(s*) ≈ {e1s:.8f}")

    norm, T_heur = heuristic_T(hb, hp, dmin)
    print(f"||H_P-H_B||_2 ≈ {norm:.6f}")
    print(f"heuristic T ≳ {T_heur:.1f}  (eps={EPS})")
    print(f"digital demo uses T={T_DEMO}, n_steps={N_STEPS}")

    probs = Statevector.from_instruction(digital_adiabatic_sv()).probabilities()
    print("P(00), P(01), P(10), P(11) =", np.round(probs, 4))
    print("success P(|00>) =", float(probs[0]))

    try:
        from qiskit_aer import AerSimulator

        backend = AerSimulator()
        qcm = digital_adiabatic_shots()
        counts = backend.run(transpile(qcm, backend), shots=4096).result().get_counts()
        print("counts:", dict(sorted(counts.items())))
    except Exception as exc:
        print("AerSimulator skipped:", exc)

    try:
        import matplotlib.pyplot as plt
        from pathlib import Path

        out = Path(__file__).resolve().parent.parent / "figures"
        fig, ax = plt.subplots(1, 2, figsize=(8.2, 3.2))
        ax[0].plot(ss, e0, label=r"$E_0$")
        ax[0].plot(ss, e1, label=r"$E_1$")
        ax[0].axvline(s_star, color="k", ls="--", lw=0.8)
        ax[0].set_xlabel(r"$s$")
        ax[0].set_ylabel(r"$E$")
        ax[0].legend(frameon=False)
        ax[1].plot(ss, gaps)
        ax[1].axvline(s_star, color="k", ls="--", lw=0.8)
        ax[1].plot([s_star], [dmin], "o")
        ax[1].set_xlabel(r"$s$")
        ax[1].set_ylabel(r"$\Delta(s)$")
        fig.tight_layout()
        fig.savefig(out / "adi_ising_qiskit_gap.pdf", bbox_inches="tight")
        fig.savefig(out / "adi_ising_qiskit_gap.png", dpi=160, bbox_inches="tight")
        print("wrote figures/adi_ising_qiskit_gap.(pdf|png)")
        plt.close(fig)
    except Exception as exc:
        print("plot skipped:", exc)


if __name__ == "__main__":
    main()
