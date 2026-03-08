import sqlite3

DB_PATH = "database.db"


def main() -> None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # garante FK
    cur.execute("PRAGMA foreign_keys = ON;")

    # =========================
    # TABELA: fornecedor
    # =========================
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS fornecedor (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            cnpj TEXT,
            contato_nome TEXT,
            contato_email TEXT,
            contato_telefone TEXT,
            UNIQUE(nome, cnpj)
        );
        """
    )

    # =========================
    # TABELA: contrato
    # =========================
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS contrato (
            id_contrato TEXT PRIMARY KEY,
            nome_contrato TEXT NOT NULL,
            modalidade TEXT,
            forma_julgamento TEXT,
            tipo_vigencia TEXT,
            processo_sei_contrato TEXT,
            numero_contrato TEXT,
            processo_sei_pagamento TEXT,

            fornecedor_id INTEGER,

            data_inicio_vigencia TEXT,
            data_fim_vigencia TEXT,

            prazo_max_pagamento_dias TEXT,
            valor_global REAL,
            valor_mensal_previsto REAL,

            status_contrato TEXT,
            gestor_responsavel TEXT,
            fiscal_tecnico TEXT,
            observacoes TEXT,

            FOREIGN KEY (fornecedor_id) REFERENCES fornecedor(id)
        );
        """
    )

    # =========================
    # TABELA: pagamento
    # =========================
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS pagamento (
            id_pagamento TEXT PRIMARY KEY,
            id_contrato TEXT NOT NULL,

            processo_sei_pagamento TEXT,
            data_emissao_nf TEXT,
            data_vencimento_nf TEXT,
            data_pagamento TEXT,

            valor_nf REAL,
            numero_nf TEXT,
            numero_requisicao_compra TEXT,
            numero_pedido_compra TEXT,
            numero_empenho TEXT,
            numero_medicao TEXT,

            tipo_pagamento TEXT,
            status_pagamento TEXT,
            observacoes TEXT,

            FOREIGN KEY (id_contrato) REFERENCES contrato(id_contrato)
        );
        """
    )

    conn.commit()
    conn.close()

    print("Tabelas criadas/atualizadas com sucesso!")


if __name__ == "__main__":
    main()