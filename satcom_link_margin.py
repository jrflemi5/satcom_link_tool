import streamlit as st
import numpy as np

# ----------------------------------------
# Frequency Band Classifier
# ----------------------------------------
def classify_band(freq_hz):
    if freq_hz < 3e8:
        return "HF/VHF"
    elif freq_hz < 1e9:
        return "UHF"
    elif freq_hz < 2e9:
        return "L-band"
    elif freq_hz < 4e9:
        return "S-band"
    elif freq_hz < 8e9:
        return "C-band"
    elif freq_hz < 12e9:
        return "X-band"
    elif freq_hz < 18e9:
        return "Ku-band"
    elif freq_hz < 26e9:
        return "K-band"
    else:
        return "Ka-band"

# ----------------------------------------
# Corrected Link Margin Calculator
# ----------------------------------------
def calculate_link_margin(
    tx_power_dbw, tx_gain_dbi, rx_gain_dbi, freq_hz,
    distance_km, noise_figure_db, required_snr_db,
    bandwidth_hz=1e6,  # 1 MHz default
    rain_fade_db=3.0, misc_losses_db=2.0
):
    c = 3e8  # speed of light
    wavelength_m = c / freq_hz
    fspl_db = 20 * np.log10((4 * np.pi * distance_km * 1000) / wavelength_m)
    total_loss_db = fspl_db + rain_fade_db + misc_losses_db

    eirp_dbw = tx_power_dbw + tx_gain_dbi
    c_rx_dbw = eirp_dbw + rx_gain_dbi - total_loss_db

    noise_floor_dbw = -228.6 + 10 * np.log10(bandwidth_hz) + noise_figure_db
    link_margin_db = c_rx_dbw - noise_floor_dbw - required_snr_db

    return link_margin_db, fspl_db, total_loss_db, noise_floor_dbw, c_rx_dbw

# ----------------------------------------
# Streamlit App UI
# ----------------------------------------
st.set_page_config(page_title="Tactical SATCOM Link Tool", layout="centered")
st.title("📡 Tactical SATCOM Link Margin Calculator")
st.markdown("Estimate link margin for tactical SATCOM terminals using noise-floor-based calculations.")

# --- Preset Profiles ---
profile = st.selectbox("Preset Config", ["Custom", "Handheld (Omni)", "Manpack (Directional)", "Vehicle Relay"])

if profile == "Handheld (Omni)":
    tx_power, tx_gain, rx_gain, freq_input, unit = 5, 2, 2, 300, "MHz"
elif profile == "Manpack (Directional)":
    tx_power, tx_gain, rx_gain, freq_input, unit = 10, 10, 10, 8.4, "GHz"
elif profile == "Vehicle Relay":
    tx_power, tx_gain, rx_gain, freq_input, unit = 15, 15, 15, 2.2, "GHz"
else:
    tx_power = st.slider("Transmitter Power (dBW)", 0, 30, 10)
    tx_gain = st.slider("Tx Antenna Gain (dBi)", 0, 30, 10)
    rx_gain = st.slider("Rx Antenna Gain (dBi)", 0, 30, 10)
    freq_input = st.number_input("Operating Frequency", value=8.4, min_value=0.001)
    unit = st.selectbox("Frequency Unit", ["Hz", "MHz", "GHz"])

# Normalize Frequency
unit_multipliers = {"Hz": 1, "MHz": 1e6, "GHz": 1e9}
freq_hz = freq_input * unit_multipliers[unit]
band = classify_band(freq_hz)

# --- Inputs for Noise Floor Calculation ---
distance_km = st.slider("Distance to Target (km)", 1, 500, 100)
noise_figure_db = st.slider("System Noise Figure (dB)", 1.0, 10.0, 3.0)
required_snr_db = st.slider("Required SNR (dB)", 1.0, 15.0, 10.0)
bandwidth_mhz = st.slider("Bandwidth (MHz)", 0.01, 20.0, 1.0)
bandwidth_hz = bandwidth_mhz * 1e6

# --- Display Frequency Info ---
st.write(f"**Normalized Frequency:** {freq_hz/1e9:.3f} GHz")
st.write(f"**Estimated Band:** {band}")

# --- Calculate Link Margin ---
margin, fspl, total_loss, noise_floor, c_rx = calculate_link_margin(
    tx_power, tx_gain, rx_gain, freq_hz, distance_km, noise_figure_db,
    required_snr_db, bandwidth_hz
)

# --- Output Results ---
st.subheader("📈 Link Budget Results")
st.metric("Link Margin", f"{margin:.2f} dB")
st.write(f"• Received Carrier Power: **{c_rx:.2f} dBW**")
st.write(f"• Noise Floor: **{noise_floor:.2f} dBW**")
st.write(f"• Free-Space Path Loss: **{fspl:.2f} dB**")
st.write(f"• Total Link Loss (incl. rain & misc): **{total_loss:.2f} dB**")

# --- Feedback Interpretation ---
if margin > 10:
    st.success("✅ Strong link — highly reliable.")
elif margin > 3:
    st.info("🟢 Sufficient margin — expected to work reliably.")
elif margin > 0:
    st.warning("⚠️ Marginal link — may degrade under stress.")
else:
    st.error("❌ Link not viable — increase power/gain, reduce distance, or widen bandwidth.")


