"""
Receitas de conciliação — Grupo LLE
====================================
Cada "receita" descreve as REGRAS de uma conta: qual Data Base usar e quais
filtros aplicar. O motor (conciliacao.py) é genérico e apenas executa a receita.

Esta é a FONTE DA VERDADE das regras. Para ajustar uma conta, mexa só aqui.

ONDA 1: apenas a conta CLIENTES está ligada, reproduzindo EXATAMENTE as listas
já validadas contra março/2026. As demais contas entram na Onda 2.
"""

# ── CLIENTES (validado contra março/2026 — NÃO alterar) ───────────────────────

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

# Fragmentos de TIPTIT que a conta Clientes EXCLUI (cartões)
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

CODPARC_SEPM = 41007  # parceiro SEPM entra sem passar pelo filtro de TIPTIT

RECEITA_CLIENTES = {
    "id": "clientes",
    "nome": "Clientes",
    "data_base": "receita",                 # lê a Data Base de Receita
    "descrnat": ["vendas notas fiscais"],
    "descroper": DESCROPER_CLIENTES,
    "tiptit": TIPTIT_CLIENTES,
    "excluir_cartoes": CARTOES_EXCLUIDOS_CLIENTES,
    "excecao_codparc": CODPARC_SEPM,        # entra sem filtro de TIPTIT
    "compensacoes": True,
}

# ── Registro das contas ativas ────────────────────────────────────────────────
# ONDA 1: só Clientes. Na Onda 2 entram Adiantamento, Cartão de crédito,
# Cartão de débito e Operação com cartão.
RECEITAS = {
    "clientes": RECEITA_CLIENTES,
}
