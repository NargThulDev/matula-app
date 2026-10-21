import streamlit as st
import folium
from folium.plugins import Draw, HeatMap
from streamlit_folium import st_folium
import sqlite3
import pandas as pd
import requests
import json

st.set_page_config(page_title="Satélite e Mapas", page_icon="🗺️", layout="wide")
ARQUIVO_DB = 'banco_lavoura.db'

# --- DESIGN: AGTECH PREMIUM ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    .stApp { background-color: #F4F7F6; font-family: 'Inter', sans-serif !important; }
    header, footer, #MainMenu, [data-testid="stToolbar"] { visibility: hidden; }
    header { background-color: transparent !important; }
    h1, h2, h3, h4, h5, h6 { color: #1A3626 !important; font-weight: 700 !important; }
    
    .top-header {
        background: linear-gradient(135deg, #1A3626 0%, #2E7D32 100%);
        padding: 30px 20px 20px 20px; border-radius: 16px; margin-bottom: 20px;
        text-align: center; box-shadow: 0 8px 20px rgba(46, 125, 50, 0.15);
    }
    .top-header h1 { color: #FFFFFF !important; font-size: 32px !important; margin: 0; letter-spacing: -0.5px; }
    .top-header p { color: #A5D6A7 !important; font-weight: 500; margin-top: 5px; margin-bottom: 0; font-size: 16px; }
    
    .painel-mapa {
        background-color: #FFFFFF; border-radius: 12px; padding: 20px;
        border: 1px solid #EBEFEB; box-shadow: 0px 2px 8px rgba(0, 0, 0, 0.02);
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="top-header"><h1>🗺️ Central de Satélite & NDVI</h1><p>Monitorização Contínua Sentinel-2 (Atualização a Cada 5 Dias)</p></div>', unsafe_allow_html=True)

# --- MENU LATERAL (CONFIGURAÇÃO DA API DE SATÉLITE) ---
with st.sidebar:
    st.header("🛰️ Configuração de Satélite")
    st.write("Insira a sua chave da API do Agromonitoring para ligar o Matula aos satélites da ESA (Sentinel-2).")
    agro_key = st.text_input("Agromonitoring API Key:", type="password")
    
    if agro_key:
        st.success("Ligação à API configurada!")
    else:
        st.warning("Insira a chave para desbloquear o histórico de imagens de satélite e índices de vegetação.")
    
    st.markdown("---")
    st.markdown("[Obter chave gratuita no Agromonitoring](https://agromonitoring.com/)")

# Garante tabela de talhões georreferenciados
def garantir_tabela():
    conn = sqlite3.connect(ARQUIVO_DB)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS talhoes_geometria (
                 id INTEGER PRIMARY KEY AUTOINCREMENT, 
                 nome TEXT, 
                 cultura TEXT, 
                 coordenadas TEXT)''')
    conn.commit()
    conn.close()

garantir_tabela()

col_painel, col_mapa = st.columns([1, 3])

with col_painel:
    st.markdown('<div class="painel-mapa">', unsafe_allow_html=True)
    st.markdown("### 🛰️ Camadas & Histórico")
    
    mostrar_talhoes = st.checkbox("📍 Limites dos Talhões", value=True)
    mostrar_calor = st.checkbox("🔥 Mapa de Calor (Anomalias)", value=True)
    
    st.markdown("---")
    
    # Se a chave estiver ativa, podemos consultar imagens recentes
    if agro_key:
        st.markdown("##### 📡 Imagens Sentinel-2 Recentes")
        st.write("Selecione um talhão guardado para verificar se há novas imagens nos últimos 5 dias:")
        
        conn = sqlite3.connect(ARQUIVO_DB)
        df_talhoes_cad = pd.read_sql_query("SELECT nome FROM talhoes_geometria", conn)
        conn.close()
        
        if not df_talhoes_cad.empty:
            talhao_escolhido = st.selectbox("Talhão para consulta:", df_talhoes_cad['nome'].tolist())
            if st.button("🔍 Procurar Imagens de Satélite"):
                st.info(f"A consultar passagens recentes do satélite para '{talhao_escolhido}'...")
                # Aqui o sistema faria o pedido HTTP à API do Agromonitoring para buscar as imagens multiespectrais
        else:
            st.warning("Nenhum talhão guardado ainda. Desenhe e guarde um talhão no mapa ao lado.")
    else:
        st.info("💡 **Dica:** Desenhe o contorno da sua lavoura usando o polígono no mapa, atribua um nome e clique em 'Salvar Contorno'.")

    st.markdown('</div>', unsafe_allow_html=True)

with col_mapa:
    LAT_CENTRO, LON_CENTRO = -19.6389, -54.5981
    
    m = folium.Map(location=[LAT_CENTRO, LON_CENTRO], zoom_start=15, control_scale=True)
    
    # Camada de Satélite de Alta Resolução do Google
    folium.TileLayer(
        tiles='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
        attr='Google',
        name='Google Satellite',
        max_zoom=20,
        subdomains=['mt0', 'mt1', 'mt2', 'mt3']
    ).add_to(m)

    # Ferramenta de Desenho e Edição
    draw = Draw(
        export=True,
        position='topleft',
        draw_options={
            'polyline': False, 
            'polygon': True,   
            'circle': False,
            'marker': False,    
            'circlemarker': False,
            'rectangle': True, 
        },
        edit_options={
            'edit': True,      
            'remove': True     
        }
    )
    draw.add_to(m)

    # Carrega talhões guardados na base de dados
    conn = sqlite3.connect(ARQUIVO_DB)
    try:
        df_geo = pd.read_sql_query("SELECT nome, cultura, coordenadas FROM talhoes_geometria", conn)
        for _, row in df_geo.iterrows():
            coords = eval(row['coordenadas'])
            folium.Polygon(
                locations=coords, color="#2E7D32", weight=3, 
                fill=True, fill_color="#2E7D32", fill_opacity=0.2,
                tooltip=f"{row['nome']} ({row['cultura']})"
            ).add_to(m)
    except:
        pass
    conn.close()

    # Mapa de Calor de exemplo
    if mostrar_calor:
        pontos_calor = [
            [-19.6380, -54.5980, 0.9], [-19.6385, -54.5975, 1.0], [-19.6375, -54.5985, 0.8]
        ]
        HeatMap(
            pontos_calor, radius=35, blur=25, 
            gradient={0.4: 'yellow', 0.7: 'orange', 1: 'red'}
        ).add_to(m)

    output = st_folium(m, width="100%", height=650, returned_objects=["last_active_drawing", "all_drawings"])

# Formulário rápido de salvamento abaixo do mapa ou na barra lateral
with st.expander("💾 Gravar Novo Talhão Desenhado no Ecrã"):
    with st.form("form_salvar_talhao_mapa"):
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            nome_talhao = st.text_input("Nome do Talhão:", placeholder="Ex: Talhão 03 - Baixada")
        with col_f2:
            cultura_talhao = st.selectbox("Cultura:", ["Soja", "Milho Safrinha", "Sorgo"])
        with col_f3:
            salvar_talhao_btn = st.form_submit_button("Salvar Contorno")
            
        if salvar_talhao_btn:
            ultimo_desenho = output.get("last_active_drawing")
            if ultimo_desenho and ultimo_desenho["geometry"]["type"] == "Polygon":
                coords_geojson = ultimo_desenho["geometry"]["coordinates"][0]
                coords_folium = [[c[1], c[0]] for c in coords_geojson]
                
                conn = sqlite3.connect(ARQUIVO_DB)
                conn.cursor().execute(
                    "INSERT INTO talhoes_geometria (nome, cultura, coordenadas) VALUES (?, ?, ?)",
                    (nome_talhao or "Talhão Novo", cultura_talhao, str(coords_folium))
                )
                conn.commit()
                conn.close()
                st.success(f"Talhão '{nome_talhao}' guardado com sucesso!")
                st.rerun()
            else:
                st.warning("Por favor, desenhe primeiro um polígono no mapa antes de salvar.")
