"""Interface Streamlit : streamlit run src/tenderpilot/app.py"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from tenderpilot.graph import analyze, load_capabilities
from tenderpilot.llm import LLMClient

ROOT = Path(__file__).resolve().parents[2]
STATUS_ICON = {"couvert": "🟢 couvert", "partiel": "🟠 partiel", "non couvert": "🔴 non couvert"}

st.set_page_config(page_title="TenderPilot", layout="wide")
st.title("TenderPilot")
st.caption("Système multi-agents d'analyse d'appels d'offres : extraction, conformité, rédaction et relecture.")

with st.sidebar:
    st.header("Données")
    uploaded = st.file_uploader("Cahier des charges (.md, .txt)", type=["md", "txt"])
    caps_file = st.file_uploader("Capacités de l'entreprise (.yaml)", type=["yaml", "yml"])
    llm = LLMClient.from_env()
    st.info(f"Mode : {'LLM ' + llm.provider if llm else 'règles (sans clé API)'}")

document = uploaded.read().decode("utf-8") if uploaded else (ROOT / "data/dce_gestion_dechets.md").read_text(encoding="utf-8")
if caps_file:
    tmp = ROOT / ".caps_upload.yaml"
    tmp.write_bytes(caps_file.read())
    capabilities = load_capabilities(tmp)
else:
    capabilities = load_capabilities(ROOT / "data/capacites_entreprise.yaml")

if st.button("Lancer l'analyse", type="primary") or "result" in st.session_state:
    if "result" not in st.session_state or st.session_state.get("doc") != document:
        with st.spinner("Les agents analysent le dossier…"):
            st.session_state.result = analyze(document, capabilities, llm)
            st.session_state.doc = document
    result = st.session_state.result
    statuses = [m.status for m in result.matches]

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Exigences", len(result.requirements))
    c2.metric("Couvertes", statuses.count("couvert"))
    c3.metric("Partielles", statuses.count("partiel"))
    c4.metric("Non couvertes", statuses.count("non couvert"))
    c5.metric("Conformité", f"{result.review.compliance_score:.0%}")

    if result.review.decision == "prêt à soumettre":
        st.success("Relecture : prêt à soumettre")
    else:
        st.warning(f"Relecture : validation humaine requise ({len(result.review.issues)} points à arbitrer)")

    tab_matrix, tab_draft, tab_trace = st.tabs(["Matrice de conformité", "Brouillon de réponse", "Trace des agents"])
    with tab_matrix:
        reqs = {r.id: r for r in result.requirements}
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "ID": m.requirement_id,
                        "Catégorie": reqs[m.requirement_id].category,
                        "Exigence": reqs[m.requirement_id].text,
                        "Statut": STATUS_ICON[m.status],
                        "Capacité": ", ".join(m.capability_ids),
                        "Justification": m.justification,
                    }
                    for m in result.matches
                ]
            ),
            hide_index=True,
            width="stretch",
        )
    with tab_draft:
        st.markdown(result.draft)
        st.download_button("Télécharger le brouillon (.md)", result.draft, file_name="memoire_technique.md")
    with tab_trace:
        st.dataframe(
            pd.DataFrame(
                [{"Agent": e.agent, "Durée (ms)": e.duration_ms, "Mode": e.mode, "Résultat": e.summary} for e in result.trace]
            ),
            hide_index=True,
            width="stretch",
        )
        for issue in result.review.issues:
            st.write(f"• **{issue.requirement_id or '–'}** · {issue.kind} : {issue.message}")
