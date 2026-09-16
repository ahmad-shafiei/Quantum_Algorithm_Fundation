# Reproduce spectrum / Delta_min / heuristic T without Qiskit (same numbers as the text).
import numpy as np
from pathlib import Path

X = np.array([[0.0, 1.0], [1.0, 0.0]])
Z = np.diag([1.0, -1.0])
I = np.eye(2)
HX, J, HZ = 1.0, 1.0, 0.25
HB = -HX * (np.kron(X, I) + np.kron(I, X))
HP = -J * np.kron(Z, Z) - HZ * (np.kron(Z, I) + np.kron(I, Z))

ss = np.linspace(0.0, 1.0, 2001)
ee = np.linalg.eigh(HB[None, :, :] + ss[:, None, None] * (HP - HB))[0]
gaps = ee[:, 1] - ee[:, 0]
i = int(np.argmin(gaps))
s_star, dmin = float(ss[i]), float(gaps[i])
norm = float(np.linalg.norm(HP - HB, ord=2))
T_heur = norm / (dmin**2 * 1e-2)
print(f"s*={s_star:.4f}  Delta_min={dmin:.8f}  ||dH/ds||={norm:.6f}  T>~{T_heur:.1f}")

# Exact piecewise-constant Schrödinger evolution (reference for Trotter)
def success(T, steps=400):
    psi = np.ones(4, dtype=complex) / 2.0
    dt = T / steps
    for k in range(steps):
        s = (k + 0.5) / steps
        e, v = np.linalg.eigh((1 - s) * HB + s * HP)
        psi = v @ (np.exp(-1j * e * dt) * (v.conj().T @ psi))
    return float(abs(psi[0]) ** 2)

for T in (5, 20, 40, 100, 500):
    print(f"T={T:4g}  P00_exact~{success(T):.4f}")

# Save a compact pdf/png for the document if matplotlib is available
try:
    import matplotlib.pyplot as plt

    out = Path(__file__).resolve().parent
    fig, ax = plt.subplots(1, 2, figsize=(8.0, 3.1))
    ax[0].plot(ss, ee[:, 0], label=r"$E_0$")
    ax[0].plot(ss, ee[:, 1], label=r"$E_1$")
    ax[0].axvline(s_star, ls="--", color="k", lw=0.8)
    ax[0].set_xlabel(r"$s$")
    ax[0].set_ylabel(r"$E$")
    ax[0].legend(frameon=False, fontsize=8)
    ax[1].plot(ss, gaps)
    ax[1].plot([s_star], [dmin], "o")
    ax[1].axvline(s_star, ls="--", color="k", lw=0.8)
    ax[1].set_xlabel(r"$s$")
    ax[1].set_ylabel(r"$\Delta(s)$")
    fig.tight_layout()
    fig.savefig(out / "adi_ising_qiskit_gap.pdf", bbox_inches="tight")
    fig.savefig(out / "adi_ising_qiskit_gap.png", dpi=160, bbox_inches="tight")
    print("wrote", out / "adi_ising_qiskit_gap.pdf")
except Exception as exc:
    print("plot skipped:", exc)
