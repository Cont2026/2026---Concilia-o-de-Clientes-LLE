"""
Motor de conciliação — Grupo LLE
=================================
Contábil × Financeiro (Data Base), consolidado por CODPARC.

Este arquivo é GENÉRICO: ele não conhece as regras de nenhuma conta.
As regras moram em `receitas.py`. O motor recebe uma receita e a executa.

ONDA 1: só a conta Clientes está ligada. `filtrar_financeiro` sem receita usa
a de Clientes, então o app atual continua funcionando exatamente como hoje.
"""
import unicodedata
import pandas as pd

from receitas import RECEITA_CLIENTES

# Valor mínimo (R$) para considerar uma compensação entre parceiros.
# Serve para ignorar centavos de arredondamento (ex.: pares de 0,01).
VALOR_MIN_COMPENSACAO = 1.00


# ── Normalização ──────────────────────────────────────────────────────────────

def norm(valor):
    """Lowercase + strip acentos para comparação case/accent-insensitive."""
    if pd.isna(valor):
        return ""
    s = str(valor).lower().strip()
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    return s


def eh_cartao_excluido(tiptit_norm: str) -> bool:
    """Compatibilidade: usa a lista de exclusão de Clientes."""
    for frag in RECEITA_CLIENTES.get("excluir_cartoes", []):
        if frag in tiptit_norm:
            return True
    return False


# ── Leitura das bases ─────────────────────────────────────────────────────────

def ler_contabil(arquivo) -> pd.DataFrame:
    """Lê a base contábil (Clientes). Header na linha 1 (padrão)."""
    df = pd.read_excel(arquivo, dtype={"CODPARC": object})
    df.columns = [c.strip().upper() for c in df.columns]
    df["CODPARC"] = pd.to_numeric(df["CODPARC"], errors="coerce")
    df["VLRDESDOB"] = pd.to_numeric(df["VLRDESDOB"], errors="coerce").fillna(0)
    return df


def ler_financeiro(arquivo) -> pd.DataFrame:
    """Lê a base financeira (Data Base). Header sempre na linha 8 (índice 7)."""
    df = pd.read_excel(arquivo, header=7, dtype={"CODPARC": object})
    df.columns = [c.strip().upper() for c in df.columns]
    df["CODPARC"] = pd.to_numeric(df["CODPARC"], errors="coerce")
    df["VLRDESDOB"] = pd.to_numeric(df["VLRDESDOB"], errors="coerce").fillna(0)
    return df


# ── Filtro por FONTE (um recorte de uma Data Base) ────────────────────────────

def filtrar_fonte(df: pd.DataFrame, fonte: dict) -> pd.DataFrame:
    """
    Aplica os filtros de UMA fonte a UMA Data Base e retorna o recorte.
    Cada condição só é aplicada se a fonte a definir — assim uma fonte simples
    (só um TOP) e uma completa (Clientes) usam o mesmo mecanismo.

    Campos possíveis: descrnat, descroper, tiptit, codtipoper,
    excluir_cartoes, excecao_codparc.
    """
    df = df.copy()
    df["_descrnat"] = df["DESCRNAT"].apply(norm) if "DESCRNAT" in df.columns else ""
    df["_descroper"] = df["DESCROPER"].apply(norm) if "DESCROPER" in df.columns else ""
    df["_tiptit"] = df["TIPTIT"].apply(norm) if "TIPTIT" in df.columns else ""

    descrnat_ok = [norm(x) for x in (fonte.get("descrnat") or [])]
    descroper_ok = [norm(x) for x in (fonte.get("descroper") or [])]
    tiptit_ok = [norm(x) for x in (fonte.get("tiptit") or [])]
    cartoes = [norm(x) for x in (fonte.get("excluir_cartoes") or [])]
    excecao = fonte.get("excecao_codparc", None)
    tops = fonte.get("codtipoper") or []

    mask = pd.Series(True, index=df.index)

    if descrnat_ok:
        mask &= df["_descrnat"].isin(descrnat_ok)

    if descroper_ok:
        mask &= df["_descroper"].isin(descroper_ok)

    if tiptit_ok:
        cond_tip = df["_tiptit"].isin(tiptit_ok)
        if excecao is not None:
            cond_tip = cond_tip | (df["CODPARC"] == excecao)
        mask &= cond_tip

    if cartoes:
        eh_cartao = df["_tiptit"].apply(lambda t: any(frag in t for frag in cartoes))
        mask &= ~eh_cartao

    if tops:
        if "CODTIPOPER" in df.columns:
            top_col = pd.to_numeric(df["CODTIPOPER"], errors="coerce")
            mask &= top_col.isin(tops)
        else:
            mask &= False

    return df[mask].drop(columns=["_descrnat", "_descroper", "_tiptit"])


