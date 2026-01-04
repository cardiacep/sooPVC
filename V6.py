# soo_app_v5.py
# Unified-input PVC SOO tool (Streamlit)
# Refactored: Added sliders, permanent table, and V3 transition nuance.
# Sources: Betensky 2011, Yoshida 2014, Ouyang 2002, Yamada 2019, Enriquez 2019.

from __future__ import annotations

import math
import json
from datetime import datetime, timezone
from typing import Any, Optional

import pandas as pd
import streamlit as st

st.set_page_config(page_title="PVC SOO (Unified Inputs)", layout="wide")

# ---------------------------
# Defaults & session helpers
# ---------------------------
DEFAULTS = {
    "bbb": "LBBB",
    "axis": "Inferior",
    "lead1": "Positive",
    "tz_pvc": "V3",
    "tz_sr": "V4",
    "qrs_pvc_ms": 140,

    # Optional: time to maximal deflection. Users can leave this as 0 when unknown.
    "tmax_defl_ms": 0,

    "R_V1_PVC": 0.2,
    "S_V1_PVC": 1.2,

    "R_V2_PVC": 0.3,
    "S_V2_PVC": 1.5,
    "R_V2_SR": 0.6,
    "S_V2_SR": 1.8,

    "R_V3_PVC": 0.5,

    "Rdur_V1_ms": 45,
    "Rdur_V2_ms": 55
}

def ensure_defaults():
    for k, v in DEFAULTS.items():
        if k not in st.session_state:
            st.session_state[k] = v

def reset_inputs():
    for k, v in DEFAULTS.items():
        st.session_state[k] = v
    # Use standard rerun, falling back if necessary
    try:
        st.rerun()
    except AttributeError:
        st.experimental_rerun()

ensure_defaults()

# ---------------------------
# Helpers
# ---------------------------
#
# NOTE: Custom helper functions for ratio calculations and formatting. These definitions include
# proper type hints, NaN handling and an "NA" placeholder for missing values. They are defined
# here (after imports) to ensure they are available throughout the application.

def is_bad_number(x: Any) -> bool:
    """
    Determine whether a numeric value should be considered invalid (None, NaN or Inf).
    """
    return (x is None) or (isinstance(x, float) and (math.isnan(x) or math.isinf(x)))


def safe_ratio(n: Any, d: Any) -> float:
    """
    Divide two numbers, returning NaN when the denominator is zero or either operand is non-numeric.
    """
    try:
        n = float(n)
        d = float(d)
        return n / d if d != 0 else math.nan
    except Exception:
        return math.nan


def pct_r(R: Any, S: Any) -> float:
    """
    Normalized R fraction: R/(R+S). This avoids a divide-by-zero when both R and S are zero.
    """
    try:
        return safe_ratio(R, (float(R) + float(S)))
    except Exception:
        return math.nan


def fmt(x: Optional[float], nd: int = 3) -> str:
    """
    Format numeric values for display. Returns 'NA' when the number is missing, NaN or infinite.
    """
    return "NA" if is_bad_number(x) else f"{float(x):.{nd}f}"

# ---------------------------
# Sidebar: unified inputs + actions
# ---------------------------
st.sidebar.title("Unified ECG Inputs")
st.sidebar.caption("All algorithms reuse these values. Units: mV (amplitude), ms (time).")

# Action buttons
if st.sidebar.button("↺ Reset to Defaults", use_container_width=True):
    reset_inputs()

# Morphology & general features
# Changed to select_slider for transitions (Refinement #1)
st.sidebar.subheader("Morphology & Transition")
bbb = st.sidebar.selectbox("PVC morphology in V1", ["LBBB", "RBBB"], index=["LBBB","RBBB"].index(st.session_state["bbb"]), key="bbb")
axis = st.sidebar.selectbox("Frontal axis (PVC)", ["Inferior", "Superior", "Indeterminate"], index=["Inferior","Superior","Indeterminate"].index(st.session_state["axis"]), key="axis")
lead1 = st.sidebar.selectbox("Lead I QRS polarity (PVC)", ["Positive", "Negative", "Isoelectric"], index=["Positive","Negative","Isoelectric"].index(st.session_state["lead1"]), key="lead1")

