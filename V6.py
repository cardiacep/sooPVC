import streamlit as st

def main():
    st.set_page_config(page_title="PVC Localization Tool", layout="wide")

    st.title("Idiopathic PVC Site of Origin Localizer")
    st.markdown("""
    This tool predicts the site of origin (SOO) for idiopathic Premature Ventricular Contractions (PVCs) 
    using 12-lead ECG features. It implements two distinct algorithms based on the following literature:
    
    1. Enriquez et al. - Contemporary Review (2019)
    2. Yamada et al. - J Cardiovasc Electrophysiol (2019)
    """)

    # --- Sidebar: ECG Feature Inputs ---
    st.sidebar.header("ECG Features")
    
    # Common Features
    bbb_pattern = st.sidebar.selectbox(
        "Bundle Branch Block Pattern (V1)",
        ("LBBB", "RBBB"),
        help="LBBB: Dominant S in V1. RBBB: Dominant R in V1."
    )

    axis_choice = st.sidebar.selectbox(
        "Frontal Plane Axis (Leads II, III)",
        ("Inferior (Positive II & III)", "Superior (Negative II & III)", "Discordant")
    )

    # Specifics for Enriquez
    st.sidebar.markdown("---")
    st.sidebar.subheader("Lead Morphologies")
    
    lead_I_polarity = st.sidebar.radio(
        "Lead I Polarity",
        ("Positive", "Negative"),
        horizontal=True
    )
    
    lead_aVL_polarity = st.sidebar.selectbox(
        "Lead aVL Morphology",
        ("Negative (QS)", "Positive (Any R or r)", "rS Pattern", "Other")
    )
    
    lead_aVR_morphology = st.sidebar.selectbox(
        "Lead aVR Morphology",
        ("QS", "Other")
    )

    # Specifics for Transition and V6
    st.sidebar.markdown("---")
    st.sidebar.subheader("Precordial Leads")
    
    transition_zone = st.sidebar.selectbox(
        "Precordial Transition Zone (First R > S)",
        ("V1", "V2", "V3", "V4", "V5", "V6", ">V6")
    )

    v6_ratio = st.sidebar.radio(
        "R/S Ratio in V6",
        ("> 1", "<= 1"),
        horizontal=True
    )
    
    v6_r_wave = st.sidebar.checkbox("R wave present in V6?", value=True)
    
    positive_concordance = st.sidebar.checkbox("Positive Concordance (All precordial leads positive)?", value=False)

    # Advanced Inputs for Yamada
    st.sidebar.markdown("---")
    st.sidebar.subheader("Advanced Features (Yamada)")
    
    inferior_leads_pattern = st.sidebar.radio(
        "Inferior Leads (II, III, aVF) Pattern",
        ("R or r wave in all", "QS in all", "Mixed/Other")
    )
    
    mdi_value = st.sidebar.number_input("Maximum Deflection Index (MDI)", min_value=0.0, max_value=1.0, value=0.40, step=0.01)
    qrs_duration = st.sidebar.number_input("QRS Duration (ms)", min_value=0, value=120)
    
    v1_morphology = st.sidebar.selectbox(
        "V1 Morphology Specifics",
        ("qR or R", "Other (rS, QS, etc.)")
    )
    
    inferior_notching = st.sidebar.checkbox("Late notching of Q/S in inferior leads?", value=False)
    
    low_voltage_inferior = st.sidebar.checkbox("R wave amp in II & III < 1 mV?", value=False)
    
    # Logic for RVOT vs LVOT
    st.sidebar.markdown("---")
    rvot_lvot_hint = st.sidebar.selectbox(
        "If LBBB & Inferior Axis: RVOT vs LVOT Index result?",
        ("Favors RVOT (e.g., V2S/V3R > 1.5, Late Trans)", "Favors LVOT (e.g., V2S/V3R <= 1.5, Early Trans)")
    )

    # --- Run Algorithms ---
    
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Algorithm 1: Enriquez et al.")
        result_enriquez = solve_enriquez(
            axis_choice, bbb_pattern, lead_I_polarity, lead_aVL_polarity, 
            transition_zone, v6_ratio, inferior_leads_pattern
        )
        st.success(f"Predicted Site: {result_enriquez}")

    with col2:
        st.subheader("Algorithm 2: Yamada et al.")
        result_yamada = solve_yamada(
            bbb_pattern, inferior_leads_pattern, lead_aVR_morphology, lead_aVL_polarity,
            rvot_lvot_hint, mdi_value, v6_r_wave, transition_zone, qrs_duration, 
            axis_choice, v6_ratio, inferior_notching, v1_morphology, 
            low_voltage_inferior, positive_concordance
        )
        st.success(f"Predicted Site: {result_yamada}")

    # --- Explanations ---
    st.markdown("---")
    st.subheader("Detailed Logic Path Used")
    
    with st.expander("See Logic for Enriquez Algorithm"):
        st.write("The algorithm follows the stepwise approach defined in the paper:")
        st.write(f"1. Axis: {axis_choice}")
        if axis_choice == "Inferior (Positive II & III)":
            st.write(f"2. Lead I: {lead_I_polarity}")
            if lead_I_polarity == "Positive":
                 st.write(f"3. aVL: {lead_aVL_polarity}")
            else:
                 st.write(f"3. Transition: {transition_zone}")
        elif axis_choice == "Superior (Negative II & III)":
            st.write(f"2. BBB Pattern: {bbb_pattern}")
    
    with st.expander("See Logic for Yamada Algorithm"):
        st.write("The algorithm follows the flowcharts in Figure 13 (A & B):")
        st.write(f"1. BBB Pattern: {bbb_pattern}")
        if bbb_pattern == "LBBB":
            st.write(f"2. Inferior Leads: {inferior_leads_pattern}")
        else:
            st.write(f"2. Inferior Leads (QS Check): {inferior_leads_pattern}")
            st.write(f"3. Axis: {axis_choice}")

