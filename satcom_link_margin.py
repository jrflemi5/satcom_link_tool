import streamlit as st
import numpy as np
import json
from pathlib import Path
import io




# ----------------------------------------
# MODCOD Table
# ----------------------------------------
modcod_table = {
    "BPSK 1/2": {"required_ebn0": 1.5, "spectral_efficiency": 0.5},
    "QPSK 1/2": {"required_ebn0": 2.0, "spectral_efficiency": 1.0},
    "QPSK 3/4": {"required_ebn0": 4.5, "spectral_efficiency": 1.5},
    "8PSK 2/3": {"required_ebn0": 6.5, "spectral_efficiency": 2.0},
    "16QAM 3/4": {"required_ebn0": 9.0, "spectral_efficiency": 3.0}
}

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
# Link Margin and Eb/N0 Calculator
# ----------------------------------------
def calculate_link_metrics(
    tx_power_dbw, tx_gain_dbi, rx_gain_dbi, freq_hz,
    distance_km, noise_figure_db, bandwidth_hz,
    spectral_efficiency, required_ebn0,
    rain_fade_db=0.0, misc_losses_db=0.0
):
    c = 3e8
    wavelength_m = c / freq_hz
    fspl_db = 20 * np.log10((4 * np.pi * distance_km * 1000) / wavelength_m)
    total_loss_db = fspl_db + rain_fade_db + misc_losses_db

    eirp_dbw = tx_power_dbw + tx_gain_dbi
    c_rx_dbw = eirp_dbw + rx_gain_dbi - total_loss_db

    noise_floor_dbw = -228.6 + 10 * np.log10(bandwidth_hz) + noise_figure_db
    cn0_dbhz = c_rx_dbw - noise_floor_dbw + 10 * np.log10(bandwidth_hz)

    data_rate_bps = bandwidth_hz * spectral_efficiency
    ebn0_db = cn0_dbhz - 10 * np.log10(data_rate_bps)
    link_margin_db = ebn0_db - required_ebn0

    return (
        link_margin_db,
        ebn0_db,
        fspl_db,
        total_loss_db,
        noise_floor_dbw,
        c_rx_dbw,
        data_rate_bps,
        cn0_dbhz
    )

#-----------------------------------------
# Export HTML
#-----------------------------------------
def render_html_report(template_path, context):
    with open(template_path, 'r') as f:
        template = f.read()
    for key, value in context.items():
        template = template.replace(f"{{{{ {key} }}}}", str(value))
    return template

# ----------------------------------------
# Streamlit App UI
# ----------------------------------------
st.set_page_config(page_title="Tactical SATCOM Link Tool", layout="wide")
st.title("📡 Tactical SATCOM Link Margin Calculator")
st.markdown("Analyze tradeoffs in SATCOM terminals based on MODCOD, bandwidth, and SWaP constraints.")

# --- Split into two columns ---
input_col, output_col = st.columns([2, 1])

with input_col:
    st.header("🔧 System Configuration")



    # Sliders with preset defaults
    tx_power = st.slider("Transmitter Power (dBW)", 0, 30, 10)
    tx_gain = st.slider("Tx Antenna Gain (dBi)", 0, 30, 10)
    rx_gain = st.slider("Rx Antenna Gain (dBi)", 0, 30, 10)
    # Determine defaults if waveform selected
    default_modcod = "QPSK 1/2"
    default_bandwidth = 1.0




    freq_ghz = st.number_input(
           "Operating Frequency (GHz)",
            min_value=0.1,
            max_value=50.0,
            value=8.4,
            step=0.1,
            help="Center frequency of the link. Tactical SATCOM typically uses UHF (~0.3), L (~1.5), S (~2.2), X (~8.4), Ku (~14), or Ka (~30) GHz."
        )
    freq_hz = freq_ghz * 1e9

    rain_fade_db = st.number_input(
        "Rain Fade Loss (dB)",
        min_value=0.0,
        max_value=20.0,
        value=3.0,
        help="Estimate of link attenuation due to precipitation. Most significant above ~6 GHz."
    )

    misc_losses_db = st.number_input(
        "Miscellaneous Losses (dB)",
        min_value=0.0,
        max_value=20.0,
        value=2.0,
        help="Includes pointing error, polarization mismatch, cable losses, etc."
    )

    distance_km = st.slider("Distance to Target (km)", 100, 40000, 35786)
    noise_figure_db = st.slider(
        "System Noise Figure (dB)",
        min_value=1.0,
        max_value=10.0,
        value=3.0,
        help="System Noise Figure represents the added internal receiver noise. Lower = better. Tactical SATCOM systems typically range from 2–6 dB."
    )
    bandwidth_mhz = st.slider(
        "Bandwidth (MHz)",
        min_value=0.01,
        max_value=20.0,
        value=default_bandwidth,
        step=0.01,
        help="Signal bandwidth used for the transmission, affects both data rate and noise floor."
    )
    bandwidth_hz = bandwidth_mhz * 1e6

    spectral_efficiency = st.number_input(
        "Spectral Efficiency (bps/Hz)", min_value=0.1, max_value=10.0, value=1.0,
        help="Ratio of data rate to bandwidth. For example, QPSK 1/2 = 1.0, 8PSK 2/3 = 2.0"
    )

    required_ebn0 = st.number_input(
        "Required Eb/N0 (dB)", min_value=-10.0, max_value=20.0, value=2.0,
        help="Threshold for reliable demodulation/decoding. Depends on modulation and coding."
    )

    band = classify_band(freq_hz)

    st.markdown(f"**Estimated Band:** {band}")

    valid_bands = ["UHF", "L-band", "S-band", "X-band", "Ku-band", "Ka-band"]
    if band not in valid_bands:
        st.error("⚠️ Frequency entered is outside typical SATCOM bands.")



