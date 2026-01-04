import streamlit as st
import math
import pandas as pd

# -----------------------------------------------------------------------------
# 1. SETUP & HELPER FUNCTIONS
# -----------------------------------------------------------------------------

st.set_page_config(page_title="PVC Localization Master Tool", layout="wide")

def safe_ratio(n, d):
    try:
        n = float(n)
        d = float(d)
        if d == 0:
            return math.nan
        return n / d
    except Exception:
        return math.nan

def pct_r(R, S):
    # Calculates R / (R + S) for use in Betensky and Ouyang indices
    try:
        den = R + S
        if den == 0:
            return math.nan
        return R / den
    except Exception:
        return math.nan

def fmt(x, nd=3):
    # Formats floats safely, handling None/NaN
    if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
        return "—"
    return f"{x:.{nd}f}"

# -----------------------------------------------------------------------------
# 2. SESSION STATE & DEFAULTS
# -----------------------------------------------------------------------------

DEFAULTS = {
    # Qualitative / Morphology
    "bbb": "LBBB",
    "axis": "Inferior (Positive II & III)",
    "lead1": "Positive",
    "avl_morph": "Negative (QS)",
    "avr_morph": "QS",
    "inf_pattern": "R or r wave in all",
    "v6_ratio_cat": "> 1",
    "v6_r_present": True,
    "pos_concordance": False,
    "inf_notch": False,
    "low_volt": False,
    "v1_morph_cat": "Other (rS, QS, etc.)",

    # Quantitative / Measurements
    "tz_pvc": "V3",
    "tz_sr": "V4",
    "qrs_pvc_ms": 140,
    "mdi_value": 0.40,
    
    # Amplitudes (mV)
    "R_V1_PVC": 0.0, "S_V1_PVC": 1.2,
    "R_V2_PVC": 0.3, "S_V2_PVC": 1.5,
    "R_V2_SR": 0.6, "S_V2_SR": 1.8,
    "R_V3_PVC": 0.5,
    
    # Durations (ms)
    "Rdur_V1_ms": 40,
    "Rdur_V2_ms": 50
}

def ensure_defaults():
    for k, v in DEFAULTS.items():
        if k not in st.session_state:
            st.session_state[k] = v

def reset_inputs():
    for k, v in DEFAULTS.items():
        st.session_state[k] = v
    try:
        st.rerun()
    except AttributeError:
        pass

ensure_defaults()

# -----------------------------------------------------------------------------
# 3. SIDEBAR INPUTS
# -----------------------------------------------------------------------------

st.sidebar.title("ECG Input Parameters")
if st.sidebar.button("Reset to Defaults", use_container_width=True):
    reset_inputs()

# --- A. General Morphology ---
with st.sidebar.expander("1. General Morphology", expanded=True):
    bbb = st.selectbox("Bundle Branch Block (V1)", ("LBBB", "RBBB"), key="bbb", help="LBBB: Dominant S in V1. RBBB: Dominant R in V1.")
    axis = st.selectbox("Frontal Axis (II, III)", ("Inferior (Positive II & III)", "Superior (Negative II & III)", "Discordant"), key="axis")
    lead1 = st.selectbox("Lead I Polarity", ("Positive", "Negative"), key="lead1")

# --- B. Specific Lead Patterns ---
with st.sidebar.expander("2. Specific Lead Patterns", expanded=False):
    avl_morph = st.selectbox("Lead aVL", ("Negative (QS)", "Positive (Any R or r)", "rS Pattern", "Other"), key="avl_morph")
    avr_morph = st.selectbox("Lead aVR", ("QS", "Other"), key="avr_morph")
    inf_pattern = st.radio("Inferior Leads (II, III, aVF)", ("R or r wave in all", "QS in all", "Mixed/Other"), key="inf_pattern")
    v1_morph_cat = st.selectbox("V1 Specifics", ("qR or R", "Other (rS, QS, etc.)"), key="v1_morph_cat")

