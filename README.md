# Conciliação de Clientes — Grupo LLE

Aplicativo Streamlit para conciliação mensal entre a base contábil (Clientes) e a base financeira (Data Base) do Grupo LLE.

## Como usar

1. Acesse o app
2. Faça upload da base **Contábil** (arquivo `Clientes.xlsx`) e da base **Financeira** (arquivo `Data Base.xlsx`)
3. Se houver lançamentos sem CODPARC (órfãos), atribua manualmente antes de conciliar
4. Visualize o resumo macro, a tabela de parceiros com diferença e o drill-down por parceiro
5. Baixe o resultado em Excel

## Filtros LLE aplicados automaticamente

- **Natureza:** Vendas notas fiscais
- **Operações válidas (DESCROPER):** 11 operações canônicas LLE
- **Tipos de título válidos (TIPTIT):** 19 tipos incluindo históricos "antigo"
- **Cartões excluídos:** GETNET TEF, CRED PARC, CREDITO A DISTANCIA, CREDITO A VISTA, DEBITO GETNET
- **Exceção:** SEPM (CODPARC 41007) entra independente do TIPTIT

## Estrutura do Excel gerado

- **Data base filtrado:** base financeira após aplicação dos filtros LLE
- **Investigação Diferença:** tabela consolidada por CODPARC com status e diferenças

## Deploy no Streamlit Cloud

1. Suba este repositório no GitHub (público)
2. Acesse [share.streamlit.io](https://share.streamlit.io)
3. Conecte sua conta GitHub
4. Selecione o repositório, branch `main` e arquivo `app.py`
5. Clique em **Deploy**

## Estrutura dos arquivos

```
lle_conciliacao/
├── app.py              # Interface Streamlit
├── conciliacao.py      # Lógica de negócio
├── requirements.txt    # Dependências
└── README.md
```

## Requisitos da base contábil (Clientes)

- Header na primeira linha
- Colunas obrigatórias: `CODEMP`, `NUMNOTA`, `CODPARC`, `NOMEPARC`, `VLRDESDOB`, `DTEMISSAO`, `HISTORICO`

## Requisitos da base financeira (Data Base)

- Header sempre na **linha 8** do arquivo Excel
- Colunas obrigatórias: `CODEMP`, `NUMNOTA`, `CODPARC`, `NOMEPARC`, `VLRDESDOB`, `DTEMISSAO`, `DESCROPER`, `TIPTIT`, `DESCRNAT`
