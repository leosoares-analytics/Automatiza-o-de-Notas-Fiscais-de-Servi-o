
import os
from datetime import date

import pandas as pd
import plotly.express as px
import psycopg2
from psycopg2 import sql
import streamlit as st
from dotenv import load_dotenv


# =========================================================
# CONFIGURAÇÃO
# =========================================================

st.set_page_config(
    page_title="Gestão de Notas Fiscais",
    page_icon="🧾",
    layout="wide"
)

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
TABLE_NAME = os.getenv("TABLE_NAME")

if not DATABASE_URL:
    st.error("❌ DATABASE_URL não encontrada no arquivo .env")
    st.stop()

if not TABLE_NAME:
    st.error("❌ TABLE_NAME não encontrada no arquivo .env")
    st.stop()


# =========================================================
# CONEXÃO
# =========================================================

def get_connection():
    return psycopg2.connect(DATABASE_URL)


# =========================================================
# FORMATAÇÃO DE VALORES
# =========================================================

def format_currency(value):
    """
    Formata valores no padrão brasileiro:

    1234.56 -> R$ 1.234,56
    25000   -> R$ 25.000,00
    """

    if pd.isna(value):
        return "-"

    value = float(value)

    formatted = f"{value:,.2f}"

    # Troca:
    # 1,234.56
    # por:
    # 1.234,56
    formatted = (
        formatted
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )

    return f"R$ {formatted}"


# =========================================================
# CARREGAR DADOS
# =========================================================

@st.cache_data(ttl=30)
def load_data():

    conn = get_connection()

    try:

        query = sql.SQL("""
            SELECT
                data_emissao,
                valor,
                numero_protocolo,
                empresa_destinataria,
                fornecedor,
                status_gerente,
                status_financeiro,
                data_gerente,
                data_financeiro,
                data_vencimento
            FROM {}
        """).format(
            sql.Identifier(TABLE_NAME)
        )

        df = pd.read_sql_query(
            query.as_string(conn),
            conn
        )

    finally:

        conn.close()

    # =====================================================
    # DATAS
    # =====================================================

    date_columns = [
        "data_emissao",
        "data_gerente",
        "data_financeiro",
        "data_vencimento"
    ]

    for column in date_columns:

        if column in df.columns:

            df[column] = pd.to_datetime(
                df[column],
                errors="coerce"
            )

    # =====================================================
    # VALOR
    # =====================================================

    df["valor"] = pd.to_numeric(
        df["valor"],
        errors="coerce"
    )

    return df


# =========================================================
# ATUALIZAR APROVAÇÃO
# =========================================================

def update_approval(numero_protocolo, etapa):

    conn = get_connection()
    cursor = conn.cursor()

    try:

        # -------------------------------------------------
        # GERENTE
        # -------------------------------------------------

        if etapa == "gerente":

            query = sql.SQL("""
                UPDATE {}
                SET
                    status_gerente = 'aprovado',
                    data_gerente = CURRENT_DATE
                WHERE numero_protocolo = %s
            """).format(
                sql.Identifier(TABLE_NAME)
            )

        # -------------------------------------------------
        # FINANCEIRO
        # -------------------------------------------------

        elif etapa == "financeiro":

            query = sql.SQL("""
                UPDATE {}
                SET
                    status_financeiro = 'aprovado',
                    data_financeiro = CURRENT_DATE
                WHERE numero_protocolo = %s
            """).format(
                sql.Identifier(TABLE_NAME)
            )

        else:

            raise ValueError("Etapa inválida")

        cursor.execute(
            query,
            (numero_protocolo,)
        )

        conn.commit()

    except Exception:

        conn.rollback()

        raise

    finally:

        cursor.close()
        conn.close()

    st.cache_data.clear()


# =========================================================
# CARREGAR DADOS DO BANCO
# =========================================================

try:

    df = load_data()

except Exception as e:

    st.error(
        "❌ Erro ao consultar o banco de dados."
    )

    st.code(str(e))

    st.stop()


# =========================================================
# TÍTULO
# =========================================================