# --- Calculate ---
margin, ebn0, fspl, total_loss, noise_floor, c_rx, data_rate, cn0_dbhz = calculate_link_metrics(
    tx_power, tx_gain, rx_gain, freq_hz,
    distance_km, noise_figure_db, bandwidth_hz,
    spectral_efficiency, required_ebn0,
    rain_fade_db, misc_losses_db
)
context = {
    "tx_power": tx_power,
    "tx_gain": tx_gain,
    "rx_gain": rx_gain,
    "freq_ghz": round(freq_ghz, 2),
    "distance_km": distance_km,
    "bandwidth_mhz": round(bandwidth_mhz, 2),
    "spectral_efficiency": round(spectral_efficiency, 2),
    "required_ebn0": round(required_ebn0, 2),
    "rain_fade": round(rain_fade_db, 2),
    "misc_losses": round(misc_losses_db, 2),
    "fspl": round(fspl, 2),
    "total_loss": round(total_loss, 2),
    "c_rx": round(c_rx, 2),
    "noise_floor": round(noise_floor, 2),
    "cn0": round(cn0_dbhz, 2),
    "ebn0": round(ebn0, 2),
    "link_margin": round(margin, 2)
}

html_report = render_html_report("report_template.html", context)
html_bytes = io.BytesIO(html_report.encode("utf-8"))

st.download_button(
    label="Download Link Budget Report (.html)",
    data=html_bytes,
    file_name="link_budget_report.html",
    mime="text/html"
)


# reference guide
with st.expander("Variable Reference Guide"):
    st.markdown(f"""
**Tx Power (dBW):** `{tx_power}`  
Transmitter output power expressed in decibel-watts. Typically constrained by terminal size, power budget, and regulatory limits.

**Tx Antenna Gain (dBi):** `{tx_gain}`  
Directional gain of the transmitting antenna located on the ground terminal. Higher values focus energy into a narrower beam, increasing effective radiated power (EIRP).

**Rx Antenna Gain (dBi):** `{rx_gain}`  
Gain of the receiving antenna located on the satellite. Generally high due to the use of parabolic or phased array antennas.

**Operating Frequency:** `{freq_ghz:.3f}` GHz  
Center frequency of the RF carrier. Determines free-space path loss, antenna design, and susceptibility to environmental effects like rain fade.  
Tactical SATCOM commonly operates in the following bands:  
- **UHF** (~0.3 GHz)  
- **L-band** (~1.5 GHz)  
- **S-band** (~2.2 GHz)  
- **X-band** (~8.4 GHz)  
- **Ku-band** (~14 GHz)  
- **Ka-band** (~30 GHz)

**Distance to Target:** `{distance_km}` km  
Slant range between the terminal and satellite.  
Typical values:  
- GEO SATCOM: ~35,786 km  
- MEO: ~8,000–12,000 km  
- LEO: ~500–2,000 km  
Values below ~1,000 km are only applicable for LEO-based systems.

**Bandwidth:** `{bandwidth_mhz}` MHz  
Allocated RF channel width. Determines maximum throughput and noise power. Not directly selected by users in most systems; defined by waveform or service plan.  
Typical ranges:  
- Voice / messaging: 25–100 kHz  
- Tactical data / C2: 0.1–2 MHz  
- Video or high-rate ISR: 2–5 MHz+

**Noise Figure:** `{noise_figure_db}` dB  
Represents degradation of signal-to-noise ratio introduced by the receiver’s RF front end. Primarily driven by the low-noise amplifier (LNA) and frequency conversion stages.  
Typical tactical values: 2–6 dB.

**Spectral Efficiency:** `{spectral_efficiency} bps/Hz`  
The ratio of data rate to bandwidth. Reflects how efficiently information is packed into the RF signal.  
- Higher values indicate more bits per second per Hz of bandwidth, but typically require better signal conditions (higher Eb/N₀).  
- For example, QPSK with 1/2 coding ≈ 1.0 bps/Hz, 8PSK 2/3 ≈ 2.0 bps/Hz.  
- Spread-spectrum systems like MUOS may operate at low spectral efficiency by design, prioritizing resilience over speed.

**Required Eb/N₀:** `{required_ebn0} dB`  
The minimum energy per bit to noise density ratio required for reliable demodulation or decoding, based on the waveform, coding, and system margin.  
- Lower values indicate more robust (but lower throughput) modulation/coding.  
- For example, robust coding might require as low as 1–2 dB, while high-speed links (e.g., 64QAM) might need 10+ dB.  
- In spread-spectrum systems, required Eb/N₀ is often much lower due to processing gain.


**Rain Fade Loss:** `{rain_fade_db}` dB  
Estimated link attenuation due to precipitation and atmospheric moisture. Increases with frequency and rainfall rate. Most significant above ~6 GHz.

**Miscellaneous Loss:** `{misc_losses_db}` dB  
Aggregate margin for non-modeled losses including polarization mismatch, antenna mispointing, RF cable loss, filter insertion loss, and implementation inefficiencies.
    """)


    
with output_col:
    st.header("📈 Link Budget Results")
    st.metric("Link Margin", f"{margin:.2f} dB")
    st.metric(
        label="C/N₀",
        value=f"{cn0_dbhz:.2f} dB-Hz",
        help="Carrier-to-noise density ratio. Indicates received signal strength per Hz of bandwidth. Higher C/N₀ generally means better link quality."
    )
    st.metric("Eb/N0 (Actual)", f"{ebn0:.2f} dB")
    st.metric("Eb/N0 (Required)", f"{required_ebn0:.2f} dB")
    st.metric("Data Rate", f"{data_rate/1e6:.2f} Mbps")

    st.markdown(f"• Received Carrier Power: **{c_rx:.2f} dBW**")
    st.markdown(f"• Noise Floor: **{noise_floor:.2f} dBW**")
    st.markdown(f"• Free-Space Path Loss: **{fspl:.2f} dB**")
    st.markdown(f"• Total Link Loss: **{total_loss:.2f} dB**")
    st.write(f"• Rain Fade Loss: **{rain_fade_db} dB**")
    st.write(f"• Miscellaneous Loss: **{misc_losses_db} dB**")
    with st.expander("ℹ️ Loss Term Definitions"):
        st.markdown("""
        - **Received Carrier Power:** Power level at the receiver input after path losses and gains.
        - **Noise Floor:** Thermal noise plus system noise figure over bandwidth.
        - **Free-Space Path Loss:** Loss due to spreading of signal over distance in free space.
        - **Rain Fade Loss:** Additional attenuation from rainfall, more severe at higher frequencies.
        - **Miscellaneous Loss:** Accounts for polarization mismatch, pointing errors, and other non-modeled losses.
        """)

    show_loss_chart = st.checkbox("📊 Show Loss Breakdown Chart")

    if show_loss_chart:
        import matplotlib.pyplot as plt

        labels = ['Free-Space Loss', 'Rain Fade', 'Misc Loss']
        loss_values = [
            max(abs(fspl), 0.01),
            max(rain_fade_db, 0.01),
            max(misc_losses_db, 0.01)
        ]

        fig, ax = plt.subplots()
        bars = ax.bar(labels, loss_values, color=["#5DADE2", "#58D68D", "#F4D03F"])
        ax.set_ylabel("Loss (dB)")
        ax.set_title("Environmental and Path Loss Components")
        ax.set_yscale("log")
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2., height + 0.5, f'{height:.1f}', ha='center')
        st.caption("This chart visualizes how different loss components reduce the received signal power.")
        st.pyplot(fig)
    if margin > 10:
        st.success("✅ Strong link — highly reliable.")
    elif margin > 3:
        st.info("🟢 Sufficient margin — expected to work reliably.")
    elif margin > 0:
        st.warning("⚠️ Marginal link — may degrade under stress.")
    else:
        st.error("❌ Link not viable — adjust system parameters.")



