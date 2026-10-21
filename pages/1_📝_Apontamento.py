import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import google.generativeai as genai

# --- CONFIGURAÇÕES E DESIGN ---
st.set_page_config(page_title="Novo Apontamento", page_icon="📝", layout="centered")
ARQUIVO_DB = 'banco_lavoura.db'

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    .stApp { background-color: #F4F7F6; font-family: 'Inter', sans-serif !important; }
    .block-container { max-width: 950px !important; padding-top: 1rem !important; }
    header, footer, #MainMenu { visibility: hidden; }
    header { background-color: transparent !important; }
    h1, h2, h3, h4, h5, h6 { color: #1A3626 !important; font-weight: 700 !important; }
    
    .top-header {
        background: linear-gradient(135deg, #1A3626 0%, #2E7D32 100%);
        padding: 40px 20px 20px 20px; border-radius: 16px; margin-bottom: 30px;
        text-align: center; box-shadow: 0 8px 20px rgba(46, 125, 50, 0.15);
    }
    .top-header h1 { color: #FFFFFF !important; font-size: 32px !important; margin: 0; letter-spacing: -0.5px; }
    .top-header p { color: #A5D6A7 !important; font-weight: 500; margin-top: 5px; margin-bottom: 0; font-size: 16px; }
    
    [data-testid="stForm"] { background-color: #FFFFFF; border-radius: 16px; padding: 30px; border: 1px solid #EBEFEB; box-shadow: 0px 4px 16px rgba(0, 0, 0, 0.03); margin-bottom: 20px; }
    [data-testid="stExpander"] { background-color: #FFFFFF; border-radius: 12px; border: 1px solid #EBEFEB; box-shadow: 0px 2px 8px rgba(0, 0, 0, 0.02); }
    
    .stTextInput>div>div>input, .stSelectbox>div>div>div, .stTextArea>div>div>textarea, .stNumberInput>div>div>div>input {
        background-color: #FFFFFF !important; border-radius: 8px !important; border: 1.5px solid #2E7D32 !important; color: #1E1E1E !important;
    }
    .stSelectbox label, .stTextInput label, .stNumberInput label, .stSlider label { color: #4A5D52 !important; font-weight: 600 !important; font-size: 14px !important; }
    
    .stButton>button {
        background-color: #2E7D32 !important; color: white !important; border-radius: 8px !important; font-weight: 600 !important;
        padding: 12px 24px !important; border: none !important; box-shadow: 0 4px 10px rgba(46, 125, 50, 0.2) !important; transition: all 0.2s ease !important; width: 100%; margin-top: 10px;
    }
    .stButton>button:hover { background-color: #1B5E20 !important; transform: translateY(-1px); }
    
    .stChatMessage { background-color: #FFFFFF; border-radius: 12px; padding: 20px; border: 1px solid #E0E5E2; box-shadow: 0 2px 8px rgba(0,0,0,0.02); }
    hr { border-color: #EBEFEB !important; margin-top: 25px; margin-bottom: 25px; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="top-header"><h1>🌾 MATULA</h1><p>Apontamento Técnico de Safra</p></div>', unsafe_allow_html=True)

# --- MENU LATERAL ---
with st.sidebar:
    st.header("🤖 Felipe (IA Agronômica)")
    st.write("Insira sua chave do Google AI Studio para ativar as análises.")
    api_key = st.text_input("API Key (Gemini):", type="password")
    if api_key: st.info("Felipe está ativo.")
    else: st.warning("Operando com motor offline.")
    st.markdown("---")
    st.markdown("[Pegar minha chave gratuita](https://aistudio.google.com/app/apikey)")

# --- BASES DE CONHECIMENTO ---
INFO_PRAGAS = {
    # SOJA
    "Percevejo-marrom (Euschistus heros)": {"dano": "Insere o estilete nas vagens e injeta toxinas. Causa abortamento, grãos chochos ou enrugados.", "id": "11-13mm. Marrom-escuro. Meia-lua branca no dorso."},
    "Percevejo-verde-pequeno (Piezodorus guildinii)": {"dano": "Injeta saliva altamente tóxica, causando retenção foliar e reduzindo qualidade da semente.", "id": "8-10mm. Verde-claro. Faixa transversal avermelhada no dorso."},
    "Percevejo-verde (Nezara viridula)": {"dano": "Perfura vagens em formação, favorecendo fungos nas sementes.", "id": "14-17mm. Verde-escuro intenso. Três pequenos pontos brancos no dorso."},
    "Percevejo-asa-preta (Edessa meditabunda)": {"dano": "Ataca hastes e ramos, sugando seiva. Dano menor nas vagens.", "id": "11-14mm. Corpo verde com asas na cor preta/marrom-escura."},
    "Percevejo-barriga-verde (Dichelops spp.) - Soja": {"dano": "Dano focado na sucção de seiva de hastes e vagens em estágios finais.", "id": "9-11mm. Dorso marrom, ventre verde. Cabeça com duas pontas agudas."},
    "Lagarta-da-soja (Anticarsia gemmatalis)": {"dano": "Consome limbo foliar, poupa nervuras. Reduz fotossíntese.", "id": "Até 40mm. Verde ou negra. 4 pares de pernas abdominais. Joga-se no chão quando tocada."},
    "Lagarta-falsa-medideira (Chrysodeixis includens)": {"dano": "Deixa a folha rendilhada. Fica no baixeiro da planta.", "id": "Até 35mm. Verde-clara. 2 pares de pernas falsas (anda medindo palmos)."},
    "Lagarta Helicoverpa (Helicoverpa armigera)": {"dano": "Ataca folhas, hastes, flores e vagens. Muito resistente a defensivos.", "id": "Até 40mm. Pelos finos e tubérculos escuros. Enrola-se em espiral."},
    "Lagarta-das-maçãs (Heliothis virescens)": {"dano": "Ataca ponteiros, flores e vagens.", "id": "Até 35mm. Verde/amarelada com estrias claras. Micro-espinhos escuros no corpo."},
    "Lagarta-preta (Spodoptera cosmioides)": {"dano": "Desfolhadora voraz. Ataca até vagens maduras.", "id": "Até 45mm. Preta/marrom-escura aveludada. Listras amareladas laterais."},
    "Lagarta-elasmo (Elasmopalpus lignosellus)": {"dano": "Penetra no colo da planta causando 'coração morto'.", "id": "15-20mm. Verde-azulada/avermelhada. Fica em casulo de terra na base da planta."},
    "Broca-das-axilas (Epinotia aporema)": {"dano": "Broqueia axilas das folhas e ponteiros, unindo folíolos com teia.", "id": "10-15mm. Branca-amarelada a rosada. Escondida no ponteiro."},
    "Tamanduá-da-soja (Sternechus subsignatus)": {"dano": "Adulto raspa a haste (desfiamento). Larva broqueia haste/raiz.", "id": "Adulto: Besouro bicudo de 8mm, preto com listras amarelas. Larva: Branca, sem pernas."},
    "Mosca-branca (Bemisia tabaci)": {"dano": "Excreta honeydew (fumagina). Vetor de viroses.", "id": "1-2mm. Inseto alado, corpo amarelado coberto com pó ceroso branco."},
    "Ácaro-rajado (Tetranychus urticae)": {"dano": "Bronzeamento foliar e desfolha precoce. Agravado em secas.", "id": "0,5mm. Esverdeado com duas manchas escuras no dorso. Forma teias."},
    "Ácaro-branco (Polyphagotarsonemus latus)": {"dano": "Causa encarquilhamento foliar e engrossamento de nervuras.", "id": "0,2mm. Translúcido a branco brilhante. Não tece teia."},
    "Ácaro-vermelho (Tetranychus ludeni)": {"dano": "Pontuações claras que evoluem para amarelecimento foliar.", "id": "0,5mm. Vermelho intenso e brilhante. Tece pequena quantidade de teia."},
    "Tripes (Frankliniella schultzei)": {"dano": "Raspa folhas (aspecto prateado). Transmite queima-do-broto.", "id": "1-2mm. Corpo alongado, amarelado, marrom ou preto. Muito rápido."},
    "Coró-da-soja (Phyllophaga cuyabana)": {"dano": "Larva de solo que consome raízes em reboleiras.", "id": "Larva branca (bicho-bolo) em 'C', cabeça marrom, 3 pares de pernas."},
    "Piolho-de-cobra / Embuá (Julida)": {"dano": "Ataca sementes e raízes de plântulas.", "id": "20-50mm. Corpo cilíndrico rígido (parece mola) com dezenas de pernas."},
    # MILHO SAFRINHA
    "Cigarrinha-do-milho (Dalbulus maidis)": {"dano": "Vetor de molicutes (enfezamento). Atrofia o milho e impede formação da espiga.", "id": "3-4mm. Cor palha. Duas manchas negras circulares na cabeça."},
    "Lagarta-do-cartucho (Spodoptera frugiperda)": {"dano": "Destrói o cartucho do milho. Pode perfurar a espiga.", "id": "Até 40mm. Y invertido branco na cabeça e 4 pontos escuros em quadrado no abdômen."},
    "Percevejo-barriga-verde (Dichelops spp.) - Milho": {"dano": "Perfura a base da plântula. Causa 'encharutamento' e morte do perfilho.", "id": "9-11mm. Dorso marrom, ventre verde vivo."},
    "Lagarta-da-espiga (Helicoverpa zea)": {"dano": "Penetra na espiga, destruindo grãos do topo.", "id": "Até 40mm. Listras longitudinais claras e escuras, microespinhas ásperas."},
    "Lagarta-rosca (Agrotis ipsilon)": {"dano": "Corta plântulas rente ao chão à noite.", "id": "Até 45mm. Cinza-escura/marrom. Fica enrolada enterrada próxima à planta de dia."},
    "Lagarta-elasmo (Elasmopalpus lignosellus) - Milho": {"dano": "Perfura o colmo ('coração morto'). Comum em solo arenoso.", "id": "Lagarta saltitante verde-azulada. Constrói tubo de terra na entrada do colmo."},
    "Larva-alfinete (Diabrotica speciosa)": {"dano": "Destrói raízes adventícias (acamamento / pescoço de ganso).", "id": "Larva fina, cilíndrica, branca-amarelada. 10-15mm."},
    "Coró-do-milho (Liogenys spp.)": {"dano": "Larva de solo. Mastiga sistema radicular jovem em reboleiras.", "id": "Branca em 'C' com cabeça marrom e traseira dilatada escura (terra translúcida)."},
    "Pulgão-do-milho (Rhopalosiphum maidis)": {"dano": "Suga seiva em cartuchos e pendões. Atrai fumagina.", "id": "2mm. Corpo mole, formato de pêra, verde-azulada escura a preta. Vivem em colônias."},
    "Broca-do-colmo (Diatraea saccharalis) - Milho": {"dano": "Broqueia colmo, causando tombamento.", "id": "Até 25mm. Lagarta branco-amarelada com pintas escuras (verrugas)."},
    "Tripes (Frankliniella spp.)": {"dano": "Raspa epiderme (V2-V5). Folhas esbranquiçadas que podem enrolar.", "id": "1-2mm. Corpo alongado (parece traço). Ficam no cartucho de plantas jovens."},
    "Ácaro-rajado (Tetranychus urticae) - Milho": {"dano": "Suga seiva (bronzeamento). Inicia na baixeira e sobe.", "id": "0,5mm. Esverdeado com manchas escuras no dorso. Produz teia."},
    "Formiga-saúva (Atta spp.)": {"dano": "Cortam intensamente folhas jovens. Desfolham bordaduras.", "id": "Formigas grandes. Soldado com cabeça muito grande. Cortes em meia-lua."},
    "Formiga-quemquém (Acromyrmex spp.)": {"dano": "Cortam pedaços menores de plantas novas.", "id": "Mais de três pares de espinhos no dorso do tórax."},
    "Cupim-de-montículo (Procornitermes spp.)": {"dano": "Ataca sementes e raízes em solos secos com palhada.", "id": "Insetos sociais esbranquiçados de corpo mole."},
    "Percevejo-marrom (Euschistus heros) - Milho": {"dano": "Transição da soja. Suga seiva de plântulas.", "id": "Escudo marrom com espinhos laterais e meia-lua branca."},
    "Besouro-saltador / Larva-arame (Conoderus spp.)": {"dano": "Larva perfura sementes e raízes.", "id": "Larva fina e muito dura (arame), amarelada. Adulto dá 'saltos' (cliques)."},
    "Bicho-bolo (Cyclocephala spp.)": {"dano": "Consome raízes superficiais.", "id": "Coró em 'C', branco com cabeça marrom clara."},
    "Mosca-da-espiga (Euxesta spp.)": {"dano": "Larvas comem cabelos e grãos leitosos.", "id": "Mosca com asas transparentes possuindo faixas pretas. Larva branca/amarelada."},
    "Lagarta-falsa-medideira (Chrysodeixis) - Milho": {"dano": "Praga ocasional, desfolha baixeiro.", "id": "Anda medindo palmos. Cor verde com listras brancas."},
    # SORGO
    "Mosca-do-sorgo (Stenodiplosis sorghicola)": {"dano": "A fêmea põe ovos nas flores; larvas destroem o ovário (panícula chocha).", "id": "2mm (parece mosquito). Vermelho-alaranjado vivo com asas transparentes."},
    "Pulgão-verde (Schizaphis graminum)": {"dano": "Injeta saliva tóxica (manchas avermelhadas). Reduz fotossíntese.", "id": "2mm. Verde-amarelada clara com listra verde-escura central no dorso."},
    "Pulgão-da-cana / Pulgão-amarelo (Melanaphis sacchari)": {"dano": "Multiplica rápido, produz muita fumagina, travando a colheita.", "id": "Cor amarelo a palha. Pontas das antenas e pernas na cor negra."},
    "Pulgão-do-milho (Rhopalosiphum maidis) - Sorgo": {"dano": "Fica no cartucho. Atrasa a panícula ('vassoura presa').", "id": "Verde-azulado intenso a preto. Corpo e pernas escuros."},
    "Lagarta-do-cartucho (Spodoptera frugiperda) - Sorgo": {"dano": "Destrói folhas internas do cartucho e meristema apical.", "id": "Y invertido claro na cabeça. 4 pontos escuros em quadrado no abdômen."},
    "Lagarta-da-panícula / Espiga (Helicoverpa zea)": {"dano": "Alimenta-se de grãos leitosos/pastosos na panícula.", "id": "Cores variáveis. Listras longitudinais e microespinhas no dorso."},
    "Broca-do-colmo (Diatraea saccharalis) - Sorgo": {"dano": "Cava galerias no colmo (tombamento).", "id": "Lagarta branca/amarela com verrugas pretas visíveis no dorso."},
    "Lagarta-elasmo (Elasmopalpus lignosellus) - Sorgo": {"dano": "Destrói o ponto de crescimento ('coração morto').", "id": "Esverdeada com listras vermelhas. Casulo de terra na base da haste."},
    "Lagarta-rosca (Agrotis ipsilon) - Sorgo": {"dano": "Corta a base das plântulas à noite.", "id": "Liso/grossa cinza-terrosa. Escondida sob a terra de dia."},
    "Percevejo-barriga-verde (Dichelops spp.) - Sorgo": {"dano": "Suga base de plantas jovens. Perfilhamento improdutivo.", "id": "Dorso marrom, barriga verde. Cabeça com pontas afiadas."},
    "Percevejo-verde (Nezara viridula) - Sorgo": {"dano": "Ataca panículas, sugando grãos e reduzindo peso.", "id": "Totalmente verde-escuro, 3 pontos brancos na base do escudo."},
    "Percevejo-marrom (Euschistus heros) - Sorgo": {"dano": "Suga grãos jovens na panícula.", "id": "Marrom com espinhos laterais atrás da cabeça. Meia-lua branca."},
    "Percevejo-do-sorgo (Thyanta spp.)": {"dano": "Sugador secundário na panícula.", "id": "8-10mm. Predominantemente verde, mas com margens do tórax avermelhadas."},
    "Coró-das-pastagens (Diloboderus abderus)": {"dano": "Consome raízes, definhando plantas em manchas.", "id": "Coró de grande porte (50mm). Cabeça vermelho-escura."},
    "Larva-alfinete (Diabrotica speciosa) - Sorgo": {"dano": "Alimenta-se de raízes novas, comprometendo ancoragem.", "id": "Larva fina, esbranquiçada e alongada."},
    "Tripes-do-sorgo (Caliothrips spp.)": {"dano": "Raspa a folha (estrias prateadas). Seca pontas de plantas jovens.", "id": "Corpo afilado milimétrico, escuro (preto a marrom)."},
    "Ácaro-rajado (Tetranychus urticae) - Sorgo": {"dano": "Prolifera no calor seco. Bronzeia folhas do baixeiro.", "id": "Amarelado com duas manchas escuras dorsais. Forma teia fina."},
    "Formiga-cortadeira (Atta spp. / Acromyrmex)": {"dano": "Destruição rápida de bordaduras jovens.", "id": "Formigas grandes cortando folhas em pedaços."},
    "Cupim-de-raiz (Syntermes spp.)": {"dano": "Seca plântulas atacando raízes no cerrado.", "id": "Operários esbranquiçados, soldados com cabeças alaranjadas."},
    "Vaquinha-verde-amarela (Diabrotica speciosa) - Sorgo": {"dano": "Adulto mastiga folhas (pequenos furos).", "id": "Besourinho verde brilhante com 6 grandes manchas amarelas."}
}

INFO_DOENCAS = {
    # SOJA
    "Ferrugem-asiática (Phakopsora pachyrhizi)": {"dano": "Desfolha precoce severa. O fungo drena nutrientes e água, impedindo o enchimento de grãos.", "id": "Pústulas como pequenos 'vulcões' na face inferior da folha, cor castanha/escura."},
    "Mancha-alvo (Corynespora cassiicola)": {"dano": "Causa desfolha prematura. Atinge folhas, hastes e vagens.", "id": "Manchas circulares com anéis concêntricos (formato de alvo) e um ponto negro central."},
    "Antracnose (Colletotrichum truncatum)": {"dano": "Ataca desde a semente até a vagem. Causa vagens retorcidas/chochas.", "id": "Manchas deprimidas escuras (pontuações negras com setas que lembram espinhos)."},
    "Oídio (Microsphaera diffusa)": {"dano": "O fungo cobre a folha, bloqueando a luz do sol e reduzindo a fotossíntese.", "id": "Fina camada de pó branco a acinzentado sobre as folhas e hastes."},
    "Mancha-parda / Septoriose (Septoria glycines)": {"dano": "Uma das primeiras a aparecer. Amarelecimento e queda das folhas do baixeiro.", "id": "Pequenos pontos escuros angulares, delimitados pelas nervuras."},
    "Crestamento-foliar / Cercosporiose (Cercospora kikuchii)": {"dano": "Desfolha severa reprodutiva e mancha-púrpura nas sementes.", "id": "Folhas superiores com manchas vermelho-arroxeadas, aspecto de couro."},
    "Mofo-branco (Sclerotinia sclerotiorum)": {"dano": "Apodrece hastes e vagens. Forma estruturas de resistência (escleródios).", "id": "Crescimento semelhante a algodão branco nas hastes, com pedrinhas pretas."},
    "Podridão-radicular (Phytophthora sojae)": {"dano": "Morte em áreas com encharcamento.", "id": "Apodrecimento marrom-escuro que sobe da raiz até os primeiros nós da haste."},
    "Podridão-cinzenta-do-caule (Macrophomina phaseolina)": {"dano": "Morte prematura ('soja seca em pé'). Associada a seca.", "id": "Tecido cinzento com pontuações pretas minúsculas ao abrir a base da haste."},
    "Morte-súbita (Fusarium virguliforme)": {"dano": "Toxina sobe pela planta, causando necrose foliar fulminante.", "id": "Manchas amarelas entre nervuras que evoluem para necrose marrom."},
    # MILHO SAFRINHA
    "Complexo Enfezamento (Molicutes / Cigarrinha)": {"dano": "Entupimento vascular. A planta não cresce, espigas malformadas.", "id": "Vermelho: folhas avermelhadas nas bordas. Pálido: estrias brancas largas."},
    "Ferrugem-polissora (Puccinia polysora)": {"dano": "Destrói a área foliar verde muito rápido no terço médio e superior.", "id": "Pústulas pequenas, circulares e em grande quantidade, cor amarelo-ouro a dourada."},
    "Mancha-branca (Phaeosphaeria / Pantoea)": {"dano": "Reduz drasticamente a fotossíntese. Senescência antecipada.", "id": "Lesões iniciais aquosas que se tornam esbranquiçadas e arredondadas (1-2 cm)."},
    "Cercosporiose (Cercospora zeae-maydis)": {"dano": "Seca o milho de baixo para cima.", "id": "Lesões cinza a marrons, alongadas e estritamente retangulares nas nervuras."},
    "Helmintosporiose (Exserohilum turcicum)": {"dano": "Necrose intensa de folhas. Comum com acúmulo de palha.", "id": "Lesões grandes elípticas, formato de 'charuto', palha com bordos escuros."},
    "Podridão-do-colmo (Fusarium / Colletotrichum)": {"dano": "Decompõe a medula do colmo. A planta tomba.", "id": "Colmo oco e descolorido. Rosada (Fusarium) ou preta brilhante (Antracnose)."},
    "Podridão-de-espiga (Fusarium verticillioides)": {"dano": "Destrói os grãos e produz micotoxinas.", "id": "Mofo branco a rosado sobre os grãos, partindo da ponta da espiga."},
    "Mancha-de-diplodia (Stenocarpella macrospora)": {"dano": "Progride da folha para apodrecer espigas e colmos.", "id": "Lesões foliares muito grandes, marrons com ponto claro no centro e pontinhos negros."},
    "Ferrugem-comum (Puccinia sorghi)": {"dano": "Reduz área fotossintética em climas amenos.", "id": "Pústulas alongadas, cor marrom-ferrugem a canela."},
    "Virose-da-risca (MRFV - Vetor: Cigarrinha)": {"dano": "Afeta o desenvolvimento geral e tamanho das espigas.", "id": "Pontinhos cloróticos alinhados nas nervuras foliares ('riscos' tracejados)."},
    # SORGO
    "Ferrugem-do-sorgo (Puccinia purpurea)": {"dano": "Acelera a maturação foliar e debilita a panícula.", "id": "Pústulas marrom-arroxeadas, circulares, que rompem a epiderme."},
    "Antracnose-do-sorgo (Colletotrichum sublineolum)": {"dano": "Ataca folhas, panículas e sementes.", "id": "Manchas circulares a elípticas com centro pardo e bordas arroxeadas."},
    "Helmintosporiose / Mancha-foliar (Exserohilum turcicum)": {"dano": "Destrói a folhagem precocemente, reduzindo peso do grão.", "id": "Lesões grandes (charuto), tecido morto cor de palha no centro."},
    "Doença-açucarada / Ergot (Claviceps africana)": {"dano": "Infecta o ovário da flor, impedindo a formação do grão.", "id": "Exsudação de líquido pegajoso (mel) que escorre das espiguetas."},
    "Mancha-zonada (Gloeocercospora sorghi)": {"dano": "Extensa necrose foliar em umidade.", "id": "Grandes lesões semi-circulares formando anéis alternados ('zonas')."},
    "Podridão-seca-do-colmo (Macrophomina phaseolina)": {"dano": "Colapso do colmo na fase de enchimento, levando a acamamento extremo.", "id": "Desintegração da medula folhando fibras intactas com pontuações pretas."},
    "Míldio-do-sorgo (Peronosclerospora sorghi)": {"dano": "Infeção sistêmica que esteriliza a planta.", "id": "Listras cloróticas paralelas. Penugem branca fina na face inferior no orvalho."},
    "Estria-bacteriana (Xanthomonas vasicola)": {"dano": "Redução fotossintética favorecida por ventos fortes.", "id": "Estrias estreitas e inter-nervais, vermelho-escuras."},
    "Podridão-vermelha-do-colmo (Colletotrichum graminicola)": {"dano": "Enfraquece a estrutura da planta.", "id": "Parte interna do colmo com áreas na cor vermelho-púrpura a marrom."},
    "Mancha-retangular (Cercospora sorghi)": {"dano": "Desfolha e queda de rendimento do grão.", "id": "Manchas pequenas, retangulares perfeitas e marrom-avermelhadas."}
}

INFO_DANINHAS = {
    "Capim-amargoso (Digitaria insularis)": {"dano": "Gramínea perene, alta competição. Casos de resistência a Glifosato e ACCase.", "id": "Folhas pilosas, entouceiramento agressivo, inflorescência branca e plumosa."},
    "Buva (Conyza spp.)": {"dano": "Sementeira dispersa pelo vento. Alta resistência a Glifosato e ALS. Competição extrema inicial.", "id": "Caule ereto, folhas estreitas e pilosas. Crescimento em roseta no estágio inicial."},
    "Capim-pé-de-galinha (Eleusine indica)": {"dano": "Touceira espalmada. Casos de resistência múltipla. Rouba nutrientes rápido.", "id": "Hábito prostrado, hastes esbranquiçadas na base. Inflorescência lembra dedos de galinha."},
    "Caruru (Amaranthus spp.)": {"dano": "Crescimento explosivo, folha larga. Alerta máximo para Amaranthus palmeri.", "id": "Caule liso ou com espinhos, avermelhado na base. Inflorescência em espiga densa."},
    "Corda-de-viola (Ipomoea spp.)": {"dano": "Trepadeira. Enrola na cultura, causando quebra e travando a colheitadeira.", "id": "Folhas em formato de coração. Flores grandes em formato de funil (rosa, azul, branca)."},
    "Trapoeraba (Commelina benghalensis)": {"dano": "Tolera glifosato. Reproduz por rizomas e sementes (inclusive subterrâneas).", "id": "Folhas carnudas, caule suculento. Flor azul pequena. Raízes nos nós que tocam o solo."},
    "Leiteiro / Amendoim-bravo (Euphorbia heterophylla)": {"dano": "Sombreamento rápido da cultura. Alta taxa de infestação.", "id": "Folhas de formatos variados. Exsuda látex branco espesso quando o caule ou folha é quebrado."},
    "Picão-preto (Bidens pilosa)": {"dano": "Rápida propagação. Competição forte por luz e água.", "id": "Sementes em formato de agulhas com ganchos que grudam (carrapicho). Caule quadrangular."},
    "Milho-tiguera (Zea mays voluntário)": {"dano": "Competidor feroz na soja. Serve de ponte verde para cigarrinha e enfezamento.", "id": "Plantas de milho crescendo fora de época e alinhamento no meio da cultura atual."},
    "Soja-tiguera (Glycine max voluntária)": {"dano": "Ponte verde para ferrugem e outras doenças no milho ou pousio.", "id": "Plântulas de soja emergindo de grãos caídos na colheita anterior."},
    "Tiririca (Cyperus rotundus)": {"dano": "Extremamente agressiva, reprodução vegetativa subterrânea rápida.", "id": "Folhas estreitas e brilhantes. Caule triangular. Raiz forma cadeia de pequenos tubérculos escuros."},
    "Vassourinha-de-botão (Spermacoce verticillata)": {"dano": "Caule lenhoso, dificulta ação de herbicidas de contato.", "id": "Hábito subarbustivo, folhas dispostas em círculo no nó (verticiladas). Flores brancas em 'botão'."},
    "Capim-massambará (Sorghum halepense)": {"dano": "Perene, rizomatosa. Forte efeito alelopático (inibe crescimento de outras plantas).", "id": "Parece sorgo ou milho novo. Rizomas grossos e esbranquiçados no solo. Folhas largas."},
    "Guanxuma (Sida spp.)": {"dano": "Raiz pivotante profunda, rouba água das camadas inferiores.", "id": "Caule duro, quase lenhoso ('vassoura'). Folhas serrilhadas. Difícil arranque manual."},
    "Capim-colonião (Panicum maximum)": {"dano": "Crescimento agressivo, porte muito alto. Sombreia a cultura.", "id": "Gramínea robusta, touceiras grandes, folhas largas. Inflorescência grande e ramificada."},
    "Capim-carrapicho (Cenchrus echinatus)": {"dano": "Atrasa colheita, incomoda operadores e contamina grãos.", "id": "Folhas verdes claras, bainha avermelhada. Produz os famosos 'carrapichos' espinhosos."},
    "Maria-pretinha (Solanum americanum)": {"dano": "Frutos mancham os grãos da soja na colheita, gerando desconto na umidade e impureza.", "id": "Folhas verde-escuras. Produz pequenos frutos esféricos que ficam pretos brilhantes quando maduros."},
    "Apaga-fogo / Periquito (Alternanthera tenella)": {"dano": "Cobre o solo rapidamente em tapete, abafando plântulas.", "id": "Planta rasteira. Caule avermelhado e muito ramificado. Inflorescência como pequenas 'bolinhas' brancas."},
    "Nabiça / Fumo-bravo (Raphanus raphanistrum)": {"dano": "Crucífera agressiva no sul e safrinhas de inverno.", "id": "Folhas lobadas ásperas, caule com pelos rígidos. Flores amarelas em cruz."},
    "Aveia / Azevém voluntário": {"dano": "Matocompetição severa em áreas de transição inverno-verão no Sul.", "id": "Gramíneas de clima ameno que rebrotam ou nascem de sementes perdidas antes do plantio da soja."}
}

CATALOGO_PRODUTOS = {
    "Herbicida": ["Glyphosate (Glifosato)", "Clethodim", "2,4-D", "Atrazina", "Glufosinato de amônio", "Haloxifope", "Diquat", "S-metolacloro", "Flumioxazina", "Dicamba", "Outro (Digitar)"],
    "Inseticida": ["Bifentrina", "Lambda-cialotrina", "Imidacloprid", "Tiametoxam", "Clorantraniliprole (Premio)", "Metomil", "Acefato", "Espinosade", "Flubendiamida", "Bacillus thuringiensis (Bt)", "Outro (Digitar)"],
    "Fungicida": ["Azoxistrobina + Ciproconazol (Priori Xtra)", "Piraclostrobina + Epoxiconazol (Opera)", "Trifloxistrobina + Protioconazol (Fox)", "Picoxistrobina + Ciproconazol (Aproach Prima)", "Mancozebe", "Clorotalonil", "Tebuconazol", "Outro (Digitar)"],
    "Adubo Foliar": ["Boro (B)", "Manganês (Mn)", "Zinco (Zn)", "Cobre (Cu)", "Aminoácidos", "Co-Mo (Cobalto e Molibdênio)", "Outro (Digitar)"],
    "Regulador de Crescimento": ["Trinexapac-etil", "Cloreto de Mepiquate", "Outro (Digitar)"],
    "Óleo/Adjuvante": ["Óleo Mineral", "Óleo Vegetal", "Espalhante Siliconado", "Condicionador de Calda", "Outro (Digitar)"],
    "Outro": ["Outro (Digitar)"]
}

def salvar_registro(talhao_id, tipo, detalhes, foto):
    caminho = None
    if foto:
        caminho = f"fotos_app/foto_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        with open(caminho, "wb") as f: f.write(foto.getbuffer())
    conn = sqlite3.connect(ARQUIVO_DB)
    conn.cursor().execute("INSERT INTO apontamentos (talhao_id, tipo, detalhes, foto_path) VALUES (?, ?, ?, ?)", (talhao_id, tipo, detalhes, caminho))
    conn.commit()
    conn.close()

# --- MOTORES OFFLINE DE ANÁLISE ---
def conselheiro_praga(cultura, estagio, praga, quant, desfolha, pressao, estagio_praga, distribuicao, estresse, inimigos):
    p_lower = praga.lower()
    is_reprodutivo = any(x in estagio for x in ["R1","R2","R3","R4","R5","R6","R7","R8","Florescimento","Enchimento"])
    is_emergencia = any(x in estagio for x in ["VE", "V1", "V2", "Emergência"])
    fator_estresse = 5 if "Severo" in estresse else (2 if "Leve" in estresse else 0)
    alerta_inimigos = " Considere preservar inimigos naturais." if "Alta" in inimigos else ""
    txt_dist = f"em {distribuicao.lower()}" if "Não avaliada" not in distribuicao else "no talhão"

    if "percevejo" in p_lower:
        limite = 2.0 if "Vigorosa" in estresse else (1.5 if "Leve" in estresse else 1.0)
        if is_reprodutivo:
            if quant >= limite: return f"🔴 AÇÃO IMEDIATA", f"Toxinas na estrutura reprodutiva. Limite atingido.{alerta_inimigos}", "error"
            elif quant >= (limite/2): return "🟡 ESTADO DE ALERTA", f"População próxima ao dano {txt_dist}.", "warning"
            else: return "🟢 NÍVEL SEGURO", "Planta tolera danos atuais.", "success"
        elif "barriga-verde" in p_lower and is_emergencia:
            if quant >= 1.0: return "🔴 RISCO DE ESTANDE", "Dano letal na plântula recém-emergida.", "error"
            else: return "🟡 ATENÇÃO", "Monitorar encharutamento foliar.", "warning"
        else: return "🟢 FASE VEGETATIVA", "Baixo risco. Preservar inimigos naturais.", "success"
            
    elif any(l in p_lower for l in ["lagarta", "broca", "vaquinha"]):
        limite = (15 if is_reprodutivo else 30) - fator_estresse
        if "helicoverpa" in p_lower or "espiga" in p_lower or "panícula" in p_lower: limite = 10 - (fator_estresse/2)
        if "broca" in p_lower: limite = 5
        txt_estagio = f" ({estagio_praga})" if "Não avaliado" not in estagio_praga else ""
        if desfolha >= limite: return f"🔴 DANO ECONÔMICO ({desfolha}%)", f"Ultrapassou limite reajustado ({limite}%){txt_estagio}.{alerta_inimigos}", "error"
        else: return f"🟢 TOLERÂNCIA", "Planta compensa a perda foliar nesta fase.", "success"
            
    elif any(s in p_lower for s in ["elasmo", "rosca", "tamanduá", "alfinete", "coró", "cupim", "formiga", "piolho", "besouro"]):
        if desfolha >= 10: return "🔴 PERDA DE ESTANDE", "Morte irreversível de plântulas. Manejo corretivo urgente.", "error"
        else: return "🟡 ALERTA DE REBOLEIRAS", f"Pragas de solo atacando {txt_dist}.", "warning"
            
    elif any(v in p_lower for v in ["cigarrinha", "pulgão", "mosca-branca", "ácaro", "tripes", "mosca-do-sorgo"]):
        if "cigarrinha" in p_lower and is_emergencia:
            if pressao in ["Média", "Alta"]: return "🔴 RISCO DE ENFEZAMENTO", "Milho susceptível com alta presença do vetor.", "error"
            else: return "🟡 MONITORAMENTO", "Presença de vetor na fase crítica.", "warning"
        elif "mosca-do-sorgo" in p_lower and "Floresc" in estagio:
            if quant >= 1.0: return "🔴 ALERTA DE PANÍCULA", "1 mosca/panícula indica controle necessário.", "error"
            else: return "🟡 ESTÁGIO CRÍTICO", "Monitore floradas ativas.", "warning"
        elif pressao in ["Média", "Alta"]: return "🟡 PRESSÃO ELEVADA", "Risco de perda de vigor agravado pelo clima.", "warning"
        else: return "🔵 ESTÁVEL", "Pressão não oferece risco imediato.", "info"

    return "🔵 REGISTRADO", "Apontamento catalogado.", "info"

def conselheiro_doenca(cultura, estagio, doenca, severidade, incidencia, local, clima, genetica):
    d_lower = doenca.lower()
    is_reprodutivo = any(x in estagio for x in ["R1","R2","R3","R4","R5","R6","R7","R8","Florescimento","Enchimento"])
    doenca_critica = any(x in d_lower for x in ["ferrugem", "enfezamento", "mofo-branco", "morte-súbita", "ergot", "açucarada"])
    limite_acao = 5 if doenca_critica else 10
    
    if "Suscetível" in genetica: limite_acao -= 3
    elif "Resistente" in genetica: limite_acao += 5
    if "Úmido" in clima or "Chuvoso" in clima: limite_acao -= 2
    if limite_acao < 1: limite_acao = 1
    
    if doenca_critica and "enfezamento" not in d_lower and "mofo" not in d_lower:
        if incidencia >= 1 and severidade >= limite_acao: return f"🔴 INTERVENÇÃO IMEDIATA", f"Severidade cruzou o NDE ajustado ({limite_acao}%).", "error"
        elif incidencia >= 1: return "🟡 APLICAÇÃO PREVENTIVA", "Patógeno agressivo identificado.", "warning"
        else: return "🟢 MONITORAMENTO", "Doença crítica não visível.", "success"
            
    elif "mofo-branco" in d_lower:
        if incidencia > 0 and is_reprodutivo: return "🔴 ALERTA DE ESCLERÓDIOS", "Exige proteção imediata com fungicida para evitar contaminação do solo.", "error"
        else: return "🟡 ATENÇÃO AO DOSSEL", "Fechamento da entrelinha favorecerá o fungo.", "warning"
            
    elif any(s in d_lower for s in ["radicular", "podridão", "colmo", "morte", "seca-do-colmo"]):
        if incidencia >= 5: return "🔴 PERDA DE ESTANDE/ACAMAMENTO", "Foco na regulagem da colheitadeira e rotação de cultura.", "error"
        else: return "🟡 MANCHAS/REBOLEIRAS", "Marque o local. Avalie compactação no pós-colheita.", "warning"
            
    else: 
        if severidade >= limite_acao:
            txt_local = "Ponteiro atingido!" if "Ponteiro" in local else "Defesa curativa necessária."
            return f"🔴 CONTROLE DE MANCHAS", f"Severidade ({severidade}%) excedeu limite seguro ({limite_acao}%). {txt_local}", "error"
        elif severidade > 0: return f"🟡 INÍCIO DE EPIDEMIA", f"Tolerância de {limite_acao}% para esta cultivar.", "warning"
        else: return "🟢 DOSSEL LIMPO", "Lavoura sadia aparente.", "success"

def conselheiro_daninha(cultura, daninha, estagio_daninha, densidade, distribuicao, estresse, resistencia):
    d_lower = daninha.lower()
    alertas = []; status = "success"
    
    if "tiguera" in d_lower or "voluntári" in d_lower:
        alertas.append("🔴 **Ponte Verde:** Plantas voluntárias hospedam pragas e doenças críticas. Exigem dessecação rigorosa.")
        status = "error"
        
    if any(x in estagio_daninha for x in ["Perenizada", "> 6", "> 15cm", "Entrelaçando", "Multiplicação"]):
        alertas.append("🔴 **Estágio Avançado:** Plantas grandes ou perenizadas. Doses normais sistêmicas perderão eficiência.")
        status = "error"
    elif any(x in estagio_daninha for x in ["Ideal", "Cotilédone", "Roseta (< 5cm", "1 a 3 folhas"]):
        alertas.append("🟢 **Estágio Ideal:** Máxima taxa de absorção de herbicidas.")
        
    if "Seca" in estresse or "Mecânico" in estresse:
        alertas.append("🟡 **Planta Estressada:** Metabolismo parado. O herbicida sistêmico não será bem translocado.")
        status = "warning" if status != "error" else "error"
        
    if "Sim" in resistencia:
        alertas.append("🔴 **Resistência:** Rotação de MOA obrigatória. Associe pré-emergentes.")
        status = "error"
        
    if not alertas: return "🔵 INFESTAÇÃO MONITORADA", f"Competição sob controle no momento.", "info"
    
    if status == "error": return "🔴 ALERTA DE MATOCOMPETIÇÃO SEVERA", "\n\n".join(alertas), "error"
    elif status == "warning": return "🟡 ATENÇÃO AO MANEJO HERBICIDA", "\n\n".join(alertas), "warning"
    else: return "🟢 MANEJO FACILITADO", "\n\n".join(alertas), "success"

def conselheiro_aplicacao(temp, umidade, vento, equipamento):
    alertas = []; status = "success"
    if temp > 30: alertas.append("⚠️ **Temperatura Elevada:** Evaporação rápida da gota."); status = "warning"
    elif temp < 12: alertas.append("ℹ️ **Temperatura Baixa:** Absorção muito lenta.")
    if umidade < 50: alertas.append("🔴 **Umidade Crítica:** UR < 50% resseca gotas finas."); status = "error"
    if vento > 10: alertas.append("🔴 **Risco de Deriva Severa:** Vento forte."); status = "error"
    elif vento < 3 and equipamento != "Drone Agrícola":
        alertas.append("🟡 **Risco de Inversão Térmica:** Gotas suspensas."); status = "warning" if status != "error" else "error"
    if not alertas: return "🟢 CONDIÇÕES CLIMÁTICAS IDEAIS", "Janela de aplicação excelente.", "success"
    if status == "error": return "🔴 ALERTA DE PERDA DE EFICIÊNCIA", "\n\n".join(alertas), "error"
    else: return "🟡 ATENÇÃO NA TECNOLOGIA DE APLICAÇÃO", "\n\n".join(alertas), "warning"

def conselheiro_adubacao(tipo_insumo, metodo, umidade_solo):
    alertas = []; status = "success"
    if "Nitrogênio" in tipo_insumo or "Ureia" in tipo_insumo:
        if "Seco" in umidade_solo:
            alertas.append("🔴 **Risco de Volatilização:** Ureia em solo seco tem alta perda atmosférica."); status = "error"
    if "Calcário" in tipo_insumo:
        if "lanço (Sem incorporação)" in metodo:
            alertas.append("🟡 **Reação Lenta:** Aplicação em superfície tem reação milimétrica."); status = "warning" if status != "error" else "error"
    if "Encharcado" in umidade_solo:
        alertas.append("🟡 **Risco de Lixiviação:** Solos saturados lavam nutrientes solúveis."); status = "warning" if status != "error" else "error"
    if not alertas: return "🟢 CONDIÇÕES ADEQUADAS", "Parâmetros nutricionais adequados.", "success"
    if status == "error": return "🔴 ALERTA NA OPERAÇÃO", "\n\n".join(alertas), "error"
    else: return "🟡 ATENÇÃO NO MANEJO", "\n\n".join(alertas), "warning"

def conselheiro_solo(estagio, umidade, compactacao, palhada, erosao, temp):
    alertas = []; status = "success"
    is_plantio = any(x in estagio for x in ["VE", "V1", "V2", "Emergência"])
    if umidade == "Pó / Muito Seco" and is_plantio:
        alertas.append("🔴 **Risco de Germinação:** Plantio no pó compromete o estande."); status = "error"
    elif umidade == "Encharcado / Barro":
        alertas.append("🟡 **Risco de Compactação:** Tráfego causará asfixia radicular."); status = "warning" if status != "error" else "error"
    if "Severa" in compactacao:
        alertas.append("🔴 **Física Comprometida:** Compactação limitando raízes."); status = "error"
    if "Sulcos" in erosao or "Ravinas" in erosao:
        alertas.append("🔴 **Perda de Solo:** O processo erosivo está lavando nutrientes."); status = "error"
    if "Descoberto" in palhada:
        alertas.append("🟡 **Proteção Deficiente:** Solo exposto eleva evaporação."); status = "warning" if status != "error" else "error"
        
    if not alertas: return "🟢 SOLO CONSERVADO E APTO", "Estrutura e umidade ideais.", "success"
    if status == "error": return "🔴 ALERTA DE DEGRADAÇÃO", "\n\n".join(alertas), "error"
    else: return "🟡 ATENÇÃO AO MANEJO DO SOLO", "\n\n".join(alertas), "warning"

# --- INTERFACE E FORMULÁRIOS ---
col1, col2, col3 = st.columns(3)
with col1: cultura = st.selectbox("Cultura:", ["Soja", "Milho Safrinha", "Sorgo"])
with col2:
    if cultura == "Soja": estagios = ["VE a VC (Emergência)", "V1 a V3 (Desenvolvimento)", "V4 a V6 (Fechamento)", "R1 a R2 (Florescimento)", "R3 a R4 (Vagens)", "R5 a R6 (Enchimento)", "R7 a R8 (Maturação)"]
    elif cultura == "Milho Safrinha": estagios = ["VE a V2 (Emergência)", "V3 a V6 (Definição de potencial)", "V7 a VT (Pendoamento)", "R1 a R3 (Cabelo/Leitoso)", "R4 a R6 (Maturação)"]
    else: estagios = ["VE a V3 (Emergência/Inicial)", "V4 a V8 (Crescimento Vegetativo)", "Emborrachamento a Florescimento", "Enchimento de Grãos", "Maturação"]
    estagio_cultura = st.selectbox("Fase:", estagios)
with col3: tipo_selecionado = st.selectbox("Categoria:", ["Praga", "Doença", "Plantas Daninhas", "Aplicação", "Adubação/Correção", "Condição do Solo"])

if tipo_selecionado in ["Praga", "Doença", "Plantas Daninhas"]:
    if tipo_selecionado == "Praga":
        if cultura == "Soja": opcoes = ["Percevejo-marrom (Euschistus heros)", "Percevejo-verde-pequeno (Piezodorus guildinii)", "Percevejo-verde (Nezara viridula)", "Percevejo-asa-preta (Edessa meditabunda)", "Percevejo-barriga-verde (Dichelops spp.) - Soja", "Lagarta-da-soja (Anticarsia gemmatalis)", "Lagarta-falsa-medideira (Chrysodeixis includens)", "Lagarta Helicoverpa (Helicoverpa armigera)", "Lagarta-das-maçãs (Heliothis virescens)", "Lagarta-preta (Spodoptera cosmioides)", "Lagarta-elasmo (Elasmopalpus lignosellus)", "Broca-das-axilas (Epinotia aporema)", "Tamanduá-da-soja (Sternechus subsignatus)", "Mosca-branca (Bemisia tabaci)", "Ácaro-rajado (Tetranychus urticae)", "Ácaro-branco (Polyphagotarsonemus latus)", "Ácaro-vermelho (Tetranychus ludeni)", "Tripes (Frankliniella schultzei)", "Coró-da-soja (Phyllophaga cuyabana)", "Piolho-de-cobra / Embuá (Julida)"]
        elif cultura == "Milho Safrinha": opcoes = ["Cigarrinha-do-milho (Dalbulus maidis)", "Lagarta-do-cartucho (Spodoptera frugiperda)", "Percevejo-barriga-verde (Dichelops spp.) - Milho", "Lagarta-da-espiga (Helicoverpa zea)", "Lagarta-rosca (Agrotis ipsilon)", "Lagarta-elasmo (Elasmopalpus lignosellus) - Milho", "Larva-alfinete (Diabrotica speciosa)", "Coró-do-milho (Liogenys spp.)", "Pulgão-do-milho (Rhopalosiphum maidis)", "Broca-do-colmo (Diatraea saccharalis) - Milho", "Tripes (Frankliniella spp.)", "Ácaro-rajado (Tetranychus urticae) - Milho", "Formiga-saúva (Atta spp.)", "Formiga-quemquém (Acromyrmex spp.)", "Cupim-de-montículo (Procornitermes spp.)", "Percevejo-marrom (Euschistus heros) - Milho", "Besouro-saltador / Larva-arame (Conoderus spp.)", "Bicho-bolo (Cyclocephala spp.)", "Mosca-da-espiga (Euxesta spp.)", "Lagarta-falsa-medideira (Chrysodeixis) - Milho"]
        else: opcoes = ["Mosca-do-sorgo (Stenodiplosis sorghicola)", "Pulgão-verde (Schizaphis graminum)", "Pulgão-da-cana / Pulgão-amarelo (Melanaphis sacchari)", "Pulgão-do-milho (Rhopalosiphum maidis) - Sorgo", "Lagarta-do-cartucho (Spodoptera frugiperda) - Sorgo", "Lagarta-da-panícula / Espiga (Helicoverpa zea)", "Broca-do-colmo (Diatraea saccharalis) - Sorgo", "Lagarta-elasmo (Elasmopalpus lignosellus) - Sorgo", "Lagarta-rosca (Agrotis ipsilon) - Sorgo", "Percevejo-barriga-verde (Dichelops spp.) - Sorgo", "Percevejo-verde (Nezara viridula) - Sorgo", "Percevejo-marrom (Euschistus heros) - Sorgo", "Percevejo-do-sorgo (Thyanta spp.)", "Coró-das-pastagens (Diloboderus abderus)", "Larva-alfinete (Diabrotica speciosa) - Sorgo", "Tripes-do-sorgo (Caliothrips spp.)", "Ácaro-rajado (Tetranychus urticae) - Sorgo", "Formiga-cortadeira (Atta spp. / Acromyrmex)", "Cupim-de-raiz (Syntermes spp.)", "Vaquinha-verde-amarela (Diabrotica speciosa) - Sorgo"]
    elif tipo_selecionado == "Doença":
        if cultura == "Soja": opcoes = ["Ferrugem-asiática (Phakopsora pachyrhizi)", "Mancha-alvo (Corynespora cassiicola)", "Antracnose (Colletotrichum truncatum)", "Oídio (Microsphaera diffusa)", "Mancha-parda / Septoriose (Septoria glycines)", "Crestamento-foliar / Cercosporiose (Cercospora kikuchii)", "Mofo-branco (Sclerotinia sclerotiorum)", "Podridão-radicular (Phytophthora sojae)", "Podridão-cinzenta-do-caule (Macrophomina phaseolina)", "Morte-súbita (Fusarium virguliforme)"]
        elif cultura == "Milho Safrinha": opcoes = ["Complexo Enfezamento (Molicutes / Cigarrinha)", "Ferrugem-polissora (Puccinia polysora)", "Mancha-branca (Phaeosphaeria / Pantoea)", "Cercosporiose (Cercospora zeae-maydis)", "Helmintosporiose (Exserohilum turcicum)", "Podridão-do-colmo (Fusarium / Colletotrichum)", "Podridão-de-espiga (Fusarium verticillioides)", "Mancha-de-diplodia (Stenocarpella macrospora)", "Ferrugem-comum (Puccinia sorghi)", "Virose-da-risca (MRFV - Vetor: Cigarrinha)"]
        else: opcoes = ["Ferrugem-do-sorgo (Puccinia purpurea)", "Antracnose-do-sorgo (Colletotrichum sublineolum)", "Helmintosporiose / Mancha-foliar (Exserohilum turcicum)", "Doença-açucarada / Ergot (Claviceps africana)", "Mancha-zonada (Gloeocercospora sorghi)", "Podridão-seca-do-colmo (Macrophomina phaseolina)", "Míldio-do-sorgo (Peronosclerospora sorghi)", "Estria-bacteriana (Xanthomonas vasicola)", "Podridão-vermelha-do-colmo (Colletotrichum graminicola)", "Mancha-retangular (Cercospora sorghi)"]
    elif tipo_selecionado == "Plantas Daninhas":
        opcoes = ["Capim-amargoso (Digitaria insularis)", "Buva (Conyza spp.)", "Capim-pé-de-galinha (Eleusine indica)", "Caruru (Amaranthus spp.)", "Corda-de-viola (Ipomoea spp.)", "Trapoeraba (Commelina benghalensis)", "Leiteiro / Amendoim-bravo (Euphorbia heterophylla)", "Picão-preto (Bidens pilosa)", "Milho-tiguera (Zea mays voluntário)", "Soja-tiguera (Glycine max voluntária)", "Tiririca (Cyperus rotundus)", "Vassourinha-de-botão (Spermacoce verticillata)", "Capim-massambará (Sorghum halepense)", "Guanxuma (Sida spp.)", "Capim-colonião (Panicum maximum)", "Capim-carrapicho (Cenchrus echinatus)", "Maria-pretinha (Solanum americanum)", "Apaga-fogo / Periquito (Alternanthera tenella)", "Nabiça / Fumo-bravo (Raphanus raphanistrum)", "Aveia / Azevém voluntário"]
    
    alvo_escolhido = st.selectbox(f"Identificação da {tipo_selecionado}:", opcoes)
    
    if tipo_selecionado == "Plantas Daninhas": dicionario_ativo = INFO_DANINHAS
    elif tipo_selecionado == "Praga": dicionario_ativo = INFO_PRAGAS
    else: dicionario_ativo = INFO_DOENCAS
        
    if alvo_escolhido in dicionario_ativo:
        with st.expander("📖 Guia de Campo: Biologia, Danos e Identificação"):
            st.markdown(f"**🌿 Biologia e Danos:**\n{dicionario_ativo[alvo_escolhido]['dano']}")
            st.markdown(f"**🔎 Como Identificar:**\n{dicionario_ativo[alvo_escolhido]['id']}")

with st.form("form_novo", clear_on_submit=False):
    detalhes_alvo = ""; txt_mip = ""
    quant = 0.0; desfolha = 0; pressao = "Baixa"; estagio_alvo = "Não avaliado"; distribuicao = "Não avaliada"; estresse = "Não avaliada"; inimigos = "Não avaliado"
    severidade = 0; incidencia = 0; local = "Não avaliado"; clima = "Não avaliado"; genetica = "Não avaliada"
    tipo_produto = ""; alvo_aplicacao = ""; produto_comercial = ""; dose = 0.0; unidade_dose = "L/ha"; volume_calda = 0; equipamento = ""; tipo_bico = ""; temp_aplicacao = 0; umidade_aplicacao = 0; vento_aplicacao = 0
    tipo_insumo = ""; insumo_comercial = ""; dose_adubo = 0.0; unid_adubo = "kg/ha"; metodo_aplicacao = ""; umidade_solo = ""
    compactacao = ""; palhada = ""; erosao = ""; temp_solo = 0; densidade = ""; resistencia = ""
    
    if tipo_selecionado in ["Praga", "Doença", "Plantas Daninhas"]:
        st.markdown(f"### 📊 Avaliação de {tipo_selecionado} e MIP")
        p_eval = alvo_escolhido.lower() if alvo_escolhido else ""
        colA, colB = st.columns(2)
        
        with colA:
            if tipo_selecionado == "Praga":
                st.markdown("##### Parâmetros da Praga")
                if "percevejo" in p_eval:
                    quant = st.number_input("Média de percevejos por pano:", min_value=0.0, step=0.5)
                    estagio_alvo = st.selectbox("Fase predominante:", ["Não avaliado no momento", "Ninfas (Pequenos)", "Adultos voando", "Misto"])
                    detalhes_alvo = f"Média: {quant} | Fase: {estagio_alvo}"
                elif "mosca-do-sorgo" in p_eval:
                    quant = st.number_input("Média de moscas por panícula:", min_value=0.0, step=0.5)
                    detalhes_alvo = f"Média: {quant} | Adultos"
                elif any(s in p_eval for s in ["pulgão", "cigarrinha", "ácaro", "mosca-branca", "tripes"]):
                    pressao = st.selectbox("Pressão aparente:", ["Indeterminada", "Baixa", "Média", "Alta"])
                    estagio_alvo = st.selectbox("Fase predominante:", ["Não avaliado no momento", "Ovos/Ninfas", "Adultos", "Colônia formada"])
                    detalhes_alvo = f"Pressão: {pressao} | Fase: {estagio_alvo}"
                elif any(s in p_eval for s in ["elasmo", "rosca", "tamanduá", "alfinete", "coró", "cupim", "formiga", "piolho", "besouro"]):
                    desfolha = st.slider("Plantas mortas/acamadas (% estande):", 0, 100, 5)
                    detalhes_alvo = f"Dano Estande: {desfolha}%"
                else: 
                    desfolha = st.slider("Desfolha ou Dano Foliar (%):", 0, 100, 5)
                    estagio_alvo = st.selectbox("Tamanho predominante:", ["Não avaliado no momento", "Lagartas < 1,5cm", "Lagartas > 1,5cm", "Misto"])
                    detalhes_alvo = f"Dano: {desfolha}% | Tamanho: {estagio_alvo}"
            
            elif tipo_selecionado == "Doença":
                st.markdown("##### Parâmetros da Doença")
                severidade = st.slider("Severidade (Área afetada %):", 0, 100, 5)
                incidencia = st.slider("Incidência (% de plantas no talhão):", 0, 100, 10)
                local = st.selectbox("Posição dos sintomas:", ["Não avaliado no momento", "Baixeiro (Inferiores)", "Terço Médio", "Ponteiro (Novas)", "Colmo / Raiz / Espiga"])
                detalhes_alvo = f"Severidade: {severidade}% | Incidência: {incidencia}% | Progresso: {local}"
                
            elif tipo_selecionado == "Plantas Daninhas":
                st.markdown("##### Parâmetros da Daninha")
                if "buva" in p_eval:
                    opcoes_estagio = ["Não avaliado no momento", "Estágio de Roseta (< 5cm - Ideal)", "Roseta > 5cm", "Elongação da haste (< 15cm)", "Haste desenvolvida (> 15cm)", "Florescimento"]
                elif any(g in p_eval for g in ["capim", "milho", "aveia", "azevém"]):
                    opcoes_estagio = ["Não avaliado no momento", "1 a 3 folhas (Plantula - Ideal)", "1 a 2 perfilhos", "Mais de 3 perfilhos", "Pré-pendoamento", "Touceira perenizada (Baixa absorção)"]
                elif any(t in p_eval for t in ["corda-de-viola", "trapoeraba", "apaga-fogo"]):
                    opcoes_estagio = ["Não avaliado no momento", "Cotilédones a 2 folhas", "Início de ramificação (Ideal)", "Ramos longos / Entrelaçando na cultura", "Florescimento"]
                elif "tiririca" in p_eval:
                    opcoes_estagio = ["Não avaliado no momento", "Brotação inicial foliar", "Formação da roseta foliar", "Emissão do pendão floral", "Multiplicação ativa subterrânea"]
                else:
                    opcoes_estagio = ["Não avaliado no momento", "Cotilédone a 2 folhas (Ideal)", "4 a 6 folhas", "Mais de 6 folhas", "Início de Florescimento", "Haste lenhosa / Perenizada"]
                
                estagio_alvo = st.selectbox("Estágio de Desenvolvimento Específico:", opcoes_estagio)
                densidade = st.selectbox("Densidade de infestação:", ["Não avaliada", "Baixa (1 a 5 plantas/m²)", "Média (5 a 15 plantas/m²)", "Alta (Tapete / > 15 plantas/m²)"])
                resistencia = st.selectbox("Suspeita de Resistência no Talhão:", ["Nenhuma suspeita", "Sim, falha de controle com Glifosato", "Sim, falha de controle com ALS/ACCase", "Histórico de Resistência Múltipla"])
                detalhes_alvo = f"Estágio: {estagio_alvo} | Densidade: {densidade} | Resistência: {resistencia}"
                
        with colB:
            st.markdown("##### Condições da Lavoura")
            if tipo_selecionado == "Doença":
                distribuicao = st.selectbox("Distribuição no talhão:", ["Não avaliada no momento", "Manchas/Reboleiras", "Generalizada uniforme"])
                clima = st.selectbox("Condição Climática atual:", ["Não avaliado no momento", "Quente e Seco", "Quente e Úmido (Abafo)", "Frio e Úmido / Chuvoso"])
                genetica = st.selectbox("Genética da Semente:", ["Não avaliada no momento", "Cultivar Suscetível", "Cultivar com Tolerância", "Cultivar Resistente"])
                txt_mip = f"Local: {distribuicao} | Clima: {clima} | Genética: {genetica}"
            elif tipo_selecionado == "Plantas Daninhas":
                distribuicao = st.selectbox("Distribuição no talhão:", ["Não avaliada no momento", "Generalizada na área", "Restrita à bordadura", "Manchas/Reboleiras (Focos)"])
                estresse = st.selectbox("Condição da Daninha (Absorção):", ["Não avaliada no momento", "Vigorosa (Folhas túrgidas, verde intenso)", "Estressada por Seca (Folhas murchas/dobradas)", "Dano Mecânico (Roçada/Acamada)"])
                txt_mip = f"Local: {distribuicao} | Condição da Planta: {estresse}"
            else: 
                distribuicao = st.selectbox("Distribuição no talhão:", ["Não avaliada no momento", "Generalizada na área", "Restrita à bordadura", "Manchas/Reboleiras"])
                estresse = st.selectbox("Condição da planta:", ["Não avaliada no momento", "Vigorosa / Bom clima", "Estresse Leve / Fase de recuperação", "Estresse Hídrico / Térmico Severo"])
                inimigos = st.selectbox("Inimigos naturais:", ["Não avaliado no momento", "Ausente ou Baixa", "Média (Alguns visíveis)", "Alta presença (Ajuda biológica)"])
                txt_mip = f"Local: {distribuicao} | Clima: {estresse} | Inimigos: {inimigos}"
            
    elif tipo_selecionado == "Aplicação":
        st.markdown("### 🚜 Tecnologia de Aplicação")
        colA, colB = st.columns(2)
        with colA:
            st.markdown("##### Produto e Dosagem")
            tipo_produto = st.selectbox("Classe do Produto:", ["Herbicida", "Inseticida", "Fungicida", "Adubo Foliar", "Regulador de Crescimento", "Óleo/Adjuvante", "Outro"])
            alvo_aplicacao = st.text_input("Qual o alvo principal? (Ex: Buva, Ferrugem)")
            
            opcoes_produto = CATALOGO_PRODUTOS.get(tipo_produto, ["Outro (Digitar)"])
            produto_selecionado = st.selectbox("Produto Comercial / Ingrediente Ativo:", opcoes_produto)
            produto_comercial = st.text_input("Digite o nome do produto ou ativo:") if produto_selecionado == "Outro (Digitar)" else produto_selecionado
            
            c1, c2 = st.columns([2, 1])
            with c1: dose = st.number_input("Dose por Hectare:", min_value=0.0, step=0.1)
            with c2: unidade_dose = st.selectbox("Unid:", ["L/ha", "kg/ha", "g/ha", "mL/ha"])
                
        with colB:
            st.markdown("##### Equipamento e Clima")
            equipamento = st.selectbox("Equipamento:", ["Pulverizador Autopropelido", "Pulverizador Tratorizado", "Drone Agrícola", "Avião Agrícola", "Bomba Costal"])
            c3, c4 = st.columns(2)
            with c3: tipo_bico = st.selectbox("Tipo de Bico:", ["Cone Vazio", "Cone Cheio", "Leque Padrão", "Leque Duplo", "Indução de Ar", "Rotativo (Drone)", "Outro"])
            with c4: volume_calda = st.number_input("Calda (L/ha):", min_value=0, step=10, value=100)
                
            st.markdown("###### Condições no Momento")
            ct, cu, cv = st.columns(3)
            with ct: temp_aplicacao = st.number_input("Temp(°C):", min_value=10, max_value=45, value=25)
            with cu: umidade_aplicacao = st.number_input("UR(%):", min_value=10, max_value=100, value=60)
            with cv: vento_aplicacao = st.number_input("Vento(km/h):", min_value=0, max_value=40, value=5)
            
        detalhes_alvo = f"{tipo_produto}: {produto_comercial} ({dose} {unidade_dose}) | Alvo: {alvo_aplicacao}"
        txt_mip = f"Equipamento: {equipamento} ({tipo_bico} a {volume_calda} L/ha) | Clima: {temp_aplicacao}°C, UR {umidade_aplicacao}%, Vento {vento_aplicacao} km/h"

    elif tipo_selecionado == "Adubação/Correção":
        st.markdown("### 🚜 Adubação e Correção de Solo")
        colA, colB = st.columns(2)
        with colA:
            st.markdown("##### Insumo e Dosagem")
            tipo_insumo = st.selectbox("Classe do Insumo:", ["Calcário", "Gesso Agrícola", "Fertilizante NPK", "Nitrogênio (Ureia/Sulfato)", "Fosfatado (MAP/DAP/SS)", "Potássico (KCl)", "Organomineral / Orgânico", "Outro"])
            insumo_comercial = st.text_input("Especificação / Produto Comercial:", placeholder="Ex: Calcário Dolomítico, NPK 00-20-20...")
            c1, c2 = st.columns([2, 1])
            with c1: dose_adubo = st.number_input("Dose:", min_value=0.0, step=10.0)
            with c2: unid_adubo = st.selectbox("Unid:", ["kg/ha", "ton/ha"])
        with colB:
            st.markdown("##### Método e Condição")
            metodo_aplicacao = st.selectbox("Método de Aplicação:", ["A lanço (Sem incorporação)", "A lanço (Com incorporação)", "Na linha de plantio", "Cobertura", "Fertirrigação"])
            umidade_solo = st.selectbox("Umidade do Solo:", ["Seco (Pouca umidade)", "Friável (Ideal)", "Úmido", "Muito Úmido / Encharcado"])
            
        detalhes_alvo = f"{tipo_insumo}: {insumo_comercial} ({dose_adubo} {unid_adubo})"
        txt_mip = f"Método: {metodo_aplicacao} | Solo: {umidade_solo}"

    elif tipo_selecionado == "Condição do Solo":
        st.markdown("### 🌱 Avaliação Física e Conservação")
        colA, colB = st.columns(2)
        with colA:
            st.markdown("##### Estrutura Física")
            umidade_solo = st.selectbox("Umidade Atual:", ["Friável (Ideal)", "Seco (Pouca umidade)", "Pó / Muito Seco", "Úmido", "Encharcado / Barro"])
            compactacao = st.selectbox("Nível de Compactação:", ["Ausente / Baixo", "Leve (Superficial)", "Moderada", "Severa (Pé-de-grade / Raiz torta)"])
            temp_solo = st.number_input("Temperatura do Solo (°C):", min_value=0, max_value=60, value=25)
        with colB:
            st.markdown("##### Cobertura e Conservação")
            palhada = st.selectbox("Cobertura de Palha (Plantio Direto):", ["Boa Cobertura (>60%)", "Cobertura Parcial (20% a 60%)", "Solo Descoberto (<20%)", "Excesso de Palha (Dificulta corte)"])
            erosao = st.selectbox("Processo Erosivo Visível:", ["Nenhum (Solo estabilizado)", "Erosão Laminar (Lavagem superficial)", "Presença de Sulcos / Ravinas"])
            
        detalhes_alvo = f"Física: Umidade {umidade_solo} | Compactação: {compactacao} | Temp: {temp_solo}°C"
        txt_mip = f"Conservação: {palhada} | Erosão: {erosao}"

    st.markdown("<hr>", unsafe_allow_html=True)
    conn = sqlite3.connect(ARQUIVO_DB)
    df_talhoes = pd.read_sql_query("SELECT id, nome FROM talhoes", conn)
    conn.close()
    mapa_t = dict(zip(df_talhoes['nome'], df_talhoes['id']))
    
    talhao_escolhido = st.selectbox("Talhão Avaliado:", list(mapa_t.keys()))
    anotacoes = st.text_area("Observações Extras", placeholder="Detalhes operacionais...")
    foto = st.camera_input("Evidência Fotográfica")
    salvou = st.form_submit_button("Gerar Análise e Salvar")

if salvou:
    if tipo_selecionado in ["Praga", "Doença", "Plantas Daninhas"]: tipo_final = f"{cultura} | {alvo_escolhido.split('(')[0].strip()}"
    elif tipo_selecionado == "Aplicação": tipo_final = f"Aplicação ({cultura}): {tipo_produto}"
    elif tipo_selecionado == "Adubação/Correção": tipo_final = f"Adubação ({cultura}): {tipo_insumo}"
    elif tipo_selecionado == "Condição do Solo": tipo_final = f"Solo ({cultura})"
    
    detalhes_finais = f"{detalhes_alvo} | {txt_mip}\nObs: {anotacoes}"
    
    st.markdown("---")
    st.header("📋 Laudo Técnico")

    c_alerta = "info"
    if tipo_selecionado == "Praga": t_alerta, d_alerta, c_alerta = conselheiro_praga(cultura, estagio_cultura, alvo_escolhido, quant, desfolha, pressao, estagio_alvo, distribuicao, estresse, inimigos)
    elif tipo_selecionado == "Doença": t_alerta, d_alerta, c_alerta = conselheiro_doenca(cultura, estagio_cultura, alvo_escolhido, severidade, incidencia, local, clima, genetica)
    elif tipo_selecionado == "Plantas Daninhas": t_alerta, d_alerta, c_alerta = conselheiro_daninha(cultura, alvo_escolhido, estagio_alvo, densidade, distribuicao, estresse, resistencia)
    elif tipo_selecionado == "Aplicação": t_alerta, d_alerta, c_alerta = conselheiro_aplicacao(temp_aplicacao, umidade_aplicacao, vento_aplicacao, equipamento)
    elif tipo_selecionado == "Adubação/Correção": t_alerta, d_alerta, c_alerta = conselheiro_adubacao(tipo_insumo, metodo_aplicacao, umidade_solo)
    elif tipo_selecionado == "Condição do Solo": t_alerta, d_alerta, c_alerta = conselheiro_solo(estagio_cultura, umidade_solo, compactacao, palhada, erosao, temp_solo)
            
    if c_alerta == "error": st.error(f"**{t_alerta}**\n\n{d_alerta}")
    elif c_alerta == "warning": st.warning(f"**{t_alerta}**\n\n{d_alerta}")
    elif c_alerta == "success": st.success(f"**{t_alerta}**\n\n{d_alerta}")
    else: st.info(f"**{t_alerta}**\n\n{d_alerta}")
    
    if api_key:
        st.markdown("### 🤖 Parecer do Felipe")
        if c_alerta == "error": avatar_felipe = "🚨" 
        elif c_alerta == "warning": avatar_felipe = "🧐" 
        elif c_alerta == "success": avatar_felipe = "😎" 
        else: avatar_felipe = "👨‍🌾"

        with st.chat_message("ai", avatar=avatar_felipe):
            with st.spinner("Analisando dados..."):
                try:
                    genai.configure(api_key=api_key)
                    model = genai.GenerativeModel('models/gemini-3.5-flash')
                    
                    prompt_felipe = f"""
                    Aja como Felipe, um agrônomo de campo sênior focado em alta performance.
                    Cultura: {cultura} ({estagio_cultura}). Categoria avaliada: {tipo_selecionado}. 
                    Parâmetros: {detalhes_alvo}. Condições: {txt_mip}. Obs: {anotacoes}. 
                    Ignore dados 'Não avaliado'. 
                    
                    REGRAS DE FORMATAÇÃO E ESTILO (OBRIGATÓRIO):
                    1. Inicie com uma saudação rápida e com personalidade (Ex: "Fala, pessoal! Felipe por aqui.")
                    2. JAMAIS escreva um único bloco de texto longo.
                    3. Divida o laudo em duas seções com títulos em negrito: **DIAGNÓSTICO CLÍNICO** e **PLANO DE AÇÃO TÁTICO**.
                    4. Use marcadores (bullet points) no plano de ação para leitura rápida.
                    5. Destaque obrigatoriamente em **NEGRITO E MAIÚSCULAS** os alertas críticos, fases de risco, nomes de ingredientes ativos/grupos químicos e instruções de dose (Ex: **ALERTA VERMELHO**, **INIBIDORES DE ACCase**, **VOLUME DE CALDA**).
                    6. Seja altamente técnico, direto e evite o excesso de emojis (seja sóbrio e profissional).
                    """
                        
                    resposta_ia = model.generate_content(prompt_felipe)
                    st.write(resposta_ia.text)
                except Exception as e:
                    st.error(f"**Felipe indisponível.** Erro: `{e}`")

    salvar_registro(mapa_t[talhao_escolhido], tipo_final, detalhes_finais, foto)
    st.toast('Apontamento salvo no banco local!', icon='💾')