tz_options = ["≤V1","V2","V3","V4","V5","≥V6"]
tz_pvc = st.sidebar.select_slider("Transition (PVC)", options=tz_options, value=st.session_state["tz_pvc"], key="tz_pvc")
tz_sr  = st.sidebar.select_slider("Transition (SR)", options=tz_options, value=st.session_state["tz_sr"], key="tz_sr")

qrs_pvc_ms = st.sidebar.number_input("QRS duration (PVC, ms)", min_value=60, max_value=260, value=st.session_state["qrs_pvc_ms"], step=1, key="qrs_pvc_ms")

# Optional: time to maximal deflection (ms). A value of 0 indicates that the parameter is unknown. When provided (>0), the maximal deflection index will be computed.
tmax_defl_ms = st.sidebar.number_input(
    "Time to maximal deflection (PVC, ms) [optional]",
    min_value=0,
    max_value=260,
    value=st.session_state["tmax_defl_ms"],
    step=1,
    key="tmax_defl_ms",
    help="Shortest interval from QRS onset to maximal positive or negative deflection in any precordial lead. Used to compute the maximal deflection index (MDI).",
)

st.sidebar.markdown("---")
st.sidebar.subheader("Lead V1 amplitudes (PVC)")
R_V1_PVC = st.sidebar.number_input("R in V1 (mV)", min_value=0.0, value=st.session_state["R_V1_PVC"], step=0.1, format="%.3f", key="R_V1_PVC")
S_V1_PVC = st.sidebar.number_input("S in V1 (mV)", min_value=0.0, value=st.session_state["S_V1_PVC"], step=0.1, format="%.3f", key="S_V1_PVC")

st.sidebar.subheader("Lead V2 amplitudes (PVC & SR)")
R_V2_PVC = st.sidebar.number_input("R in V2 (PVC, mV)", min_value=0.0, value=st.session_state["R_V2_PVC"], step=0.1, format="%.3f", key="R_V2_PVC")
S_V2_PVC = st.sidebar.number_input("S in V2 (PVC, mV)", min_value=0.0, value=st.session_state["S_V2_PVC"], step=0.1, format="%.3f", key="S_V2_PVC")
R_V2_SR  = st.sidebar.number_input("R in V2 (SR, mV)",  min_value=0.0, value=st.session_state["R_V2_SR"], step=0.1, format="%.3f", key="R_V2_SR")
S_V2_SR  = st.sidebar.number_input("S in V2 (SR, mV)",  min_value=0.0, value=st.session_state["S_V2_SR"], step=0.1, format="%.3f", key="S_V2_SR")

st.sidebar.subheader("Lead V3 amplitude (PVC)")
R_V3_PVC = st.sidebar.number_input("R in V3 (PVC, mV)", min_value=0.0, value=st.session_state["R_V3_PVC"], step=0.1, format="%.3f", key="R_V3_PVC")

st.sidebar.markdown("---")
st.sidebar.subheader("R-wave durations (PVC)")
Rdur_V1_ms = st.sidebar.number_input("R duration V1 (ms)", min_value=0, max_value=260, value=st.session_state["Rdur_V1_ms"], step=1, key="Rdur_V1_ms")
Rdur_V2_ms = st.sidebar.number_input("R duration V2 (ms)", min_value=0, max_value=260, value=st.session_state["Rdur_V2_ms"], step=1, key="Rdur_V2_ms")

# Convert transition labels to numeric bins for comparisons
tz_map = {"≤V1":1,"V2":2,"V3":3,"V4":4,"V5":5,"≥V6":6}
tzp = tz_map[tz_pvc]; tzs = tz_map[tz_sr]

