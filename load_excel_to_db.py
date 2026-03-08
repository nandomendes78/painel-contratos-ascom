import re
import sqlite3
from pathlib import Path

import pandas as pd

DB_PATH = "database.db"
EXCEL_PATH = Path("2_data") / "contratos_ascom_base.xlsx"


# -------------------------
# Helpers de limpeza
# -------------------------
def norm_col(c: str) -> str:
    return str(c).strip().lower().replace(" ", "")


def br_money_to_float(x) -> float | None:
    """
    Converte 'R$ 1.860.000,00' -> 1860000.00
    """
    if x is None:
        return None
    s = str(x).strip()
    if s == "" or s.lower() in {"nan", "none", "-"}:
        return None

    s = s.replace("R$", "").strip()
    s = s.replace(".", "").replace(",", ".")
    s = re.sub(r"[^\d.]+", "", s)

    if s == "":
        return None
    try:
        return float(s)
    except ValueError:
        return None


def to_iso_date(x) -> str | None:
    """
    Converte datas como '01/04/2026' para '2026-04-01' (texto).
    """
    if x is None:
        return None
    s = str(x).strip()
    if s == "" or s.lower() in {"nan", "none", "-"}:
        return None

    dt = pd.to_datetime(s, dayfirst=True, errors="coerce")
    if pd.isna(dt):
        return None
    return dt.date().isoformat()


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


# -------------------------
# Leitura do Excel (acha aba por nome, independente de maiúsculas)
# -------------------------
def _find_sheet(xls: pd.ExcelFile, wanted: str) -> str:
    wanted = wanted.strip().lower()
    for s in xls.sheet_names:
        if s.strip().lower() == wanted:
            return s
    # tenta match parcial
    for s in xls.sheet_names:
        if wanted in s.strip().lower():
            return s
    raise ValueError(f"Não encontrei aba '{wanted}'. Abas disponíveis: {xls.sheet_names}")


def carregar_dados() -> tuple[pd.DataFrame, pd.DataFrame]:
    if not EXCEL_PATH.exists():
        raise FileNotFoundError(f"Excel não encontrado em: {EXCEL_PATH.resolve()}")

    print(f"Lendo Excel em: {EXCEL_PATH}")

    xls = pd.ExcelFile(EXCEL_PATH)
    sheet_contratos = _find_sheet(xls, "contratos")
    sheet_pagamentos = _find_sheet(xls, "pagamentos")

    df_contratos = pd.read_excel(EXCEL_PATH, sheet_name=sheet_contratos, dtype=str)
    df_pagamentos = pd.read_excel(EXCEL_PATH, sheet_name=sheet_pagamentos, dtype=str)

    # normaliza nomes de colunas
    df_contratos.columns = [norm_col(c) for c in df_contratos.columns]
    df_pagamentos.columns = [norm_col(c) for c in df_pagamentos.columns]

    return df_contratos, df_pagamentos


