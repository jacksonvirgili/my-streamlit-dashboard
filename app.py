import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# Configuração da página
st.set_page_config(page_title="Dashboard Faturamento STZ", layout="wide")

# Aplicação do CSS personalizado (Identidade Visual STZ)
st.markdown("""
<style>
    /* Fundo cinza clarinho para dar destaque aos blocos brancos */
    .stApp {
        background-color: #F5F5F5;
    }
    /* Barra lateral limpa */
    [data-testid="stSidebar"] {
        background-color: #FFFFFF;
        border-right: 1px solid #E0E0E0;
    }
    /* Tipografia e Títulos corporativos (Preto STZ) */
    h1, h2, h3, h4, h5, h6, p, span, div, label {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    h1 {
        color: #000000 !important;
        font-weight: 700 !important;
    }
</style>
""", unsafe_allow_html=True)

# 1. FUNÇÃO DE PROCESSAMENTO COM CACHE
@st.cache_data
def carregar_e_processar_dados():
    df = pd.read_excel('Base Histórico Masculino.xlsx')

    def classificar_quintil(x):
        return pd.qcut(x.rank(method='first'), q=5, labels=['p1', 'p2', 'p3', 'p4', 'p5'])

    df['Classificação Preço'] = df.groupby(['Material - Subgrupo', 'Mês/Ano Comercial'])['Preço Material'].transform(classificar_quintil)

    df_resumo = df.groupby(['Mês/Ano Comercial', 'Material - Subgrupo', 'Classificação Preço', 'Próprio x Terceiro']).agg(
        Venda_Valor=('Venda Valor', 'sum'),
        Venda_Pecas=('Venda Peças', 'sum'),
        Venda_Lucro_Bruto=('Venda Lucro Bruto', 'sum'),
        Estoque_Custo_Mes=('Estoque Custo Mês', 'sum'),
        Estoque_Pecas_Mes=('Estoque Peças Mês', 'sum'),
        Contagem_Material_Pai=('Material Pai - Código', 'nunique')
    ).reset_index()

    df_resumo['Média_Estoque_Custo'] = df_resumo['Estoque_Custo_Mes']
    df_resumo['Média_Estoque_Pecas'] = df_resumo['Estoque_Pecas_Mes']

    df_resumo['GMROI'] = np.where(df_resumo['Média_Estoque_Custo'] == 0, 0, df_resumo['Venda_Lucro_Bruto'] / df_resumo['Média_Estoque_Custo'])
    df_resumo['Margem'] = np.where(df_resumo['Venda_Valor'] == 0, 0, df_resumo['Venda_Lucro_Bruto'] / df_resumo['Venda_Valor'])
    df_resumo['Giro'] = np.where(df_resumo['Média_Estoque_Pecas'] == 0, 0, df_resumo['Venda_Pecas'] / df_resumo['Média_Estoque_Pecas'])
    
    total_pecas_st = df_resumo['Venda_Pecas'] + df_resumo['Estoque_Pecas_Mes']
    df_resumo['ST%'] = np.where(total_pecas_st == 0, 0, df_resumo['Venda_Pecas'] / total_pecas_st)

    return df_resumo

df_resumo = carregar_e_processar_dados()

# 2. CONSTRUÇÃO DA INTERFACE
st.title("Faturamento por Classificação")

st.sidebar.header("Filtros do Relatório")

lista_subgrupos = ['Todos'] + sorted(df_resumo['Material - Subgrupo'].dropna().unique().tolist())
lista_classificacoes = ['Todas', 'p1', 'p2', 'p3', 'p4', 'p5']

subgrupo = st.sidebar.selectbox("Subgrupo:", options=lista_subgrupos)
classificacao = st.sidebar.selectbox("Classificação (Preço):", options=lista_classificacoes)

# 3. LÓGICA DO GRÁFICO
df_f = df_resumo.copy()

if subgrupo != 'Todos':
    df_f = df_f[df_f['Material - Subgrupo'] == subgrupo]

if classificacao != 'Todas':
    df_f = df_f[df_f['Classificação Preço'] == classificacao]

if df_f.empty:
    st.warning(f"Não houve vendas para a combinação de Subgrupo: '{subgrupo}' e Classificação: '{classificacao}'.")
else:
    df_total = df_f.groupby('Mês/Ano Comercial', as_index=False)['Venda_Valor'].sum()
    df_bars = df_f.groupby(['Mês/Ano Comercial', 'Próprio x Terceiro'], as_index=False)['Venda_Valor'].sum()
    
    df_prop = df_bars[df_bars['Próprio x Terceiro'] == 'Própria']
    df_terc = df_bars[df_bars['Próprio x Terceiro'] == 'Terceiro']

    fig = go.Figure()

    # Barra: Própria (Preto STZ)
    fig.add_trace(go.Bar(
        x=df_prop['Mês/Ano Comercial'], 
        y=df_prop['Venda_Valor'], 
        name='Própria', 
        marker_color='#000000', 
        hovertemplate='Própria: R$ %{y:,.2f}'
    ))
    
    # Barra: Terceiro (Cinza Claro)
    fig.add_trace(go.Bar(
        x=df_terc['Mês/Ano Comercial'], 
        y=df_terc['Venda_Valor'], 
        name='Terceiro', 
        marker_color='#BDBDBD', 
        hovertemplate='Terceiro: R$ %{y:,.2f}'
    ))
    
    # Linha: Total (Destaque Institucional - Vermelho/Laranja STZ)
    fig.add_trace(go.Scatter(
        x=df_total['Mês/Ano Comercial'], 
        y=df_total['Venda_Valor'], 
        name='Total (R$)', 
        mode='lines+markers', 
        line=dict(color='#E3372B', width=3),
        marker=dict(size=8),
        hovertemplate='Total: R$ %{y:,.2f}'
    ))

    # Layout Minimalista e Corporativo
    fig.update_layout(
        title_text=f"Visão de Faturamento: <b>{subgrupo}</b> | Classificação: <b>{classificacao.upper()}</b>",
        title_font=dict(size=18, color="#000000", family="Arial, sans-serif"),
        barmode='group',
        hovermode="x unified",
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="#FFFFFF",
        font=dict(color="#000000", family="Arial, sans-serif"),
        xaxis=dict(
            showgrid=False, 
            zeroline=False
        ),
        yaxis=dict(
            title="Faturamento em R$",
            tickprefix="R$ ",
            separatethousands=True,
            rangemode="tozero",
            showgrid=True,
            gridcolor="#E0E0E0", # Linha de grade sutil
            zeroline=False
        ),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    # Renderiza no centro de um container branco para dar o efeito de "Card"
    with st.container():
        st.plotly_chart(fig, use_container_width=True)