# Precompute shared derived values
rfrac_V1 = pct_r(R_V1_PVC, S_V1_PVC)
rfrac_V2_PVC = pct_r(R_V2_PVC, S_V2_PVC)
rfrac_V2_SR  = pct_r(R_V2_SR,  S_V2_SR)

v2_transition_ratio = safe_ratio(rfrac_V2_PVC, rfrac_V2_SR)  # Betensky
v2s_v3r = safe_ratio(S_V2_PVC, R_V3_PVC)                     # Yoshida

Rdur_idx = safe_ratio(max(Rdur_V1_ms, Rdur_V2_ms), qrs_pvc_ms)  # Ouyang duration index
Rfrac_idx = max(rfrac_V1, rfrac_V2_PVC)                          # Ouyang amplitude index (percentage R)

tz_index = tzp - tzs
later_than_sr = tzp > tzs

# Compute maximal deflection index (MDI). When the time to maximal deflection is zero or not provided,
# treat MDI as missing.
mdi = math.nan if (tmax_defl_ms is None or float(tmax_defl_ms) <= 0) else safe_ratio(tmax_defl_ms, qrs_pvc_ms)

# ---------------------------
# Layout
# ---------------------------
st.title("PVC Site-of-Origin (SOO) – Unified Input App")

# Brief description
st.markdown(
    "This tool computes multiple literature-based indices from a **single** set of ECG inputs and "
    "summarizes likely RVOT/LVOT and related origins. Cutoffs and applicability notes are shown with each algorithm."
)

# Key metrics panel for quick reference
metric_cols = st.columns(6)
metric_cols[0].metric("V2S/V3R (PVC)", fmt(v2s_v3r))
metric_cols[1].metric("V2 transition ratio", fmt(v2_transition_ratio))
metric_cols[2].metric("R duration index", fmt(Rdur_idx))
metric_cols[3].metric("R fraction index", fmt(Rfrac_idx))
metric_cols[4].metric("TZ index (PVC−SR)", f"{tz_index:+d}")
metric_cols[5].metric("MDI", fmt(mdi))

# Two-column layout for algorithm interpretations
colA, colB = st.columns(2)

with colA:
    st.subheader("Yoshida 2014 – V2S/V3R index")
    st.write(f"V2S/V3R = {fmt(v2s_v3r)}")
    if math.isnan(v2s_v3r):
        st.info("Enter S(V2) and R(V3) during the PVC.")
        yoshida_call = "Insufficient data"
        yoshida_interp = ""
    else:
        if v2s_v3r <= 1.5:
            st.success("≤1.5 → favors **LVOT** origin.")
            yoshida_interp = "≤1.5 → favors LVOT"
        else:
            st.warning(">1.5 → favors **RVOT** origin.")
            yoshida_interp = ">1.5 → favors RVOT"
        yoshida_call = yoshida_interp
    st.caption("Yoshida N et al., J Cardiovasc Electrophysiol. 2014.")

    st.subheader("Betensky 2011 – V2 transition ratio")
    st.write(f"V2 transition ratio = {fmt(v2_transition_ratio)}")
    st.write(
        f"PVC transition vs SR: {'Later than SR' if later_than_sr else 'Not later than SR or equal'} "
        f"(TZ index = {tz_index:+d})"
    )

    # Betensky algorithm: applicable when the PVC transition is exactly at V3.
    if tz_pvc != "V3":
        st.warning("Applicability: cutoff-based Betensky interpretation is validated for PVC transition at V3 only.")
        st.info("Computed ratio shown for reference; not validated outside V3 transition.")
        betensky_interp = "Not validated (PVC transition not V3)"
    else:
        # PVC transition is exactly at V3: follow the two-step algorithm.
        if later_than_sr:
            st.warning("PVC transition later than SR → RVOT favored (LVOT unlikely).")
            st.info("In the original algorithm, a later transition than SR was highly specific for RVOT and made LVOT unlikely.")
            betensky_interp = "Later than SR → RVOT"
        else:
            # PVC transition is not later than SR; compute ratio.
            if math.isnan(v2_transition_ratio):
                st.info("Provide V2 amplitudes (PVC & SR) to compute the ratio.")
                betensky_interp = "Insufficient data"
            else:
                if v2_transition_ratio >= 0.60:
                    st.success("Ratio ≥0.60 → LVOT favored.")
                    st.info("Cutoff: V2 transition ratio ≥0.60 suggests LVOT when the PVC transition is V3 and not later than SR.")
                    betensky_interp = "Ratio ≥0.60 → LVOT"
                else:
                    st.warning("Ratio <0.60 → RVOT favored.")
                    st.info("Cutoff: V2 transition ratio <0.60 suggests RVOT when the PVC transition is V3 and not later than SR.")
                    betensky_interp = "Ratio <0.60 → RVOT"
    st.caption("Betensky BP et al., J Am Coll Cardiol. 2011.")

