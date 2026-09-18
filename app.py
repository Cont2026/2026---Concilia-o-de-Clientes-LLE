import streamlit as st
import pandas as pd
import re

import banco
from receitas import RECEITAS
from conciliacao import (
    ler_contabil,
    ler_financeiro,
    conciliar_conta,
    drill_down,
    gerar_excel,
)

# ══════════════════════════════════════════════════════════════════════════════
# Formatação BR
# ══════════════════════════════════════════════════════════════════════════════
def fmt_brl(valor):
    try:
        return f"R$ {float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        return valor

def fmt_int(valor):
    try:
        if pd.isna(valor):
            return "—"
        return f"{int(float(valor))}"
    except (ValueError, TypeError):
        return "—" if valor in (None, "") else str(valor)

def fmt_nf(valor):
    try:
        if pd.isna(valor):
            return ""
        return f"{int(float(valor))}"
    except (ValueError, TypeError):
        return "" if valor in (None, "") else str(valor)

def norm_nome(s):
    if not s:
        return ""
    s = re.sub(r"[^a-zA-Z0-9À-ÿ ]", "", str(s))
    return " ".join(s.split()).upper()

def mes_key(mes_ref):
    ano, mes = mes_ref
    return f"{int(ano):04d}-{int(mes):02d}"


# ══════════════════════════════════════════════════════════════════════════════
# Store em memória do servidor (bases/resultados da sessão de trabalho).
# A ANÁLISE (observações + fantasmas) é persistida no Neon por mês+conta.
# ══════════════════════════════════════════════════════════════════════════════
@st.cache_resource
def _get_store():
    return {
        "processado": False,
        "mes_ref": None,
        "bases": {},
        "contabeis": {},
        "atrib": {},
        "resultados": {},
        "obs": {},
    }

store = _get_store()

MESES = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
         "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]

CONTAS_CONTABEIS = {
    "clientes": "Clientes",
    "adiantamento": "Adiantamento de Clientes",
    "cartao_credito": "Cartão de Crédito",
    "cartao_debito": "Cartão de Débito",
    "operacao_cartao": "Operação com Cartão",
}


def recomputa_conta(conta_id):
    """Reaplica as atribuições de fantasmas e recalcula uma conta."""
    receita = RECEITAS[conta_id]
    raw = store["contabeis"].get(conta_id)
    if raw is None:
        return
    df_cli = raw.copy()
    for idx, cod in store["atrib"].get(conta_id, {}).items():
        if idx in df_cli.index:
            df_cli.loc[idx, "CODPARC"] = cod
    store["resultados"][conta_id] = conciliar_conta(
        receita, df_cli, store["bases"], store["mes_ref"]
    )