# --- Algorithm Logic Functions ---

def solve_enriquez(axis, bbb, lead_I, aVL, transition, v6_ratio, inferior_pattern):
    # Logic derived from Enriquez et al.
    
    # 1. Inferior Axis (Positive II and III)
    if axis == "Inferior (Positive II & III)":
        if lead_I == "Positive": # Rightward from midline
            if aVL == "Negative (QS)":
                if transition in [">V6", "V6", "V5", "V4"]:
                    return "Posterior RVOT"
                elif transition == "V3":
                    return "Posterior RVOT or RCC"
                else: # <= V2
                    return "RCC"
            else: # Any R or r in aVL
                if transition in [">V6", "V6", "V5", "V4"]:
                    return "TV free wall"
                else: # <= V3
                    return "TV septum, Parahisian"
        
        else: # Lead I Negative (Leftward from midline)
            if transition in [">V6", "V6", "V5", "V4", "V3"]:
                return "Anterior RVOT"
            elif transition == "V2":
                return "LCC (notched V1), LV summit (pseudo-delta)"
            else: # V1 (RBBB pattern usually)
                return "LCC, LV summit, AMC, Top MV, APM, or LAF"

    # 2. Superior Axis (Negative II and III)
    elif axis == "Superior (Negative II & III)":
        if bbb == "LBBB": # Right Ventricle, Crux
            if transition in [">V6", "V6", "V5", "V4"]:
                return "TV free wall, MB"
            else: # <= V3
                return "TV septum, Crux (QS inferior, pseudo-delta)"
        else: # RBBB (Left Ventricle)
            if v6_ratio == "> 1":
                return "Inferior MV"
            else: # < 1
                return "PPM, LPF"

    # 3. Discordance
    else: # Discordant
        return "Lateral TV/MB/Parahisian (Pos II/Neg III) OR Lateral MV/APM (Neg II/Pos III)"


def solve_yamada(bbb, inf_pat, aVR, aVL, rvot_lvot, mdi, v6_r, trans, qrsd, axis, v6_rat, notch, v1_morph, low_volt, pos_conc):
    # Logic derived from Yamada et al.

    # --- Tree A: LBBB ---
    if bbb == "LBBB":
        # Split 1: R or r in all inferior leads
        if inf_pat == "R or r wave in all":
            # Split 2: aVR=QS, aVL=QS or rS
            is_avl_qs_rs = (aVL == "Negative (QS)" or aVL == "rS Pattern")
            if aVR == "QS" and is_avl_qs_rs:
                # RVOT vs LVOT algorithm
                if "RVOT" in rvot_lvot:
                    return "RVOT, PA"
                else:
                    return "ASV, L-RCC, AMC, LV Summit"
            else:
                return "PB, SB, Sept-PM, HB, NSV, RSV"
        else:
            # Split 3: QS in inferior leads, MDI > 0.55, polarity reversal V1-V3
            is_inf_qs = (inf_pat == "QS in all")
            if is_inf_qs and mdi > 0.55:
                 return "Crux"
            else:
                if not v6_r: # No R wave in V6
                    return "Ant-PM, Post-PM, MB"
                else:
                    return "TA-FW, SB, PB, HB, NSV, LV Sept"

    # --- Tree B: RBBB ---
    else:
        # Split 1: QS in inferior leads, MDI > 0.55
        is_inf_qs = (inf_pat == "QS in all")
        if is_inf_qs and mdi > 0.55:
            return "Crux"
        
        # Split 2: Axis
        if axis == "Superior (Negative II & III)":
            if v6_rat == "<= 1":
                # Check QRSd and V1
                if qrsd > 160 and v1_morph == "qR or R":
                    return "PPM"
                else:
                    return "LPF"
            else: # R/S > 1
                if notch: # Late notching
                    return "Post-MA"
                else:
                    return "LV Sept, PS-MA"
        
        else: # Inferior Axis
            if aVR == "QS":
                return "LSV, AMC, LV Summit"
            else:
                if aVL == "rS Pattern": # Note: Tree says "aVL=rS" -> Yes
                     # Positive concordance check
                     if pos_conc:
                         return "Ant-, Lat-MA"
                     else:
                         if v6_rat == "<= 1":
                             return "APM"
                         else:
                             return "LAF"
                else: # aVL != rS
                    if low_volt: # R amp < 1mV
                        return "Ant-, Lat-MA"
                    else:
                        return "LSV, AMC, LV Summit"

if __name__ == "__main__":
    main()