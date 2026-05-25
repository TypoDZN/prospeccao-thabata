import os
import sqlite3
import unicodedata

import numpy as np
import pandas as pd
import streamlit as st
from rapidfuzz import fuzz, process


def sem_acento(texto: str) -> str:
    normalizado = unicodedata.normalize("NFD", texto)
    return "".join(c for c in normalizado if unicodedata.category(c) != "Mn").lower()

DB_PATH = os.path.join("database", "prospeccao.db")

COLUNAS_LISTA = [
    "nome", "cnpj", "ramo", "cidade", "bairro", "cep",
    "endereco", "numero", "celular", "telefone", "email",
]

st.set_page_config(page_title="Prospecção de Clientes", layout="wide")
st.title("Sistema de Prospecção de Clientes")


@st.cache_data(ttl=60)
def carregar_dados() -> pd.DataFrame:
    if not os.path.exists(DB_PATH):
        return pd.DataFrame()
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT * FROM clientes", conn)
    conn.close()
    return df


df = carregar_dados()

if df.empty:
    st.warning(
        "Banco de dados não encontrado ou vazio. "
        "Execute `python importar_dados.py` para importar os dados."
    )
    st.stop()

# ── Filtros (sidebar) ──────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Filtros")

    ramos = sorted(df["ramo"].dropna().unique().tolist())
    ramo_sel = st.multiselect("Ramo de atividade", ramos)

    cidades = sorted(df["cidade"].dropna().unique().tolist())
    cidade_sel = st.multiselect("Cidade", cidades)

    busca = st.text_input("Buscar por nome ou CNPJ")
    busca_bairro = st.text_input("Buscar por bairro")
    busca_cep = st.text_input("Buscar por CEP")

# ── Aplicar filtros ────────────────────────────────────────────────────────────
filtrado = df.copy()

if ramo_sel:
    filtrado = filtrado[filtrado["ramo"].isin(ramo_sel)]
if cidade_sel:
    cidades_norm = [sem_acento(c) for c in cidade_sel]
    filtrado = filtrado[filtrado["cidade"].fillna("").apply(sem_acento).isin(cidades_norm)]
if busca:
    termo = sem_acento(busca)
    nomes_norm = filtrado["nome"].fillna("").apply(sem_acento).tolist()
    scores = process.cdist([termo], nomes_norm, scorer=fuzz.partial_ratio)[0]
    mask_nome = scores >= 70
    mask_cnpj = filtrado["cnpj"].fillna("").apply(sem_acento).str.contains(termo, regex=False).values
    filtrado = filtrado[mask_nome | mask_cnpj]
if busca_bairro:
    termo_bairro = sem_acento(busca_bairro)
    filtrado = filtrado[
        filtrado["bairro"].fillna("").apply(sem_acento).str.contains(termo_bairro, regex=False)
    ]
if busca_cep:
    filtrado = filtrado[filtrado["cep"].str.startswith(busca_cep, na=False)]

# ── Métricas ───────────────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total de clientes", len(df))
c2.metric("Registros filtrados", len(filtrado))
c3.metric("Cidades únicas", df["cidade"].nunique())
c4.metric("Ramos únicos", df["ramo"].nunique())

st.divider()

# ── Tabela ─────────────────────────────────────────────────────────────────────
colunas_validas = [c for c in COLUNAS_LISTA if c in filtrado.columns]

st.subheader(f"Clientes ({len(filtrado)} registros)")
st.dataframe(
    filtrado[colunas_validas].reset_index(drop=True),
    use_container_width=True,
    hide_index=True,
    height=500,
)

def gerar_texto_whatsapp(df: pd.DataFrame) -> str:
    def s(row, col):
        v = row.get(col, "")
        return str(v).strip() if pd.notna(v) and str(v).strip().lower() != "nan" else ""

    blocos = []
    for _, row in df.iterrows():
        end_num = ", ".join(filter(None, [s(row, "endereco"), s(row, "numero")]))
        partes_local = list(filter(None, [end_num, s(row, "bairro"), s(row, "cidade")]))
        linha_local = " — ".join(partes_local)

        bloco = "\n".join(filter(None, [
            f"🏪 {s(row, 'nome').upper()}",
            f"🍽️ {s(row, 'ramo')}"     if s(row, "ramo")    else "",
            f"📍 {linha_local}"         if linha_local        else "",
            f"📱 {s(row, 'celular')}"   if s(row, "celular") else "",
            f"✉️ {s(row, 'email')}"     if s(row, "email")   else "",
        ]))
        blocos.append(bloco)
    return "\n\n".join(blocos)


if st.button("📋 Copiar lista para WhatsApp"):
    st.session_state["wa_texto"] = gerar_texto_whatsapp(filtrado[colunas_validas])

if st.session_state.get("wa_texto"):
    st.code(st.session_state["wa_texto"], language="")
