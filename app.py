import pandas as pd
import streamlit as st
from rapidfuzz import fuzz
import os
import sys
from streamlit_javascript import st_javascript

# ---------------- CONFIGURAZIONE PAGINA ----------------
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

# ---------------- CSS MODERNO ----------------
st.markdown("""
    <style>
    body, .stApp {
        font-family: 'Segoe UI', sans-serif;
    }
    .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
    }
    /* Card Style */
    .card {
        background-color: #f8f9fa;
        border-radius: 12px;
        padding: 15px;
        margin-bottom: 10px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }
    .card h4 {
        margin: 0;
        font-size: 18px;
        color: #333;
    }
    .card p {
        margin: 5px 0;
        font-size: 14px;
        color: #555;
    }
    /* Sticky sidebar on mobile */
    @media (max-width: 768px) {
        .sidebar .block-container {
            position: sticky;
            top: 0;
            background-color: white;
            z-index: 10;
        }
    }
    </style>
""", unsafe_allow_html=True)

# ---------------- CARICA DATI ----------------
df = load_data()
if df.empty:
    st.stop()

df.columns = df.columns.str.strip().str.title()

# ---------------- INIZIALIZZAZIONE SESSION_STATE ----------------
st.session_state.setdefault("codice", "")
st.session_state.setdefault("descrizione", "")
st.session_state.setdefault("ubicazione", "")
st.session_state.setdefault("categoria", "Tutte")

# ---------------- FUNZIONE RESET ----------------
def reset_filtri():
    st.session_state.codice = ""
    st.session_state.descrizione = ""
    st.session_state.ubicazione = ""
    st.session_state.categoria = "Tutte"

# ---------------- INTERFACCIA ----------------
st.title("🔍 Ricerca Ricambi in Magazzino")

with st.sidebar:
    st.header("📌 Filtri ricerca")
    codice_input = st.text_input("🔢 Codice", placeholder="Inserisci codice...", key="codice")
    descrizione_input = st.text_input("📄 Descrizione", placeholder="Inserisci descrizione...", key="descrizione")
    posizione_input = st.text_input("📍 Ubicazione", placeholder="Inserisci ubicazione...", key="ubicazione")
    categorie_uniche = ["Tutte"] + sorted(df["Categoria"].dropna().unique().tolist())
    macchinario_input = st.selectbox("🛠️ Categoria", categorie_uniche, key="categoria")

    # Pulsante reset con on_click
    st.button("🔄 Reset filtri", on_click=reset_filtri)

# ---------------- RILEVA MOBILE AUTOMATICAMENTE ----------------
screen_width = st_javascript("window.innerWidth")
is_mobile = screen_width is not None and screen_width < 768

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

# Download CSV solo su DESKTOP
if not filtro.empty and not is_mobile:
    st.download_button("📥 Scarica tutti i risultati (CSV)", filtro.to_csv(index=False), "risultati.csv", "text/csv")

# ---------------- VISUALIZZAZIONE ----------------
if is_mobile:
    st.info("📱 Visualizzazione Mobile attiva")
    # Mostra tutte le card senza paginazione
    for _, row in filtro.iterrows():
        st.markdown(f"""
            <div class="card">
                <h4>{row['Codice']}</h4>
                <p><strong>Descrizione:</strong> {row['Descrizione']}</p>
                <p><strong>📍 Ubicazione:</strong> {row['Ubicazione']}</p>
                <p><strong>🛠️ Categoria:</strong> {row['Categoria']}</p>
            </div>
        """, unsafe_allow_html=True)

else:
    st.dataframe(filtro[["Codice", "Descrizione", "Ubicazione", "Categoria"]],
                 use_container_width=True, height=450)