with colB:
    st.subheader("Ouyang 2002 – Aortic sinus cusp indices")
    st.write(f"R-wave duration index = max(RdurV1,V2)/QRS = {fmt(Rdur_idx)}")
    st.write(f"R/(R+S) amplitude index (best of V1 or V2) = {fmt(Rfrac_idx)}")
    if not math.isnan(Rdur_idx) and not math.isnan(Rfrac_idx):
        if (Rdur_idx >= 0.50) and (Rfrac_idx >= 0.30):
            st.success("≥0.50 and ≥0.30 → suggests **LVOT (aortic sinus cusp)** origin.")
            ouyang_interp = "Meets ASC criteria → LVOT (aortic sinus cusp) likely"
        else:
            st.warning("Below at least one cutoff → does **not** meet classic ASC criteria.")
            ouyang_interp = "Does not meet ASC criteria"
    else:
        st.info("Enter QRS (PVC), R-durations (V1,V2), and V1/V2 amplitudes.")
        ouyang_interp = "Insufficient data"
    st.caption("Ouyang F et al., J Am Coll Cardiol. 2002.")

st.markdown("---")
colC, colD = st.columns(2)

with colC:
    st.subheader("Yamada 2019 – heuristic summary")
    # Summarize the Yamada multi‑branch algorithm using a structured narrative derived from the published decision tree (Figure 13).
    # We provide high‑level guidance rather than a rigid output, because many of the variables required (e.g., aVL polarity, notching, specific QS patterns) are not collected in this simple calculator.
    bullets: list[str] = []
    # Always report the key inputs so the user understands what is being analysed.
    bullets.append(
        f"Inputs: BBB={bbb}; axis={axis}; lead I polarity={lead1}; PVC transition={tz_pvc}; SR transition={tz_sr}; QRS duration={qrs_pvc_ms} ms."
    )
    # Provide MDI context if available.
    if not is_bad_number(mdi):
        bullets.append(
            f"Maximal deflection index (MDI) = {fmt(mdi)}. In general, values ≥0.55 suggest an epicardial origin, whereas values <0.55 suggest an endocardial origin."
        )
    # LBBB patterns: differentiate outflow‑tract versus non‑outflow origins using inferior lead morphology, aVL/aVR patterns, and transition.
    if bbb == "LBBB":
        bullets.append(
            "**LBBB morphology:** the site of origin may lie in the right ventricular structures (RVOT/crux) or in the left ventricular outflow tract/adjacent structures depending on the appearance of the inferior leads and high‑lateral leads (aVL/aVR)."
        )
        bullets.append(
            "- If small R or r waves are present in all inferior leads and both aVR and aVL demonstrate QS or rS complexes, the arrhythmia is likely originating from the outflow tracts. In such cases, apply the Betensky/Yoshida indices (V2 transition ratio and V2S/V3R) to distinguish between RVOT and LVOT origins."
        )
        bullets.append(
            "- If r waves are present in all inferior leads but aVR or aVL do *not* show QS/rS patterns, non‑outflow left‑sided structures become more likely. These include the aortomitral continuity (AMC), the junction between the left and right coronary cusps, and the left ventricular (LV) summit. Clues supporting these diagnoses include the absence of an S wave in V6, a low R‑wave amplitude ratio in leads III/II (<0.9), and a qrS pattern in V1–V3."
        )
        bullets.append(
            "- If there are QS complexes in the inferior leads, an MDI >0.45 and polarity reversal across V1–V3 (i.e., progressive change from positive to negative), the origin may be at the ventricular **crux** (the junction of the interventricular septum, atrioventricular ring and ventricular free walls). Further differentiation uses the presence or absence of an R wave in V6: an R wave in V6 favours free‑wall sites along the tricuspid annulus, septal band or parietal band, whereas absence of R in V6 suggests septal or non‑coronary cusp origins."
        )
    # RBBB patterns: interpret left‑sided origins and papillary muscle involvement using axis and additional ECG markers.
    else:  # RBBB pattern
        bullets.append(
            "**RBBB morphology:** idiopathic ventricular arrhythmias with an RBBB pattern often arise from left‑sided structures (left sinus of Valsalva, aortomitral continuity, LV summit) or the mitral annulus/papillary muscles."
        )
        bullets.append(
            "- A QS pattern in the inferior leads together with a very broad QRS (≥160 ms) and a qR or R in V1 suggests involvement of the posterior fascicle (LPF) or posteromedial papillary muscle (PPM)."
        )
        bullets.append(
            "- When the R‑wave amplitude in leads II and III is low (< 1 mV) and an r or R wave is present in aVL, arrhythmias may arise from the left sinus of Valsalva (LSV), AMC or LV summit."
        )
        bullets.append(
            "- Positive concordance across the precordial leads (i.e., uniformly positive QRS morphology) raises the possibility of anterolateral papillary muscle (APM) or lateral mitral annulus origin; a prominent S wave in V6 makes LV summit less likely."
        )
        bullets.append(
            "- Late notching of the Q or S wave in the inferior leads and a relatively narrow QRS duration suggests septal or fascicular LV origins."
        )
    # Compose the narrative.
    yamada_text = "\n\n".join(bullets)
    st.write(yamada_text)
    st.caption("Adapted from the multi‑branch algorithm described by Yamada et al. (J Cardiovasc Electrophysiol, 2019).")

