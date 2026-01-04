# soo_app_v5.py
# Unified-input PVC SOO tool (Streamlit)
# Refactored: Added sliders, permanent table, and V3 transition nuance.
# Sources: Betensky 2011, Yoshida 2014, Ouyang 2002, Yamada 2019, Enriquez 2019.

import math
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
def safe_ratio(n, d):
    try:
        n = float(n); d = float(d)
        return n / d if d != 0 else math.nan
    except Exception:
        return math.nan

def pct_r(R, S):
    """R fraction as R/(R+S). Used by Betensky and Ouyang amplitude index."""
    try:
        return safe_ratio(R, (R + S))
    except Exception:
        return math.nan

def fmt(x, nd=3):
    return "—" if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))) else f"{x:.{nd}f}"

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

# Helper functions for Yamada 2019 and Enriquez 2019 interactive decision trees
def decision_yamada(bbb: str, axis: str, tzp: int, lead1: str) -> str:
    """
    Simplified decision tree for Yamada 2019 algorithm.
    Uses bundle branch block morphology (bbb), frontal axis (axis),
    transition lead (numeric tzp) and lead I polarity (lead1) to
    propose a likely region of origin. This is a high-level heuristic and
    does not replace clinical judgment.
    """
    # LBBB pattern often implies right ventricular or septal origin
    if bbb == "LBBB":
        # Early transition (≤V2) suggests a left-sided outflow tract or anterior origin
        if tzp <= 2:
            return "Early transition (≤V2) pattern → LVOT/anterior origin more likely."
        # Late transition (≥V4) suggests a right ventricular outflow or free‑wall origin
        elif tzp >= 4:
            return "Late transition (≥V4) pattern → RVOT/free‑wall origin more likely."
        else:
            # Borderline transition at V3
            return "Borderline transition (V3) pattern → consider both LVOT and RVOT; correlate with other indices."
    else:
        # RBBB pattern usually implies left ventricular origin
        if lead1 == "Negative":
            return "RBBB with negative lead I → LV free‑wall/epicardial origin suspicion."
        else:
            return "RBBB pattern → LV origin (papillary or fascicular) more likely."

