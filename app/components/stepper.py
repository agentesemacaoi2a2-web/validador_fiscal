import streamlit as st

def render(labels: list[str], done: list[bool]):
    cols = st.columns(len(labels))
    for i, lab in enumerate(labels):
        cols[i].metric(
            lab,
            "✅" if (i < len(done) and done[i]) else "⏳"
        )

def render_etapas(etapas: list[dict]):
    """
    Aceita etapas do pipeline com formato:
    [{"step": "...", "status": "..."}]
    Apenas exibe abaixo dos cards
    """
    st.write("### Etapas do Pipeline")
    for e in etapas:
        status = e.get("status", "")
        nome = e.get("step", "")
        if status.lower() == "ok":
            st.success(f"✔ {nome}")
        else:
            st.warning(f"⚠ {nome} — {status}")
