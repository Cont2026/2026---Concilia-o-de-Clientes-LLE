"""
Receitas de conciliação — Grupo LLE
====================================
Cada "receita" descreve as REGRAS de uma conta: qual(is) Data Base(s) usar e
quais filtros aplicar. O motor (conciliacao.py) é genérico e apenas executa.

FONTE DA VERDADE das regras — para ajustar uma conta, mexa só aqui.

Formatos suportados:
- Receita "plana" (Clientes): campos de filtro no topo + `data_base`.
- Receita com "fontes": lista de recortes, cada um de uma Data Base
  (usada pelas contas que leem mais de uma base ou têm filtros distintos
  por base, como Adiantamento).

Campos de filtro possíveis por fonte (todos opcionais; só o que existir é aplicado):
  base            -> "receita" ou "despesa"
  descrnat        -> lista de naturezas
  descroper       -> lista de operações
  tiptit          -> lista de tipos de título
  codtipoper      -> lista de TOPs (coluna CODTIPOPER)
  excluir_cartoes -> lista de fragmentos de TIPTIT a excluir
  excecao_codparc -> CODPARC que entra sem passar pelo filtro de TIPTIT

Comparação é case/accent-insensitive (o motor normaliza), então pode escrever
com ou sem acento/maiúscula.
"""

# ══════════════════════════════════════════════════════════════════════════════
# 1) CLIENTES  (validado contra março/2026 — NÃO alterar)
# ══════════════════════════════════════════════════════════════════════════════

DESCROPER_CLIENTES = [
    "importacao cheque receita",
    "pagamentos extemporaneos",
    "venda",
    "venda (gold)",
    "venda (importacao xml)",
    "venda (pisa)",
    "venda cupom fiscal",
    "venda cupom fiscal gold",
    "complemento icms st - saida",
    "complemento ipi venda",
    "bonificacao a clientes",
    "venda consumo/ativo",
]

TIPTIT_CLIENTES = [
    "adiantamento",
    "antigo cred c6 pay 10x",
    "antigo cred c6 pay 12x",
    "antigo stone credito a vista",
    "antigo cartao credito parcelada",
    "boleto",
    "boleto registrado",
    "boleto registrado liquidado",
    "boleto registrado alterado",
    "boleto rejeitado",
    "boleto retorno/titulo vencido",
    "credito manual",
    "credito automatico",
    "deposito bancario",
    "dinheiro",
    "duplicata",
    "pix",
    "pix qr code presencial",
    "edi-dda",
]

CARTOES_EXCLUIDOS_CLIENTES = [
    "getnet tef",
    "cred parc",
    "credito a distancia",
    "credito a vista",
    "debito getnet",
    "debito- vis",
    "debito- mas",
    "debito- elo",
    "cred tef",
    "deb tef",
]

CODPARC_SEPM = 41007  # entra sem passar pelo filtro de TIPTIT

RECEITA_CLIENTES = {
    "id": "clientes",
    "nome": "Clientes",
    "data_base": "receita",
    "descrnat": ["vendas notas fiscais"],
    "descroper": DESCROPER_CLIENTES,
    "tiptit": TIPTIT_CLIENTES,
    "excluir_cartoes": CARTOES_EXCLUIDOS_CLIENTES,
    "excecao_codparc": CODPARC_SEPM,
    "compensacoes": True,
}


# ══════════════════════════════════════════════════════════════════════════════
# 2) CARTÃO DE CRÉDITO  (Data Base de Receita)
#    DESCRNAT = "Vendas notas fiscais" + os tipos de título do documento.
# ══════════════════════════════════════════════════════════════════════════════

TIPTIT_CARTAO_CREDITO = [
    "credito a distancia",
    "cred parc 2 a 6-elo getnet",
    "credito parcelado cielo visa",
    "cred parc 2 - master getnet",
    "credito a vista visa getnet",
    "cred parc 2 a 6-visa getnet",
    "cred parc 2 a 6-vis/mas ps",
    "credito parcelado cielo master",
    "credito parcelado cielo elo",
    "getnet tef 2x - elo",
    "getnet tef 1x - elo",
    "getnet tef 1x - master",
    "getnet tef 3x - master",
    "getnet tef 2x - master",
    "getnet tef 1x - visa",
    "cred parc 1x - master getnet",
    "getnet tef 2x - visa",
    "getnet tef 3x - visa",
    "credito a vista vis/mas ps",
    "credito a vista-elo ps",
    "credito a vista elo getnet",
    "cred parc 2 a 6-hiper ps",
    "cred tef 2x - vis/mas ps",
    "cred tef 3x - vis/mas ps",
    "cred tef 1x - vis/mas ps",
    "getnet tef 3x - elo",
    "credito a vista cielo master",
    "cred parc 2 a 6-elo ps",
    "cred parc 2 a 6-amex ps",
    "cred parc 3 - master getnet",
]