# -------------------------
# Inserção no DB
# -------------------------
def inserir_no_banco(df_contratos: pd.DataFrame, df_pagamentos: pd.DataFrame) -> None:
    conn = get_connection()
    cur = conn.cursor()

    # garante que tabelas existem (evita "no such table")
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='fornecedor';"
    )
    if cur.fetchone() is None:
        raise RuntimeError("Tabela 'fornecedor' não existe. Rode: python database.py")

    # -------- fornecedores
    fornecedores_inseridos = 0
    fornecedor_map: dict[tuple[str, str], int] = {}

    # colunas esperadas no Excel (já normalizadas)
    col_nome = "fornecedor"
    col_cnpj = "cnpj_fornecedor"
    col_cnome = "fornecedor_contato_nome"
    col_cemail = "fornecedor_contato_email"
    col_ctel = "fornecedor_contato_telefone"

    for _, row in df_contratos.iterrows():
        nome = (row.get(col_nome) or "").strip()
        cnpj = (row.get(col_cnpj) or "").strip()
        c_nome = (row.get(col_cnome) or "").strip()
        c_email = (row.get(col_cemail) or "").strip()
        c_tel = (row.get(col_ctel) or "").strip()

        if not nome:
            continue

        key = (nome, cnpj)
        if key in fornecedor_map:
            continue

        cur.execute(
            """
            INSERT OR IGNORE INTO fornecedor (nome, cnpj, contato_nome, contato_email, contato_telefone)
            VALUES (?, ?, ?, ?, ?)
            """,
            (nome, cnpj, c_nome or None, c_email or None, c_tel or None),
        )

        # pega id (tanto se inseriu quanto se já existia)
        cur.execute("SELECT id FROM fornecedor WHERE nome=? AND cnpj=? LIMIT 1", (nome, cnpj))
        fid = cur.fetchone()[0]
        fornecedor_map[key] = fid
        fornecedores_inseridos += 1

    print(f"Fornecedores mapeados: {len(fornecedor_map)}")

    # -------- contratos
    contratos_inseridos = 0

    contrato_cols = [
        "id_contrato",
        "nome_contrato",
        "modalidade",
        "forma_julgamento",
        "tipo_vigencia",
        "processo_sei_contrato",
        "numero_contrato",
        "processo_sei_pagamento",
        "fornecedor_id",
        "data_inicio_vigencia",
        "data_fim_vigencia",
        "prazo_max_pagamento_dias",
        "valor_global",
        "valor_mensal_previsto",
        "status_contrato",
        "gestor_responsavel",
        "fiscal_tecnico",
        "observacoes",
    ]

    placeholders = ",".join(["?"] * len(contrato_cols))

    for _, row in df_contratos.iterrows():
        id_contrato = (row.get("id_contrato") or "").strip()
        if not id_contrato:
            continue

        nome = (row.get(col_nome) or "").strip()
        cnpj = (row.get(col_cnpj) or "").strip()
        fid = fornecedor_map.get((nome, cnpj))

        dados = (
            id_contrato,
            (row.get("nome_contrato") or "").strip(),
            (row.get("modalidade") or "").strip(),
            (row.get("forma_julgamento") or "").strip(),
            (row.get("tipo_vigencia") or "").strip(),
            (row.get("processo_sei_contrato") or "").strip(),
            (row.get("numero_contrato") or "").strip(),
            (row.get("processo_sei_pagamento") or "").strip(),
            fid,
            to_iso_date(row.get("data_inicio_vigencia")),
            to_iso_date(row.get("data_fim_vigencia")),
            (row.get("prazo_max_pagamento_dias") or "").strip(),
            br_money_to_float(row.get("valor_global")),
            br_money_to_float(row.get("valor_mensal_previsto")),
            (row.get("status_contrato") or "").strip(),
            (row.get("gestor_responsavel") or "").strip(),
            (row.get("fiscal_tecnico") or "").strip(),
            (row.get("observacoes") or "").strip(),
        )

        cur.execute(
            f"""
            INSERT OR REPLACE INTO contrato ({",".join(contrato_cols)})
            VALUES ({placeholders})
            """,
            dados,
        )
        contratos_inseridos += 1

    print(f"Contratos inseridos: {contratos_inseridos}")

    # -------- pagamentos
    pagamentos_inseridos = 0

    pg_cols = [
        "id_pagamento",
        "id_contrato",
        "processo_sei_pagamento",
        "data_emissao_nf",
        "data_vencimento_nf",
        "data_pagamento",
        "valor_nf",
        "numero_nf",
        "numero_requisicao_compra",
        "numero_pedido_compra",
        "numero_empenho",
        "numero_medicao",
        "tipo_pagamento",
        "status_pagamento",
        "observacoes",
    ]
    pg_placeholders = ",".join(["?"] * len(pg_cols))

    for _, row in df_pagamentos.iterrows():
        id_pagamento = (row.get("id_pagamento") or "").strip()
        id_contrato = (row.get("id_contrato") or "").strip()
        if not id_pagamento or not id_contrato:
            continue

        dados_pg = (
            id_pagamento,
            id_contrato,
            (row.get("processo_sei_pagamento") or "").strip(),
            to_iso_date(row.get("data_emissao_nf")),
            to_iso_date(row.get("data_vencimento_nf")),
            to_iso_date(row.get("data_pagamento")),
            br_money_to_float(row.get("valor_nf")),
            (row.get("numero_nf") or "").strip(),
            (row.get("numero_requisicao_compra") or "").strip(),
            (row.get("numero_pedido_compra") or "").strip(),
            (row.get("numero_empenho") or "").strip(),
            (row.get("numero_medicao") or "").strip(),
            (row.get("tipo_pagamento") or "").strip(),
            (row.get("status_pagamento") or "").strip(),
            (row.get("observacoes") or "").strip(),
        )

        cur.execute(
            f"""
            INSERT OR REPLACE INTO pagamento ({",".join(pg_cols)})
            VALUES ({pg_placeholders})
            """,
            dados_pg,
        )
        pagamentos_inseridos += 1

    print(f"Pagamentos inseridos: {pagamentos_inseridos}")

    conn.commit()
    conn.close()
    print("Carga concluída com sucesso!")


def main():
    df_contratos, df_pagamentos = carregar_dados()
    inserir_no_banco(df_contratos, df_pagamentos)


if __name__ == "__main__":
    main()