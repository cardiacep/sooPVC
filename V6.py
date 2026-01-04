# soo_app_v5_patched.py
# Unified-input PVC SOO tool (Streamlit)
# Refactored: added calculation/interpretation separation, Betensky V3 applicability gating,
# measurement help text, st.metric panel, JSON export, and a clinical-use disclaimer.
#
# Literature-based indices referenced in-app:
# - Betensky 2011 (V2 transition ratio; validated for PVC transition at V3)
# - Yoshida 2014 (V2S/V3R index)
# - Ouyang 2002 (R-wave duration and amplitude indices for ASC vs RVOT lookalike)
# - Enriquez 2019, Yamada 2019 (heuristic summaries)

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

import pandas as pd
import streamlit as st

st.set_page_config(page_title="PVC SOO (Unified Inputs)", layout="wide")

# ---------------------------
# Defaults & session helpers
# ---------------------------
DEFAULTS: Dict[str, Any] = {
    "bbb": "LBBB",
    "axis": "Inferior",
    "lead1": "Positive",
    "tz_pvc": "V3",
    "tz_sr": "V4",
    "qrs_pvc_ms": 140,

    "R_V1_PVC": 0.2,
    "S_V1_PVC": 1.2,

    "R_V2_PVC": 0.3,
    "S_V2_PVC": 1.5,
    "R_V2_SR": 0.6,
    "S_V2_SR": 1.8,

    "R_V3_PVC": 0.5,

    "Rdur_V1_ms": 45,
    "Rdur_V2_ms": 55,
}

TRANSITION_ORDER: Dict[str, int] = {"≤V1": 1, "V2": 2, "V3": 3, "V4": 4, "V5": 5, "≥V6": 6}
TZ_OPTIONS = ["≤V1", "V2", "V3", "V4", "V5", "≥V6"]

def ensure_defaults() -> None:
    for k, v in DEFAULTS.items():
        if k not in st.session_state:
            st.session_state[k] = v

def reset_inputs() -> None:
    for k, v in DEFAULTS.items():
        st.session_state[k] = v
    try:
        st.rerun()
    except AttributeError:
        st.experimental_rerun()

ensure_defaults()

# ---------------------------
# Core helpers (calculation-only)
# ---------------------------
def safe_ratio(n: Any, d: Any) -> float:
    try:
        n = float(n)
        d = float(d)
        return n / d if d != 0 else math.nan
    except Exception:
        return math.nan

def r_fraction(R: Any, S: Any) -> float:
    """Normalized R fraction: R/(R+S). Used in Betensky and in common summaries of Ouyang-style amplitude indices."""
    try:
        return safe_ratio(R, (float(R) + float(S)))
    except Exception:
        return math.nan

def is_bad_number(x: Any) -> bool:
    return (x is None) or (isinstance(x, float) and (math.isnan(x) or math.isinf(x)))

def fmt(x: Optional[float], nd: int = 3) -> str:
    return "NA" if is_bad_number(x) else f"{float(x):.{nd}f}"