st.title("🧾 Gestão de Notas Fiscais")

st.caption(
    f"Banco: Neon PostgreSQL  |  Tabela: {TABLE_NAME}"
)


if df.empty:

    st.warning(
        "⚠️ A conexão funcionou, mas a tabela não possui registros."
    )

    st.stop()


# =========================================================
# SIDEBAR — FILTROS
# =========================================================

st.sidebar.header("🔎 Filtros")

min_date = df["data_emissao"].min()
max_date = df["data_emissao"].max()

if pd.isna(min_date):
    min_date = date.today()

if pd.isna(max_date):
    max_date = date.today()


date_range = st.sidebar.date_input(
    "Período de emissão",
    value=(
        min_date.date(),
        max_date.date()
    )
)


suppliers = sorted(
    df["fornecedor"]
    .dropna()
    .astype(str)
    .unique()
)

selected_suppliers = st.sidebar.multiselect(
    "Fornecedor",
    suppliers
)


companies = sorted(
    df["empresa_destinataria"]
    .dropna()
    .astype(str)
    .unique()
)

selected_companies = st.sidebar.multiselect(
    "Empresa destinatária",
    companies
)


# =========================================================
# APLICAR FILTROS
# =========================================================

filtered_df = df.copy()


# ---------------------------------------------------------
# FILTRO DE DATA
# ---------------------------------------------------------

if isinstance(date_range, tuple) and len(date_range) == 2:

    start_date = pd.Timestamp(
        date_range[0]
    )

    # Inclui o dia final inteiro
    end_date = (
        pd.Timestamp(date_range[1])
        + pd.Timedelta(days=1)
    )

    filtered_df = filtered_df[
        (filtered_df["data_emissao"] >= start_date)
        &
        (filtered_df["data_emissao"] < end_date)
    ]


# ---------------------------------------------------------
# FILTRO DE FORNECEDOR
# ---------------------------------------------------------

if selected_suppliers:

    filtered_df = filtered_df[
        filtered_df["fornecedor"].isin(
            selected_suppliers
        )
    ]


# ---------------------------------------------------------
# FILTRO DE EMPRESA
# ---------------------------------------------------------

if selected_companies:

    filtered_df = filtered_df[
        filtered_df["empresa_destinataria"].isin(
            selected_companies
        )
    ]


# =========================================================
# STATUS
# =========================================================

today = pd.Timestamp(date.today())


# ---------------------------------------------------------
# GERENTE APROVADO
# ---------------------------------------------------------

filtered_df["gerente_aprovado"] = (
    filtered_df["status_gerente"]
    .fillna("")
    .astype(str)
    .str.strip()
    .str.lower()
    == "aprovado"
)


# ---------------------------------------------------------
# FINANCEIRO APROVADO
# ---------------------------------------------------------

filtered_df["financeiro_aprovado"] = (
    filtered_df["status_financeiro"]
    .fillna("")
    .astype(str)
    .str.strip()
    .str.lower()
    == "aprovado"
)


# =========================================================
# SITUAÇÃO DA NOTA
# =========================================================
#
# IMPORTANTE:
#
# Os campos do banco continuam contendo SOMENTE:
#
# status_gerente:
#     pendente / aprovado
#
# status_financeiro:
#     pendente / aprovado
#
# "Paga" e "Vencida" são situações calculadas apenas
# pelo Streamlit.
# =========================================================


# ---------------------------------------------------------
# NOTA PAGA
# ---------------------------------------------------------

filtered_df["paga"] = (
    filtered_df["gerente_aprovado"]
    &
    filtered_df["financeiro_aprovado"]
)


# ---------------------------------------------------------
# NOTA PENDENTE
# ---------------------------------------------------------

filtered_df["pendente"] = (
    ~filtered_df["paga"]
)


# ---------------------------------------------------------
# NOTA VENCIDA
# ---------------------------------------------------------

filtered_df["vencida"] = (
    filtered_df["data_vencimento"].notna()
    &
    (filtered_df["data_vencimento"] < today)
    &
    (~filtered_df["paga"])
)


