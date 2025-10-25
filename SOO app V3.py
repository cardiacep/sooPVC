# soo_app.py
# Unified-input PVC SOO tool (Streamlit)
# Sources: Betensky 2011 (V2 transition ratio), Yoshida 2014 (V2S/V3R),
# Ouyang 2002 (R-wave duration & amplitude indices), Yamada 2019 (overview),
# Enriquez 2019 (stepwise anatomic heuristic).

import math
import streamlit as st

st.set_page_config(page_title="PVC SOO (Unified Inputs)", layout="wide")

# ---------------------------
# Helpers
# ---------------------------
def safe_ratio(n, d):
    try:
        return float(n) / float(d) if float(d) != 0 else math.nan
    except Exception:
        return math.nan

def pct_r(R, S):
    """R fraction as R/(R+S). Used by Betensky and Ouyang amplitude index."""
    return safe_ratio(R, (R + S)) if (R is not None and S is not None) else math.nan

def fmt(x, nd=3):
    return "—" if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))) else f"{x:.{nd}f}"

# ---------------------------
# Sidebar: unified inputs
# ---------------------------
st.sidebar.title("Unified ECG Inputs")
st.sidebar.caption("All algorithms reuse these values. Units: mV (amplitude), ms (time).")

# Morphology & general features (shared by Enriquez/Yamada)
bbb = st.sidebar.selectbox("PVC morphology in V1", ["LBBB", "RBBB"], index=0, help="V1 pattern during PVC.")
axis = st.sidebar.selectbox("Frontal axis (PVC)", ["Inferior", "Superior", "Indeterminate"], index=0)
lead1 = st.sidebar.selectbox("Lead I QRS polarity (PVC)", ["Positive", "Negative", "Isoelectric"], index=0)
tz_pvc = st.sidebar.selectbox("Precordial transition lead (PVC)", ["≤V1","V2","V3","V4","V5","≥V6"], index=2)
tz_sr  = st.sidebar.selectbox("Precordial transition lead (Sinus Rhythm)", ["≤V1","V2","V3","V4","V5","≥V6"], index=3)
qrs_pvc_ms = st.sidebar.number_input("QRS duration (PVC, ms)", min_value=60, max_value=260, value=140, step=1)

st.sidebar.markdown("---")
st.sidebar.subheader("Lead V1 amplitudes (PVC)")
R_V1_PVC = st.sidebar.number_input("R in V1 (mV)", min_value=0.0, value=0.2, step=0.1, format="%.3f")
S_V1_PVC = st.sidebar.number_input("S in V1 (mV)", min_value=0.0, value=1.2, step=0.1, format="%.3f")
st.sidebar.subheader("Lead V2 amplitudes (PVC & SR)")
R_V2_PVC = st.sidebar.number_input("R in V2 (PVC, mV)", min_value=0.0, value=0.3, step=0.1, format="%.3f")
S_V2_PVC = st.sidebar.number_input("S in V2 (PVC, mV)", min_value=0.0, value=1.5, step=0.1, format="%.3f")
R_V2_SR  = st.sidebar.number_input("R in V2 (SR, mV)",  min_value=0.0, value=0.6, step=0.1, format="%.3f")
S_V2_SR  = st.sidebar.number_input("S in V2 (SR, mV)",  min_value=0.0, value=1.8, step=0.1, format="%.3f")
st.sidebar.subheader("Lead V3 amplitude (PVC)")
R_V3_PVC = st.sidebar.number_input("R in V3 (PVC, mV)", min_value=0.0, value=0.5, step=0.1, format="%.3f")

st.sidebar.markdown("---")
st.sidebar.subheader("R-wave durations (PVC)")
Rdur_V1_ms = st.sidebar.number_input("R duration V1 (ms)", min_value=0, max_value=260, value=45, step=1)
Rdur_V2_ms = st.sidebar.number_input("R duration V2 (ms)", min_value=0, max_value=260, value=55, step=1)

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
    else:
        # ≤1.5 → LVOT; >1.5 → RVOT
        if v2s_v3r <= 1.5:
            st.success("≤1.5 → favors **LVOT** origin.")
        else:
            st.warning(">1.5 → favors **RVOT** origin.")

    st.caption("Yoshida N et al., J Cardiovasc Electrophysiol. 2014;25:747–753. doi:10.1111/jce.12392.")

    st.subheader("Betensky 2011 — V2 transition ratio")
    st.write(f"V2 transition ratio = {fmt(v2_transition_ratio)}")
    st.write(f"PVC transition vs SR: {'Later than SR' if later_than_sr else 'Not later than SR or equal'} "
             f"(TZ index = {tz_index:+d})")
    notes = []
    if later_than_sr:
        notes.append("PVC transition later than SR **excludes LVOT** in the original report.")
    if not math.isnan(v2_transition_ratio):
        notes.append("Cutoff ≥0.60 → predicts **LVOT** (with V3 transition context).")
    st.info("\n".join(notes) if notes else "Provide V2 (PVC & SR) amplitudes.")
    st.caption("Betensky BP et al., J Am Coll Cardiol. 2011;57:2255–2262. doi:10.1016/j.jacc.2011.01.035.")

