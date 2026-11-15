"""Page navigation for the dashboard (V5.1 Session 2 Stage 3). No page config here, so tests can import it.

One source of truth: st.session_state["page"] is the key of the navigation widget. The page is mirrored into the URL query
string (?page=...) so a browser reload stays on the same page.
"""
from __future__ import annotations

import streamlit as st

PAGES = {"landing": "Home", "site": "Site assessment", "evidence": "Evidence explorer", "models": "Model validation",
         "legacy": "Legacy and research"}
DEFAULT_PAGE = "landing"
PAGE_KEY = "page"


def go(page: str) -> None:
    """Button callback: switch page. Unknown ids are ignored."""
    if page in PAGES:
        st.session_state[PAGE_KEY] = page


def current_page() -> str:
    """The current page id; an invalid or missing value is replaced by the default."""
    page = st.session_state.get(PAGE_KEY)
    if page not in PAGES:
        page = DEFAULT_PAGE
        st.session_state[PAGE_KEY] = page
    return page


def keep_alive(keys) -> None:
    """Streamlit drops the state of widgets that are not drawn in a run; re-assigning the value keeps it (site selection)."""
    for k in keys:
        if k in st.session_state:
            st.session_state[k] = st.session_state[k]


def render_nav() -> str:
    """Draw the navigation and return the current page id. The first run of a session starts at ?page= when it is valid."""
    if PAGE_KEY not in st.session_state:
        try:
            wanted = st.query_params.get(PAGE_KEY)
        except Exception:
            wanted = None
        st.session_state[PAGE_KEY] = wanted if wanted in PAGES else DEFAULT_PAGE
    current_page()
    st.segmented_control("Navigate", list(PAGES), key=PAGE_KEY, format_func=PAGES.get, required=True,
                         label_visibility="collapsed")
    page = current_page()
    try:
        if st.query_params.get(PAGE_KEY) != page:
            st.query_params[PAGE_KEY] = page
    except Exception:
        pass
    return page