# ---------------------------------------------------------
# SITUAÇÃO FINAL
# ---------------------------------------------------------

filtered_df["situação"] = "Paga"

filtered_df.loc[
    filtered_df["pendente"],
    "situação"
] = "Pendente"

filtered_df.loc[
    filtered_df["vencida"],
    "situação"
] = "Vencida"


# =========================================================
# KPIs
# =========================================================

total_value = filtered_df["valor"].sum()

total_notes = len(filtered_df)

pending_notes = filtered_df["pendente"].sum()

overdue_notes = filtered_df["vencida"].sum()


# =========================================================
# TEMPO MÉDIO DE PAGAMENTO
# =========================================================

paid_df = filtered_df[
    filtered_df["paga"]
    &
    filtered_df["data_financeiro"].notna()
    &
    filtered_df["data_emissao"].notna()
].copy()


if not paid_df.empty:

    paid_df["tempo_pagamento"] = (
        paid_df["data_financeiro"]
        - paid_df["data_emissao"]
    ).dt.days

    average_payment_time = (
        paid_df["tempo_pagamento"].mean()
    )

else:

    average_payment_time = 0


# =========================================================
# CARDS
# =========================================================

col1, col2, col3, col4, col5 = st.columns(5)


col1.metric(
    "💰 Valor total",
    format_currency(total_value)
)


col2.metric(
    "🧾 Notas",
    f"{total_notes}"
)


col3.metric(
    "⏳ Pendentes",
    f"{pending_notes}"
)


col4.metric(
    "🚨 Vencidas",
    f"{overdue_notes}"
)


col5.metric(
    "⏱️ Tempo médio",
    f"{average_payment_time:.1f} dias"
)


st.divider()


# =========================================================
# ABAS
# =========================================================

aba = st.radio(
    "Navegação",
    [
        "📊 Dashboard",
        "⏳ Pendências",
        "✅ Aprovações"
    ],
    horizontal=True,
    key="aba_atual",
    label_visibility="collapsed"
)


# =========================================================
# DASHBOARD
# =========================================================

if aba == "📊 Dashboard":

    col1, col2 = st.columns(2)


    # -----------------------------------------------------
    # VALOR POR FORNECEDOR
    # -----------------------------------------------------

    with col1:

        supplier_df = (
            filtered_df
            .groupby(
                "fornecedor",
                as_index=False
            )["valor"]
            .sum()
            .sort_values(
                "valor",
                ascending=False
            )
        )

        fig_supplier = px.bar(
            supplier_df,
            x="fornecedor",
            y="valor",
            title="💰 Valor por fornecedor",
            text_auto=".2f"
        )

        fig_supplier.update_layout(
            xaxis_title="Fornecedor",
            yaxis_title="Valor"
        )

        # Formatação do eixo Y para R$
        fig_supplier.update_yaxes(
            tickprefix="R$ ",
            separatethousands=True,
            tickformat=",.2f"
        )

        # Formatação dos valores exibidos nas barras
        fig_supplier.update_traces(
            texttemplate="R$ %{y:,.2f}",
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Valor: R$ %{y:,.2f}"
                "<extra></extra>"
            )
        )

        st.plotly_chart(
            fig_supplier,
            use_container_width=True
        )


    # -----------------------------------------------------
    # VALOR POR EMPRESA
    # -----------------------------------------------------

    with col2:

        company_df = (
            filtered_df
            .groupby(
                "empresa_destinataria",
                as_index=False
            )["valor"]
            .sum()
            .sort_values(
                "valor",
                ascending=False
            )
        )

        fig_company = px.bar(
            company_df,
            x="empresa_destinataria",
            y="valor",
            title="🏢 Valor por empresa",
            text_auto=".2f"
        )

        fig_company.update_layout(
            xaxis_title="Empresa",
            yaxis_title="Valor"
        )

        # Formatação do eixo Y para R$
        fig_company.update_yaxes(
            tickprefix="R$ ",
            separatethousands=True,
            tickformat=",.2f"
        )

        # Formatação dos valores exibidos nas barras
        fig_company.update_traces(
            texttemplate="R$ %{y:,.2f}",
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Valor: R$ %{y:,.2f}"
                "<extra></extra>"
            )
        )

        st.plotly_chart(
            fig_company,
            use_container_width=True
        )


    # -----------------------------------------------------
    # TABELA
    # -----------------------------------------------------

    st.subheader("📋 Notas fiscais")

    dashboard_df = filtered_df[
        [
            "numero_protocolo",
            "data_emissao",
            "fornecedor",
            "empresa_destinataria",
            "valor",
            "status_gerente",
            "status_financeiro",
            "data_vencimento",
            "situação"
        ]
    ].copy()


    # -----------------------------------------------------
    # FORMATAR VALORES
    # -----------------------------------------------------

    dashboard_df["valor"] = dashboard_df["valor"].apply(
        format_currency
    )


    # -----------------------------------------------------
    # FORMATAR DATAS
    # -----------------------------------------------------

    for column in [
        "data_emissao",
        "data_vencimento"
    ]:

        dashboard_df[column] = dashboard_df[column].apply(
            lambda x: x.strftime("%d/%m/%Y")
            if pd.notna(x)
            else "-"
        )


    st.dataframe(
        dashboard_df.sort_values(
            "data_emissao",
            ascending=False
        ),
        use_container_width=True,
        hide_index=True
    )