# --- C. V6 & Notching ---
with st.sidebar.expander("3. V6 & Other Features", expanded=False):
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        v6_ratio_cat = st.radio("V6 R/S Ratio", ("> 1", "<= 1"), key="v6_ratio_cat")
    with col_s2:
        v6_r_present = st.checkbox("R wave in V6?", key="v6_r_present")
        
    pos_concordance = st.checkbox("Positive Concordance?", key="pos_concordance")
    inf_notch = st.checkbox("Late notch Inferior Leads?", key="inf_notch")
    low_volt = st.checkbox("Low Voltage Inferior (<1mV)?", key="low_volt")

# --- D. Quantitative Measurements ---
with st.sidebar.expander("4. Quantitative Measurements", expanded=True):
    st.caption("Required for Betensky, Yoshida, Ouyang, and Yamada branching.")

    tz_options = ["≤V1","V2","V3","V4","V5","≥V6"]
    tz_pvc = st.select_slider("Transition (PVC)", options=tz_options, key="tz_pvc")
    tz_sr  = st.select_slider("Transition (Sinus)", options=tz_options, key="tz_sr")

    qrs_pvc_ms = st.number_input("QRS Duration (ms)", 60, 260, step=5, key="qrs_pvc_ms")
    mdi_value = st.number_input("MDI (Max Deflection Index)", 0.0, 1.0, step=0.01, key="mdi_value")

    st.markdown("---")
    st.caption("Amplitudes (mV)")
    c1, c2 = st.columns(2)
    with c1:
        R_V1_PVC = st.number_input("R in V1", 0.0, 5.0, step=0.1, key="R_V1_PVC")
        S_V1_PVC = st.number_input("S in V1", 0.0, 5.0, step=0.1, key="S_V1_PVC")
        R_V2_PVC = st.number_input("R in V2", 0.0, 5.0, step=0.1, key="R_V2_PVC")
        S_V2_PVC = st.number_input("S in V2", 0.0, 5.0, step=0.1, key="S_V2_PVC")
    with c2:
        R_V3_PVC = st.number_input("R in V3", 0.0, 5.0, step=0.1, key="R_V3_PVC")
        st.markdown("Sinus Rhythm")
        R_V2_SR = st.number_input("R in V2 (SR)", 0.0, 5.0, step=0.1, key="R_V2_SR")
        S_V2_SR = st.number_input("S in V2 (SR)", 0.0, 5.0, step=0.1, key="S_V2_SR")

    st.markdown("---")
    st.caption("R-wave Durations (ms)")
    Rdur_V1_ms = st.number_input("R dur V1", 0, 200, step=5, key="Rdur_V1_ms")
    Rdur_V2_ms = st.number_input("R dur V2", 0, 200, step=5, key="Rdur_V2_ms")


# -----------------------------------------------------------------------------
# 4. ALGORITHM LOGIC (CALCULATIONS)
# -----------------------------------------------------------------------------

# Map transition labels to numbers for logical comparison
tz_map = {"≤V1":1,"V2":2,"V3":3,"V4":4,"V5":5,"≥V6":6}
tzp = tz_map[tz_pvc]
tzs = tz_map[tz_sr]
tz_index = tzp - tzs
later_than_sr = tzp > tzs

# Calculate R/S ratios
rfrac_V1 = pct_r(R_V1_PVC, S_V1_PVC)
rfrac_V2_PVC = pct_r(R_V2_PVC, S_V2_PVC)
rfrac_V2_SR  = pct_r(R_V2_SR,  S_V2_SR)

# 1. Betensky Metric: Ratio of R-wave percentages in V2 (PVC vs SR)
v2_transition_ratio = safe_ratio(rfrac_V2_PVC, rfrac_V2_SR)

# 2. Yoshida Metric: S(V2) / R(V3)
v2s_v3r = safe_ratio(S_V2_PVC, R_V3_PVC)

# 3. Ouyang Metrics: R-wave duration index and Amplitude index
Rdur_idx = safe_ratio(max(Rdur_V1_ms, Rdur_V2_ms), qrs_pvc_ms)
Rfrac_idx = max(rfrac_V1, rfrac_V2_PVC)

# 4. Yamada Auto-Branching Logic
# This automates the RVOT vs LVOT decision node in the Yamada tree.
# Priority: Yoshida Index > Transition Zone
yamada_branch_reason = ""
if not math.isnan(v2s_v3r):
    # Using Yoshida Index
    if v2s_v3r > 1.5:
        yamada_auto_hint = "Favors RVOT"
        yamada_branch_reason = f"Used V2S/V3R Index ({v2s_v3r:.2f} > 1.5)"
    else:
        yamada_auto_hint = "Favors LVOT"
        yamada_branch_reason = f"Used V2S/V3R Index ({v2s_v3r:.2f} <= 1.5)"
else:
    # Fallback to Transition Zone if amplitudes are missing
    if tzp >= 4: # >= V4
        yamada_auto_hint = "Favors RVOT"
        yamada_branch_reason = f"Used Transition Zone ({tz_pvc} >= V4)"
    else:
        yamada_auto_hint = "Favors LVOT"
        yamada_branch_reason = f"Used Transition Zone ({tz_pvc} < V4)"

# -----------------------------------------------------------------------------
# 5. ALGORITHM LOGIC (DECISION TREES)
# -----------------------------------------------------------------------------

def solve_enriquez(axis, bbb, lead_I, aVL, transition_val, v6_ratio, inferior_pattern):
    # Logic based on Enriquez et al. 2019 Figure 3
    
    if axis == "Inferior (Positive II & III)":
        if lead_I == "Positive": # Rightward from midline
            if aVL == "Negative (QS)":
                if transition_val >= 4:
                    return "Posterior RVOT"
                elif transition_val == 3:
                    return "Posterior RVOT or RCC"
                else: 
                    return "RCC"
            else: # Any R or r in aVL
                if transition_val >= 4:
                    return "TV free wall"
                else:
                    return "TV septum, Parahisian"
        
        else: # Lead I Negative (Leftward from midline)
            if transition_val >= 3:
                return "Anterior RVOT"
            elif transition_val == 2:
                return "LCC (notched V1), LV summit (pseudo-delta)"
            else:
                return "LCC, LV summit, AMC, Top MV, APM, or LAF"

    elif axis == "Superior (Negative II & III)":
        if bbb == "LBBB": 
            if transition_val >= 4:
                return "TV free wall, MB"
            else: 
                return "TV septum, Crux (QS inferior, pseudo-delta)"
        else: # RBBB
            if v6_ratio == "> 1":
                return "Inferior MV"
            else: 
                return "PPM, LPF"
    else: 
        return "Lateral TV/MB/Parahisian (Pos II/Neg III) OR Lateral MV/APM (Neg II/Pos III)"

def solve_yamada(bbb, inf_pat, aVR, aVL, auto_hint, mdi, v6_r, qrsd, axis, v6_rat, notch, v1_morph, low_volt, pos_conc):
    # Logic based on Yamada et al. 2019 Figure 13
    
    # Tree A: LBBB
    if bbb == "LBBB":
        if inf_pat == "R or r wave in all":
            is_avl_qs_rs = (aVL == "Negative (QS)" or aVL == "rS Pattern")
            if aVR == "QS" and is_avl_qs_rs:
                # The branching decision is automated here
                if auto_hint == "Favors RVOT":
                    return "RVOT, PA"
                else:
                    return "ASV, L-RCC, AMC, LV Summit"
            else:
                return "PB, SB, Sept-PM, HB, NSV, RSV"
        else:
            is_inf_qs = (inf_pat == "QS in all")
            if is_inf_qs and mdi > 0.55:
                 return "Crux"
            else:
                if not v6_r: 
                    return "Ant-PM, Post-PM, MB"
                else:
                    return "TA-FW, SB, PB, HB, NSV, LV Sept"

    # Tree B: RBBB
    else:
        is_inf_qs = (inf_pat == "QS in all")
        if is_inf_qs and mdi > 0.55:
            return "Crux"
        
        if axis == "Superior (Negative II & III)":
            if v6_rat == "<= 1":
                if qrsd > 160 and v1_morph == "qR or R":
                    return "PPM"
                else:
                    return "LPF"
            else: # R/S > 1
                if notch: 
                    return "Post-MA"
                else:
                    return "LV Sept, PS-MA"
        
        else: # Inferior Axis
            if aVR == "QS":
                return "LSV, AMC, LV Summit"
            else:
                if aVL == "rS Pattern": 
                     if pos_conc:
                         return "Ant-, Lat-MA"
                     else:
                         if v6_rat == "<= 1":
                             return "APM"
                         else:
                             return "LAF"
                else: 
                    if low_volt: 
                        return "Ant-, Lat-MA"
                    else:
                        return "LSV, AMC, LV Summit"

