# SATCOM Link Budget Calculator

This project is a fully user-configurable link budget calculator designed for tactical and satellite communications (SATCOM) analysis. Built with Python and Streamlit, the tool prioritizes transparency, engineering accuracy, and educational clarity. Every variable is explicitly defined by the user—there are no hidden presets or black-box assumptions.

## Purpose

Originally developed as part of a graduate-level systems engineering project, this tool was created to analyze performance tradeoffs in tactical SATCOM configurations. It has since been extended to support practical planning scenarios and waveform modeling.

## Features

- Calculates FSPL, total link loss, carrier power, C/N₀, Eb/N₀, and link margin
- Fully user-driven inputs for power, gain, frequency, distance, noise, bandwidth, and losses
- Visual breakdown of path loss components
- Inline tooltips for educational use and systems analysis
- Optional export to HTML report
- Clean architecture for future expansion (e.g., CDMA gain, antenna modeling)

## Getting Started

## Getting Started

You can use the SATCOM Link Budget Calculator directly in your browser or run it locally on your machine.

### Use in Your Browser (No Installation Required)

A live version of the tool is hosted here:  
[https://satcomlinktool-snggrz8hwqmdfjdy55fxp2.streamlit.app](https://satcomlinktool-snggrz8hwqmdfjdy55fxp2.streamlit.app)

- No setup required
- Use the tool to evaluate link parameters and observe real-time feedback

### Run Locally (For Development or Offline Use)

1. **Clone the repository**

```bash
git clone https://github.com/your-username/satcom-link-tool.git
cd satcom-link-tool
pip install -r requirements.txt
streamlit run satcom_link_margin.py


