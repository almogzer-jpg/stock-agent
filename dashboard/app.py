# -*- coding: utf-8 -*-
"""Stock Agent Pro: the Streamlit entry point.

The interface is V4 (dashboard/v4). It reads the precomputed artifacts the daily bot
writes to data/ (run.py, scanner.py), and the live engine's verdicts (verdict.py via
stockdata). The four-dimension engine runs in shadow mode only and is never read here.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st  # noqa: E402

st.set_page_config(page_title="Stock Agent Pro", page_icon="📈", layout="wide",
                   initial_sidebar_state="expanded")

from dashboard.v4 import shell  # noqa: E402

shell.main()
