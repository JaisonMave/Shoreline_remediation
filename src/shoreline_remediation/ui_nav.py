"""Page navigation and brand header for the dashboard (V5.1 Session 2 Stage 3; V5.4 shell). No page config here, so tests can import it.

One source of truth: st.session_state["page"] is the key of the navigation widget. The page is mirrored into the URL query
string (?page=...) so a browser reload stays on the same page.
"""
from __future__ import annotations

import streamlit as st

# Visible labels are short so the navigation fits beside the brand; the page ids (and ?page= routing) are unchanged.
PAGES = {"landing": "Map", "site": "Assessment", "evidence": "Evidence", "models": "Models", "legacy": "Research"}
# Full page names, shown in the navigation tooltip (the page headers use them too).
PAGE_TITLES = {"landing": "Home", "site": "Site assessment", "evidence": "Evidence explorer", "models": "Model validation",
               "legacy": "Legacy and research"}
BRAND_NAME = "Shoreline Remediation"
BRAND_TAGLINE = "Scientific decision support for oil spill response"
BRAND_HTML = ('<div class="sr-brand"><svg class="sr-brand-mark" viewBox="0 0 48 48" aria-hidden="true" focusable="false">'
              '<path d="M3 17c5-7 10-7 15 0s10 7 15 0 8-5 12-2" fill="none" stroke="#28B8A5" stroke-width="3.2" stroke-linecap="round"/>'
              '<path d="M3 27c5-7 10-7 15 0s10 7 15 0 8-5 12-2" fill="none" stroke="#4E9BE8" stroke-width="3.2" stroke-linecap="round"/>'
              '<path d="M3 37c5-7 10-7 15 0s10 7 15 0 8-5 12-2" fill="none" stroke="#B6D9CF" stroke-width="3.2" stroke-linecap="round"/>'
              f'</svg><div><div class="sr-brand-name">{BRAND_NAME}</div><div class="sr-brand-tag">{BRAND_TAGLINE}</div></div></div>')
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
    with st.container(key="sr_shell"):
        brand, nav = st.columns([5, 6], vertical_alignment="center", gap="small")
        brand.markdown(BRAND_HTML, unsafe_allow_html=True)
        nav.segmented_control("Navigate", list(PAGES), key=PAGE_KEY, format_func=PAGES.get, required=True,
                              label_visibility="collapsed", wrap=True,
                              help="; ".join(f"{PAGES[k]}: {PAGE_TITLES[k]}" for k in PAGES))
    page = current_page()
    try:
        if st.query_params.get(PAGE_KEY) != page:
            st.query_params[PAGE_KEY] = page
    except Exception:
        pass
    return page