def _fontes_da_receita(receita: dict) -> list:
    """
    Normaliza uma receita para uma lista de fontes.
    - Receita com "fontes": usa como está.
    - Receita "plana" (Clientes): monta uma fonte única a partir dos campos do topo.
    """
    if receita.get("fontes"):
        return receita["fontes"]
    return [{
        "base": receita.get("data_base", "receita"),
        "descrnat": receita.get("descrnat"),
        "descroper": receita.get("descroper"),
        "tiptit": receita.get("tiptit"),
        "codtipoper": receita.get("codtipoper"),
        "excluir_cartoes": receita.get("excluir_cartoes"),
        "excecao_codparc": receita.get("excecao_codparc"),
    }]


def _aplicar_corte_dtentsai1(df: pd.DataFrame, mes_ref) -> pd.DataFrame:
    """
    Corte do Adiantamento: mantém DTENTSAI_1 até o fim do mês conciliado
    e remove o que caiu no mês seguinte em diante.
    `mes_ref` = (ano, mes). Linhas sem DTENTSAI_1 são mantidas (não há como cortar).
    """
    if "DTENTSAI_1" not in df.columns or mes_ref is None:
        return df
    ano, mes = mes_ref
    dt = pd.to_datetime(df["DTENTSAI_1"], errors="coerce")
    ultimo_dia = pd.Timestamp(year=int(ano), month=int(mes), day=1) + pd.offsets.MonthEnd(0)
    manter = dt.isna() | (dt <= ultimo_dia)
    return df[manter]


def montar_financeiro(receita: dict, bases: dict, mes_ref=None) -> pd.DataFrame:
    """
    Monta o recorte financeiro de UMA conta, juntando todas as suas fontes.
    `bases` = {"receita": df_receita, "despesa": df_despesa} (podem faltar).
    Aplica o corte por DTENTSAI_1 se a receita pedir.
    """
    partes = []
    for fonte in _fontes_da_receita(receita):
        df_base = bases.get(fonte.get("base", "receita"))
        if df_base is None or len(df_base) == 0:
            continue
        partes.append(filtrar_fonte(df_base, fonte))

    if partes:
        df = pd.concat(partes, ignore_index=True)
    else:
        df = pd.DataFrame()

    if receita.get("corte_dtentsai1") and len(df):
        df = _aplicar_corte_dtentsai1(df, mes_ref)

    return df


def filtrar_financeiro(df: pd.DataFrame, receita: dict = None) -> pd.DataFrame:
    """
    Compatível com o app atual: chamado sem receita e com UMA base (Receita),
    usa a de Clientes — resultado idêntico ao de hoje.
    """
    if receita is None:
        receita = RECEITA_CLIENTES
    return montar_financeiro(receita, {"receita": df}, mes_ref=None)