# ══════════════════════════════════════════════════════════════════════════════
# Configuração e CSS
# ══════════════════════════════════════════════════════════════════════════════
st.set_page_config(page_title="Conciliações — LLE", page_icon="📊", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Montserrat', Calibri, sans-serif; }
.lle-header { background:#041747; padding:20px 28px; border-radius:8px; margin-bottom:20px; }
.lle-header h1 { color:#FFFFFF; font-size:20px; font-weight:700; margin:0; }
.lle-header p { color:#FAC318; font-size:12px; margin:4px 0 0 0; }
.metric-card { background:#041747; border-radius:8px; padding:14px 18px; text-align:center; }
.metric-card .label { color:#FAC318; font-size:10px; font-weight:700; text-transform:uppercase; letter-spacing:1px; }
.metric-card .value { color:#FFFFFF; font-size:20px; font-weight:700; margin-top:4px; }
.metric-card .value.ok { color:#0F8C3B; }
.metric-card .value.divergencia { color:#FF4444; }
.secao-titulo { background:#041747; color:#FFFFFF; font-weight:700; font-size:13px; padding:8px 16px; border-radius:6px 6px 0 0; letter-spacing:0.5px; }
.stButton > button { background:#041747 !important; color:#FFFFFF !important; border:none !important; font-family:'Montserrat',sans-serif !important; font-weight:700 !important; border-radius:6px !important; }
.stButton > button:hover { background:#0071FE !important; }
.stDownloadButton > button { background:#0F8C3B !important; color:#FFFFFF !important; border:none !important; font-weight:700 !important; border-radius:6px !important; }
.stFileUploader > div { border:2px dashed #0071FE !important; border-radius:8px !important; }
hr { border-color:#D9D9D9; }
section[data-testid="stSidebar"] { background:#0A1F3C; }
section[data-testid="stSidebar"] * { color:#FFFFFF; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="lle-header">
    <h1>📊 Conciliações — Grupo LLE</h1>
    <p>Contabilidade · Comparação Contábil × Financeiro por CODPARC</p>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("### 📁 Conciliações")

    # Status do Neon
    if banco.disponivel():
        st.caption("💾 Neon conectado — análise salva automaticamente.")
    else:
        st.caption("⚠️ Sem Neon — análise só na memória desta sessão.")

    if store["processado"]:
        ano, mes = store["mes_ref"]
        mk = mes_key(store["mes_ref"])
        st.caption(f"Mês em análise: **{MESES[mes-1]}/{ano}**")
        st.markdown("---")

        contas_ok = [cid for cid in RECEITAS if cid in store["resultados"]]
        if "conta_ativa" not in st.session_state or st.session_state.conta_ativa not in contas_ok:
            st.session_state.conta_ativa = contas_ok[0] if contas_ok else None

        for cid in contas_ok:
            qtd = len(store["resultados"][cid]["divergentes"])
            marca = "▶ " if st.session_state.conta_ativa == cid else ""
            if st.button(f"{marca}{RECEITAS[cid]['nome']}  ({qtd})",
                         key=f"nav_{cid}", use_container_width=True):
                st.session_state.conta_ativa = cid
                st.rerun()

        st.markdown("---")
        with st.expander("🧹 Resetar análise"):
            st.caption("Apaga observações e fantasmas salvos das contas escolhidas (só deste mês).")
            nomes_sel = st.multiselect(
                "Contas a resetar:",
                [RECEITAS[c]["nome"] for c in contas_ok],
                key="reset_sel",
            )
            confirma = st.checkbox("Confirmo que quero apagar", key="reset_conf")
            if st.button("Resetar selecionadas", use_container_width=True):
                if nomes_sel and confirma:
                    ids = [c for c in contas_ok if RECEITAS[c]["nome"] in nomes_sel]
                    for cid in ids:
                        banco.resetar(mk, cid)
                        store["obs"][cid] = {}
                        store["atrib"][cid] = {}
                        recomputa_conta(cid)
                    st.success(f"Resetadas: {', '.join(nomes_sel)}")
                    st.rerun()
                else:
                    st.warning("Escolha ao menos uma conta e marque a confirmação.")

        st.markdown("---")
        if st.button("↩ Nova conciliação (voltar ao upload)", use_container_width=True):
            store.update({
                "processado": False, "mes_ref": None, "bases": {},
                "contabeis": {}, "atrib": {}, "resultados": {}, "obs": {},
            })
            st.session_state.pop("conta_ativa", None)
            st.rerun()
        st.caption("Isto não apaga o que está salvo no Neon — só limpa a sessão para subir novos arquivos.")
    else:
        st.caption("Suba os arquivos e clique em Processar para começar.")


# ══════════════════════════════════════════════════════════════════════════════
# TELA DE UPLOAD
# ══════════════════════════════════════════════════════════════════════════════
if not store["processado"]:
    st.markdown('<div class="secao-titulo">🗓️ Mês da conciliação</div>', unsafe_allow_html=True)
    cma, cmb, _ = st.columns([1, 1, 3])
    mes_nome = cma.selectbox("Mês", MESES, index=5, key="sel_mes")
    ano = cmb.number_input("Ano", min_value=2020, max_value=2100, value=2026, step=1, key="sel_ano")
    mes = MESES.index(mes_nome) + 1

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="secao-titulo">📥 Bases Financeiras (Data Base)</div>', unsafe_allow_html=True)
    cf1, cf2 = st.columns(2)
    up_receita = cf1.file_uploader("Data Base — RECEITA", type=["xlsx"], key="up_receita")
    up_despesa = cf2.file_uploader("Data Base — DESPESA", type=["xlsx"], key="up_despesa")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="secao-titulo">📥 Bases Contábeis (uma por conta)</div>', unsafe_allow_html=True)
    ups_contabil = {}
    cols = st.columns(3)
    for i, (cid, nome) in enumerate(CONTAS_CONTABEIS.items()):
        ups_contabil[cid] = cols[i % 3].file_uploader(nome, type=["xlsx"], key=f"up_{cid}")

    st.markdown("<br>", unsafe_allow_html=True)

    tem_receita = up_receita is not None
    tem_algum_contabil = any(v is not None for v in ups_contabil.values())

    if not tem_receita:
        st.info("A Data Base de **Receita** é obrigatória para começar.")
    if up_despesa is None:
        st.warning("Sem a Data Base de **Despesa**, as contas *Operação com Cartão* e a parte de despesa do *Adiantamento* ficarão incompletas.")

    if st.button("▶ Processar conciliações", use_container_width=True,
                 disabled=not (tem_receita and tem_algum_contabil)):
        with st.spinner("Lendo arquivos e processando as contas..."):
            try:
                bases = {"receita": ler_financeiro(up_receita)}
                if up_despesa is not None:
                    bases["despesa"] = ler_financeiro(up_despesa)

                store["bases"] = bases
                store["mes_ref"] = (int(ano), int(mes))
                store["contabeis"] = {}
                store["atrib"] = {}
                store["resultados"] = {}
                store["obs"] = {}
                mk = mes_key(store["mes_ref"])

                for cid in RECEITAS:
                    up = ups_contabil.get(cid)
                    if up is None:
                        continue
                    df_cont = ler_contabil(up)
                    store["contabeis"][cid] = df_cont

                    # carrega análise salva no Neon para este mês/conta
                    obs_salvas, atrib_salvas = banco.carregar(mk, cid)
                    store["obs"][cid] = obs_salvas
                    store["atrib"][cid] = atrib_salvas

                    # aplica os fantasmas já atribuídos e concilia
                    df_apl = df_cont.copy()
                    for idx, cod in atrib_salvas.items():
                        if idx in df_apl.index:
                            df_apl.loc[idx, "CODPARC"] = cod
                    store["resultados"][cid] = conciliar_conta(
                        RECEITAS[cid], df_apl, bases, store["mes_ref"]
                    )

                store["processado"] = True
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao processar: {e}")
                st.exception(e)


# ══════════════════════════════════════════════════════════════════════════════
# TELA DE RESULTADO
# ══════════════════════════════════════════════════════════════════════════════
else:
    conta = st.session_state.get("conta_ativa")
    if not conta or conta not in store["resultados"]:
        st.info("Selecione uma conta na barra lateral.")
        st.stop()

    mk = mes_key(store["mes_ref"])
    receita = RECEITAS[conta]
    res = store["resultados"][conta]
    df_divergentes = res["divergentes"]
    resumo = res["resumo"]
    obs_conta = store["obs"].setdefault(conta, {})

    st.markdown(f'<div class="secao-titulo">📈 {receita["nome"]} — Resumo</div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    c1, c2, c3, c4, c5 = st.columns(5)
    def card(col, label, value, classe=""):
        col.markdown(f"""<div class="metric-card"><div class="label">{label}</div>
        <div class="value {classe}">{value}</div></div>""", unsafe_allow_html=True)
    card(c1, "Total Contábil", fmt_brl(resumo["total_contabil"]))
    card(c2, "Total Financeiro", fmt_brl(resumo["total_financeiro"]))
    card(c3, "Diferença Macro", fmt_brl(resumo["diferenca_macro"]))
    card(c4, "Parceiros c/ diferença", str(resumo["qtd_parceiros"]))
    card(c5, "Validação", resumo["status"], "ok" if "OK" in resumo["status"] else "divergencia")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Fantasmas (órfãos) INLINE ─────────────────────────────────────────────
    orfaos_cli = res["orfaos_cli"]
    if len(orfaos_cli) > 0:
        with st.expander(f"👻 Fantasmas a atribuir nesta conta ({len(orfaos_cli)})", expanded=False):
            st.caption("Lançamentos contábeis sem CODPARC. Atribua um código e clique em aplicar.")
            cli_ok = res["cli_ok"]
            nomes_map = {
                norm_nome(r["NOMEPARC"]): r["CODPARC"]
                for _, r in cli_ok.groupby("NOMEPARC")["CODPARC"].first().reset_index().iterrows()
            }
            novas = {}
            for idx, row in orfaos_cli.iterrows():
                a1, a2, a3, a4 = st.columns([3, 2, 1, 2])
                a1.write(f"**{row.get('NOMEPARC', '—')}**")
                a2.write(f"NF {fmt_int(row.get('NUMNOTA'))}")
                a3.write(fmt_brl(row.get("VLRDESDOB", 0)))
                sug = nomes_map.get(norm_nome(str(row.get("NOMEPARC", ""))), "")
                atual = store["atrib"].get(conta, {}).get(idx, "")
                val = str(int(atual)) if atual else (str(int(sug)) if sug else "")
                cod = a4.text_input("CODPARC", value=val, key=f"orf_{conta}_{idx}",
                                    label_visibility="collapsed", placeholder="CODPARC")
                if cod.strip():
                    try:
                        novas[idx] = int(cod.strip())
                    except ValueError:
                        a4.warning("Só números")
            if st.button("✅ Aplicar atribuições", key=f"aplicar_orf_{conta}"):
                store["atrib"][conta] = novas
                banco.salvar_atrib(mk, conta, novas)
                recomputa_conta(conta)
                st.rerun()

    # ── Tabela de diferenças ──────────────────────────────────────────────────
    st.markdown('<div class="secao-titulo">🔍 Parceiros com Diferença — |Diferença| decrescente</div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    cab = st.columns([0.3, 0.9, 2, 0.6, 0.6, 1.1, 1.1, 1, 1.4, 2])
    labels_cab = ["#", "CODPARC", "Parceiro", "Qtd Cont.", "Qtd Fin.",
                  "Soma Contábil", "Soma Financeiro", "Diferença", "Status", "📝 Observação"]
    for col, lbl in zip(cab, labels_cab):
        col.markdown(f"<div style='background:#041747;color:#FAC318;font-weight:700;font-size:11px;padding:6px 4px;text-align:center'>{lbl}</div>", unsafe_allow_html=True)

    for i, (_, row) in enumerate(df_divergentes.iterrows(), start=1):
        codparc = int(row["CODPARC"])
        dif = row["DIFERENCA"]
        cor_dif = "#C00000" if dif > 0 else "#0071FE"
        status = row["STATUS"]
        cor_st, bg_st = ("#C00000", "#FFE6E6") if ("Contábil" in status or "Financeiro" in status) else ("#041747", "#FFF4CC")
        bg = "#FFFFFF" if i % 2 == 1 else "#F5F7FA"
        borda = "border-bottom:1px solid #D9D9D9;"
        c0, c1, c2, c3, c4, c5, c6, c7, c8, c9 = st.columns([0.3, 0.9, 2, 0.6, 0.6, 1.1, 1.1, 1, 1.4, 2])
        cel = f"background:{bg};{borda}padding:6px 4px;font-size:12px;"
        c0.markdown(f"<div style='{cel}text-align:center;color:#595959'>{i}</div>", unsafe_allow_html=True)
        c1.markdown(f"<div style='{cel}text-align:center'>{codparc}</div>", unsafe_allow_html=True)
        c2.markdown(f"<div style='{cel}font-weight:600'>{row['NOMEPARC']}</div>", unsafe_allow_html=True)
        c3.markdown(f"<div style='{cel}text-align:center'>{int(row['QTD_CLI'])}</div>", unsafe_allow_html=True)
        c4.markdown(f"<div style='{cel}text-align:center'>{int(row['QTD_FIN'])}</div>", unsafe_allow_html=True)
        c5.markdown(f"<div style='{cel}text-align:right'>{fmt_brl(row['SOMA_CLI'])}</div>", unsafe_allow_html=True)
        c6.markdown(f"<div style='{cel}text-align:right'>{fmt_brl(row['SOMA_FIN'])}</div>", unsafe_allow_html=True)
        c7.markdown(f"<div style='{cel}text-align:right;color:{cor_dif};font-weight:700'>{fmt_brl(dif)}</div>", unsafe_allow_html=True)
        c8.markdown(f"<div style='background:{bg_st};{borda}padding:6px 4px;font-size:11px;text-align:center;color:{cor_st};font-weight:700'>{status}</div>", unsafe_allow_html=True)
        obs_atual = obs_conta.get(codparc, "")
        nova_obs = c9.text_input("obs", value=obs_atual, key=f"obs_{conta}_{codparc}",
                                 label_visibility="collapsed", placeholder="Observação...")
        if nova_obs != obs_atual:
            obs_conta[codparc] = nova_obs
            banco.salvar_obs(mk, conta, codparc, nova_obs)

    st.markdown("<div style='border-bottom:2px solid #041747;margin-bottom:16px'></div>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    # ── Drill-down ────────────────────────────────────────────────────────────
    st.markdown('<div class="secao-titulo">🔎 Drill-Down por Parceiro</div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    if len(df_divergentes) > 0:
        opcoes = [f"{int(r['CODPARC'])} — {r['NOMEPARC']}" for _, r in df_divergentes.iterrows()]
        selecao = st.selectbox("Selecione o parceiro:", options=opcoes, index=0, key=f"drill_{conta}")
        if selecao:
            cod_sel = int(selecao.split(" — ")[0])
            nfs_cli, nfs_fin, resumo_nf = drill_down(cod_sel, res["cli_ok"], res["fin_ok"])
            rp = df_divergentes[df_divergentes["CODPARC"] == cod_sel].iloc[0]
            d1, d2, d3, d4 = st.columns(4)
            d1.metric("Soma Contábil", fmt_brl(rp["SOMA_CLI"]))
            d2.metric("Soma Financeiro", fmt_brl(rp["SOMA_FIN"]))
            d3.metric("Diferença", fmt_brl(rp["DIFERENCA"]))
            d4.metric("Status", rp["STATUS"])
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("**📋 Resumo por Nota Fiscal**")

            def colorir(val):
                mapa = {
                    "OK": "background-color:#D9F2DC;color:#0F8C3B;",
                    "Diverge": "background-color:#FFF4CC;color:#041747;font-weight:bold;",
                    "Só Contábil": "background-color:#FFE6E6;color:#C00000;",
                    "Só Financeiro": "background-color:#FFE6E6;color:#C00000;",
                    "Compensa internamente": "background-color:#F2F2F2;color:#595959;",
                }
                return mapa.get(val, "")

            styled = (resumo_nf[["NF", "Σ_Contábil", "Σ_Financeiro", "Δ", "Status"]].style
                      .map(colorir, subset=["Status"])
                      .format({"NF": fmt_nf, "Σ_Contábil": fmt_brl, "Σ_Financeiro": fmt_brl, "Δ": fmt_brl})
                      .set_properties(**{"font-family": "Calibri, sans-serif", "font-size": "12px"}))
            st.dataframe(styled, use_container_width=True, height=280)

            st.markdown("<br>", unsafe_allow_html=True)
            cc, cf = st.columns(2)
            with cc:
                st.markdown(f'<div style="background:#0071FE;color:white;padding:6px 12px;border-radius:4px;font-weight:700;font-size:13px;">📋 NFs CONTÁBIL ({len(nfs_cli)})</div>', unsafe_allow_html=True)
                if len(nfs_cli) > 0:
                    st.dataframe(nfs_cli.style.format({"NF": fmt_nf, "Valor (R$)": fmt_brl}), use_container_width=True, height=250)
                else:
                    st.info("Sem lançamentos contábeis.")
            with cf:
                st.markdown(f'<div style="background:#0F8C3B;color:white;padding:6px 12px;border-radius:4px;font-weight:700;font-size:13px;">📋 NFs FINANCEIRO ({len(nfs_fin)})</div>', unsafe_allow_html=True)
                if len(nfs_fin) > 0:
                    st.dataframe(nfs_fin.style.format({"NF": fmt_nf, "Valor (R$)": fmt_brl}), use_container_width=True, height=250)
                else:
                    st.info("Sem lançamentos financeiros.")
    else:
        st.success("Nenhum parceiro com diferença nesta conta. ✅")

    st.markdown("<br><hr>", unsafe_allow_html=True)

    # ── Download Excel da conta ───────────────────────────────────────────────
    with st.spinner("Preparando Excel..."):
        excel_bytes = gerar_excel(
            res["fin_ok"], df_divergentes, resumo,
            res["orfaos_cli"], res["orfaos_fin"], obs_conta,
        )
    st.download_button(
        label=f"⬇️ Baixar Excel — {receita['nome']}",
        data=excel_bytes,
        file_name=f"conciliacao_{conta}_LLE.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )
