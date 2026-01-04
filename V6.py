# soo_app_v5_patched.py
# Unified-input PVC SOO tool (Streamlit)
# Refactored: added calculation/interpretation separation, Betensky V3 applicability gating,
# measurement help text, st.metric panel, and JSON export.
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
    "tmax_defl_ms": 0,
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

TRANSITION_O_