def conciliar_conta(receita: dict, df_contabil: pd.DataFrame, bases: dict, mes_ref=None) -> dict:
    """
    Executa a conciliação completa de UMA conta e devolve tudo pronto para a tela.
    Não mistura com outras contas — cada chamada é isolada.
    """
    df_fin = montar_financeiro(receita, bases, mes_ref)
    cli_ok, fin_ok, orfaos_cli, orfaos_fin = separar_orfaos(df_contabil, df_fin)
    divergentes = conciliar(cli_ok, fin_ok)
    resumo = resumo_macro(cli_ok, fin_ok, divergentes, orfaos_cli, orfaos_fin)
    return {
        "df_fin": df_fin,
        "cli_ok": cli_ok,
        "fin_ok": fin_ok,
        "orfaos_cli": orfaos_cli,
        "orfaos_fin": orfaos_fin,
        "divergentes": divergentes,
        "resumo": resumo,
    }


# ── Detecção de órfãos ────────────────────────────────────────────────────────

def separar_orfaos(df_cli: pd.DataFrame, df_fin_filtrado: pd.DataFrame):
    """
    Retorna (df_cli_sem_orfaos, df_fin_sem_orfaos, orfaos_cli, orfaos_fin).
    Órfão = CODPARC nulo ou zero.
    """
    mask_cli = df_cli["CODPARC"].isna() | (df_cli["CODPARC"] == 0)
    mask_fin = df_fin_filtrado["CODPARC"].isna() | (df_fin_filtrado["CODPARC"] == 0)

    orfaos_cli = df_cli[mask_cli].copy()
    orfaos_fin = df_fin_filtrado[mask_fin].copy()

    df_cli_ok = df_cli[~mask_cli].copy()
    df_fin_ok = df_fin_filtrado[~mask_fin].copy()

    return df_cli_ok, df_fin_ok, orfaos_cli, orfaos_fin


def aplicar_atribuicoes_orfaos(
    df_cli: pd.DataFrame,
    orfaos_cli: pd.DataFrame,
    atribuicoes: dict,  # {index_original: codparc_novo}
) -> pd.DataFrame:
    """
    Aplica as atribuições manuais de CODPARC aos órfãos e devolve
    o dataframe contábil completo (sem órfãos pendentes).
    """
    orfaos_atualizados = orfaos_cli.copy()
    for idx, codparc in atribuicoes.items():
        orfaos_atualizados.loc[idx, "CODPARC"] = codparc

    # Remover os que ainda ficaram sem código (usuário deixou em branco)
    orfaos_atualizados = orfaos_atualizados[
        ~(orfaos_atualizados["CODPARC"].isna() | (orfaos_atualizados["CODPARC"] == 0))
    ]

    return pd.concat([df_cli, orfaos_atualizados], ignore_index=True)


# ── Conciliação ───────────────────────────────────────────────────────────────

def conciliar(df_cli: pd.DataFrame, df_fin: pd.DataFrame) -> pd.DataFrame:
    """
    Consolida por CODPARC e retorna tabela de diferenças.
    Somente parceiros com diferença != 0 (tolerância exata zero).
    """
    grp_cli = (
        df_cli.groupby("CODPARC")
        .agg(
            NOMEPARC=("NOMEPARC", "first"),
            QTD_CLI=("NUMNOTA", "count"),
            SOMA_CLI=("VLRDESDOB", "sum"),
        )
        .reset_index()
    )

    grp_fin = (
        df_fin.groupby("CODPARC")
        .agg(
            QTD_FIN=("NUMNOTA", "count"),
            SOMA_FIN=("VLRDESDOB", "sum"),
        )
        .reset_index()
    )

    merged = pd.merge(grp_cli, grp_fin, on="CODPARC", how="outer")

    # Preencher nulos
    merged["NOMEPARC"] = merged["NOMEPARC"].fillna(
        merged["CODPARC"].map(
            df_fin.dropna(subset=["CODPARC"])
            .groupby("CODPARC")["NOMEPARC"]
            .first()
        )
    )
    merged["QTD_CLI"] = merged["QTD_CLI"].fillna(0).astype(int)
    merged["SOMA_CLI"] = merged["SOMA_CLI"].fillna(0).round(2)
    merged["QTD_FIN"] = merged["QTD_FIN"].fillna(0).astype(int)
    merged["SOMA_FIN"] = merged["SOMA_FIN"].fillna(0).round(2)

    merged["DIFERENCA"] = (merged["SOMA_CLI"] - merged["SOMA_FIN"]).round(2)

    def status(row):
        if row["SOMA_FIN"] == 0 and row["SOMA_CLI"] != 0:
            return "Apenas no Contábil"
        if row["SOMA_CLI"] == 0 and row["SOMA_FIN"] != 0:
            return "Apenas no Financeiro"
        return "Diferença de valor"

    merged["STATUS"] = merged.apply(status, axis=1)

    # Apenas divergentes
    divergentes = merged[merged["DIFERENCA"] != 0].copy()

    # Ordenar por |Diferença| decrescente
    divergentes["_ABS"] = divergentes["DIFERENCA"].abs()
    divergentes = divergentes.sort_values("_ABS", ascending=False).drop(columns=["_ABS"])
    divergentes = divergentes.reset_index(drop=True)

    return divergentes


