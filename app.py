import streamlit as st
import pandas as pd
from conciliacao import (
    ler_contabil,
    ler_financeiro,
    filtrar_financeiro,
    separar_orfaos,
    conciliar,
    resumo_macro,
    drill_down,
    gerar_excel,
)

# ── Configuração da página ────────────────────────────────────────────────────
st.set_page_config(
    page_title="Conciliação de Clientes — LLE",
    page_icon="📊",
    layout="wide",
)

# ── CSS padrão visual LLE ─────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Montserrat', Calibri, sans-serif;
}

/* Header principal */
.lle-header {
    background: #041747;
    padding: 24px 32px;
    border-radius: 8px;
    margin-bottom: 24px;
    display: flex;
    align-items: center;
    gap: 16px;
}
.lle-header h1 {
    color: #FFFFFF;
    font-size: 22px;
    font-weight: 700;
    margin: 0;
}
.lle-header p {
    color: #FAC318;
    font-size: 13px;
    margin: 4px 0 0 0;
}

/* Cards de métricas */
.metric-card {
    background: #041747;
    border-radius: 8px;
    padding: 16px 20px;
    text-align: center;
}
.metric-card .label {
    color: #FAC318;
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1px;
}
.metric-card .value {
    color: #FFFFFF;
    font-size: 22px;
    font-weight: 700;
    margin-top: 4px;
}
.metric-card .value.ok { color: #0F8C3B; }
.metric-card .value.divergencia { color: #FF4444; }

/* Seção */
.secao-titulo {
    background: #041747;
    color: #FFFFFF;
    font-weight: 700;
    font-size: 13px;
    padding: 8px 16px;
    border-radius: 6px 6px 0 0;
    margin-bottom: 0;
    letter-spacing: 0.5px;
}

/* Status badges */
.badge-contabil {
    background: #FFE6E6;
    color: #C00000;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 600;
}
.badge-financeiro {
    background: #FFE6E6;
    color: #C00000;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 600;
}
.badge-diferenca {
    background: #FFF4CC;
    color: #041747;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 700;
}

/* Drill-down NF status */
.nf-ok { background-color: #D9F2DC; color: #0F8C3B; }
.nf-diverge { background-color: #FFF4CC; color: #041747; font-weight: bold; }
.nf-so { background-color: #FFE6E6; color: #C00000; }
.nf-compensa { background-color: #F2F2F2; color: #595959; }

/* Upload area */
.stFileUploader > div {
    border: 2px dashed #0071FE !important;
    border-radius: 8px !important;
}

/* Botões */
.stButton > button {
    background: #041747 !important;
    color: #FFFFFF !important;
    border: none !important;
    font-family: 'Montserrat', sans-serif !important;
    font-weight: 700 !important;
    border-radius: 6px !important;
    padding: 8px 24px !important;
}
.stButton > button:hover {
    background: #0071FE !important;
}

/* Download button */
.stDownloadButton > button {
    background: #0F8C3B !important;
    color: #FFFFFF !important;
    border: none !important;
    font-family: 'Montserrat', sans-serif !important;
    font-weight: 700 !important;
    border-radius: 6px !important;
}

/* Tabela parceiros */
.tabela-parceiros th {
    background: #041747 !important;
    color: white !important;
}

/* Divider */
hr { border-color: #D9D9D9; }

/* Selectbox */
.stSelectbox label { font-weight: 600; color: #041747; }
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="lle-header">
    <div>
        <h1>📊 Conciliação de Clientes — Grupo LLE</h1>
        <p>Contabilidade · Comparação Contábil × Financeiro por CODPARC</p>
    </div>
</div>
""", unsafe_allow_html=True)

# ── Estado da sessão ──────────────────────────────────────────────────────────
if "etapa" not in st.session_state:
    st.session_state.etapa = "upload"
if "df_cli_ok" not in st.session_state:
    st.session_state.df_cli_ok = None
if "df_fin_ok" not in st.session_state:
    st.session_state.df_fin_ok = None
if "orfaos_cli" not in st.session_state:
    st.session_state.orfaos_cli = None
if "orfaos_fin" not in st.session_state:
    st.session_state.orfaos_fin = None
if "df_fin_filtrado" not in st.session_state:
    st.session_state.df_fin_filtrado = None
if "df_cli_raw" not in st.session_state:
    st.session_state.df_cli_raw = None
if "resultado" not in st.session_state:
    st.session_state.resultado = None
if "resumo" not in st.session_state:
    st.session_state.resumo = None
if "observacoes" not in st.session_state:
    st.session_state.observacoes = {}


# ══════════════════════════════════════════════════════════════════════════════
# ETAPA 1 — UPLOAD
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.etapa == "upload":

    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<div class="secao-titulo">📁 Base Contábil (Clientes)</div>', unsafe_allow_html=True)
        arq_cli = st.file_uploader(
            "Arquivo exportado do sistema contábil",
            type=["xlsx"],
            key="upload_cli",
            label_visibility="collapsed",
        )
        if arq_cli:
            st.success(f"✅ {arq_cli.name}")

    with col2:
        st.markdown('<div class="secao-titulo">📁 Base Financeira (Data Base)</div>', unsafe_allow_html=True)
        arq_fin = st.file_uploader(
            "Arquivo exportado do sistema financeiro",
            type=["xlsx"],
            key="upload_fin",
            label_visibility="collapsed",
        )
        if arq_fin:
            st.success(f"✅ {arq_fin.name}")

    st.markdown("<br>", unsafe_allow_html=True)

    if arq_cli and arq_fin:
        if st.button("▶ Carregar e verificar bases", use_container_width=True):
            with st.spinner("Lendo arquivos e aplicando filtros LLE..."):
                try:
                    df_cli = ler_contabil(arq_cli)
                    df_fin_bruto = ler_financeiro(arq_fin)
                    df_fin_filtrado = filtrar_financeiro(df_fin_bruto)

                    df_cli_ok, df_fin_ok, orfaos_cli, orfaos_fin = separar_orfaos(
                        df_cli, df_fin_filtrado
                    )

                    st.session_state.df_cli_raw = df_cli
                    st.session_state.df_cli_ok = df_cli_ok
                    st.session_state.df_fin_ok = df_fin_ok
                    st.session_state.df_fin_filtrado = df_fin_filtrado
                    st.session_state.orfaos_cli = orfaos_cli
                    st.session_state.orfaos_fin = orfaos_fin

                    total_orfaos = len(orfaos_cli) + len(orfaos_fin)

                    if total_orfaos > 0:
                        st.session_state.etapa = "orfaos"
                    else:
                        st.session_state.etapa = "processar"

                    st.rerun()

                except Exception as e:
                    st.error(f"Erro ao ler os arquivos: {e}")
                    st.exception(e)


# ══════════════════════════════════════════════════════════════════════════════
# ETAPA 2 — ATRIBUIÇÃO DE ÓRFÃOS
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.etapa == "orfaos":

    orfaos_cli = st.session_state.orfaos_cli
    orfaos_fin = st.session_state.orfaos_fin
    df_cli_ok = st.session_state.df_cli_ok

    # Mapa de nomes para sugestão de CODPARC
    nomes_codparc = (
        df_cli_ok.groupby("NOMEPARC")["CODPARC"]
        .first()
        .reset_index()
        .set_index("NOMEPARC")["CODPARC"]
        .to_dict()
    )

    st.markdown("""
    <div style="background:#FFF4CC; border-left:4px solid #FAC318; padding:12px 16px; border-radius:4px; margin-bottom:16px;">
        <strong style="color:#041747;">⚠️ Órfãos encontrados — atribua um CODPARC antes de conciliar</strong><br>
        <span style="color:#595959; font-size:13px;">Lançamentos sem CODPARC não entram no cálculo por parceiro. 
        Preencha o campo abaixo para cada um ou deixe em branco para manter como órfão.</span>
    </div>
    """, unsafe_allow_html=True)

    atribuicoes = {}

    if len(orfaos_cli) > 0:
        st.markdown('<div class="secao-titulo">📋 Contábil — Lançamentos sem CODPARC</div>', unsafe_allow_html=True)
        for idx, row in orfaos_cli.iterrows():
            c1, c2, c3, c4 = st.columns([2, 2, 1, 2])
            c1.write(f"**{row.get('NOMEPARC', '—')}**")
            c2.write(f"NF {row.get('NUMNOTA', '—')}")
            c3.write(f"R$ {row.get('VLRDESDOB', 0):,.2f}")

            # Sugestão automática pelo nome
            sugestao = nomes_codparc.get(str(row.get("NOMEPARC", "")), "")
            cod = c4.text_input(
                "CODPARC",
                value=str(int(sugestao)) if sugestao else "",
                key=f"orf_cli_{idx}",
                label_visibility="collapsed",
                placeholder="Digite o CODPARC",
            )
            if cod.strip():
                try:
                    atribuicoes[idx] = int(cod.strip())
                except ValueError:
                    c4.warning("Somente números")

    if len(orfaos_fin) > 0:
        st.markdown('<br><div class="secao-titulo">📋 Financeiro — Lançamentos sem CODPARC</div>', unsafe_allow_html=True)
        for idx, row in orfaos_fin.iterrows():
            c1, c2, c3 = st.columns([3, 2, 1])
            c1.write(f"**{row.get('NOMEPARC', '—')}**")
            c2.write(f"NF {row.get('NUMNOTA', '—')}")
            c3.write(f"R$ {row.get('VLRDESDOB', 0):,.2f}")

    st.markdown("<br>", unsafe_allow_html=True)
    col_btn1, col_btn2 = st.columns(2)

    with col_btn1:
        if st.button("✅ Confirmar e conciliar", use_container_width=True):
            # Aplicar atribuições
            orfaos_atualizados = orfaos_cli.copy()
            for idx, codparc in atribuicoes.items():
                orfaos_atualizados.loc[idx, "CODPARC"] = codparc

            # Mesclar órfãos atualizados que ganharam CODPARC
            orfaos_com_cod = orfaos_atualizados[
                ~(orfaos_atualizados["CODPARC"].isna() | (orfaos_atualizados["CODPARC"] == 0))
            ]
            orfaos_sem_cod = orfaos_atualizados[
                orfaos_atualizados["CODPARC"].isna() | (orfaos_atualizados["CODPARC"] == 0)
            ]

            df_cli_final = pd.concat(
                [st.session_state.df_cli_ok, orfaos_com_cod], ignore_index=True
            )

            st.session_state.df_cli_ok = df_cli_final
            st.session_state.orfaos_cli = orfaos_sem_cod  # apenas os que ficaram órfãos
            st.session_state.etapa = "processar"
            st.rerun()

    with col_btn2:
        if st.button("↩ Voltar ao upload", use_container_width=False):
            st.session_state.etapa = "upload"
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# ETAPA 3 — PROCESSAMENTO E RESULTADO
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.etapa == "processar":

    if st.session_state.resultado is None:
        with st.spinner("Processando conciliação..."):
            df_cli_ok = st.session_state.df_cli_ok
            df_fin_ok = st.session_state.df_fin_ok
            orfaos_cli = st.session_state.orfaos_cli
            orfaos_fin = st.session_state.orfaos_fin
            df_fin_filtrado = st.session_state.df_fin_filtrado

            df_divergentes = conciliar(df_cli_ok, df_fin_ok)
            res = resumo_macro(df_cli_ok, df_fin_ok, df_divergentes, orfaos_cli, orfaos_fin)

            st.session_state.resultado = df_divergentes
            st.session_state.resumo = res

    df_divergentes = st.session_state.resultado
    res = st.session_state.resumo

    # ── Métricas macro ─────────────────────────────────────────────────────────
    st.markdown('<div class="secao-titulo">📈 Resumo da Conciliação</div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    c1, c2, c3, c4, c5 = st.columns(5)

    def fmt_brl(valor):
        return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    def card(col, label, value, classe=""):
        col.markdown(f"""
        <div class="metric-card">
            <div class="label">{label}</div>
            <div class="value {classe}">{value}</div>
        </div>
        """, unsafe_allow_html=True)

    card(c1, "Total Contábil", fmt_brl(res['total_contabil']))
    card(c2, "Total Financeiro", fmt_brl(res['total_financeiro']))
    card(c3, "Diferença Macro", fmt_brl(res['diferenca_macro']))
    card(c4, "Parceiros com diferença", str(res["qtd_parceiros"]))
    status_classe = "ok" if "OK" in res["status"] else "divergencia"
    card(c5, "Validação", res["status"], status_classe)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Tabela de diferenças com observações editáveis ────────────────────────
    st.markdown('<div class="secao-titulo">🔍 Parceiros com Diferença — ordenados por |Diferença| decrescente</div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    # Cabeçalho via colunas Streamlit
    cab = st.columns([0.3, 0.9, 2, 0.6, 0.6, 1.1, 1.1, 1.4, 1, 2])
    labels_cab = ["#", "CODPARC", "Parceiro", "Qtd NFs Cont.", "Qtd NFs Fin.",
                  "Soma Contábil", "Soma Financeiro", "Status", "Diferença", "📝 Observação do Analista"]
    for col, lbl in zip(cab, labels_cab):
        col.markdown(f"<div style='background:#041747;color:#FAC318;font-weight:700;font-size:11px;padding:6px 4px;text-align:center'>{lbl}</div>", unsafe_allow_html=True)

    for i, (_, row) in enumerate(df_divergentes.iterrows(), start=1):
        codparc = int(row["CODPARC"])
        dif = row["DIFERENCA"]
        cor_dif = "#C00000" if dif > 0 else "#0071FE"
        status = row["STATUS"]
        if "Contábil" in status:
            cor_st, bg_st = "#C00000", "#FFE6E6"
        elif "Financeiro" in status:
            cor_st, bg_st = "#C00000", "#FFE6E6"
        else:
            cor_st, bg_st = "#041747", "#FFF4CC"
        bg = "#FFFFFF" if i % 2 == 1 else "#F5F7FA"
        borda = "border-bottom:1px solid #D9D9D9;"

        c0, c1, c2, c3, c4, c5, c6, c7, c8, c9 = st.columns([0.3, 0.9, 2, 0.6, 0.6, 1.1, 1.1, 1.4, 1, 2])

        cel = f"background:{bg};{borda}padding:6px 4px;font-size:12px;"
        c0.markdown(f"<div style='{cel}text-align:center;color:#595959'>{i}</div>", unsafe_allow_html=True)
        c1.markdown(f"<div style='{cel}text-align:center'>{codparc}</div>", unsafe_allow_html=True)
        c2.markdown(f"<div style='{cel}font-weight:600'>{row['NOMEPARC']}</div>", unsafe_allow_html=True)
        c3.markdown(f"<div style='{cel}text-align:center'>{int(row['QTD_CLI'])}</div>", unsafe_allow_html=True)
        c4.markdown(f"<div style='{cel}text-align:center'>{int(row['QTD_FIN'])}</div>", unsafe_allow_html=True)
        c5.markdown(f"<div style='{cel}text-align:right'>{fmt_brl(row['SOMA_CLI'])}</div>", unsafe_allow_html=True)
        c6.markdown(f"<div style='{cel}text-align:right'>{fmt_brl(row['SOMA_FIN'])}</div>", unsafe_allow_html=True)
        c7.markdown(f"<div style='background:{bg_st};{borda}padding:6px 4px;font-size:11px;text-align:center;color:{cor_st};font-weight:700'>{status}</div>", unsafe_allow_html=True)
        c8.markdown(f"<div style='{cel}text-align:right;color:{cor_dif};font-weight:700'>{fmt_brl(dif)}</div>", unsafe_allow_html=True)

        obs_atual = st.session_state.observacoes.get(codparc, "")
        nova_obs = c9.text_input(
            label="obs",
            value=obs_atual,
            key=f"obs_{codparc}",
            label_visibility="collapsed",
            placeholder="Digite a observação...",
        )
        if nova_obs != obs_atual:
            st.session_state.observacoes[codparc] = nova_obs

    st.markdown("<div style='border-bottom:2px solid #041747;margin-bottom:16px'></div>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    # ── Drill-down interativo ──────────────────────────────────────────────────
    st.markdown('<div class="secao-titulo">🔎 Drill-Down por Parceiro</div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    opcoes = [
        f"{int(row['CODPARC'])} — {row['NOMEPARC']}"
        for _, row in df_divergentes.iterrows()
    ]

    selecao = st.selectbox(
        "Selecione o parceiro para investigar:",
        options=opcoes,
        index=0,
        key="drill_select",
    )

    if selecao:
        codparc_selecionado = int(selecao.split(" — ")[0])
        nome_selecionado = selecao.split(" — ")[1]

        nfs_cli, nfs_fin, resumo_nf = drill_down(
            codparc_selecionado,
            st.session_state.df_cli_ok,
            st.session_state.df_fin_ok,
        )

        # Mini resumo do parceiro
        row_parceiro = df_divergentes[df_divergentes["CODPARC"] == codparc_selecionado].iloc[0]
        col_a, col_b, col_c, col_d = st.columns(4)
        col_a.metric("Soma Contábil", fmt_brl(row_parceiro['SOMA_CLI']))
        col_b.metric("Soma Financeiro", fmt_brl(row_parceiro['SOMA_FIN']))
        col_c.metric("Diferença", fmt_brl(row_parceiro['DIFERENCA']))
        col_d.metric("Status", row_parceiro["STATUS"])

        st.markdown("<br>", unsafe_allow_html=True)

        # Tabela resumo por NF com status
        st.markdown("**📋 Resumo por Nota Fiscal**")

        def colorir_status_nf(val):
            mapa = {
                "OK": "background-color: #D9F2DC; color: #0F8C3B;",
                "Diverge": "background-color: #FFF4CC; color: #041747; font-weight: bold;",
                "Só Contábil": "background-color: #FFE6E6; color: #C00000;",
                "Só Financeiro": "background-color: #FFE6E6; color: #C00000;",
                "Compensa internamente": "background-color: #F2F2F2; color: #595959;",
            }
            return mapa.get(val, "")

        styled_nf = (
            resumo_nf[["NF", "Σ_Contábil", "Σ_Financeiro", "Δ", "Status"]]
            .style
            .map(colorir_status_nf, subset=["Status"])
            .format({
                "Σ_Contábil": "R$ {:,.2f}",
                "Σ_Financeiro": "R$ {:,.2f}",
                "Δ": "R$ {:,.2f}",
            })
            .set_properties(**{"font-family": "Calibri, sans-serif", "font-size": "12px"})
        )
        st.dataframe(styled_nf, use_container_width=True, height=280)

        # NFs lado a lado
        st.markdown("<br>", unsafe_allow_html=True)
        col_cli, col_fin = st.columns(2)

        with col_cli:
            st.markdown(
                f'<div style="background:#0071FE;color:white;padding:6px 12px;border-radius:4px;font-weight:700;font-size:13px;">📋 NFs CONTÁBIL ({len(nfs_cli)} lançamentos)</div>',
                unsafe_allow_html=True
            )
            if len(nfs_cli) > 0:
                st.dataframe(
                    nfs_cli.style.format({"Valor (R$)": "R$ {:,.2f}"}),
                    use_container_width=True,
                    height=250,
                )
            else:
                st.info("Nenhum lançamento contábil para este parceiro.")

        with col_fin:
            st.markdown(
                f'<div style="background:#0F8C3B;color:white;padding:6px 12px;border-radius:4px;font-weight:700;font-size:13px;">📋 NFs FINANCEIRO ({len(nfs_fin)} lançamentos)</div>',
                unsafe_allow_html=True
            )
            if len(nfs_fin) > 0:
                st.dataframe(
                    nfs_fin.style.format({"Valor (R$)": "R$ {:,.2f}"}),
                    use_container_width=True,
                    height=250,
                )
            else:
                st.info("Nenhum lançamento financeiro para este parceiro.")

    st.markdown("<br><hr>", unsafe_allow_html=True)

    # ── Download e ações ───────────────────────────────────────────────────────
    col_dl, col_reiniciar = st.columns([2, 1])

    with col_dl:
        with st.spinner("Preparando Excel..."):
            excel_bytes = gerar_excel(
                st.session_state.df_fin_filtrado,
                df_divergentes,
                res,
                st.session_state.orfaos_cli,
                st.session_state.orfaos_fin,
                st.session_state.observacoes,
            )
        st.download_button(
            label="⬇️ Baixar resultado em Excel",
            data=excel_bytes,
            file_name="conciliacao_clientes_LLE.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

    with col_reiniciar:
        if st.button("🔄 Nova conciliação", use_container_width=True):
            for key in ["etapa", "df_cli_ok", "df_fin_ok", "orfaos_cli", "orfaos_fin",
                        "df_fin_filtrado", "df_cli_raw", "resultado", "resumo", "observacoes"]:
                st.session_state.pop(key, None)
            st.rerun()
