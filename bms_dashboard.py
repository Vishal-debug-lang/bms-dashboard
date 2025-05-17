import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import cantools
import re
from collections import defaultdict

st.set_page_config(page_title="BMS Log Dashboard", layout="wide")
st.title("🔋 BMS ASC/LOG + DBC Viewer")

# Signals to extract
TARGET_SIGNALS = [
    "B2V_SOC", "B2V_MaxCellV", "B2V_MinCellV",
    "B2V_TotalI", "B2V_AccuChrgAh", "B2V_MinCellT", "B2V_MaxCellT"
]

# File upload widgets
uploaded_log = st.file_uploader("Upload ASC or LOG file", type=["asc", "log"])
uploaded_dbc = st.file_uploader("Upload DBC file", type=["dbc"])

if uploaded_log and uploaded_dbc:
    try:
        # Load DBC
        dbc_text = uploaded_dbc.read().decode("utf-8")
        dbc = cantools.database.load_string(dbc_text)

        # Regex to match log lines (Vector ASC format)
        asc_pattern = re.compile(
            r"^\s*(\d+\.\d+)\s+\d+\s+([0-9A-Fa-f]+)x\s+Rx\s+d\s+\d+\s+((?:[0-9A-Fa-f]{2}\s*)+)"
        )

        timestamps = defaultdict(list)
        values = defaultdict(list)

        # Try decoding log file with UTF-8, fallback to Latin-1
        try:
            text = uploaded_log.read().decode("utf-8")
        except UnicodeDecodeError:
            st.warning("⚠️ UTF-8 decoding failed. Trying 'latin-1' fallback...")
            uploaded_log.seek(0)
            text = uploaded_log.read().decode("latin-1")

        lines = text.splitlines()

        for line in lines:
            match = asc_pattern.match(line)
            if match:
                timestamp = float(match.group(1))
                frame_id = int(match.group(2), 16)
                data_bytes = bytes(int(b, 16) for b in match.group(3).split())

                try:
                    message = dbc.get_message_by_frame_id(frame_id)
                    decoded_signals = message.decode(data_bytes)

                    for signal_name in TARGET_SIGNALS:
                        if signal_name in decoded_signals:
                            value = decoded_signals[signal_name]
                            timestamps[signal_name].append(timestamp)
                            values[signal_name].append(value)
                except Exception:
                    continue

        # Plotting
        fig, ax1 = plt.subplots(figsize=(12, 6))

        primary_signals = ("B2V_SOC", "B2V_TotalI", "B2V_MinCellT", "B2V_MaxCellT")
        secondary_signals = ("B2V_MaxCellV", "B2V_MinCellV")

        for signal in primary_signals:
            if signal in timestamps:
                y_vals = [abs(v) if signal == "B2V_TotalI" else v for v in values[signal]]
                ax1.plot(timestamps[signal], y_vals, label=signal)

        ax1.set_xlabel("Time (s)")
        ax1.set_ylabel("SOC / Current (A) / Temp (°C)")
        ax1.grid(True)

        ax2 = ax1.twinx()
        for signal in secondary_signals:
            if signal in timestamps:
                ax2.plot(timestamps[signal], values[signal], linestyle='--', label=signal)

        ax2.set_ylabel("Min/Max Voltage (V)")

        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper right')

        st.pyplot(fig)

    except Exception as e:
        st.error(f"⚠️ Error: {e}")
else:
    st.info("⬆️ Please upload both ASC/LOG and DBC files to proceed.")




