import os
import sys
import pathlib
import numpy as np
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parents[1]))
import design as d
import budget
import calibrate as cal
import spice_check

needs_spice = pytest.mark.skipif(spice_check.ngspice() is None and not os.environ.get("CI"),
                                 reason="ngspice not installed (required in CI)")


@pytest.fixture(scope="module")
def sim():
    return spice_check.run()


@needs_spice
def test_dc_gain_matches_rg(sim):
    assert sim["VADC_DC"] / sim["VIN_DC"] == pytest.approx(d.GAIN, rel=0.01)


@needs_spice
def test_ac_gain_matches_rg(sim):
    assert sim["G_AC"] == pytest.approx(d.GAIN, rel=0.01)


@needs_spice
def test_minus3db_corner(sim):
    assert sim["F3DB"] == pytest.approx(d.F3DB, rel=0.05)


@needs_spice
def test_alias_attenuation_at_modulator_rate(sim):
    assert sim["ATT256K_DB"] < -45


@needs_spice
def test_input_noise_matches_model(sim):
    # 0.1 Hz..1 kHz, INA e_n 50 nV/rtHz plus bridge and RG thermal noise
    assert 1.4e-6 < sim["INOISE_RMS_1K"] < 2.0e-6


def test_design_numbers():
    assert d.GAIN == pytest.approx(40.2, abs=0.05)
    assert d.V_FS_BRIDGE * d.GAIN < d.VEXC / 2   # output stays inside +-1.65 V around REF
    assert d.F_MOD / d.F3DB > 200                 # corner far below modulator rate


def test_budget_after_cal_better_than_raw():
    _, p95, raw, res = budget.report(cal_residual_pa=5.0)
    assert res < raw / 20
    assert 100 * p95 / d.P_FS < 0.2


def test_ratiometric_term_is_zero():
    assert dict((n, r) for n, r, _ in budget.budget())["Excitation/reference drift (ratiometric)"] == 0


def test_known_coefficient_recovery():
    rng = np.random.default_rng(3)
    v = rng.uniform(0, d.V_FS_BRIDGE, 200)
    t = rng.uniform(-20, 60, 200)
    true = rng.normal(0, 1000, (cal.DEG_V + 1) * (cal.DEG_T + 1))
    p = cal.design_matrix(v, t) @ true
    assert np.allclose(cal.fit(v, t, p), true, rtol=1e-6, atol=1e-6)


def test_residuals_before_and_after(tmp_path):
    s = cal.run(out=tmp_path, plots=False)
    assert s["max_abs_residual_before_pa"] > 0.01 * d.P_FS     # > 1 % FS uncalibrated over T
    assert s["max_abs_residual_after_pa"] < 0.001 * d.P_FS     # < 0.1 % FS after fit
    assert (tmp_path / "calibration_table.csv").read_text().count("\n") == 1 + 12
