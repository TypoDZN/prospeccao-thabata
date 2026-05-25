import os
import sqlite3
import pandas as pd

DATA_DIR = "data"
DB_PATH = os.path.join("database", "prospeccao.db")

COLUNAS_ORIGEM = [
    "FANTASIA", "CNPJ", "RAMO", "NOMECIDADE", "BAIRROENT",
    "ENDERENT", "NUMEROENT", "CEPENT", "CELULAR", "TELEFONE", "EMAIL",
    "DTULTCOMP", "LATITUDE", "LONGITUDE",
]

COLUNAS_DESTINO = [
    "nome", "cnpj", "ramo", "cidade", "bairro",
    "endereco", "numero", "cep", "celular", "telefone", "email",
    "ultima_compra", "latitude", "longitude",
]

RENAME_MAP = dict(zip(COLUNAS_ORIGEM, COLUNAS_DESTINO))


def carregar_xls(caminho: str) -> pd.DataFrame:
    """Lê um arquivo XLS/XLSX e retorna apenas as colunas esperadas."""
    try:
        df = pd.read_excel(caminho, dtype=str)
    except Exception as e:
        print(f"  [ERRO] Falha ao ler {caminho}: {e}")
        return pd.DataFrame()

    colunas_presentes = [c for c in COLUNAS_ORIGEM if c in df.columns]
    colunas_ausentes = [c for c in COLUNAS_ORIGEM if c not in df.columns]

    if colunas_ausentes:
        print(f"  [AVISO] Colunas ausentes em {os.path.basename(caminho)}: {colunas_ausentes}")

    df = df[colunas_presentes].rename(columns=RENAME_MAP)

    # garante que todas as colunas destino existam (preenche com None se ausente)
    for col in COLUNAS_DESTINO:
        if col not in df.columns:
            df[col] = None

    return df[COLUNAS_DESTINO]


def importar():
    arquivos = [f for f in os.listdir(DATA_DIR) if f.lower().endswith((".xls", ".xlsx"))]
    if not arquivos:
        print(f"Nenhum arquivo XLS encontrado em '{DATA_DIR}/'.")
        return

    frames = []
    for arquivo in sorted(arquivos):
        caminho = os.path.join(DATA_DIR, arquivo)
        print(f"Lendo: {arquivo}")
        df = carregar_xls(caminho)
        if df.empty:
            continue
        df["origem"] = arquivo
        df["status_prospeccao"] = "Não contactado"
        frames.append(df)
        print(f"  {len(df)} registros carregados.")

    if not frames:
        print("Nenhum dado importado.")
        return

    dados = pd.concat(frames, ignore_index=True)

    total_antes = len(dados)
    # mantém a primeira ocorrência de cada CNPJ (preserva a origem do primeiro arquivo)
    dados = dados.dropna(subset=["cnpj"])
    dados["cnpj"] = dados["cnpj"].str.strip()
    dados = dados.drop_duplicates(subset=["cnpj"], keep="first")
    total_depois = len(dados)
    print(f"\nDuplicatas removidas por CNPJ: {total_antes - total_depois}")
    print(f"Total de registros únicos: {total_depois}")

    os.makedirs("database", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    dados.to_sql("clientes", conn, if_exists="replace", index=False)
    conn.close()

    print(f"\nBanco de dados criado em: {DB_PATH}")


if __name__ == "__main__":
    importar()
