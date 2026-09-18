"""
Persistência no Neon (Postgres) — Grupo LLE
===========================================
Guarda apenas o TRABALHO DE ANÁLISE:
  - observações por parceiro
  - atribuições de fantasmas (órfãos)
tudo marcado por MÊS + CONTA. As bases (arquivos) continuam por upload.

Segurança: a string de conexão vem de st.secrets["NEON_URL"] — nunca do código.
Robustez: se o secret não existir, ou a lib/conexão falhar, TUDO vira no-op e o
app segue funcionando em memória, sem quebrar.
"""
import streamlit as st


def _url():
    try:
        return st.secrets.get("NEON_URL")
    except Exception:
        return None


@st.cache_resource
def _connstore():
    return {"conn": None}


def _criar_tabelas(conn):
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS observacoes (
                mes     TEXT   NOT NULL,
                conta   TEXT   NOT NULL,
                codparc BIGINT NOT NULL,
                texto   TEXT,
                PRIMARY KEY (mes, conta, codparc)
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS atribuicoes (
                mes     TEXT   NOT NULL,
                conta   TEXT   NOT NULL,
                idx     BIGINT NOT NULL,
                codparc BIGINT NOT NULL,
                PRIMARY KEY (mes, conta, idx)
            );
        """)


def _conn():
    """Devolve uma conexão viva ou None (com reconexão automática)."""
    url = _url()
    if not url:
        return None
    store = _connstore()
    c = store.get("conn")
    # reaproveita se ainda estiver viva
    if c is not None:
        try:
            with c.cursor() as cur:
                cur.execute("SELECT 1")
            return c
        except Exception:
            c = None
    # (re)conecta
    try:
        import psycopg2
        c = psycopg2.connect(url)
        c.autocommit = True
        _criar_tabelas(c)
        store["conn"] = c
        return c
    except Exception as e:
        print("Neon indisponível (seguindo em memória):", e)
        store["conn"] = None
        return None


def disponivel() -> bool:
    return _conn() is not None


# ── Carregar análise salva de um mês/conta ────────────────────────────────────

def carregar(mes: str, conta: str):
    """Retorna (observacoes {codparc: texto}, atribuicoes {idx: codparc})."""
    obs, atrib = {}, {}
    c = _conn()
    if c is None:
        return obs, atrib
    try:
        with c.cursor() as cur:
            cur.execute("SELECT codparc, texto FROM observacoes WHERE mes=%s AND conta=%s", (mes, conta))
            for codparc, texto in cur.fetchall():
                if texto:
                    obs[int(codparc)] = texto
            cur.execute("SELECT idx, codparc FROM atribuicoes WHERE mes=%s AND conta=%s", (mes, conta))
            for idx, codparc in cur.fetchall():
                atrib[int(idx)] = int(codparc)
    except Exception as e:
        print("Erro ao carregar do Neon:", e)
    return obs, atrib


# ── Salvar observação (upsert; apaga se vazia) ────────────────────────────────

def salvar_obs(mes: str, conta: str, codparc: int, texto: str):
    c = _conn()
    if c is None:
        return
    try:
        with c.cursor() as cur:
            if texto and texto.strip():
                cur.execute("""
                    INSERT INTO observacoes (mes, conta, codparc, texto)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (mes, conta, codparc)
                    DO UPDATE SET texto = EXCLUDED.texto
                """, (mes, conta, int(codparc), texto))
            else:
                cur.execute("DELETE FROM observacoes WHERE mes=%s AND conta=%s AND codparc=%s",
                            (mes, conta, int(codparc)))
    except Exception as e:
        print("Erro ao salvar observação:", e)


# ── Salvar atribuições de fantasmas (substitui as da conta/mês) ───────────────

def salvar_atrib(mes: str, conta: str, atrib: dict):
    c = _conn()
    if c is None:
        return
    try:
        with c.cursor() as cur:
            cur.execute("DELETE FROM atribuicoes WHERE mes=%s AND conta=%s", (mes, conta))
            for idx, codparc in (atrib or {}).items():
                cur.execute("""
                    INSERT INTO atribuicoes (mes, conta, idx, codparc)
                    VALUES (%s, %s, %s, %s)
                """, (mes, conta, int(idx), int(codparc)))
    except Exception as e:
        print("Erro ao salvar atribuições:", e)


# ── Reset por conta (apaga análise de um mês/conta) ───────────────────────────

def resetar(mes: str, conta: str):
    c = _conn()
    if c is None:
        return
    try:
        with c.cursor() as cur:
            cur.execute("DELETE FROM observacoes WHERE mes=%s AND conta=%s", (mes, conta))
            cur.execute("DELETE FROM atribuicoes WHERE mes=%s AND conta=%s", (mes, conta))
    except Exception as e:
        print("Erro ao resetar:", e)
