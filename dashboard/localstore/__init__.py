# -*- coding: utf-8 -*-
"""Per-visitor persistence in the browser's localStorage.

On Streamlit Cloud the server filesystem is shared by every visitor and wiped
on each redeploy (the daily data commit redeploys), so personal lists must live
in the visitor's own browser. This wraps a tiny dependency-free component
(index.html) and exposes a JSON get/put API backed by st.session_state.
"""
import json
import os

import streamlit as st
import streamlit.components.v1 as components

_component = components.declare_component(
    "stockagent_localstore", path=os.path.dirname(os.path.abspath(__file__)))

_SS = "_ls_cache"


def sync(key: str, default=None):
    """Return the stored JSON value for `key` (from session cache once the
    browser has answered). Must be called once per run before reading."""
    cache = st.session_state.setdefault(_SS, {})
    pending = st.session_state.get(f"_ls_write_{key}")
    res = _component(key=f"ls_{key}", default=None,
                     **({"write": pending} if pending is not None else {}))
    if pending is not None:
        st.session_state.pop(f"_ls_write_{key}", None)
        try:
            cache[key] = json.loads(pending)
        except ValueError:
            pass
    elif isinstance(res, dict) and key not in cache:
        raw = res.get("value")
        try:
            cache[key] = json.loads(raw) if raw else default
        except ValueError:
            cache[key] = default
    return cache.get(key, default)


def ready(key: str) -> bool:
    return key in st.session_state.get(_SS, {})


def put(key: str, value) -> None:
    """Store `value` (JSON-serialisable): updates the session cache now and the
    browser on the next render of sync()."""
    st.session_state.setdefault(_SS, {})[key] = value
    st.session_state[f"_ls_write_{key}"] = json.dumps(value, ensure_ascii=False)