# =========================================================
# PENDÊNCIAS
# =========================================================

elif aba == "⏳ Pendências":

    st.subheader("⏳ Notas pendentes")


    # -----------------------------------------------------
    # SOMENTE NOTAS PENDENTES
    # -----------------------------------------------------

    pending_df = filtered_df[
        filtered_df["pendente"]
    ].copy()


    if pending_df.empty:

        st.success(
            "🎉 Não existem notas pendentes!"
        )

    else:

        pending_df = pending_df[
            [
                "numero_protocolo",
                "fornecedor",
                "empresa_destinataria",
                "valor",
                "data_emissao",
                "data_vencimento",
                "status_gerente",
                "status_financeiro",
                "situação"
            ]
        ].copy()


        # -------------------------------------------------
        # FORMATAR VALORES
        # -------------------------------------------------

        pending_df["valor"] = pending_df["valor"].apply(
            format_currency
        )


        # -------------------------------------------------
        # FORMATAR DATAS
        # -------------------------------------------------

        for column in [
            "data_emissao",
            "data_vencimento"
        ]:

            pending_df[column] = pending_df[column].apply(
                lambda x: x.strftime("%d/%m/%Y")
                if pd.notna(x)
                else "-"
            )


        # -------------------------------------------------
        # VENCIDAS EM VERMELHO
        # -------------------------------------------------

        def highlight_overdue(row):

            if row["situação"] == "Vencida":

                return [
                    "color: red; font-weight: bold;"
                    for _ in row
                ]

            return [""] * len(row)


        styled_pending_df = pending_df.style.apply(
            highlight_overdue,
            axis=1
        )


        st.dataframe(
            styled_pending_df,
            use_container_width=True,
            hide_index=True
        )


# =========================================================
# APROVAÇÕES
# =========================================================

