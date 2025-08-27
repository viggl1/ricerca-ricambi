import pandas as pd
import streamlit as st
from rapidfuzz import fuzz
import os
import sys
import pyperclip

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
        font-size: 15px;
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
    .copy-btn {
        background-color: #007bff;
        color: white;
        border: none;
        padding: 8px 12px;
        font-size: 14px;
        border-radius: 8px;
        cursor: pointer;
    }
    .copy-btn:hover {
        background-color: #0056b3;
    }
    /* Sticky search bar for mobile */
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

# ---------------- RILEVAMENTO MOBILE (Semplice) ----------------
is_mobile = st.experimental_get_query_params().get("mobile", ["false"])[0] == "true"
# (Alternativa avanzata: usare streamlit-javascript)

# ---------------- CARICA DATI ----------------
df = load_data()
if df.empty:
    st.stop()

df.columns = df.columns.str.strip().str.title()

# ---------------- INTERFACCIA ----------------
st.title("🔍 Ricerca Ricambi in Magazzino")

with st.sidebar:
    st.header("📌 Filtri ricerca")
    codice_input = st.text_input("🔢 Codice", placeholder="Inserisci codice...")
    descrizione_input = st.text_input("📄 Descrizione", placeholder="Inserisci descrizione...")
    posizione_input = st.text_input("📍 Ubicazione", placeholder="Inserisci ubicazione...")
    categorie_uniche = ["Tutte"] + sorted(df["Categoria"].dropna().unique().tolist())
    macchinario_input = st.selectbox("🛠️ Categoria", categorie_uniche)

    if st.button("🔄 Reset filtri"):
        st.experimental_rerun()

# ---------------- FILTRAGGIO ----------------
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

# ---------------- RISULTATI ----------------
st.markdown(f"### 📦 {len(filtro)} risultato(i) trovati")

if st.button("📥 Scarica tutti i risultati"):
    st.download_button("Download CSV", filtro.to_csv(index=False), "risultati.csv", "text/csv")

# Visualizzazione: Mobile → Card View, Desktop → Tabella
if is_mobile or st.sidebar.checkbox("Modalità Mobile (simula)"):
    st.info("📱 Visualizzazione Mobile attiva")
    for _, row in filtro.iterrows():
        st.markdown(f"""
            <div class="card">
                <h4>{row['Codice']}</h4>
                <p><strong>Descrizione:</strong> {row['Descrizione']}</p>
                <p><strong>📍 Ubicazione:</strong> {row['Ubicazione']}</p>
                <p><strong>🛠️ Categoria:</strong> {row['Categoria']}</p>
            </div>
        """, unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            if st.button(f"📋 Copia Codice {row['Codice']}", key=f"copy_{row['Codice']}"):
                pyperclip.copy(str(row['Codice']))
                st.success("Codice copiato!")
        with col2:
            st.download_button(f"⬇ Scarica {row['Codice']}", data=row.to_frame().T.to_csv(index=False), file_name=f"{row['Codice']}.csv", mime="text/csv", key=f"dl_{row['Codice']}")
else:
    st.dataframe(filtro[["Codice", "Descrizione", "Ubicazione", "Categoria"]], use_container_width=True, height=450)