with colB:
    st.subheader("Ouyang 2002 — Aortic sinus cusp indices")
    st.write(f"R-wave duration index = max(RdurV1,V2)/QRS = {fmt(Rdur_idx)}")
    st.write(f"R/(R+S) amplitude index (best of V1 or V2) = {fmt(Rfrac_idx)}")
    if not math.isnan(Rdur_idx) and not math.isnan(Rfrac_idx):
        if (Rdur_idx >= 0.50) and (Rfrac_idx >= 0.30):
            st.success("≥0.50 and ≥0.30 → suggests **LVOT (aortic sinus cusp)** origin.")
        else:
            st.warning("Below at least one cutoff → does **not** meet classic ASC criteria.")
    else:
        st.info("Enter QRS (PVC), R-durations (V1,V2), and V1/V2 amplitudes.")
    st.caption("Ouyang F et al., J Am Coll Cardiol. 2002;39:500–508.")

st.markdown("---")
colC, colD = st.columns(2)

with colC:
    st.subheader("Yamada 2019 — heuristic summary")
    # Very concise rule-of-thumbs tied to shared inputs
    bullets = []
    if bbb == "LBBB":
        bullets.append("LBBB in V1 → **RV or septum** more likely; with inferior axis and OT pattern, think RVOT/LVOT.")
        if tzp <= 2:
            bullets.append("Early transition (≤V2) → favors **LVOT/anterior**.")
        elif tzp >= 4:
            bullets.append("Late transition (≥V4) → favors **RVOT/free wall**.")
    else:
        bullets.append("RBBB in V1 → **LV origin** more likely.")
        if lead1 == "Negative":
            bullets.append("Negative lead I → **LV free wall/epicardial** features.")
    st.write("\n\n".join(bullets) if bullets else "Provide morphology, axis, and transition.")
    st.caption("Yamada T., J Cardiovasc Electrophysiol. 2019;30:2603–2617.")

with colD:
    st.subheader("Enriquez 2019 — stepwise anatomic heuristic")
    # Simple, transparent branch using shared inputs
    enq = []
    if bbb == "LBBB" and axis == "Inferior":
        if tzp <= 2:
            enq.append("LBBB + inferior axis + early transition → **LVOT** more likely.")
        elif tzp >= 4:
            enq.append("LBBB + inferior axis + late transition → **RVOT** more likely.")
        else:
            enq.append("Borderline transition (V3) → check Betensky/Yoshida indices.")
    elif bbb == "RBBB":
        if lead1 == "Negative":
            enq.append("RBBB + negative lead I → **LV free wall/epicardial** suspicion.")
        else:
            enq.append("RBBB + nonnegative lead I → **LV septal/papillary/annular** possibilities.")
    else:
        enq.append("Use BBB pattern, axis, lead I, and transition together for an anatomic guess.")
    st.write("\n\n".join(enq))
    st.caption("Enriquez A. et al., Heart Rhythm. 2019;16:1538–1544.")

st.markdown("---")
st.subheader("What’s reused where (so you only enter once)")
st.markdown(
    "- **S(V2) (PVC)** → Yoshida 2014 & Betensky 2011 & Ouyang amplitude index\n"
    "- **R(V3) (PVC)** → Yoshida 2014\n"
    "- **R/S in V2 (PVC & SR)** → Betensky 2011 (V2 transition ratio)\n"
    "- **R/S in V1–V2 (PVC)** → Ouyang amplitude index\n"
    "- **R-durations V1–V2 (PVC)** + **QRS (PVC)** → Ouyang duration index\n"
    "- **BBB, axis, lead I polarity, transition (PVC & SR)** → Enriquez 2019 & Yamada 2019 & Betensky rule"
)

st.caption("This app provides decision support only and does not replace clinical judgment or invasive mapping.")
