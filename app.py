import streamlit as st
import sqlite3
import pandas as pd
import os

st.set_page_config(page_title="Matula - Início", page_icon="🌱")
os.makedirs('fotos_app', exist_ok=True)
ARQUIVO_DB = 'banco_lavoura.db'

# Inicia o banco de dados caso não exista
def iniciar_banco():
    conn = sqlite3.connect(ARQUIVO_DB)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS talhoes (id INTEGER PRIMARY KEY, nome TEXT, cultura TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS apontamentos (
                 id INTEGER PRIMARY KEY, talhao_id INTEGER, tipo TEXT, 
                 detalhes TEXT, foto_path TEXT, data_hora DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('SELECT COUNT(*) FROM talhoes')
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO talhoes (nome, cultura) VALUES ('Talhão 01 - Sede', 'Soja')")
        c.execute("INSERT INTO talhoes (nome, cultura) VALUES ('Talhão 02 - Fundo', 'Milho Safrinha')")
    conn.commit()
    conn.close()

iniciar_banco()

st.title("🌱 Matula")
st.header("Resumo Operacional")
st.info("O banco de dados local SQLite está rodando perfeitamente na sua máquina.")

# Carrega e mostra os últimos registros
conn = sqlite3.connect(ARQUIVO_DB)
query = '''SELECT t.nome as Talhão, a.tipo as Tipo, a.detalhes as Detalhes, a.data_hora as Data 
           FROM apontamentos a JOIN talhoes t ON a.talhao_id = t.id ORDER BY a.data_hora DESC LIMIT 5'''
df_registros = pd.read_sql_query(query, conn)
conn.close()

st.subheader("Últimos Registros")
if not df_registros.empty:
    st.dataframe(df_registros, use_container_width=True, hide_index=True)
else:
    st.write("Nenhum registro ainda.")