"""Synthetic sensor data -> 2D polynomial calibration P = f(V, T) -> residuals and table.

The synthetic sensor is a made-up model with offset, span, nonlinearity and temperature
coefficients in a plausible range for a piezoresistive die. It is not data from a real part.
"""
import csv
import json
import pathlib
import numpy as np
import design as d

DEG_V, DEG_T = 3, 2
NOISE_V = 0.36e-6  # input referred rms, from budget.py


def sensor(p, t, rng=None, noise_v=0.0):
    """Bridge output in V for pressure p (Pa) and temperature t (degC)."""
    x = np.asarray(p) / d.P_FS
    dt = np.asarray(t) - 25.0
    off = 3.3e-3 + 15e-6 * dt + 0.2e-6 * dt**2                  # offset + TCO
    span = d.V_FS_BRIDGE * (1 - 2.0e-3 * dt + 4e-6 * dt**2)     # TCS about -0.2 %/degC
    v = off + span * (x + 0.024 * x * (1 - x))                  # 0.6 % FS bow at mid scale
    if rng is not None and noise_v:
        v = v + rng.normal(0, noise_v, np.shape(v))
    return v


def design_matrix(v, t):
    vn = np.asarray(v) / d.V_FS_BRIDGE
    tn = (np.asarray(t) - 25.0) / 50.0
    return np.column_stack([vn**i * tn**j for i in range(DEG_V + 1) for j in range(DEG_T + 1)])


def fit(v, t, p):
    return np.linalg.lstsq(design_matrix(v, t), p, rcond=None)[0]


def apply(coef, v, t):
    return design_matrix(v, t) @ coef


def two_point_25c(v):
    """Naive reference: linear offset and span trim at 25 degC only."""
    v0, v1 = sensor(0.0, 25.0), sensor(d.P_FS, 25.0)
    return (v - v0) / (v1 - v0) * d.P_FS


def run(out=pathlib.Path("docs"), plots=True):
    rng = np.random.default_rng(0)
    P, T = (a.ravel() for a in np.meshgrid(np.linspace(0, d.P_FS, 11), np.linspace(-20, 60, 9)))
    coef = fit(sensor(P, T, rng, NOISE_V), T, P)
    # validate on a fresh grid that does not reuse the fit points
    Pv, Tv = (a.ravel() for a in np.meshgrid(np.linspace(250, d.P_FS - 250, 15), np.linspace(-15, 55, 8)))
    Vv = sensor(Pv, Tv, rng, NOISE_V)
    before = two_point_25c(Vv) - Pv
    after = apply(coef, Vv, Tv) - Pv

    out.mkdir(exist_ok=True)
    with open(out / "calibration_table.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["i_v", "j_t", "coef_pa"])
        idx = [(i, j) for i in range(DEG_V + 1) for j in range(DEG_T + 1)]
        for (i, j), c in zip(idx, coef):
            w.writerow([i, j, f"{c:.9g}"])
    summary = {
        "model": "P = sum coef_ij * vn^i * tn^j, vn = V / 0.033 V, tn = (T - 25) / 50 degC",
        "max_abs_residual_before_pa": float(np.max(np.abs(before))),
        "max_abs_residual_after_pa": float(np.max(np.abs(after))),
        "rms_residual_after_pa": float(np.sqrt(np.mean(after**2))),
    }
    (out / "calibration_summary.json").write_text(json.dumps(summary, indent=2))

    if plots:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        for name, r, title in [("residual_before.png", before, "Before: linear 2-point trim at 25 degC"),
                               ("residual_after.png", after, "After: 2D polynomial fit (V^3 x T^2)")]:
            fig, ax = plt.subplots(figsize=(6, 3.6))
            sc = ax.scatter(Pv / 1e3, 100 * r / d.P_FS, c=Tv, cmap="coolwarm", s=14)
            fig.colorbar(sc, label="T (degC)")
            ax.set(xlabel="Applied pressure (kPa)", ylabel="Error (% FS)", title=title)
            ax.grid(alpha=0.3)
            fig.tight_layout()
            fig.savefig(out / name, dpi=120)
            plt.close(fig)
    return summary


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