def decision_enriquez(axis_class: str, lead1: str, tzp: int, avl_pattern: str, bbb: str, rs_v6: str, disc_pattern: str) -> str:
    """
    Simplified decision tree based on the stepwise anatomic algorithm described by Enriquez et al.
    Parameters:
    - axis_class: one of "Inferior", "Superior" or "Discordant" (direction of QRS axis).
    - lead1: polarity of lead I ("Positive" or "Negative").
    - tzp: numeric value of precordial transition lead (1..6).
    - avl_pattern: pattern in aVL when axis_class is Inferior and lead I is Positive.
                   Accepts "Negative aVL", "Any R or r", or "Unknown".
    - bbb: bundle branch block morphology ("LBBB" or "RBBB"), used when axis_class is Superior.
    - rs_v6: classification of R/S ratio in lead V6 (">1" or "<1"), used when axis_class is Superior and bbb is RBBB.
    - disc_pattern: pattern for discordant axis ("Positive II / Negative III" or "Negative II / Positive III").
    Returns a string describing the most likely anatomic site.
    """
    # Inferior axis: both II and III positive
    if axis_class.startswith("Inferior"):
        if lead1 == "Positive":
            # Evaluate aVL pattern
            if avl_pattern.startswith("Negative"):
                # Negative aVL: consider posterior RVOT vs RCC depending on transition
                if tzp >= 4:
                    return "Inferior axis + positive I + negative aVL + transition ≥V4 → Posterior RVOT."
                elif tzp == 3:
                    return "Inferior axis + positive I + negative aVL + transition at V3 → Posterior RVOT or right coronary cusp (RCC)."  # borderline
                else:
                    return "Inferior axis + positive I + negative aVL + transition ≤V2 → Right coronary cusp (RCC)."  # early transition
            elif avl_pattern.startswith("Any R"):
                # Any R or r in aVL: consider TV free wall or TV septum
                if tzp >= 4:
                    return "Inferior axis + positive I + aVL with R/r + transition ≥V4 → Tricuspid valve free wall."
                else:
                    return "Inferior axis + positive I + aVL with R/r + transition ≤V3 → Tricuspid valve septum or parahisian region."
            else:
                return "Inferior axis + positive I but aVL pattern unknown → insufficient data for detailed localization."
        else:
            # lead I negative
            # Use transition to distinguish anterior RVOT vs left structures
            if tzp >= 3:
                return "Inferior axis + negative I + transition ≥V3 → Anterior RVOT."
            elif tzp == 2:
                return "Inferior axis + negative I + transition at V2 → Left coronary cusp (LCC) or LV summit."
            else:
                return "Inferior axis + negative I + transition at V1 (or ≤V1) → LCC, LV summit, AMC, top mitral valve or anterolateral papillary muscle."
    # Superior axis: both II and III negative
    elif axis_class.startswith("Superior"):
        if bbb == "LBBB":
            # LBBB: right ventricular origin; use transition
            if tzp >= 4:
                return "Superior axis + LBBB + transition ≥V4 → Tricuspid valve free wall or moderator band (MB)."  # late transition
            else:
                return "Superior axis + LBBB + transition ≤V3 → Tricuspid valve septum or crux (inferior RV)."  # early transition
        else:
            # RBBB: left ventricular origin; use R/S ratio in V6
            if rs_v6 == ">1":
                return "Superior axis + RBBB + R/S(V6) > 1 → Inferior mitral annulus (IMV) or posterior mitral sites."  # R wave dominant
            else:
                return "Superior axis + RBBB + R/S(V6) < 1 → Posteromedial papillary muscle (PPM) or left posterior fascicle (LPF)."  # S wave dominant
    # Discordant axis: leads II and III have opposite polarity
    elif axis_class.startswith("Discordant"):
        if disc_pattern.startswith("Positive"):
            return "Discordant axis (positive II, negative III) → Lateral tricuspid valve (TV), moderator band or parahisian region."
        else:
            return "Discordant axis (negative II, positive III) → Lateral mitral valve (MV) or anterolateral papillary muscle (APM)."
    # Indeterminate or not provided
    return "Insufficient data to localize site; please specify axis, lead I and other parameters."
# ---------------------------
# Layout
# ---------------------------
st.title("PVC Site-of-Origin (SOO) — Unified Input App")

st.markdown(
    "This tool computes multiple literature-based indices from a **single** set of ECG inputs and "
    "summarizes likely RVOT/LVOT and related origins. Cutoffs are shown with each algorithm."
)

colA, colB = st.columns(2)

with colA:
    st.subheader("Yoshida 2014 — V2S/V3R index")
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

    st.subheader("Betensky 2011 — V2 transition ratio")
    st.write(f"V2 transition ratio = {fmt(v2_transition_ratio)}")
    st.write(f"PVC transition vs SR: {'Later than SR' if later_than_sr else 'Not later than SR or equal'} "
             f"(TZ index = {tz_index:+d})")

    # Refinement #3: Nuance tip
    if tz_pvc == "V3":
        st.caption("💡 **Note:** The Betensky ratio is most discriminatory when the PVC transition is exactly at V3.")

    notes = []
    if later_than_sr:
        notes.append("PVC transition later than SR **excludes LVOT** in the original report.")
    if not math.isnan(v2_transition_ratio):
        notes.append("Cutoff ≥0.60 → predicts **LVOT** (with V3 transition context).")
    
    if notes:
        st.info("\n".join(notes))
    else:
        st.info("Provide V2 (PVC & SR) amplitudes.")

    betensky_interp = ("Later than SR → excludes LVOT; "
                       f"ratio {fmt(v2_transition_ratio)} (≥0.60 favors LVOT)" if not math.isnan(v2_transition_ratio)
                       else "Insufficient data")
    st.caption("Betensky BP et al., J Am Coll Cardiol. 2011.")

