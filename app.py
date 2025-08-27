import pandas as pd
import streamlit as st
from rapidfuzz import fuzz
import os
import sys
import re
from streamlit_javascript import st_javascript

# ---------------- CONFIGURAZIONE ----------------
st.set_page_config(page_title="Ricerca Ricambi", layout="wide")

# ---------------- FUNZIONI ----------------
def get_path(filename):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, filename)
    return os.path.join(os.path.abspath("."), filename)

@st.cache_data
def load_data():
    try:
        excel_path = get_path("Ubicazione ricambi.xlsx")
        return pd.read_excel(excel_path)
    except Exception as e:
        st.error(f"Errore caricamento dati: {e}")
        return pd.DataFrame()

def filter_contains_all_words(df, column, query):
    words = query.lower().split()
    mask = pd.Series(True, index=df.index)
    for w in words:
        mask &= df[column].astype(str).str.lower().str.contains(w, na=False)
    return df[mask]

def fuzzy_search_balanced(df, column, query, threshold=70):
    subset = filter_contains_all_words(df, column, query)
    if not subset.empty:
        mask = subset[column].astype(str).apply(
            lambda x: fuzz.partial_ratio(query.lower(), x.lower()) >= threshold
        )
        return subset[mask]
    else:
        mask = df[column].astype(str).apply(
            lambda x: fuzz.partial_ratio(query.lower(), x.lower()) >= threshold
        )
        return df[mask]

def evidenzia_testo(testo, keyword):
    if not keyword:
        return testo
    pattern = re.compile(rf"({re.escape(keyword)})", re.IGNORECASE)
    return pattern.sub(r"<mark>\1</mark>", testo)

# ---------------- CSS ----------------
st.markdown("""
    <style>
    body, .stApp { font-family: 'Segoe UI', sans-serif; }
    .block-container { padding-top: 1rem; padding-bottom: 1rem; }
    .card {
        background-color: #ffffff;
        border-radius: 12px;
        padding: 15px;
        margin-bottom: 14px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        border-left: 5px solid #007bff;
    }
    .card h4 { margin: 0 0 8px; font-size: 18px; color: #007bff; }
    .card p { margin: 4px 0; font-size: 14px; color: #333; }
    mark { background-color: #ffeb3b; padding: 2px 4px; border-radius: 3px; }
    .fab {
        position: fixed; bottom: 20px; left: 20px;
        background-color: #007bff; color: white;
        border-radius: 50%; width: 50px; height: 50px;
        text-align: center; font-size: 24px; cursor: pointer;
        line-height: 50px; box-shadow: 0 2px 8px rgba(0,0,0,0.3);
        z-index: 100;
    }
    .popup-overlay {
        position: fixed; top: 0; left: 0; width: 100%; height: 100%;
        background: rgba(0,0,0,0.5); z-index: 200; display: flex;
        justify-content: center; align-items: center;
    }
    .popup {
        background: white; padding: 20px; border-radius: 10px;
        width: 90%; max-width: 400px; box-shadow: 0 4px 10px rgba(0,0,0,0.3);
    }
    </style>
""", unsafe_allow_html=True)

# ---------------- CARICA DATI ----------------
df = load_data()
if df.empty:
    st.stop()

df.columns = df.columns.str.strip().str.title()

# ---------------- SESSION STATE ----------------
for key, default in {"codice": "", "descrizione": "", "ubicazione": "", "categoria": "Tutte", "show_popup": False}.items():
    st.session_state.setdefault(key, default)

def reset_filtri():
    st.session_state.update({
        "codice": "",
        "descrizione": "",
        "ubicazione": "",
        "categoria": "Tutte"
    })

# ---------------- DETECT MOBILE ----------------
screen_width = st_javascript("window.innerWidth")
is_mobile = False
if screen_width is not None and screen_width < 768:
    is_mobile = True

# ---------------- UI ----------------
st.title("🔍 Ricerca Ricambi in Magazzino")

if is_mobile:
    st.info("📱 Modalità Mobile attiva")

    # Floating button Streamlit per aprire popup
    if st.button("🔧", key="fab_open", help="Apri filtri"):
        st.session_state.show_popup = True

    # Mostra popup se attivo
    if st.session_state.show_popup:
        st.markdown('<div class="popup-overlay">', unsafe_allow_html=True)
        with st.container():
            st.markdown('<div class="popup">', unsafe_allow_html=True)
            st.subheader("📌 Filtri")
            st.text_input("🔢 Codice", placeholder="Inserisci codice...", key="codice")
            st.text_input("📄 Descrizione", placeholder="Inserisci descrizione...", key="descrizione")
            st.text_input("📍 Ubicazione", placeholder="Inserisci ubicazione...", key="ubicazione")
            categorie_uniche = ["Tutte"] + sorted(df["Categoria"].dropna().unique().tolist())
            st.selectbox("🛠️ Categoria", categorie_uniche, key="categoria")
            st.button("🔄 Reset filtri", on_click=reset_filtri)
            if st.button("Chiudi"):
                st.session_state.show_popup = False
            st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
else:
    with st.sidebar:
        st.header("📌 Filtri ricerca")
        st.text_input("🔢 Codice", placeholder="Inserisci codice...", key="codice")
        st.text_input("📄 Descrizione", placeholder="Inserisci descrizione...", key="descrizione")
        st.text_input("📍 Ubicazione", placeholder="Inserisci ubicazione...", key="ubicazione")
        categorie_uniche = ["Tutte"] + sorted(df["Categoria"].dropna().unique().tolist())
        st.selectbox("🛠️ Categoria", categorie_uniche, key="categoria")
        st.button("🔄 Reset filtri", on_click=reset_filtri)

# ---------------- FILTRAGGIO ----------------
filtro = df.copy()
if st.session_state.codice:
    filtro["Codice_str"] = filtro["Codice"].astype(str).str.strip()
    filtro = filtro[filtro["Codice_str"].str.contains(st.session_state.codice.strip(), case=False, na=False)]
if st.session_state.descrizione:
    filtro = fuzzy_search_balanced(filtro, "Descrizione", st.session_state.descrizione.strip(), threshold=70)
if st.session_state.ubicazione:
    filtro = filtro[filtro["Ubicazione"].astype(str).str.contains(st.session_state.ubicazione.strip(), case=False, na=False)]
if st.session_state.categoria != "Tutte":
    filtro = filtro[filtro["Categoria"].astype(str).str.lower() == st.session_state.categoria.lower()]

# ---------------- RISULTATI ----------------
st.markdown(f"### 📦 {len(filtro)} risultato(i) trovati")

if not filtro.empty and not is_mobile:
    st.download_button("📥 Scarica tutti i risultati (CSV)", filtro.to_csv(index=False), "risultati.csv", "text/csv")

# ---------------- VISUALIZZAZIONE ----------------
if is_mobile:
    keyword = st.session_state.descrizione
    for _, row in filtro.iterrows():
        descrizione = evidenzia_testo(str(row['Descrizione']), keyword)
        st.markdown(f"""
            <div class="card">
                <h4>🔢 {row['Codice']}</h4>
                <p><strong>📄 Descrizione:</strong> {descrizione}</p>
                <p><strong>📍 Ubicazione:</strong> {row['Ubicazione']}</p>
                <p><strong>🛠️ Categoria:</strong> {row['Categoria']}</p>
            </div>
        """, unsafe_allow_html=True)
else:
    st.dataframe(filtro[["Codice", "Descrizione", "Ubicazione", "Categoria"]],
                 use_container_width=True, height=450)