elif aba == "✅ Aprovações":

    st.subheader("✅ Fluxo de aprovação")

    approval_df = filtered_df.copy()


    # -----------------------------------------------------
    # ESCOLHER PROTOCOLO
    # -----------------------------------------------------

    protocols = (
        approval_df["numero_protocolo"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )


    if not protocols:

        st.info(
            "Nenhum protocolo disponível."
        )

    else:

        selected_protocol = st.selectbox(
            "Selecione o protocolo",
            protocols,
            key="protocolo_selecionado"
        )


        note = approval_df[
            approval_df["numero_protocolo"].astype(str)
            == selected_protocol
        ]


        if not note.empty:

            row = note.iloc[0]


            # -------------------------------------------------
            # DADOS DA NOTA
            # -------------------------------------------------

            st.markdown(
                "### 📄 Dados da nota"
            )


            c1, c2, c3 = st.columns(3)


            c1.write(
                f"**Protocolo:** {row['numero_protocolo']}"
            )

            c2.write(
                f"**Fornecedor:** {row['fornecedor']}"
            )

            c3.write(
                f"**Empresa:** {row['empresa_destinataria']}"
            )


            c1, c2, c3 = st.columns(3)


            # -------------------------------------------------
            # VALOR COM FORMATO BRASILEIRO
            # -------------------------------------------------

            c1.write(
                f"**Valor:** {format_currency(row['valor'])}"
            )


            # -------------------------------------------------
            # EMISSÃO
            # -------------------------------------------------

            c2.write(
                f"**Emissão:** "
                f"{row['data_emissao'].strftime('%d/%m/%Y')}"
                if pd.notna(row["data_emissao"])
                else "**Emissão:** -"
            )


            # -------------------------------------------------
            # VENCIMENTO
            # -------------------------------------------------

            c3.write(
                f"**Vencimento:** "
                f"{row['data_vencimento'].strftime('%d/%m/%Y')}"
                if pd.notna(row["data_vencimento"])
                else "**Vencimento:** -"
            )


            # -------------------------------------------------
            # SITUAÇÃO
            # -------------------------------------------------

            if row["situação"] == "Vencida":

                st.error(
                    "🚨 Esta nota está vencida."
                )

            elif row["situação"] == "Paga":

                st.success(
                    "✅ Esta nota está paga."
                )

            else:

                st.info(
                    "⏳ Esta nota ainda possui etapas pendentes."
                )


            st.divider()


            # =================================================
            # STATUS GERENTE
            # =================================================

            st.markdown(
                "### 👨‍💼 Aprovação do gerente"
            )


            manager_approved = (
                str(row["status_gerente"]).strip().lower()
                == "aprovado"
            )


            if manager_approved:

                st.success(
                    f"✅ Gerente aprovou em "
                    f"{row['data_gerente'].strftime('%d/%m/%Y')}"
                    if pd.notna(row["data_gerente"])
                    else "✅ Gerente aprovado"
                )

            else:

                st.warning(
                    "⏳ Aguardando aprovação do gerente"
                )


                if st.button(
                    "✅ Aprovar como gerente",
                    key=f"manager_{selected_protocol}",
                    use_container_width=True
                ):

                    try:

                        update_approval(
                            selected_protocol,
                            "gerente"
                        )

                        st.success(
                            "✅ Nota aprovada pelo gerente!"
                        )

                        st.rerun()

                    except Exception as e:

                        st.error(
                            f"Erro ao aprovar: {e}"
                        )


            st.divider()


            # =================================================
            # STATUS FINANCEIRO
            # =================================================

            st.markdown(
                "### 💰 Aprovação financeira"
            )


            finance_approved = (
                str(row["status_financeiro"]).strip().lower()
                == "aprovado"
            )


            if finance_approved:

                st.success(
                    f"✅ Financeiro aprovou em "
                    f"{row['data_financeiro'].strftime('%d/%m/%Y')}"
                    if pd.notna(row["data_financeiro"])
                    else "✅ Financeiro aprovado"
                )


            elif not manager_approved:

                st.info(
                    "🔒 A aprovação financeira está bloqueada "
                    "até a aprovação do gerente."
                )


            else:

                st.warning(
                    "⏳ Aguardando aprovação financeira"
                )


                if st.button(
                    "💰 Aprovar como financeiro",
                    key=f"finance_{selected_protocol}",
                    use_container_width=True
                ):

                    try:

                        update_approval(
                            selected_protocol,
                            "financeiro"
                        )

                        st.success(
                            "✅ Nota aprovada pelo financeiro!"
                        )

                        st.rerun()

                    except Exception as e:

                        st.error(
                            f"Erro ao aprovar: {e}"
                        )


# =========================================================
# RODAPÉ
# =========================================================

st.sidebar.divider()

st.sidebar.caption(
    "🧾 Sistema de Gestão de Notas Fiscais"
)

st.sidebar.caption(
    "Neon PostgreSQL + Streamlit"
)