# ── Compensações entre parceiros ──────────────────────────────────────────────

def detectar_compensacoes(df_divergentes: pd.DataFrame, valor_minimo: float = VALOR_MIN_COMPENSACAO) -> pd.DataFrame:
    """
    Sinaliza POSSÍVEIS compensações entre parceiros: pares cujas diferenças
    têm o mesmo valor em módulo e sinais opostos (+X em um, -X em outro).

    IMPORTANTE: o vínculo é apenas o valor líquido — NÃO a nota fiscal.
    Portanto isto é uma SUGESTÃO para conferência do analista, não uma prova.

    - "Par exato": só existe um parceiro com +X e um com -X (par único).
    - "Ambíguo — confirmar": há vários candidatos para o mesmo valor; devolve
      todas as combinações possíveis, cabendo ao analista decidir.

    Valores em módulo abaixo de `valor_minimo` são ignorados (arredondamento).
    Retorna DataFrame (uma linha por combinação possível).
    """
    colunas = [
        "VALOR", "CODPARC_A", "PARCEIRO_A", "DIF_A",
        "CODPARC_B", "PARCEIRO_B", "DIF_B", "TIPO", "OBSERVACAO",
    ]
    if df_divergentes is None or len(df_divergentes) == 0:
        return pd.DataFrame(columns=colunas)

    df = df_divergentes.copy()
    df["_ABS"] = df["DIFERENCA"].abs().round(2)

    linhas = []
    for valor in sorted(df["_ABS"].unique(), reverse=True):
        if valor < valor_minimo:
            continue
        grupo = df[df["_ABS"] == valor]
        pos = grupo[grupo["DIFERENCA"] > 0]   # sobra (Contábil > Financeiro)
        neg = grupo[grupo["DIFERENCA"] < 0]   # falta (Contábil < Financeiro)
        if len(pos) == 0 or len(neg) == 0:
            continue

        ambiguo = not (len(pos) == 1 and len(neg) == 1)
        tipo = "Ambíguo — confirmar" if ambiguo else "Par exato"
        obs = (
            "Vários candidatos com o mesmo valor; confira qual par de fato se compensa."
            if ambiguo else
            "Diferenças exatamente opostas — provável troca de lançamento entre os dois."
        )

        for _, rn in neg.iterrows():
            for _, rp in pos.iterrows():
                linhas.append({
                    "VALOR": round(float(valor), 2),
                    "CODPARC_A": int(rn["CODPARC"]),
                    "PARCEIRO_A": rn["NOMEPARC"],
                    "DIF_A": round(float(rn["DIFERENCA"]), 2),
                    "CODPARC_B": int(rp["CODPARC"]),
                    "PARCEIRO_B": rp["NOMEPARC"],
                    "DIF_B": round(float(rp["DIFERENCA"]), 2),
                    "TIPO": tipo,
                    "OBSERVACAO": obs,
                })

    return pd.DataFrame(linhas, columns=colunas)


