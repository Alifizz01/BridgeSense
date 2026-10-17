"""Error and noise budget for one channel, in Pa and % FS, plus a Monte Carlo over tolerances.

Two views:
  raw      : before any calibration (what the hardware alone gives you)
  residual : what is left after the pressure x temperature calibration in calibrate.py
             (static offset/span/gain errors are absorbed by the fit; drift away from the
              calibration conditions, noise and fit residual remain)
"""
import math
import numpy as np
import design as d

K_T = 1.380649e-23 * 300


def noise_terms():
    enbw = d.DATA_RATE / 2  # ponytail: brick-wall approx of the sinc filter ENBW, refine with the real filter shape
    return {
        "INA voltage noise": d.INA_EN * math.sqrt(enbw),
        "Bridge thermal noise": math.sqrt(4 * K_T * d.R_BRIDGE * enbw),
        "ADC noise (input referred)": d.ADC_NOISE_RMS / d.GAIN,
        "Quantisation": d.ADC_FSR / 2**d.ADC_BITS / math.sqrt(12) / d.GAIN,
    }


def noise_rms():
    return math.sqrt(sum(v**2 for v in noise_terms().values()))


def budget():
    """Rows: (term, raw V, residual V), input referred, worst case at full scale."""
    vfs = d.V_FS_BRIDGE
    gdrift = (d.INA_GAIN_DRIFT + d.RG_TC) * d.DT * vfs
    rows = [
        ("Bridge offset +-2 mV/V", 2e-3 * d.VEXC, 0.0),
        ("Bridge span tolerance +-20 %", 0.20 * vfs, 0.0),
        ("INA offset", d.INA_VOS_MAX, 0.0),
        ("INA offset drift x dT", d.INA_VOS_DRIFT_MAX * d.DT, d.INA_VOS_DRIFT_MAX * d.DT),
        ("INA gain error", d.INA_GAIN_ERR_MAX * vfs, 0.0),
        ("INA + RG gain drift x dT", gdrift, gdrift),
        ("Excitation/reference drift (ratiometric)", 0.0, 0.0),
    ]
    rows += [(k + " (rms)", v, v) for k, v in noise_terms().items()]
    return rows


def to_pa(v):
    return v / d.S_V_PER_PA


def monte_carlo(n=20000, cal_residual_pa=0.0, seed=1):
    """Post-calibration error at FS in Pa: drift terms uniform within limits, noise gaussian."""
    rng = np.random.default_rng(seed)
    u = lambda: rng.uniform(-1, 1, n)
    err = (u() * d.INA_VOS_DRIFT_MAX * d.DT
           + (u() * d.INA_GAIN_DRIFT + u() * d.RG_TC) * d.DT * d.V_FS_BRIDGE
           + rng.normal(0, noise_rms(), n)
           + u() * cal_residual_pa * d.S_V_PER_PA)
    return to_pa(err)


def report(cal_residual_pa=0.0):
    rows = budget()
    pct = lambda pa: 100 * pa / d.P_FS
    out = ["| Term | Raw (Pa) | Raw (% FS) | After cal (Pa) | After cal (% FS) |", "|---|---|---|---|---|"]
    for name, raw, res in rows:
        out.append(f"| {name} | {to_pa(raw):.2f} | {pct(to_pa(raw)):.4f} | {to_pa(res):.2f} | {pct(to_pa(res)):.4f} |")
    raw_rss = to_pa(math.sqrt(sum(r**2 for _, r, _ in rows)))
    res_rss = math.sqrt(to_pa(math.sqrt(sum(r**2 for _, _, r in rows))) ** 2 + cal_residual_pa**2)
    out.append(f"| Calibration fit residual (max) | | | {cal_residual_pa:.2f} | {pct(cal_residual_pa):.4f} |")
    out.append(f"| **RSS total** | {raw_rss:.1f} | {pct(raw_rss):.3f} | {res_rss:.2f} | {pct(res_rss):.4f} |")
    p95 = float(np.percentile(np.abs(monte_carlo(cal_residual_pa=cal_residual_pa)), 95))
    n = noise_rms()
    out += ["", f"Monte Carlo (20000 runs, after cal): 95th percentile |error| = {p95:.2f} Pa = {pct(p95):.4f} % FS",
            f"Total rms noise {n*1e9:.0f} nV input referred = {to_pa(n):.3f} Pa rms; "
            f"effective resolution over the sensor span {math.log2(d.V_FS_BRIDGE / n):.1f} bits"]
    return "\n".join(out), p95, raw_rss, res_rss


if __name__ == "__main__":
    import json, pathlib
    p = pathlib.Path("docs/calibration_summary.json")
    cal = json.loads(p.read_text())["max_abs_residual_after_pa"] if p.exists() else 0.0
    print(report(cal)[0])