with colD:
    st.subheader("Enriquez 2019 – stepwise anatomical heuristic")
    # Summarize the stepwise anatomical approach proposed by Enriquez et al. using the structured algorithm from Figure 3.  
    # The algorithm uses the frontal axis (inferior, superior or discordant), lead I polarity, the presence of a negative aVL or any r‑wave in aVL, and the precordial transition to regionalize ventricular arrhythmias.  
    # Only high‑level guidance is given here because our input form does not capture aVL polarity or R/S amplitudes in V6.
    steps: list[str] = []
    steps.append(
        f"**Step 1: Regionalization.** Evaluate the bundle branch morphology (BBB={bbb}), the frontal axis (axis={axis}) and lead I polarity (lead I={lead1})."
    )
    # Inferior axis branch
    if axis == "Inferior":
        steps.append(
            "**Inferior axis (positive in leads II and III):** differentiate anterior/posterior RVOT, right coronary cusp (RCC) and tricuspid valve (TV) sites based on lead I polarity, aVL morphology and the precordial transition."
        )
        if lead1 == "Positive":
            steps.append(
                "- **Positive lead I (rightward from midline):** if lead aVL is negative, a late precordial transition (≥V4) suggests a posterior RVOT origin; transition in V3 suggests posterior RVOT or the right coronary cusp (dependent on the V2 transition ratio); early transitions (≤V2) are more consistent with right coronary cusp origins."
            )
            steps.append(
                "  If any r‑wave is present in aVL, the arrhythmia may arise from the tricuspid valve: late transitions (≥V4) favour the TV free wall, whereas early transitions (≤V3) point toward the TV septum or parahisian region."
            )
        elif lead1 == "Negative":
            steps.append(
                "- **Negative lead I (leftward from midline):** use the precordial transition to separate anterior RVOT from aortic/mitral structures. Transition ≥V3 favours an anterior RVOT origin; transition in V2 suggests the left coronary cusp or LV summit; and an even earlier transition in V1 (often accompanied by a right bundle branch block morphology) points toward the left coronary cusp, LV summit, aortomitral continuity, top of the mitral valve, anterolateral papillary muscle or left anterior fascicle."
            )
    # Superior axis branch
    elif axis == "Superior":
        steps.append(
            "**Superior axis (negative in leads II and III):** bundle branch pattern helps distinguish right versus left ventricular structures."
        )
        if bbb == "LBBB":
            steps.append(
                "- **LBBB morphology with superior axis:** this combination often localizes to the right ventricle. A late precordial transition (≥V4) favours the tricuspid valve free wall or moderator band, whereas an early transition (≤V3) suggests the tricuspid valve septum or crux region (characterized by QS complexes in inferior leads and pseudo‑delta waves)."
            )
        else:  # RBBB with superior axis
            steps.append(
                "- **RBBB morphology with superior axis:** this combination points to left‑sided structures. When the R/S amplitude ratio in V6 is >1 (not available in this app), an inferior mitral annulus origin is likely; if the ratio is <1, a posteromedial papillary muscle or left posterior fascicular origin is more probable. Both patterns typically show R, Rsr' or qR complexes in V1 and a relatively narrow QRS."
            )
    # Discordant axis branch (neither clearly inferior nor superior)
    else:
        steps.append(
            "**Discordant axis (II and III discordant):** evaluate which limb lead is positive to identify lateral annular or papillary muscle sites."
        )
        steps.append(
            "- If lead II is positive and lead III negative, lateral tricuspid valve, moderator band or parahisian sites are possibilities. These often show rS patterns in V1 and transitions around V4–V5, with QS or rS in V1 and V5–V6 transitions for moderator band origins, and QS in V1 with V2–V3 transition plus a narrow QRS for parahisian origins."
        )
        steps.append(
            "- If lead III is positive and lead II negative, lateral mitral annulus and anterolateral papillary muscle should be considered. Lateral mitral annulus sites often display a large R/S ratio in V6, whereas anterolateral papillary muscle origins display a smaller R/S ratio in V6."
        )
    # Add MDI context when available
    if not is_bad_number(mdi):
        steps.append(
            f"**MDI context:** {fmt(mdi)} – values ≥0.55 are often associated with epicardial origins; values below this threshold suggest endocardial origins."
        )
    # Compose the narrative.
    enriquez_text = "\n\n".join(steps)
    st.write(enriquez_text)
    st.caption("Adapted from the stepwise approach of Enriquez et al. (Heart Rhythm, 2019).")

