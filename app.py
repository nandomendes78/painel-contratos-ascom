import sqlite3
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

DB_PATH = "database.db"
LOGO_PATH = Path("assets/logo-artesp-horiz-cor-preto.png")

# ---------------------------
# CONFIG
# ---------------------------
st.set_page_config(
    page_title="Painel de Contratos – ASCOM",
    page_icon=None,
    layout="wide",
)

# ---------------------------
# CSS (Montserrat + identidade + tabelas mais “fortes”)
# ---------------------------
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700&display=swap');

    html, body, [class*="css"]  { font-family: 'Montserrat', sans-serif; }

    /* linhas vermelhas */
    .top-red-line { border-top: 3px solid #FF161F; margin: 0.35rem 0 0.7rem 0; }
    .section-red-line { border-top: 2px solid #FF161F; margin: 1.25rem 0; }

    /* header */
    .hdr-wrap{
        display:flex;
        justify-content:space-between;
        align-items:flex-start;
        margin-top:0.25rem;
        margin-bottom:0.15rem;
    }
    .hdr-left{
        display:flex;
        flex-direction:column;
        justify-content:center;
        gap:0.65rem;
    }
    .hdr-title{
        font-size: 2.15rem;
        font-weight: 700;
        color:#111111;
        margin:0;
        line-height:1.05;
    }
    .hdr-right{
        font-size:0.9rem;
        color:#666;
        margin:0;
        text-align:right;
        padding-top:0.15rem;
    }

    /* centralizar título+logo entre as linhas */
    .mid-block{
        display:flex;
        flex-direction:column;
        justify-content:center;
        align-items:flex-start;
        gap:0.55rem;
        min-height: 86px; /* garante “meio” entre as linhas */
        padding: 0.35rem 0 0.2rem 0;
    }

    /* KPI cards */
    .kpi-strip-top { border-top: 2px solid #FF161F; margin-bottom: 1rem; }
    .kpi-card {
        background-color: #F9F9F9;
        border-radius: 16px;
        padding: 1.25rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.04);
        border-left: 4px solid #FF161F;
    }
    .kpi-label { font-size: 0.9rem; color: #666; margin-bottom: 0.25rem; }
    .kpi-value { font-size: 2rem; font-weight: 700; color: #111; }

    /* Deixar tabelas com bordas e cabeçalho mais escuros */
    div[data-testid="stDataFrame"] {
        border: 1px solid #706F6F !important;
        border-radius: 12px !important;
        overflow: hidden;
    }
    div[data-testid="stDataFrame"] thead tr th {
        background: #F0F0F0 !important;
        color: #111 !important;
        font-weight: 700 !important;
        border-bottom: 1px solid #706F6F !important;
    }
    div[data-testid="stDataFrame"] tbody tr td {
        border-bottom: 1px solid #C0C0C0 !important;
    }

    /* Inputs (selectbox/search) com borda mais evidente */
    div[data-testid="stSelectbox"] > div,
    div[data-testid="stTextInput"] > div {
        border: 1px solid #706F6F !important;
        border-radius: 10px !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------
# DB helpers
# ---------------------------
def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

@st.cache_data
def carregar_contratos() -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql_query(
        """
        SELECT
            c.id_contrato,
            c.nome_contrato,
            c.modalidade,
            c.forma_julgamento,
            c.tipo_vigencia,
            c.processo_sei_contrato,
            c.numero_contrato,
            c.processo_sei_pagamento,
            c.data_inicio_vigencia,
            c.data_fim_vigencia,
            c.prazo_max_pagamento_dias,
            c.valor_global,
            c.valor_mensal_previsto,
            c.status_contrato,
            c.gestor_responsavel,
            c.fiscal_tecnico,
            c.observacoes,
            f.nome AS fornecedor_nome,
            f.cnpj AS fornecedor_cnpj,
            f.contato_nome AS fornecedor_contato_nome,
            f.contato_email AS fornecedor_contato_email,
            f.contato_telefone AS fornecedor_contato_telefone
        FROM contrato c
        LEFT JOIN fornecedor f ON c.fornecedor_id = f.id
        """,
        conn,
    )
    conn.close()

    # datas
    for col in ["data_inicio_vigencia", "data_fim_vigencia"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    return df

@st.cache_data
def carregar_pagamentos() -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql_query(
        """
        SELECT
            id_pagamento,
            id_contrato,
            processo_sei_pagamento,
            data_emissao_nf,
            data_vencimento_nf,
            data_pagamento,
            valor_nf,
            numero_nf,
            numero_requisicao_compra,
            numero_pedido_compra,
            numero_empenho,
            numero_medicao,
            tipo_pagamento,
            status_pagamento,
            observacoes
        FROM pagamento
        """,
        conn,
    )
    conn.close()

    for col in ["data_emissao_nf", "data_vencimento_nf", "data_pagamento"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    return df

# ---------------------------
# Formatação / Faróis
# ---------------------------
def fmt_data_ptbr(ts: pd.Timestamp) -> str:
    if pd.isna(ts):
        return "-"
    return ts.strftime("%d/%m/%Y")

def fmt_brl(valor) -> str:
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return "-"
    try:
        v = float(str(valor).replace("R$", "").replace(".", "").replace(" ", "").replace(",", "."))
        s = f"{v:,.2f}"
        # troca separadores US -> BR
        s = s.replace(",", "X").replace(".", ",").replace("X", ".")
        return f"R$ {s}"
    except Exception:
        return str(valor)

def calc_meses_dias(dias: int) -> tuple[int, int]:
    meses = max(dias, 0) // 30
    resto = max(dias, 0) % 30
    return meses, resto

# Contratos: verde > 180; laranja 91..180; vermelho 0..90; cinza vencido
def status_vigencia(data_fim: pd.Timestamp) -> tuple[str, str, int]:
    if pd.isna(data_fim):
        return ("⚪", "Sem data de fim", 999999)

    hoje = date.today()
    dias = (data_fim.date() - hoje).days

    if dias < 0:
        return ("⚫", f"Vencido ({abs(dias)} dias)", dias)

    meses, resto = calc_meses_dias(dias)
    msg = f"Faltam {meses} meses ({dias} dias)" if meses > 0 else f"Faltam {dias} dias"

    if dias <= 90:
        return ("🔴", msg, dias)
    elif dias <= 180:
        return ("🟠", msg, dias)
    else:
        return ("🟢", msg, dias)

# Pagamentos: verde 16..30; laranja 8..15; vermelho 0..7; cinza vencido; pago em dia/atraso
def status_pagamento(data_venc: pd.Timestamp, data_pgto: pd.Timestamp) -> tuple[str, str, int]:
    if pd.isna(data_venc):
        return ("⚪", "Sem vencimento", 999999)

    hoje = date.today()
    dias = (data_venc.date() - hoje).days

    if pd.notna(data_pgto):
        # já pago
        if data_pgto.date() <= data_venc.date():
            return ("✅", "Pago em dia", dias)
        return ("🟠", "Pago com atraso", dias)

    # não pago
    if dias < 0:
        return ("⚫", f"Vencido ({abs(dias)} dias)", dias)
    if dias <= 7:
        return ("🔴", f"Vence em {dias} dia(s)", dias)
    if dias <= 15:
        return ("🟠", f"Vence em {dias} dias", dias)
    if dias <= 30:
        return ("🟢", f"Vence em {dias} dias", dias)

    return ("🟢", f"Vence em {dias} dias", dias)

def id_display(s: str, prefix: str) -> str:
    # PGTO_0001 -> PGTO 01 | AI_PRESS_2026 -> AI PRESS 2026
    if not isinstance(s, str):
        return str(s)
    if prefix == "PGTO":
        # pega últimos 2 dígitos numéricos se existir
        digits = "".join(ch for ch in s if ch.isdigit())
        if digits:
            return f"PGTO {int(digits):02d}"
        return s.replace("_", " ")
    return s.replace("_", " ")

# ---------------------------
# HEADER (frase topo direita + linhas + bloco título+logo central)
# ---------------------------
st.markdown(
    """
    <div class="hdr-wrap">
        <div></div>
        <p class="hdr-right">MVP para gestão de contratos e pagamentos da comunicação – ARTESP.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="top-red-line"></div>', unsafe_allow_html=True)

left = st.container()
with left:
    st.markdown('<div class="mid-block">', unsafe_allow_html=True)
    st.markdown('<p class="hdr-title">Painel de Contratos – ASCOM</p>', unsafe_allow_html=True)
    if LOGO_PATH.exists():
        st.image("assets/logo-artesp-horiz-cor-preto.png", width=240)
    else:
        st.warning(f"Logo não encontrada em: {LOGO_PATH}")
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown('<div class="section-red-line"></div>', unsafe_allow_html=True)

# ---------------------------
# DATA
# ---------------------------
df_contratos = carregar_contratos()
df_pagamentos = carregar_pagamentos()

if df_contratos.empty:
    st.error("Não há contratos no banco ainda. Rode: python database.py e depois python load_excel_to_db.py")
    st.stop()

# vigência
vig = df_contratos["data_fim_vigencia"].apply(status_vigencia)
df_contratos["vig_icone"] = vig.apply(lambda x: x[0])
df_contratos["vig_texto"] = vig.apply(lambda x: x[1])
df_contratos["vig_dias"] = vig.apply(lambda x: x[2])

# pagamento
pg = df_pagamentos.apply(lambda r: status_pagamento(r["data_vencimento_nf"], r["data_pagamento"]), axis=1) if not df_pagamentos.empty else []
if not df_pagamentos.empty:
    df_pagamentos["pg_icone"] = pg.apply(lambda x: x[0])
    df_pagamentos["pg_texto"] = pg.apply(lambda x: x[1])
    df_pagamentos["pg_dias"] = pg.apply(lambda x: x[2])

# ---------------------------
# TABS
# ---------------------------
abas = st.tabs(["Visão Geral", "Contratos", "Pagamentos", "Detalhes"])

# --- ABA 1: Visão Geral ---
with abas[0]:
    st.subheader("Visão geral de contratos e pagamentos")

    total_contratos = len(df_contratos)
    total_pagamentos = len(df_pagamentos)

    contratos_vencidos = (df_contratos["vig_dias"] < 0).sum()

    pagamentos_vencidos = 0
    if not df_pagamentos.empty:
        pagamentos_vencidos = ((df_pagamentos["pg_icone"] == "⚫") & (df_pagamentos["data_pagamento"].isna())).sum()

    st.markdown('<div class="kpi-strip-top"></div>', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.markdown(f'<div class="kpi-card"><div class="kpi-label">Contratos cadastrados</div><div class="kpi-value">{total_contratos}</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="kpi-card"><div class="kpi-label">Pagamentos registrados</div><div class="kpi-value">{total_pagamentos}</div></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="kpi-card"><div class="kpi-label">Contratos vencidos</div><div class="kpi-value">{contratos_vencidos}</div></div>', unsafe_allow_html=True)
    with c4:
        st.markdown(f'<div class="kpi-card"><div class="kpi-label">Pagamentos vencidos</div><div class="kpi-value">{pagamentos_vencidos}</div></div>', unsafe_allow_html=True)

    st.markdown('<div class="section-red-line"></div>', unsafe_allow_html=True)

    # tabela visão geral (SEM erro de mismatch: usamos rename)
    df_v = df_contratos[[
        "id_contrato", "nome_contrato", "vig_icone", "vig_texto", "status_contrato", "processo_sei_pagamento"
    ]].copy()

    df_v.insert(0, "Nº", range(1, len(df_v) + 1))
    df_v["Contrato (ID)"] = df_v["id_contrato"].apply(lambda x: id_display(x, "CTR"))
    df_v["Situação (vigência)"] = df_v["vig_icone"] + " " + df_v["vig_texto"]

    df_v = df_v.drop(columns=["id_contrato", "vig_icone", "vig_texto"])
    df_v = df_v.rename(columns={
        "nome_contrato": "Contrato",
        "status_contrato": "Status",
        "processo_sei_pagamento": "SEI (pagamento)",
    })

    # organiza ordem
    df_v = df_v[["Nº", "Contrato (ID)", "Contrato", "Situação (vigência)", "Status", "SEI (pagamento)"]]

    st.write("Contratos (situação de vigência):")
    st.dataframe(df_v, width="stretch", hide_index=True)

# --- ABA 2: Contratos ---
with abas[1]:
    st.subheader("Contratos")

    filtro_status = st.selectbox(
        "Filtrar por status do contrato:",
        options=["Todos"] + sorted(df_contratos["status_contrato"].dropna().unique().tolist()),
    )

    df_c = df_contratos.copy()
    if filtro_status != "Todos":
        df_c = df_c[df_c["status_contrato"] == filtro_status]

    df_c = df_c.copy()
    df_c.insert(0, "Nº", range(1, len(df_c) + 1))
    df_c["Contrato (ID)"] = df_c["id_contrato"].apply(lambda x: id_display(x, "CTR"))
    df_c["Situação (vigência)"] = df_c["vig_icone"] + " " + df_c["vig_texto"]
    df_c["Início"] = df_c["data_inicio_vigencia"].apply(fmt_data_ptbr)
    df_c["Fim"] = df_c["data_fim_vigencia"].apply(fmt_data_ptbr)
    df_c["Valor global"] = df_c["valor_global"].apply(fmt_brl)

    mostrar = [
        "Nº", "Contrato (ID)", "nome_contrato", "modalidade", "tipo_vigencia",
        "processo_sei_pagamento", "Início", "Fim", "Situação (vigência)", "Valor global", "status_contrato"
    ]
    df_c = df_c[mostrar].rename(columns={
        "nome_contrato": "Contrato",
        "modalidade": "Modalidade",
        "tipo_vigencia": "Vigência",
        "processo_sei_pagamento": "SEI (pagamento)",
        "status_contrato": "Status",
    })

    st.dataframe(df_c, width="stretch", hide_index=True)

# --- ABA 3: Pagamentos ---
with abas[2]:
    st.subheader("Pagamentos")

    if df_pagamentos.empty:
        st.info("Nenhum pagamento cadastrado.")
    else:
        filtro_pg = st.selectbox(
            "Filtrar por situação do pagamento:",
            options=["Todos"] + sorted(df_pagamentos["pg_texto"].dropna().unique().tolist()),
        )

        df_p = df_pagamentos.copy()
        df_p["Situação (pagamento)"] = df_p["pg_icone"] + " " + df_p["pg_texto"]

        if filtro_pg != "Todos":
            df_p = df_p[df_p["pg_texto"] == filtro_pg]

        df_p = df_p.copy()
        df_p.insert(0, "Nº", range(1, len(df_p) + 1))
        df_p["Pagamento (ID)"] = df_p["id_pagamento"].apply(lambda x: id_display(x, "PGTO"))
        df_p["Emissão"] = df_p["data_emissao_nf"].apply(fmt_data_ptbr)
        df_p["Vencimento"] = df_p["data_vencimento_nf"].apply(fmt_data_ptbr)
        df_p["Pagamento"] = df_p["data_pagamento"].apply(fmt_data_ptbr)
        df_p["Valor NF"] = df_p["valor_nf"].apply(fmt_brl)

        # **NF antes de requisição**
        mostrar = [
            "Nº", "Pagamento (ID)", "id_contrato", "processo_sei_pagamento",
            "Emissão", "Vencimento", "Pagamento", "Valor NF",
            "numero_nf", "numero_requisicao_compra", "numero_pedido_compra", "numero_empenho", "numero_medicao",
            "tipo_pagamento", "Situação (pagamento)", "status_pagamento", "observacoes"
        ]
        df_p = df_p[mostrar].rename(columns={
            "id_contrato": "Contrato (ID)",
            "processo_sei_pagamento": "SEI (pagamento)",
            "numero_nf": "NF",
            "numero_requisicao_compra": "Requisição",
            "numero_pedido_compra": "Pedido",
            "numero_empenho": "Empenho",
            "numero_medicao": "Medição",
            "tipo_pagamento": "Tipo",
            "status_pagamento": "Status",
            "observacoes": "Obs.",
        })

        # limpa underscores do contrato id
        df_p["Contrato (ID)"] = df_p["Contrato (ID)"].apply(lambda x: id_display(x, "CTR"))

        st.dataframe(df_p, width="stretch", hide_index=True)

# --- ABA 4: Detalhes ---
with abas[3]:
    st.subheader("Detalhes do contrato")

    contratos_ids = df_contratos["id_contrato"].dropna().tolist()
    escolhido = st.selectbox("Escolha um contrato:", options=contratos_ids)

    df_sel = df_contratos[df_contratos["id_contrato"] == escolhido].copy()
    if df_sel.empty:
        st.warning("Contrato não encontrado.")
        st.stop()

    contrato = df_sel.iloc[0]
    pagamentos_sel = df_pagamentos[df_pagamentos["id_contrato"] == escolhido].copy() if not df_pagamentos.empty else pd.DataFrame()

    st.markdown(f"### {contrato['nome_contrato']} ({id_display(contrato['id_contrato'], 'CTR')})")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Dados principais**")
        st.write(f"Fornecedor: {contrato.get('fornecedor_nome','-') or '-'}")
        st.write(f"CNPJ: {contrato.get('fornecedor_cnpj','-') or '-'}")
        st.write(f"Modalidade: {contrato.get('modalidade','-') or '-'}")
        st.write(f"Forma de julgamento: {contrato.get('forma_julgamento','-') or '-'}")
        st.write(f"Tipo de vigência: {contrato.get('tipo_vigencia','-') or '-'}")
        st.write(f"Nº do contrato: {contrato.get('numero_contrato','-') or '-'}")
        st.write(f"SEI (pagamento): {contrato.get('processo_sei_pagamento','-') or '-'}")

        # ✅ Expander agora mostra detalhes úteis de pagamentos (não repete SEI do contrato)
        with st.expander("Ver detalhes de pagamento (NF / Requisição / Pedido / Empenho / Medição)"):
            if pagamentos_sel.empty:
                st.info("Nenhum pagamento cadastrado para este contrato.")
            else:
                df_det = pagamentos_sel.copy()
                df_det.insert(0, "Nº", range(1, len(df_det) + 1))
                df_det["Pagamento (ID)"] = df_det["id_pagamento"].apply(lambda x: id_display(x, "PGTO"))
                df_det["Emissão"] = df_det["data_emissao_nf"].apply(fmt_data_ptbr)
                df_det["Vencimento"] = df_det["data_vencimento_nf"].apply(fmt_data_ptbr)
                df_det["Pagamento"] = df_det["data_pagamento"].apply(fmt_data_ptbr)
                df_det["Valor NF"] = df_det["valor_nf"].apply(fmt_brl)

                df_det = df_det[[
                    "Nº", "Pagamento (ID)", "numero_nf", "numero_requisicao_compra",
                    "numero_pedido_compra", "numero_empenho", "numero_medicao",
                    "Emissão", "Vencimento", "Pagamento", "Valor NF", "status_pagamento"
                ]].rename(columns={
                    "numero_nf": "NF",
                    "numero_requisicao_compra": "Requisição",
                    "numero_pedido_compra": "Pedido",
                    "numero_empenho": "Empenho",
                    "numero_medicao": "Medição",
                    "status_pagamento": "Status",
                })
                st.dataframe(df_det, width="stretch", hide_index=True)

        st.markdown("**Contato do fornecedor**")
        st.write(f"Nome: {contrato.get('fornecedor_contato_nome','-') or '-'}")
        st.write(f"E-mail: {contrato.get('fornecedor_contato_email','-') or '-'}")
        st.write(f"Telefone: {contrato.get('fornecedor_contato_telefone','-') or '-'}")

    with col2:
        st.markdown("**Valores e vigência**")
        st.write(f"Início: {fmt_data_ptbr(contrato['data_inicio_vigencia'])}")
        st.write(f"Fim: {fmt_data_ptbr(contrato['data_fim_vigencia'])}")
        st.write(f"Situação: {contrato.get('vig_icone','⚪')} {contrato.get('vig_texto','-')}")
        st.write(f"Prazo máx. pagamento (dias): {contrato.get('prazo_max_pagamento_dias','-')}")
        st.write(f"Valor global: {fmt_brl(contrato.get('valor_global'))}")
        st.write(f"Valor mensal previsto: {fmt_brl(contrato.get('valor_mensal_previsto'))}")

        st.markdown("**Gestão**")
        st.write(f"Gestor: {contrato.get('gestor_responsavel','-') or '-'}")
        st.write(f"Fiscal técnico: {contrato.get('fiscal_tecnico','-') or '-'}")

    st.markdown("**Observações**")
    st.write(contrato.get("observacoes", "-") or "-")

    st.markdown("---")
    st.markdown("#### Pagamentos vinculados (com NF / Requisição / Pedido / Medição)")

    if pagamentos_sel.empty:
        st.info("Nenhum pagamento cadastrado para este contrato ainda.")
    else:
        df_pv = pagamentos_sel.copy()
        df_pv.insert(0, "Nº", range(1, len(df_pv) + 1))
        df_pv["Pagamento (ID)"] = df_pv["id_pagamento"].apply(lambda x: id_display(x, "PGTO"))
        df_pv["Emissão"] = df_pv["data_emissao_nf"].apply(fmt_data_ptbr)
        df_pv["Vencimento"] = df_pv["data_vencimento_nf"].apply(fmt_data_ptbr)
        df_pv["Pagamento"] = df_pv["data_pagamento"].apply(fmt_data_ptbr)
        df_pv["Valor NF"] = df_pv["valor_nf"].apply(fmt_brl)
        df_pv["Situação"] = df_pv["pg_icone"] + " " + df_pv["pg_texto"]

        # NF antes de requisição
        df_pv = df_pv[[
            "Nº", "Pagamento (ID)", "processo_sei_pagamento",
            "Emissão", "Vencimento", "Pagamento", "Valor NF",
            "numero_nf", "numero_requisicao_compra", "numero_pedido_compra", "numero_medicao",
            "Situação", "status_pagamento", "observacoes"
        ]].rename(columns={
            "processo_sei_pagamento": "SEI (pagamento)",
            "numero_nf": "NF",
            "numero_requisicao_compra": "Requisição",
            "numero_pedido_compra": "Pedido",
            "numero_medicao": "Medição",
            "status_pagamento": "Status",
            "observacoes": "Obs.",
        })

        st.dataframe(df_pv, width="stretch", hide_index=True)