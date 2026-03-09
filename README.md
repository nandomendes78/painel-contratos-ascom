[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://painel-contratos-ascom.streamlit.app)

# Painel de Contratos – ASCOM (ARTESP)

MVP para gestão de contratos e pagamentos da comunicação – ARTESP.

## 🎯 Objetivo
Centralizar o controle de:
- Vigência de contratos (alertas por prazo)
- Pagamentos (vencimentos, atrasos e status)
- Detalhes por contrato (fornecedor, contato, etc.)

## ✨ Funcionalidades Principais

Contadores em Tempo Real
- Alertas de Criticidade: Identificação imediata de contratos ou pagamentos vencidos.
- Linha do Tempo de Vigência: Tabela com sinalização em verde, amarelo e vermelho, indicando os dias restantes para o término do contrato.

Gestão de Contratos e SEI
- Rastreabilidade: Vinculação direta com o número do processo no sistema SEI.
- Detalhamento de Modalidade: Diferenciação entre Concorrência, Pregão, Dispensa e Inexigibilidade.
- Monitoramento de Status: Acompanhamento desde a fase de elaboração e análise (CJ) até a vigência plena.

## Controle Financeiro de Pagamentos

- Fluxo de Caixa: Monitoramento de Notas Fiscais, Datas de Emissão e Vencimentos.
- Indicadores de Performance: Classificação automática de pagamentos como "Pago em dia", "Pago com atraso" ou "Vencido".
- Dados de Liquidação: Registro de números de Empenho, Requisição e Medição por parcela.

Deep Dive: Detalhes do Contrato
- Dados Cadastrais: CNPJ, Valor Global e Valor Mensal previsto.
- Contatos Diretos: E-mail e telefone dos representantes dos fornecedores.
- Equipe Responsável: Identificação nominal do Gestor e do Fiscal Técnico do contrato.

## 🚀 Acesso ao aplicativo

O painel pode ser acessado online pelo link:

🔗 https://painel-contratos-ascom.streamlit.app

Aplicação hospedada no Streamlit Cloud.

## 🧱 Tecnologias
- Python
- Streamlit
- SQLite
- Pandas

## 🖼️ Print do painel
![Visão Geral](assets/imagem_pagina.jpeg)

## ▶️ Como rodar localmente (Windows)
```bash
# 1) entrar na pasta
cd C:\Dev\ARTESP\painel_contratos

# 2) ativar venv
.\.venv\Scripts\activate

# 3) instalar dependências
pip install -r requirements.txt

# 4) criar banco (tabelas)
python database.py

# 5) (opcional) carregar dados fictícios (se existir seed)
# python seed.py

# 6) rodar o app
streamlit run app.py