# -----------------------------------------------------------------------------
# 6. MAIN DISPLAY
# -----------------------------------------------------------------------------

st.title("Unified PVC Localization Tool")
st.markdown("""
This tool aggregates 5 algorithms to predict the site of origin (SOO) of idiopathic PVCs.
It combines quantitative indices (for Outflow Tract differentiation) and decision trees (for anatomical mapping).
""")

# --- Tab Structure ---
tab1, tab2, tab3 = st.tabs(["Quantitative Indices (OT Focus)", "Decision Trees (Site Prediction)", "Summary Table"])

# --- TAB 1: Quantitative ---
with tab1:
    st.header("Quantitative Algorithms (RVOT vs LVOT)")
    c1, c2, c3 = st.columns(3)
    
    # Yoshida
    with c1:
        st.subheader("1. Yoshida 2014")
        st.caption("Criterion: V2S/V3R Index")
        val_y = fmt(v2s_v3r)
        st.metric("V2S/V3R Index", val_y)
        
        if math.isnan(v2s_v3r):
            st.info("Input V2(S) and V3(R)")
        else:
            if v2s_v3r <= 1.5:
                st.success("≤ 1.5 → LVOT")
            else:
                st.warning("> 1.5 → RVOT")
        
        with st.expander("Calculation Details"):
            st.write(f"S in V2: {fmt(S_V2_PVC)} mV")
            st.write(f"R in V3: {fmt(R_V3_PVC)} mV")
            st.write(f"Index = {fmt(S_V2_PVC)} / {fmt(R_V3_PVC)}")

    # Betensky
    with c2:
        st.subheader("2. Betensky 2011")
        st.caption("Criterion: V2 Transition Ratio")
        st.metric("V2 Trans Ratio", fmt(v2_transition_ratio))
        
        if later_than_sr:
            st.warning("Transition Later than SR → RVOT (Excludes LVOT)")
        elif not math.isnan(v2_transition_ratio):
            if v2_transition_ratio >= 0.60:
                st.success("Ratio ≥ 0.60 → LVOT")
            else:
                st.warning("Ratio < 0.60 → RVOT")
        else:
            st.info("Input V2 R/S for PVC & SR")
            
        with st.expander("Calculation Details"):
            st.write(f"PVC Trans: {tz_pvc}, SR Trans: {tz_sr}")
            st.write(f"PVC R/(R+S): {fmt(rfrac_V2_PVC)}")
            st.write(f"SR R/(R+S): {fmt(rfrac_V2_SR)}")
            if later_than_sr:
                st.write("Result: Excluded (Later than SR)")
            else:
                st.write(f"Ratio = {fmt(rfrac_V2_PVC)} / {fmt(rfrac_V2_SR)}")

    # Ouyang
    with c3:
        st.subheader("3. Ouyang 2002")
        st.caption("Criteria: ASC Indices")
        st.write(f"R-Dur Index: {fmt(Rdur_idx)}")
        st.write(f"Amp Index: {fmt(Rfrac_idx)}")
        
        if not math.isnan(Rdur_idx) and not math.isnan(Rfrac_idx):
            if (Rdur_idx >= 0.50) and (Rfrac_idx >= 0.30):
                st.success("LVOT (ASC) Likely")
            else:
                st.info("Does not meet ASC criteria")
        else:
            st.info("Input durations and amplitudes")
            
        with st.expander("Calculation Details"):
            st.markdown("**R-Duration Index**")
            st.write(f"Max R-Dur (V1, V2): {max(Rdur_V1_ms, Rdur_V2_ms)} ms")
            st.write(f"QRS Duration: {qrs_pvc_ms} ms")
            st.markdown("**Amplitude Index**")
            st.write(f"V1 R/(R+S): {fmt(rfrac_V1)}")
            st.write(f"V2 R/(R+S): {fmt(rfrac_V2_PVC)}")
            st.write(f"Max Amp Ratio: {fmt(Rfrac_idx)}")