# ── Resumo macro ──────────────────────────────────────────────────────────────

def resumo_macro(df_cli, df_fin, df_dif, orfaos_cli, orfaos_fin):
    total_cli = round(df_cli["VLRDESDOB"].sum(), 2)
    total_fin = round(df_fin["VLRDESDOB"].sum(), 2)
    soma_orfaos = round(
        orfaos_cli["VLRDESDOB"].sum() + orfaos_fin["VLRDESDOB"].sum(), 2
    )
    diferenca_macro = round(total_cli - total_fin - soma_orfaos, 2)
    soma_parceiros = round(df_dif["DIFERENCA"].sum(), 2)
    valido = abs(diferenca_macro - soma_parceiros) <= 0.02

    return {
        "total_contabil": total_cli,
        "total_financeiro": total_fin,
        "soma_orfaos": soma_orfaos,
        "diferenca_macro": diferenca_macro,
        "soma_parceiros": soma_parceiros,
        "qtd_parceiros": len(df_dif),
        "status": "OK ✅" if valido else "DIVERGÊNCIA ⚠️",
    }


# ── Drill-down por CODPARC ────────────────────────────────────────────────────

def drill_down(codparc: int, df_cli: pd.DataFrame, df_fin: pd.DataFrame):
    """Retorna NFs do parceiro nas duas bases."""
    colunas_cli = ["CODEMP", "NUMNOTA", "VLRDESDOB", "DTEMISSAO", "HISTORICO"]
    colunas_cli_exist = [c for c in colunas_cli if c in df_cli.columns]
    nfs_cli = df_cli[df_cli["CODPARC"] == codparc][colunas_cli_exist].copy()
    nfs_cli = nfs_cli.rename(
        columns={
            "CODEMP": "CODEMP",
            "NUMNOTA": "NF",
            "VLRDESDOB": "Valor (R$)",
            "DTEMISSAO": "Data",
            "HISTORICO": "Histórico",
        }
    )

    colunas_fin = ["CODEMP", "NUMNOTA", "VLRDESDOB", "DTEMISSAO", "DESCROPER"]
    colunas_fin_exist = [c for c in colunas_fin if c in df_fin.columns]
    nfs_fin = df_fin[df_fin["CODPARC"] == codparc][colunas_fin_exist].copy()
    nfs_fin = nfs_fin.rename(
        columns={
            "CODEMP": "CODEMP",
            "NUMNOTA": "NF",
            "VLRDESDOB": "Valor (R$)",
            "DTEMISSAO": "Data",
            "DESCROPER": "Operação",
        }
    )

    # Resumo por NF — agrega CODEMP junto com NF
    grp_cli = (
        nfs_cli.groupby(["CODEMP", "NF"] if "CODEMP" in nfs_cli.columns else ["NF"])
        .agg(Σ_Contábil=("Valor (R$)", "sum"), Qtd_C=("Valor (R$)", "count"))
        .reset_index()
    )
    grp_fin = (
        nfs_fin.groupby(["CODEMP", "NF"] if "CODEMP" in nfs_fin.columns else ["NF"])
        .agg(Σ_Financeiro=("Valor (R$)", "sum"), Qtd_F=("Valor (R$)", "count"))
        .reset_index()
    )

    merge_keys = ["CODEMP", "NF"] if "CODEMP" in grp_cli.columns else ["NF"]
    resumo_nf = pd.merge(grp_cli, grp_fin, on=merge_keys, how="outer").fillna(0)
    resumo_nf["Σ_Contábil"] = resumo_nf["Σ_Contábil"].round(2)
    resumo_nf["Σ_Financeiro"] = resumo_nf["Σ_Financeiro"].round(2)
    resumo_nf["Δ"] = (resumo_nf["Σ_Contábil"] - resumo_nf["Σ_Financeiro"]).round(2)

    def status_nf(row):
        c, f = row["Σ_Contábil"], row["Σ_Financeiro"]
        delta = abs(row["Δ"])
        if c == 0 and f == 0:
            return "Compensa internamente"
        if f == 0 and c != 0:
            return "Só Contábil"
        if c == 0 and f != 0:
            return "Só Financeiro"
        if delta <= 0.02:
            return "OK"
        return "Diverge"

    resumo_nf["Status"] = resumo_nf.apply(status_nf, axis=1)
    resumo_nf = resumo_nf.sort_values("Δ", key=abs, ascending=False)

    return nfs_cli, nfs_fin, resumo_nf


