import streamlit as st
import numpy as np
import json
from pathlib import Path


# ----------------------------------------
# Import presets
# ----------------------------------------
preset_path = Path(__file__).parent / "terminal_presets.json"
with open(preset_path) as f:
    terminal_presets = json.load(f)

# ----------------------------------------
# Preset Notes
# ----------------------------------------
preset_notes = {
    "Custom": "Manually configure your terminal’s RF parameters. Useful for testing custom or hypothetical configurations.",
    "PRC-117G (SATCOM)": "Manpack terminal used for UHF SATCOM, IW, and DAMA waveforms. Common in dismounted operations and vehicle mounts. Typical bands: UHF, L-band.",
    "AN/PSC-5D": "Multiband tactical terminal supporting both line-of-sight and SATCOM. Often used in mobile or command post configurations. Bands: UHF to S-band.",
    "AN/PRC-158": "Dual-channel multiband terminal supporting SATCOM, LOS, and MANET operations. Frequently employed for mid-tier tactical comms across L and S bands.",
    "DRT 4340A": "Signals intelligence receiver typically used for SATCOM monitoring and analysis. High-gain reception, often paired with direction-finding or demodulation systems.",
    "MUOS Terminal": "Dedicated terminal for Mobile User Objective System (MUOS) SATCOM. Uses UHF band with WCDMA-like waveform. Prioritized for secure beyond-line-of-sight communications."
}

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
    distance_km, noise_figure_db, bandwidth_hz, modcod,
    rain_fade_db=3.0, misc_losses_db=2.0
):
    c = 3e8
    wavelength_m = c / freq_hz
    fspl_db = 20 * np.log10((4 * np.pi * distance_km * 1000) / wavelength_m)
    total_loss_db = fspl_db + rain_fade_db + misc_losses_db

    eirp_dbw = tx_power_dbw + tx_gain_dbi
    c_rx_dbw = eirp_dbw + rx_gain_dbi - total_loss_db

    noise_floor_dbw = -228.6 + 10 * np.log10(bandwidth_hz) + noise_figure_db
    cn0_dbhz = c_rx_dbw - noise_floor_dbw + 10 * np.log10(bandwidth_hz)

    spectral_efficiency = modcod_table[modcod]["spectral_efficiency"]
    data_rate_bps = bandwidth_hz * spectral_efficiency
    ebn0_db = cn0_dbhz - 10 * np.log10(data_rate_bps)
    required_ebn0 = modcod_table[modcod]["required_ebn0"]
    link_margin_db = ebn0_db - required_ebn0

    return (
        link_margin_db,
        ebn0_db,
        required_ebn0,
        fspl_db,
        total_loss_db,
        noise_floor_dbw,
        c_rx_dbw,
        data_rate_bps,
        rain_fade_db,
        misc_losses_db
    )


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

    preset_names = ["Custom"] + list(terminal_presets.keys())
    profile = st.selectbox("Preset Config", preset_names)
    selected_note = preset_notes.get(profile)
    if selected_note:
        st.info(f"**Preset Info:** {selected_note}")

    # Handle config selection
    if profile in terminal_presets:
        preset = terminal_presets[profile]
        tx_power = preset["tx_power_dbw"]
        tx_gain = preset["tx_gain_dbi"]
        rx_gain = preset["rx_gain_dbi"]
    else:
        tx_power = st.slider("Transmitter Power (dBW)", 0, 30, 10)
        tx_gain = st.slider("Tx Antenna Gain (dBi)", 0, 30, 10)
        rx_gain = st.slider("Rx Antenna Gain (dBi)", 0, 30, 10)

    freq_ghz = st.number_input(
           "Operating Frequency (GHz)",
            min_value=0.1,
            max_value=50.0,
            value=8.4,
            step=0.1,
            help="Center frequency of the link. Tactical SATCOM typically uses UHF (~0.3), L (~1.5), S (~2.2), X (~8.4), Ku (~14), or Ka (~30) GHz."
        )
    freq_hz = freq_ghz * 1e9
    environment = st.selectbox("Environment Profile", [
        "Open/LOS", "Urban", "Dense Forest", "Mountainous", "Rainy (Tropical)", "Desert", "Maritime"
    ])
    environmental_losses = {
        "Open/LOS": {"rain_fade": 0.0, "misc": 1.0},
        "Urban": {"rain_fade": 2.0, "misc": 6.0},
        "Dense Forest": {"rain_fade": 3.0, "misc": 10.0},
        "Mountainous": {"rain_fade": 2.0, "misc": 8.0},
        "Rainy (Tropical)": {"rain_fade": 6.0, "misc": 3.0},
        "Desert": {"rain_fade": 1.0, "misc": 5.0},
        "Maritime": {"rain_fade": 4.0, "misc": 2.0}
    }
    env_losses = environmental_losses[environment]
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
        0.01, 20.0, 1.0,
        help="Receiver channel bandwidth. Higher bandwidth allows higher data rates but increases noise power."
    )
    bandwidth_hz = bandwidth_mhz * 1e6
    modcod = st.selectbox("MODCOD Scheme", list(modcod_table.keys()))

    band = classify_band(freq_hz)

    st.markdown(f"**Normalized Frequency:** {freq_hz/1e9:.3f} GHz")
    st.markdown(f"**Estimated Band:** {band}")

    valid_bands = ["UHF", "L-band", "S-band", "X-band", "Ku-band", "Ka-band"]
    if band not in valid_bands:
        st.error("⚠️ Frequency entered is outside typical SATCOM bands.")

# --- Calculate ---
margin, ebn0, required_ebn0, fspl, total_loss, noise_floor, c_rx, data_rate, rain_fade_db, misc_losses_db = calculate_link_metrics(
    tx_power, tx_gain, rx_gain, freq_hz,
    distance_km, noise_figure_db, bandwidth_hz, modcod,
    rain_fade_db=env_losses["rain_fade"],
    misc_losses_db=env_losses["misc"]
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

**MODCOD:** `{modcod}`  
Modulation and coding scheme used to map digital data to RF signals. Affects spectral efficiency and required Eb/N0 for reliable demodulation.  
Higher-order MODCODs provide more throughput but require higher link margins. In most systems, selection is automatic based on link conditions.

**Rain Fade Loss:** `{rain_fade_db}` dB  
Estimated link attenuation due to precipitation and atmospheric moisture. Increases with frequency and rainfall rate. Most significant above ~6 GHz.

**Miscellaneous Loss:** `{misc_losses_db}` dB  
Aggregate margin for non-modeled losses including polarization mismatch, antenna mispointing, RF cable loss, filter insertion loss, and implementation inefficiencies.
    """)


    
with output_col:
    st.header("📈 Link Budget Results")
    st.metric("Link Margin", f"{margin:.2f} dB")
    st.metric("Eb/N0 (Actual)", f"{ebn0:.2f} dB")
    st.metric("Eb/N0 (Required)", f"{required_ebn0:.2f} dB")
    st.metric("Data Rate", f"{data_rate/1e6:.2f} Mbps")

    st.markdown(f"• Received Carrier Power: **{c_rx:.2f} dBW**")
    st.markdown(f"• Noise Floor: **{noise_floor:.2f} dBW**")
    st.markdown(f"• Free-Space Path Loss: **{fspl:.2f} dB**")
    st.markdown(f"• Total Link Loss: **{total_loss:.2f} dB**")
    st.write(f"• Rain Fade Loss: **{env_losses['rain_fade']} dB**")
    st.write(f"• Miscellaneous Loss: **{env_losses['misc']} dB**")
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
            max(env_losses["rain_fade"], 0.01),
            max(env_losses["misc"], 0.01)
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