RECEITA_CARTAO_CREDITO = {
    "id": "cartao_credito",
    "nome": "Cartão de Crédito",
    "data_base": "receita",
    "descrnat": ["vendas notas fiscais"],
    "tiptit": TIPTIT_CARTAO_CREDITO,
    "compensacoes": True,
}


# ══════════════════════════════════════════════════════════════════════════════
# 3) CARTÃO DE DÉBITO  (Data Base de Receita)
#    DESCRNAT = "Vendas notas fiscais" + os tipos de título do documento.
# ══════════════════════════════════════════════════════════════════════════════

TIPTIT_CARTAO_DEBITO = [
    "debito- vis/mas ps",
    "debito- master getnet",
    "debito- elo ps",
    "debito getnet elo",
    "debito getnet visa",
    "deb tef-vis/mas ps",
]

RECEITA_CARTAO_DEBITO = {
    "id": "cartao_debito",
    "nome": "Cartão de Débito",
    "data_base": "receita",
    "descrnat": ["vendas notas fiscais"],
    "tiptit": TIPTIT_CARTAO_DEBITO,
    "compensacoes": True,
}


# ══════════════════════════════════════════════════════════════════════════════
# 4) OPERAÇÃO COM CARTÃO  (Data Base de Despesa)
#    TOP 1613 (coluna CODTIPOPER). O documento só traz o TOP.
# ══════════════════════════════════════════════════════════════════════════════

RECEITA_OPERACAO_CARTAO = {
    "id": "operacao_cartao",
    "nome": "Operação com Cartão",
    "data_base": "despesa",
    "codtipoper": [1613],
    "compensacoes": True,
}


# ══════════════════════════════════════════════════════════════════════════════
# 5) ADIANTAMENTO DE CLIENTES  (lê Data Base de Receita E de Despesa)
#    Corte por DTENTSAI_1: mantém até o fim do mês conciliado, tira o seguinte.
# ══════════════════════════════════════════════════════════════════════════════

# --- parte na Data Base de RECEITA (imagem: OPERAÇÃO) ---
DESCROPER_ADIANT_RECEITA = [
    "despesas adiantamento cheque",
    "receita emprestimos",
]

# --- parte na Data Base de DESPESA (imagem: NATUREZAS + OPERAÇÕES) ---
DESCRNAT_ADIANT_DESPESA = [
    "adiantamentos/credito para clientes",
    "vendas notas fiscais",
    "troca bonificada",
    "recebimentos indevidos",
    "bonificacao a clientes",
]

DESCROPER_ADIANT_DESPESA = [
    "despesas adiantamento",
    "devolucao de venda (nf terceiro) wms",
    "devolucao de venda fora wms",
    "devolucao de venda wms",
    "receita emprestimos",
    "retorno de venda nao entregue",
    "retorno de venda nao entregue fora",
    "vale clientes",
    "complemento ipi - devolucao venda",
    "devolucao de venda (credito manual)",
]

RECEITA_ADIANTAMENTO = {
    "id": "adiantamento",
    "nome": "Adiantamento de Clientes",
    "fontes": [
        {
            "base": "receita",
            "descroper": DESCROPER_ADIANT_RECEITA,
            # PENDENTE (documento: "VER COM ALINE"): TOP 1466 - Complemento IPI
            #   - Devolução Venda. Deixado de fora até confirmação.
        },
        {
            "base": "despesa",
            "descrnat": DESCRNAT_ADIANT_DESPESA,
            "descroper": DESCROPER_ADIANT_DESPESA,
        },
    ],
    "corte_dtentsai1": True,   # corta pelo mês escolhido (via DTENTSAI_1)
    "compensacoes": True,
}


# ══════════════════════════════════════════════════════════════════════════════
# Registro das contas ativas (ordem dos botões na tela)
# ══════════════════════════════════════════════════════════════════════════════
RECEITAS = {
    "clientes": RECEITA_CLIENTES,
    "adiantamento": RECEITA_ADIANTAMENTO,
    "cartao_credito": RECEITA_CARTAO_CREDITO,
    "cartao_debito": RECEITA_CARTAO_DEBITO,
    "operacao_cartao": RECEITA_OPERACAO_CARTAO,
}
