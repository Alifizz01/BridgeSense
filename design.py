"""Design constants shared by the budget, the SPICE checks and the README.

Part values are transcribed from public datasheets (TI SBOS445 INA333, TI SBAS660 ADS124S08).
Re-check against the current datasheet revision before using them for anything real.
"""
import math

# example sensor (generic piezoresistive die, not a specific product)
P_FS = 10e3          # Pa, 0..10 kPa differential
VEXC = 3.3           # V, bridge excitation = ADC reference (ratiometric)
SENS_V_PER_V = 10e-3 # 10 mV/V at full scale
R_BRIDGE = 5e3
V_FS_BRIDGE = SENS_V_PER_V * VEXC          # 33 mV
S_V_PER_PA = V_FS_BRIDGE / P_FS            # 3.3 uV/Pa

# INA333 (G = 1 + 100k/RG)
RG = 2.55e3
GAIN = 1 + 100e3 / RG                      # 40.2
INA_VOS_MAX = 25e-6 + 75e-6 / GAIN         # V, max, input referred
INA_VOS_DRIFT_MAX = 0.1e-6 + 0.5e-6 / GAIN # V/degC, max
INA_EN = 50e-9                             # V/rtHz, flat (chopper, no 1/f)
INA_GAIN_ERR_MAX = 0.25e-2                 # G > 1, max
INA_GAIN_DRIFT = 10e-6                     # 1/degC, excludes RG
RG_TC = 25e-6                              # 1/degC, thin film RG

# anti-alias RC (differential) and ADC
R_AA = 1e3
C_DIFF = 82e-9
C_CM = 4.7e-9
F3DB = 1 / (2 * math.pi * 2 * R_AA * (C_DIFF + C_CM / 2))   # ~943 Hz
F_MOD = 4.096e6 / 16                       # ADS124S08 modulator rate, 256 kHz
DATA_RATE = 100                            # SPS per channel after mux settling
ADC_BITS = 24
ADC_FSR = 2 * VEXC                         # +-Vref, PGA bypassed
ADC_NOISE_RMS = 4e-6                       # V rms at 100 SPS, gain 1: conservative assumption, see README
DT = 20.0                                  # degC excursion from calibration conditions

if __name__ == "__main__":
    print(f"gain {GAIN:.2f}, bridge FS {V_FS_BRIDGE*1e3:.1f} mV, ADC FS use {V_FS_BRIDGE*GAIN:.3f} V, f3dB {F3DB:.0f} Hz")