st.markdown("---")

# ---------------------------
# Results table (Permanent display - Refinement #2)
# ---------------------------
st.subheader("Summary Table")

rows = []

# Yoshida
rows.append({
    "Algorithm": "Yoshida 2014 (V2S/V3R)",
    "Metric(s)": f"V2S/V3R = {fmt(v2s_v3r)}",
    "Rule / Cutoff": "≤1.5 → LVOT; >1.5 → RVOT",
    "Interpretation": "NA" if is_bad_number(v2s_v3r) else yoshida_interp
})

# Betensky
rows.append({
    "Algorithm": "Betensky 2011 (V2 transition ratio)",
    "Metric(s)": f"Ratio = {fmt(v2_transition_ratio)}; TZ index = {tz_index:+d}",
    "Rule / Cutoff": "PVC later than SR → excludes LVOT; Ratio ≥0.60 → LVOT",
    "Interpretation": betensky_interp
})

# Ouyang
rows.append({
    "Algorithm": "Ouyang 2002 (ASC indices)",
    "Metric(s)": f"Rdur idx = {fmt(Rdur_idx)}; R/(R+S) idx = {fmt(Rfrac_idx)}",
    "Rule / Cutoff": "Both ≥ (0.50 & 0.30) → LVOT likely",
    "Interpretation": ouyang_interp
})