def compute_metrics(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """Compute shared metrics once; keep Streamlit/UI out of this function."""
    tz_pvc = inputs["tz_pvc"]
    tz_sr = inputs["tz_sr"]
    tzp = TRANSITION_ORDER[tz_pvc]
    tzs = TRANSITION_ORDER[tz_sr]

    rfrac_v1 = r_fraction(inputs["R_V1_PVC"], inputs["S_V1_PVC"])
    rfrac_v2_pvc = r_fraction(inputs["R_V2_PVC"], inputs["S_V2_PVC"])
    rfrac_v2_sr = r_fraction(inputs["R_V2_SR"], inputs["S_V2_SR"])

    v2_transition_ratio = safe_ratio(rfrac_v2_pvc, rfrac_v2_sr)
    v2s_v3r = safe_ratio(inputs["S_V2_PVC"], inputs["R_V3_PVC"])

    rdur_idx = safe_ratio(max(inputs["Rdur_V1_ms"], inputs["Rdur_V2_ms"]), inputs["qrs_pvc_ms"])
    rfrac_idx = max(rfrac_v1, rfrac_v2_pvc)

    tz_index = tzp - tzs
    later_than_sr = tzp > tzs

    return {
        "tzp": tzp,
        "tzs": tzs,
        "tz_index": tz_index,
        "later_than_sr": later_than_sr,
        "rfrac_v1": rfrac_v1,
        "rfrac_v2_pvc": rfrac_v2_pvc,
        "rfrac_v2_sr": rfrac_v2_sr,
        "v2_transition_ratio": v2_transition_ratio,
        "v2s_v3r": v2s_v3r,
        "rdur_idx": rdur_idx,
        "rfrac_idx": rfrac_idx,
    }

# ---------------------------
# Interpretation helpers (no UI side effects)
# ---------------------------
def interpret_yoshida(v2s_v3r: float) -> Tuple[str, str]:
    if is_bad_number(v2s_v3r):
        return "Insufficient data", "Enter S(V2) and R(V3) during the PVC."
    if v2s_v3r <= 1.5:
        return "≤1.5 → favors LVOT", "≤1.5 → favors LVOT origin"
    return ">1.5 → favors RVOT", ">1.5 → favors RVOT origin"

def interpret_betensky(tz_pvc: str, later_than_sr: bool, v2_transition_ratio: float) -> Tuple[str, str, bool]:
    """
    Betensky two-step approach is commonly summarized as:
    - Developed/validated in cases with PVC precordial transition at V3.
    - If PVC transition later than sinus rhythm: favors RVOT (LVOT unlikely).
    - Otherwise compute V2 transition ratio; ≥0.60 suggests LVOT.
    """
    applicable = (tz_pvc == "V3")
    if not applicable:
        return (
            "Not validated (PVC transition not V3)",
            "Computed for reference only; the cutoff-based Betensky algorithm was developed for PVC transition at V3.",
            False,
        )

    if later_than_sr:
        return (
            "PVC transition later than SR → RVOT favored",
            "In the original algorithm, later transition than SR was highly specific for RVOT and made LVOT unlikely (within V3-transition cases).",
            True,
        )

    if is_bad_number(v2_transition_ratio):
        return (
            "Insufficient data",
            "Provide V2 amplitudes for both PVC and sinus rhythm to compute the ratio.",
            True,
        )

    if v2_transition_ratio >= 0.60:
        return (
            "Ratio ≥0.60 → LVOT favored",
            "Cutoff: V2 transition ratio ≥0.60 suggests LVOT (when PVC transition is V3 and not later than SR).",
            True,
        )
    return (
        "Ratio <0.60 → RVOT favored",
        "Cutoff: V2 transition ratio <0.60 suggests RVOT (when PVC transition is V3 and not later than SR).",
        True,
    )

def interpret_ouyang(rdur_idx: float, rfrac_idx: float) -> Tuple[str, str]:
    if is_bad_number(rdur_idx) or is_bad_number(rfrac_idx):
        return "Insufficient data", "Enter QRS duration, R-wave durations, and V1/V2 amplitudes."
    if (rdur_idx >= 0.50) and (rfrac_idx >= 0.30):
        return "Meets cutoffs → left-sided OT (ASC/LVOT) favored", "Both indices meet commonly cited cutoffs (≥0.50 and ≥0.30)."
    return "Below cutoff(s) → RVOT favored", "At least one index below common cutoffs; classic ASC criteria not met."

# ---------------------------
# Sidebar: unified inputs + actions
# ---------------------------
st.sidebar.title("Unified ECG Inputs")
st.sidebar.caption("All algorithms reuse these values. Units: mV (amplitude), ms (time).")

if st.sidebar.button("↺ Reset to Defaults", use_container_width=True):
    reset_inputs()

st.sidebar.subheader("Morphology & Transition")

bbb = st.sidebar.selectbox(
    "PVC morphology in V1",
    ["LBBB", "RBBB"],
    index=["LBBB", "RBBB"].index(st.session_state["bbb"]),
    key="bbb",
)
axis = st.sidebar.selectbox(
    "Frontal axis (PVC)",
    ["Inferior", "Superior", "Indeterminate"],
    index=["Inferior", "Superior", "Indeterminate"].index(st.session_state["axis"]),
    key="axis",
)
lead1 = st.sidebar.selectbox(
    "Lead I QRS polarity (PVC)",
    ["Positive", "Negative", "Isoelectric"],
    index=["Positive", "Negative", "Isoelectric"].index(st.session_state["lead1"]),
    key="lead1",
)

transition_help = "Transition lead: first precordial lead where R>S (R/S crosses 1)."
tz_pvc = st.sidebar.select_slider(
    "Transition (PVC)",
    options=TZ_OPTIONS,
    value=st.session_state["tz_pvc"],
    key="tz_pvc",
    help=transition_help,
)
tz_sr = st.sidebar.select_slider(
    "Transition (sinus rhythm)",
    options=TZ_OPTIONS,
    value=st.session_state["tz_sr"],
    key="tz_sr",
    help=transition_help,
)

qrs_pvc_ms = st.sidebar.number_input(
    "QRS duration (PVC, ms)",
    min_value=60,
    max_value=260,
    value=st.session_state["qrs_pvc_ms"],
    step=1,
    key="qrs_pvc_ms",
    help="PVC QRS duration in milliseconds. Measure in the lead with the widest QRS (consistent method).",
)

st.sidebar.markdown("---")
st.sidebar.subheader("Lead V1 amplitudes (PVC)")
amp_help_r = "R amplitude: peak positive deflection above isoelectric baseline (use T-P segment as baseline when possible)."
amp_help_s = "S amplitude: deepest negative deflection below baseline (magnitude)."
R_V1_PVC = st.sidebar.number_input(
    "R in V1 (mV)",
    min_value=0.0,
    value=st.session_state["R_V1_PVC"],
    step=0.1,
    format="%.3f",
    key="R_V1_PVC",
    help=amp_help_r,
)
S_V1_PVC = st.sidebar.number_input(
    "S in V1 (mV)",
    min_value=0.0,
    value=st.session_state["S_V1_PVC"],
    step=0.1,
    format="%.3f",
    key="S_V1_PVC",
    help=amp_help_s,
)

st.sidebar.subheader("Lead V2 amplitudes (PVC and sinus rhythm)")
R_V2_PVC = st.sidebar.number_input(
    "R in V2 (PVC, mV)",
    min_value=0.0,
    value=st.session_state["R_V2_PVC"],
    step=0.1,
    format="%.3f",
    key="R_V2_PVC",
    help=amp_help_r,
)
S_V2_PVC = st.sidebar.number_input(
    "S in V2 (PVC, mV)",
    min_value=0.0,
    value=st.session_state["S_V2_PVC"],
    step=0.1,
    format="%.3f",
    key="S_V2_PVC",
    help=amp_help_s,
)
R_V2_SR = st.sidebar.number_input(
    "R in V2 (sinus rhythm, mV)",
    min_value=0.0,
    value=st.session_state["R_V2_SR"],
    step=0.1,
    format="%.3f",
    key="R_V2_SR",
    help=amp_help_r,
)
S_V2_SR = st.sidebar.number_input(
    "S in V2 (sinus rhythm, mV)",
    min_value=0.0,
    value=st.session_state["S_V2_SR"],
    step=0.1,
    format="%.3f",
    key="S_V2_SR",
    help=amp_help_s,
)

st.sidebar.subheader("Lead V3 amplitude (PVC)")
R_V3_PVC = st.sidebar.number_input(
    "R in V3 (PVC, mV)",
    min_value=0.0,
    value=st.session_state["R_V3_PVC"],
    step=0.1,
    format="%.3f",
    key="R_V3_PVC",
    help=amp_help_r,
)

st.sidebar.markdown("---")
st.sidebar.subheader("R-wave durations (PVC)")
dur_help = "R-wave duration (ms): duration of the positive R deflection during PVC (from onset of upstroke to return to baseline of the positive component)."
Rdur_V1_ms = st.sidebar.number_input(
    "R duration V1 (ms)",
    min_value=0,
    max_value=260,
    value=st.session_state["Rdur_V1_ms"],
    step=1,
    key="Rdur_V1_ms",
    help=dur_help,
)
Rdur_V2_ms = st.sidebar.number_input(
    "R duration V2 (ms)",
    min_value=0,
    max_value=260,
    value=st.session_state["Rdur_V2_ms"],
    step=1,
    key="Rdur_V2_ms",
    help=dur_help,
)

# ---------------------------
# Compute once from unified inputs
# ---------------------------
inputs: Dict[str, Any] = {
    "bbb": bbb,
    "axis": axis,
    "lead1": lead1,
    "tz_pvc": tz_pvc,
    "tz_sr": tz_sr,
    "qrs_pvc_ms": qrs_pvc_ms,
    "R_V1_PVC": R_V1_PVC,
    "S_V1_PVC": S_V1_PVC,
    "R_V2_PVC": R_V2_PVC,
    "S_V2_PVC": S_V2_PVC,
    "R_V2_SR": R_V2_SR,
    "S_V2_SR": S_V2_SR,
    "R_V3_PVC": R_V3_PVC,
    "Rdur_V1_ms": Rdur_V1_ms,
    "Rdur_V2_ms": Rdur_V2_ms,
}

m = compute_metrics(inputs)

# Interpretations
yoshida_title, yoshida_interp = interpret_yoshida(m["v2s_v3r"])
bet_title, bet_note, bet_applicable = interpret_betensky(inputs["tz_pvc"], m["later_than_sr"], m["v2_transition_ratio"])
ouy_title, ouy_note = interpret_ouyang(m["rdur_idx"], m["rfrac_idx"])

# ---------------------------
# Layout
# ---------------------------
st.title("PVC Site-of-Origin (SOO) NA Unified Input App")

st.warning(
    "Educational support tool only. This is not a medical device and does not replace clinical judgment, mapping, or imaging."
)

# Key metrics panel
metric_cols = st.columns(5)
metric_cols[0].metric("V2S/V3R (PVC)", fmt(m["v2s_v3r"]))
metric_cols[1].metric("V2 transition ratio", fmt(m["v2_transition_ratio"]))
metric_cols[2].metric("R duration index", fmt(m["rdur_idx"]))
metric_cols[3].metric("R fraction index", fmt(m["rfrac_idx"]))
metric_cols[4].metric("TZ index (PVC−SR)", f"{m['tz_index']:+d}")

st.markdown(
    "This tool computes multiple literature-based indices from a single set of ECG inputs and summarizes likely RVOT/LVOT and related origins. "
    "Cutoffs and applicability notes are shown with each algorithm."
)

colA, colB = st.columns(2)

with colA:
    st.subheader("Yoshida 2014 NA V2S/V3R index")
    st.write(f"V2S/V3R = {fmt(m['v2s_v3r'])}")
    if yoshida_title == "Insufficient data":
        st.info(yoshida_interp)
    else:
        if "LVOT" in yoshida_title:
            st.success(yoshida_title)
        else:
            st.warning(yoshida_title)
    st.caption("PubMed: https://pubmed.ncbi.nlm.nih.gov/24612087/")

    st.subheader("Betensky 2011 NA V2 transition ratio")
    st.write(f"V2 transition ratio = {fmt(m['v2_transition_ratio'])}")
    st.write(
        f"PVC transition vs sinus rhythm: {'Later than sinus rhythm' if m['later_than_sr'] else 'Not later than sinus rhythm'} "
        f"(TZ index = {m['tz_index']:+d})"
    )

    # Applicability gating
    if inputs["tz_pvc"] != "V3":
        st.warning("Applicability: cutoff-based Betensky interpretation is validated for PVC transition at V3 only.")
        st.info(bet_note)
    else:
        if m["later_than_sr"]:
            st.warning(bet_title)
            st.info(bet_note)
        else:
            if is_bad_number(m["v2_transition_ratio"]):
                st.info(bet_note)
            else:
                if "LVOT" in bet_title:
                    st.success(bet_title)
                else:
                    st.warning(bet_title)
                st.info(bet_note)
                st.caption("Cutoff shown assumes PVC transition at V3 and PVC transition not later than sinus rhythm.")
    st.caption("PubMed: https://pubmed.ncbi.nlm.nih.gov/21616286/")

with colB:
    st.subheader("Ouyang 2002 NA Aortic sinus cusp (ASC) indices")
    st.write(f"R-wave duration index = max(Rdur V1,V2) / QRS = {fmt(m['rdur_idx'])}")
    st.write(f"Normalized R fraction index (best of V1 or V2) = {fmt(m['rfrac_idx'])}")
    if ouy_title == "Insufficient data":
        st.info(ouy_note)
    else:
        if "left-sided" in ouy_title:
            st.success(ouy_title)
        else:
            st.warning(ouy_title)
        st.info(ouy_note)
    st.caption("PubMed: https://pubmed.ncbi.nlm.nih.gov/11823089/")

st.markdown("---")
colC, colD = st.columns(2)

with colC:
    st.subheader("Yamada 2019 NA heuristic summary")
    bullets = []
    if bbb == "LBBB":
        bullets.append("LBBB in V1: RV or septal origin more likely. With inferior axis and OT pattern, consider RVOT or LVOT.")
        if m["tzp"] <= 2:
            bullets.append("Early transition (≤V2): LVOT/anterior more likely.")
        elif m["tzp"] >= 4:
            bullets.append("Late transition (≥V4): RVOT/free wall more likely.")
    else:
        bullets.append("RBBB in V1: LV origin more likely.")
        if lead1 == "Negative":
            bullets.append("Negative lead I: LV free wall or epicardial features.")
    yamada_text = "\n\n".join(bullets) if bullets else "Provide morphology, axis, and transition."
    st.write(yamada_text)

with colD:
    st.subheader("Enriquez 2019 NA stepwise anatomic heuristic")
    enq = []
    if bbb == "LBBB" and axis == "Inferior":
        if m["tzp"] <= 2:
            enq.append("LBBB + inferior axis + early transition: LVOT more likely.")
        elif m["tzp"] >= 4:
            enq.append("LBBB + inferior axis + late transition: RVOT more likely.")
        else:
            enq.append("Borderline transition (V3): integrate Betensky and Yoshida indices.")
    elif bbb == "RBBB":
        if lead1 == "Negative":
            enq.append("RBBB + negative lead I: LV free wall or epicardial suspicion.")
        else:
            enq.append("RBBB + nonnegative lead I: LV septal/papillary/annular possibilities.")
    else:
        enq.append("Use BBB pattern, axis, lead I, and transition together for an anatomic estimate.")
    enriquez_text = "\n\n".join(enq)
    st.write(enriquez_text)

st.markdown("---")

# ---------------------------
# Results table (permanent)
# ---------------------------
st.subheader("Summary Table")

rows = []

rows.append({
    "Algorithm": "Yoshida 2014 (V2S/V3R)",
    "Metric(s)": f"V2S/V3R = {fmt(m['v2s_v3r'])}",
    "Rule / Cutoff": "≤1.5 → LVOT; >1.5 → RVOT",
    "Applicability": "Generally applicable (OT-VAs with LBBB/inferior axis in original cohort)",
    "Interpretation": yoshida_interp if yoshida_title != "Insufficient data" else yoshida_title,
})

rows.append({
    "Algorithm": "Betensky 2011 (V2 transition ratio)",
    "Metric(s)": f"Ratio = {fmt(m['v2_transition_ratio'])}; TZ index = {m['tz_index']:+d}",
    "Rule / Cutoff": "If PVC transition later than SR → RVOT; else ratio ≥0.60 → LVOT",
    "Applicability": "Validated for PVC transition at V3",
    "Interpretation": bet_title if bet_applicable else "Not validated (PVC transition not V3)",
})

rows.append({
    "Algorithm": "Ouyang 2002 (ASC indices)",
    "Metric(s)": f"Rdur idx = {fmt(m['rdur_idx'])}; R fraction idx = {fmt(m['rfrac_idx'])}",
    "Rule / Cutoff": "Both ≥ (0.50 and 0.30) → left-sided OT (ASC/LVOT) favored",
    "Applicability": "Most relevant when RVOT vs ASC/LVOT is the differential",
    "Interpretation": ouy_title if ouy_title != "Insufficient data" else ouy_title,
})

rows.append({
    "Algorithm": "Yamada 2019",
    "Metric(s)": "NA",
    "Rule / Cutoff": "Pattern-based summary",
    "Applicability": "Heuristic",
    "Interpretation": yamada_text.replace("\n", " "),
})

rows.append({
    "Algorithm": "Enriquez 2019",
    "Metric(s)": "NA",
    "Rule / Cutoff": "Stepwise heuristic",
    "Applicability": "Heuristic",
    "Interpretation": enriquez_text.replace("\n", " "),
})

df = pd.DataFrame(rows, columns=["Algorithm", "Metric(s)", "Rule / Cutoff", "Applicability", "Interpretation"])
st.dataframe(df, use_container_width=True, hide_index=True)

csv = df.to_csv(index=False).encode("utf-8")
st.download_button("Download Results (CSV)", data=csv, file_name="pvc_soo_results.csv", mime="text/csv")

# JSON export: include inputs, metrics, and table rows for reproducibility
payload = {
    "generated_utc": datetime.now(timezone.utc).isoformat(),
    "inputs": inputs,
    "metrics": {
        "v2s_v3r": None if is_bad_number(m["v2s_v3r"]) else float(m["v2s_v3r"]),
        "v2_transition_ratio": None if is_bad_number(m["v2_transition_ratio"]) else float(m["v2_transition_ratio"]),
        "r_wave_duration_index": None if is_bad_number(m["rdur_idx"]) else float(m["rdur_idx"]),
        "r_fraction_index": None if is_bad_number(m["rfrac_idx"]) else float(m["rfrac_idx"]),
        "tz_index": int(m["tz_index"]),
        "pvc_transition_num": int(m["tzp"]),
        "sr_transition_num": int(m["tzs"]),
        "pvc_transition_later_than_sr": bool(m["later_than_sr"]),
    },
    "summary_rows": rows,
}

json_bytes = json.dumps(payload, indent=2).encode("utf-8")
st.download_button("Download Results (JSON)", data=json_bytes, file_name="pvc_soo_results.json", mime="application/json")

with st.expander("References (links)"):
    st.markdown("- Betensky 2011 (PubMed): https://pubmed.ncbi.nlm.nih.gov/21616286/")
    st.markdown("- Yoshida 2014 (PubMed): https://pubmed.ncbi.nlm.nih.gov/24612087/")
    st.markdown("- Ouyang 2002 (PubMed): https://pubmed.ncbi.nlm.nih.gov/11823089/")
    st.markdown("- Enriquez 2019 (PubMed): https://pubmed.ncbi.nlm.nih.gov/30954600/")
