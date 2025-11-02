import streamlit as st

_CSS = """
<style>
.bubble-wrap { margin: 0.25rem 0; display: flex; }
.bubble-user { margin-left: auto; background: #e9e9eb; color: #111; padding: 8px 12px; border-radius: 16px 16px 2px 16px; max-width: 85%; white-space: pre-wrap; }
.bubble-assistant { margin-right: auto; background: #007aff; color: #fff; padding: 8px 12px; border-radius: 16px 16px 16px 2px; max-width: 85%; white-space: pre-wrap;}
.bubble-system { margin: 0.4rem auto; background: #f5f5f7; color: #555; padding: 6px 10px; border-radius: 8px; font-size: 12px; text-align: center; max-width: 60%; white-space: pre-wrap;}
.bubble-assistant a { color: #fff; text-decoration: underline; }
</style>
"""

_css_done = False

def _css_once():
    global _css_done
    if not _css_done:
        st.markdown(_CSS, unsafe_allow_html=True)
        _css_done = True

def user(text: str):
    _css_once()
    st.markdown(f'<div class="bubble-wrap"><div class="bubble-user">{text}</div></div>', unsafe_allow_html=True)

def assistant(text: str):
    _css_once()
    st.markdown(f'<div class="bubble-wrap"><div class="bubble-assistant">{text}</div></div>', unsafe_allow_html=True)

def system(text: str):
    _css_once()
    st.markdown(f'<div class="bubble-system">{text}</div>', unsafe_allow_html=True)