with colB:
    st.subheader("Ouyang 2002 — Aortic sinus cusp indices")
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
    "Interpretation": "—" if math.isnan(v2s_v3r) else yoshida_interp
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

# Heuristics rows removed: Yamada and Enriquez algorithms will be represented via interactive decision trees.

df = pd.DataFrame(rows, columns=["Algorithm", "Metric(s)", "Rule / Cutoff", "Interpretation"])
st.dataframe(df, use_container_width=True, hide_index=True)

csv = df.to_csv(index=False).encode("utf-8")
st.download_button("Download Results (CSV)", data=csv, file_name="pvc_soo_results.csv", mime="text/csv")

# -----------------------------------------------------------------------------
# Interactive decision trees for Yamada 2019 and Enriquez 2019 algorithms
# These sections provide step‑wise anatomic predictions based on simplified
# decision trees derived from published algorithms. They use the current
# unified input values by default, but you can override some parameters for
# the Enriquez algorithm to refine the classification.

st.markdown("---")
st.subheader("Yamada 2019 — Interactive Decision Tree")
# Use unified inputs for morphology (bbb), axis, transition (tzp) and lead I polarity (lead1)
yamada_prediction = decision_yamada(bbb, axis, tzp, lead1)
st.write(f"**Yamada prediction:** {yamada_prediction}")

st.markdown("")

st.subheader("Enriquez 2019 — Interactive Decision Tree")
# Axis classification select box (user may override default axis classification)
axis_class_options = [
    "Inferior (positive II and III)",
    "Superior (negative II and III)",
    "Discordant (opposite polarity)"
]
default_axis_idx = 0
if axis == "Inferior":
    default_axis_idx = 0
elif axis == "Superior":
    default_axis_idx = 1
else:
    default_axis_idx = 2
axis_class_choice = st.selectbox(
    "Axis classification (for Enriquez)",
    axis_class_options,
    index=default_axis_idx
)
# Normalize axis_class for decision function
if axis_class_choice.startswith("Inferior"):
    axis_class_val = "Inferior"
elif axis_class_choice.startswith("Superior"):
    axis_class_val = "Superior"
else:
    axis_class_val = "Discordant"

# Lead I polarity (allow override); default to unified lead1
lead1_options = ["Positive", "Negative"]
default_lead1_idx = lead1_options.index(lead1) if lead1 in lead1_options else 0
lead1_choice = st.selectbox(
    "Lead I polarity (for Enriquez)",
    lead1_options,
    index=default_lead1_idx
)

# Pattern in aVL (only used when axis is inferior and lead I is positive)
avl_pattern_options = ["Negative aVL", "Any R or r", "Unknown"]
avl_choice = st.selectbox(
    "Pattern in lead aVL (if axis is inferior and lead I positive)",
    avl_pattern_options
)

# Morphology in V1 (LBBB vs RBBB); default to unified bbb
bbb_options = ["LBBB", "RBBB"]
bbb_default_idx = bbb_options.index(bbb) if bbb in bbb_options else 0
bbb_choice = st.selectbox(
    "Morphology in V1 (for Enriquez)",
    bbb_options,
    index=bbb_default_idx
)

# R/S ratio in V6 classification (only used when axis is superior and RBBB pattern)
rs_v6_options = [">1", "<1"]
rs_v6_choice = st.selectbox(
    "R/S ratio in V6 (if axis is superior and RBBB)",
    rs_v6_options
)

# Pattern for discordant axis (only used when axis is discordant)
disc_pattern_options = ["Positive II / Negative III", "Negative II / Positive III"]
disc_choice = st.selectbox(
    "Discordant II/III pattern (if axis is discordant)",
    disc_pattern_options
)

# Compute Enriquez prediction
enriquez_prediction = decision_enriquez(
    axis_class_val,
    lead1_choice,
    tzp,
    avl_choice,
    bbb_choice,
    rs_v6_choice,
    disc_choice,
)
st.write(f"**Enriquez prediction:** {enriquez_prediction}")