# --- TAB 2: Decision Trees ---
with tab2:
    st.header("Anatomical Decision Trees")
    
    col_tree1, col_tree2 = st.columns(2)
    
    # Enriquez
    with col_tree1:
        st.subheader("4. Enriquez et al. (2019)")
        res_enriquez = solve_enriquez(axis, bbb, lead1, avl_morph, tzp, v6_ratio_cat, inf_pattern)
        st.info(f"Prediction: {res_enriquez}")
        with st.expander("Logic Path"):
            st.write(f"- Axis: {axis}")
            st.write(f"- Lead I: {lead1}")
            st.write(f"- Transition: {tz_pvc} (Level {tzp})")
            st.write(f"- aVL: {avl_morph}")
            st.write(f"- V6 R/S: {v6_ratio_cat}")
            st.write(f"- BBB: {bbb}")
    
    # Yamada
    with col_tree2:
        st.subheader("5. Yamada et al. (2019)")
        # Calculate result
        res_yamada = solve_yamada(
            bbb, inf_pattern, avr_morph, avl_morph, yamada_auto_hint, 
            mdi_value, v6_r_present, qrs_pvc_ms, axis, 
            v6_ratio_cat, inf_notch, v1_morph_cat, low_volt, pos_concordance
        )
        st.success(f"Prediction: {res_yamada}")
        
        with st.expander("Logic Path & Automation"):
            st.write("This algorithm automatically used the calculated Quantitative Indices to decide between RVOT and LVOT branches if applicable.")
            st.write(f"- Branch Decision: {yamada_auto_hint}")
            st.write(f"- Reason: {yamada_branch_reason}")
            st.write(f"- MDI: {mdi_value}")
            st.write(f"- Inferior Pattern: {inf_pattern}")
            st.write(f"- aVL: {avl_morph}")
            st.write(f"- aVR: {avr_morph}")

# --- TAB 3: Summary Table ---
with tab3:
    st.subheader("Consolidated Results")
    
    # Prepare data strings
    yoshida_res = "Insufficient Data" if math.isnan(v2s_v3r) else ("LVOT (≤1.5)" if v2s_v3r <= 1.5 else "RVOT (>1.5)")
    
    betensky_res = "Insufficient Data"
    if later_than_sr:
        betensky_res = "RVOT (Transition > SR)"
    elif not math.isnan(v2_transition_ratio):
        betensky_res = "LVOT (≥0.6)" if v2_transition_ratio >= 0.6 else "RVOT (<0.6)"
        
    ouyang_res = "Insufficient Data"
    if not math.isnan(Rdur_idx) and not math.isnan(Rfrac_idx):
        ouyang_res = "LVOT (ASC)" if (Rdur_idx >= 0.50 and Rfrac_idx >= 0.30) else "Not ASC"

    data = [
        ["Yoshida (2014)", f"V2S/V3R: {fmt(v2s_v3r)}", yoshida_res],
        ["Betensky (2011)", f"Ratio: {fmt(v2_transition_ratio)}", betensky_res],
        ["Ouyang (2002)", f"R-Dur Idx: {fmt(Rdur_idx)}", ouyang_res],
        ["Enriquez (2019)", "Decision Tree", res_enriquez],
        ["Yamada (2019)", "Decision Tree", res_yamada]
    ]
    
    df = pd.DataFrame(data, columns=["Algorithm", "Metrics", "Prediction"])
    st.table(df)
    
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("Download Summary CSV", csv, "pvc_soo_summary.csv", "text/csv")