# ── Export Excel ──────────────────────────────────────────────────────────────

def gerar_excel(df_filtrado, df_divergentes, resumo, orfaos_cli, orfaos_fin, observacoes=None) -> bytes:
    """Gera Excel com abas: Investigação Diferença e Compensações entre Parceiros."""
    import io
    from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    from openpyxl.cell.cell import MergedCell
    from openpyxl import Workbook

    wb = Workbook()

    # Cores LLE
    AZUL_ESCURO = "041747"
    AMARELO = "FAC318"
    VERDE = "0F8C3B"
    BRANCO = "FFFFFF"
    CINZA = "F2F2F2"
    BORDA_COR = "D9D9D9"

    def header_style(cell, bg=AZUL_ESCURO, fg=BRANCO):
        cell.fill = PatternFill("solid", fgColor=bg)
        cell.font = Font(bold=True, color=fg, name="Calibri")
        cell.alignment = Alignment(horizontal="center", vertical="center")

    def borda_fina(cell):
        lado = Side(style="thin", color=BORDA_COR)
        cell.border = Border(left=lado, right=lado, top=lado, bottom=lado)

    # ── Aba 1: Investigação Diferença ────────────────────────────────────────
    ws2 = wb.active
    ws2.title = "Investigação Diferença"

    ws2["A1"] = "INVESTIGAÇÃO DIFERENÇA — Comparação Consolidada por Parceiro (CODPARC)"
    ws2["A1"].font = Font(bold=True, color=BRANCO, size=14, name="Calibri")
    ws2["A1"].fill = PatternFill("solid", fgColor=AZUL_ESCURO)
    ws2.merge_cells("A1:H1")
    ws2["A1"].alignment = Alignment(horizontal="center")

    labels2 = [
        ("Diferença macro (Cont. − Fin.):", resumo["diferenca_macro"]),
        ("Soma diferenças por parceiro:", resumo["soma_parceiros"]),
        ("Qtd parceiros com diferença:", resumo["qtd_parceiros"]),
        ("Validação:", resumo["status"]),
    ]
    for i, (lb, vl) in enumerate(labels2, start=3):
        ws2[f"A{i}"] = lb
        ws2[f"A{i}"].font = Font(bold=True, name="Calibri")
        ws2[f"B{i}"] = vl
        if i == 6:  # Validação
            cor = VERDE if "OK" in str(vl) else "C00000"
            ws2[f"B{i}"].font = Font(bold=True, color=cor, name="Calibri")

    # Cabeçalho tabela
    cabecalhos = ["CODPARC", "NOMEPARC", "Qtd NFs Contábil", "Qtd NFs Financeiro", "Soma Contábil (R$)", "Soma Financeiro (R$)", "Diferença (R$)", "Status", "Observação do Analista"]
    for col_i, nome in enumerate(cabecalhos, start=1):
        cell = ws2.cell(row=10, column=col_i, value=nome)
        header_style(cell)
        borda_fina(cell)

    # Dados
    for row_i, (_, row_data) in enumerate(df_divergentes.iterrows(), start=11):
        obs = (observacoes or {}).get(int(row_data["CODPARC"]), "")
        vals = [
            row_data["CODPARC"], row_data["NOMEPARC"],
            row_data["QTD_CLI"], row_data["QTD_FIN"],
            row_data["SOMA_CLI"], row_data["SOMA_FIN"],
            row_data["DIFERENCA"], row_data["STATUS"], obs,
        ]
        for col_i, val in enumerate(vals, start=1):
            cell = ws2.cell(row=row_i, column=col_i, value=val)
            cell.font = Font(name="Calibri", size=10)
            fill_cor = BRANCO if (row_i - 11) % 2 == 0 else CINZA
            cell.fill = PatternFill("solid", fgColor=fill_cor)
            borda_fina(cell)
            if col_i in (5, 6, 7):  # Soma Contábil, Soma Financeiro, Diferença
                cell.number_format = '#,##0.00'

        # Cor da coluna observação
        obs_cell = ws2.cell(row=row_i, column=9)
        if obs_cell.value:
            obs_cell.fill = PatternFill("solid", fgColor="EAF4FF")
            obs_cell.font = Font(color="041747", name="Calibri", size=10)

        # Cor da coluna status
        status_cell = ws2.cell(row=row_i, column=8)
        s = row_data["STATUS"]
        if s == "Apenas no Contábil":
            status_cell.fill = PatternFill("solid", fgColor="FFE6E6")
            status_cell.font = Font(color="C00000", name="Calibri", size=10)
        elif s == "Apenas no Financeiro":
            status_cell.fill = PatternFill("solid", fgColor="FFE6E6")
            status_cell.font = Font(color="C00000", name="Calibri", size=10)
        else:
            status_cell.fill = PatternFill("solid", fgColor="FFF4CC")
            status_cell.font = Font(bold=True, color=AZUL_ESCURO, name="Calibri", size=10)

    ws2.freeze_panes = "A11"

    # Órfãos (se houver)
    ultima_linha = 11 + len(df_divergentes) + 2
    if len(orfaos_cli) > 0 or len(orfaos_fin) > 0:
        ws2.cell(row=ultima_linha, column=1, value="ÓRFÃOS SEM CODPARC").fill = \
            PatternFill("solid", fgColor=AMARELO)
        ws2.cell(row=ultima_linha, column=1).font = Font(bold=True, name="Calibri")
        ws2.merge_cells(f"A{ultima_linha}:F{ultima_linha}")

        sub_cab = ["Fonte", "NUMNOTA", "NOMEPARC", "Valor (R$)", "Data", "Observação"]
        for col_i, nome in enumerate(sub_cab, start=1):
            cell = ws2.cell(row=ultima_linha + 1, column=col_i, value=nome)
            header_style(cell, bg=AZUL_ESCURO)

        linha_orf = ultima_linha + 2
        for _, row_data in orfaos_cli.iterrows():
            ws2.cell(row=linha_orf, column=1, value="Contábil")
            ws2.cell(row=linha_orf, column=2, value=row_data.get("NUMNOTA", ""))
            ws2.cell(row=linha_orf, column=3, value=row_data.get("NOMEPARC", ""))
            ws2.cell(row=linha_orf, column=4, value=row_data.get("VLRDESDOB", 0))
            ws2.cell(row=linha_orf, column=5, value=row_data.get("DTEMISSAO", ""))
            linha_orf += 1
        for _, row_data in orfaos_fin.iterrows():
            ws2.cell(row=linha_orf, column=1, value="Financeiro")
            ws2.cell(row=linha_orf, column=2, value=row_data.get("NUMNOTA", ""))
            ws2.cell(row=linha_orf, column=3, value=row_data.get("NOMEPARC", ""))
            ws2.cell(row=linha_orf, column=4, value=row_data.get("VLRDESDOB", 0))
            ws2.cell(row=linha_orf, column=5, value=row_data.get("DTEMISSAO", ""))
            linha_orf += 1

    # ── Aba 2: Compensações entre Parceiros ──────────────────────────────────
    ws3 = wb.create_sheet("Compensações entre Parceiros")
    df_comp = detectar_compensacoes(df_divergentes)

    ws3["A1"] = "COMPENSAÇÕES ENTRE PARCEIROS — pares com diferença igual e oposta"
    ws3["A1"].font = Font(bold=True, color=BRANCO, size=14, name="Calibri")
    ws3["A1"].fill = PatternFill("solid", fgColor=AZUL_ESCURO)
    ws3.merge_cells("A1:I1")
    ws3["A1"].alignment = Alignment(horizontal="center")

    ws3["A3"] = (
        "Sugestão para conferência: o vínculo é apenas o VALOR líquido (não a nota fiscal). "
        "Um parceiro com sobra (+) e outro com falta (−) do mesmo valor podem indicar "
        "lançamento trocado entre eles. Confirme antes de considerar resolvido."
    )
    ws3["A3"].font = Font(italic=True, color="595959", name="Calibri", size=10)
    ws3["A3"].alignment = Alignment(wrap_text=True, vertical="top")
    ws3.merge_cells("A3:I4")

    cab_comp = [
        "Valor Compensado (R$)",
        "CODPARC (−)", "Parceiro com falta (−)", "Diferença (−)",
        "CODPARC (+)", "Parceiro com sobra (+)", "Diferença (+)",
        "Tipo", "Observação",
    ]
    for col_i, nome in enumerate(cab_comp, start=1):
        cell = ws3.cell(row=6, column=col_i, value=nome)
        header_style(cell)
        borda_fina(cell)

    if df_comp is None or len(df_comp) == 0:
        cell = ws3.cell(
            row=7, column=1,
            value="Nenhuma compensação encontrada (nenhum par de diferenças opostas acima do valor mínimo).",
        )
        cell.font = Font(italic=True, color="595959", name="Calibri", size=10)
        ws3.merge_cells("A7:I7")
    else:
        for row_i, (_, rc) in enumerate(df_comp.iterrows(), start=7):
            vals = [
                rc["VALOR"],
                rc["CODPARC_A"], rc["PARCEIRO_A"], rc["DIF_A"],
                rc["CODPARC_B"], rc["PARCEIRO_B"], rc["DIF_B"],
                rc["TIPO"], rc["OBSERVACAO"],
            ]
            for col_i, val in enumerate(vals, start=1):
                cell = ws3.cell(row=row_i, column=col_i, value=val)
                cell.font = Font(name="Calibri", size=10)
                fill_cor = BRANCO if (row_i - 7) % 2 == 0 else CINZA
                cell.fill = PatternFill("solid", fgColor=fill_cor)
                borda_fina(cell)
                if col_i in (1, 4, 7):  # Valor, Diferença (−), Diferença (+)
                    cell.number_format = '#,##0.00'

            # Cor do tipo
            tipo_cell = ws3.cell(row=row_i, column=8)
            if "Ambíguo" in str(rc["TIPO"]):
                tipo_cell.fill = PatternFill("solid", fgColor="FFF4CC")
                tipo_cell.font = Font(bold=True, color=AZUL_ESCURO, name="Calibri", size=10)
            else:
                tipo_cell.fill = PatternFill("solid", fgColor="D9F2DC")
                tipo_cell.font = Font(bold=True, color=VERDE, name="Calibri", size=10)

    ws3.freeze_panes = "A7"

    # Ajuste de largura das colunas (ambas as abas)
    for ws in [ws2, ws3]:
        larguras = {}
        for row in ws.iter_rows():
            for cell in row:
                if isinstance(cell, MergedCell):
                    continue
                if cell.value is not None:
                    letra = cell.column_letter
                    larguras[letra] = max(larguras.get(letra, 0), len(str(cell.value)))
        for letra, largura in larguras.items():
            ws.column_dimensions[letra].width = min(largura + 4, 50)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.getvalue()