# Heuristics
rows.append({
    "Algorithm": "Yamada 2019",
    "Metric(s)": "NA",
    "Rule / Cutoff": "Pattern-based summary",
    "Interpretation": yamada_text.replace("\n", " ")
})

rows.append({
    "Algorithm": "Enriquez 2019",
    "Metric(s)": "NA",
    "Rule / Cutoff": "Stepwise heuristic",
    "Interpretation": enriquez_text.replace("\n", " ")
})

df = pd.DataFrame(rows, columns=["Algorithm", "Metric(s)", "Rule / Cutoff", "Interpretation"])
st.dataframe(df, use_container_width=True, hide_index=True)

csv = df.to_csv(index=False).encode("utf-8")
st.download_button("Download Results (CSV)", data=csv, file_name="pvc_soo_results.csv", mime="text/csv")

# JSON export: include inputs, derived metrics and summary rows for reproducibility
payload = {
    "generated_utc": datetime.now(timezone.utc).isoformat(),
    "inputs": {
        "bbb": bbb,
        "axis": axis,
        "lead1": lead1,
        "tz_pvc": tz_pvc,
        "tz_sr": tz_sr,
        "qrs_pvc_ms": qrs_pvc_ms,
        "tmax_defl_ms": tmax_defl_ms,
        "R_V1_PVC": R_V1_PVC,
        "S_V1_PVC": S_V1_PVC,
        "R_V2_PVC": R_V2_PVC,
        "S_V2_PVC": S_V2_PVC,
        "R_V2_SR": R_V2_SR,
        "S_V2_SR": S_V2_SR,
        "R_V3_PVC": R_V3_PVC,
        "Rdur_V1_ms": Rdur_V1_ms,
        "Rdur_V2_ms": Rdur_V2_ms,
    },
    "metrics": {
        "v2s_v3r": None if is_bad_number(v2s_v3r) else float(v2s_v3r),
        "v2_transition_ratio": None if is_bad_number(v2_transition_ratio) else float(v2_transition_ratio),
        "r_wave_duration_index": None if is_bad_number(Rdur_idx) else float(Rdur_idx),
        "r_fraction_index": None if is_bad_number(Rfrac_idx) else float(Rfrac_idx),
        "max_deflection_index": None if is_bad_number(mdi) else float(mdi),
        "tz_index": int(tz_index),
        "pvc_transition_num": int(tzp),
        "sr_transition_num": int(tzs),
        "pvc_transition_later_than_sr": bool(later_than_sr),
    },
    "summary_rows": rows,
}

json_bytes = json.dumps(payload, indent=2).encode("utf-8")
st.download_button(
    "Download Results (JSON)",
    data=json_bytes,
    file_name="pvc_soo_results.json",
    mime="application/json",
)

#
# Additional figures: Yamada algorithm and stepwise anatomical approach
# These images are provided for educational reference. They illustrate the multi-branch algorithms described in the
# heuristic summaries above. Use the expander to toggle their visibility.
with st.expander("Algorithm figures (Yamada and stepwise approaches)"):
    st.image(
        "/home/oai/share/e53851f8-f105-4c3f-804f-27502e3c59a8.png",
        caption="Yamada 2019 electrocardiographic algorithm (panels A and B) for LBBB (top) and RBBB (bottom) ventricular arrhythmias.",
        use_column_width=True,
    )
    st.image(
        "/home/oai/share/61a4ce96-a76c-4b06-96e8-708045fb279a.png",
        caption="Stepwise electrocardiographic approach for prediction of ventricular arrhythmia site of origin (Enriquez et al.).",
        use_column_width=True,
    )