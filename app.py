import pandas as pd
import streamlit as st
from rapidfuzz import fuzz
import os
import sys

# Configura pagina Streamlit
st.set_page_config(page_title="Ricerca Ricambi", layout="wide")

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

# Funzione per rilevare se mobile (via JS)
def detect_device():
    st.markdown("""
        <script>
        const width = window.innerWidth;
        const isMobile = width < 768;
        window.parent.postMessage({type: 'streamlit:setComponentValue', value: isMobile}, '*');
        </script>
    """, unsafe_allow_html=True)

# Carica dati
df = load_data()
if df.empty:
    st.stop()

# Normalizza colonne
df.columns = df.columns.str.strip().str.title()

# Titolo
st.title("🔍 Ricerca Ricambi in Magazzino")

# CSS per mobile friendly
st.markdown("""
    <style>
    body, .stApp { font-size: 15px; }
    .block-container { padding-top: 1rem; padding-bottom: 1rem; }
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
    </style>
""", unsafe_allow_html=True)

# Detect device
detect_device()
# Variabile di fallback (se JS non funziona)
is_mobile = st.session_state.get("is_mobile", False)

# Sidebar filtri
with st.sidebar:
    st.header("📌 Filtri ricerca")
    codice_input = st.text_input("🔢 Codice", placeholder="Inserisci codice...")
    descrizione_input = st.text_input("📄 Descrizione", placeholder="Inserisci descrizione...")
    posizione_input = st.text_input("📍 Ubicazione", placeholder="Inserisci ubicazione...")

    categorie_uniche = ["Tutte"] + sorted(df["Categoria"].dropna().unique().tolist())
    macchinario_input = st.selectbox("🛠️ Categoria", categorie_uniche)

    if st.button("🔄 Reset filtri"):
        st.experimental_rerun()

# Filtraggio
filtro = df.copy()

if codice_input:
    filtro["Codice_str"] = filtro["Codice"].astype(str).str.strip()
    filtro = filtro[filtro["Codice_str"].str.contains(codice_input.strip(), case=False, na=False)]

if descrizione_input:
    filtro = fuzzy_search_balanced(filtro, "Descrizione", descrizione_input.strip(), threshold=70)

if posizione_input:
    filtro = filtro[filtro["Ubicazione"].astype(str).str.contains(posizione_input.strip(), case=False, na=False)]

if macchinario_input != "Tutte":
    filtro = filtro[filtro["Categoria"].astype(str).str.lower() == macchinario_input.lower()]

# Conteggio risultati
st.markdown(f"### 📦 {len(filtro)} risultato(i) trovati")

# Visualizzazione
if is_mobile:
    st.info("📱 Modalità mobile attiva")
    for _, row in filtro.iterrows():
        st.markdown(f"""
            <div class="card">
                <h4>{row['Codice']}</h4>
                <p><strong>Descrizione:</strong> {row['Descrizione']}</p>
            </div>
        """, unsafe_allow_html=True)
        with st.expander("Dettagli"):
            st.write(f"📍 Ubicazione: {row['Ubicazione']}")
            st.write(f"🛠️ Categoria: {row['Categoria']}")
else:
    st.dataframe(filtro[["Codice", "Descrizione", "Ubicazione", "Categoria"]], use_container_width=True, height=450)

# Download CSV
if not filtro.empty:
    st.download_button("📥 Scarica risultati (CSV)", filtro.to_csv(index=False), "risultati.csv", "text/csv")
