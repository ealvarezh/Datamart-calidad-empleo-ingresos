# -*- coding: utf-8 -*-
"""
Dashboard de Calidad del Empleo e Ingresos Laborales
Ministerio de Trabajo y Promocion del Empleo (MTPE)

Basado en el Data Mart EmpleoIngresos_DM
Indicadores:
  1. Tasa de informalidad laboral (%)
  2. Ingreso promedio mensual (S/.)
  3. Ratio ingreso / RMV promedio
  4. Tasa de subocupacion visible (%)
  5. Cobertura de seguro de salud (%)
  6. Promedio de horas semanales
"""

import dash
from dash import dcc, html, Input, Output, callback
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pyodbc
import pandas as pd
import numpy as np
import warnings

warnings.filterwarnings('ignore')

# ------------------------------ Configuracion --------------------------------

SERVER = 'localhost'
UID = 'sa'
PWD = '1234567890'
DATAMART_DB = 'EmpleoIngresos_DM'

def get_dm_connection():
    try:
        conn = pyodbc.connect(
            f'DRIVER={{ODBC Driver 17 for SQL Server}};'
            f'SERVER={SERVER};DATABASE={DATAMART_DB};UID={UID};PWD={PWD}',
            timeout=30
        )
        print("✓ Conexion al Data Mart exitosa")
        return conn
    except pyodbc.Error as e:
        print(f"Error de conexion: {e}")
        return None


def create_sample_data():
    """Genera datos de ejemplo para demostracion si no hay conexion a la DB."""
    print("Generando datos de ejemplo...")
    np.random.seed(42)
    n = 3000

    deptos = ['Lima', 'Arequipa', 'Cusco', 'La Libertad', 'Piura',
              'Lambayeque', 'Junin', 'Ancash', 'Cajamarca', 'Callao']
    sectores = ['Agropecuario/Pesca', 'Mineria', 'Manufactura', 'Construccion',
                'Comercio', 'Servicios', 'Electricidad/Gas/Agua']
    ocupaciones = ['Profesionales', 'Tecnicos', 'Servicios y vendedores',
                    'Oficiales y operarios', 'Ocupaciones elementales',
                    'Agricultores y pesqueros', 'Apoyo administrativo']

    df = pd.DataFrame({
        'departamento':    np.random.choice(deptos, n),
        'dominio_desc':    np.random.choice(['Costa', 'Sierra', 'Selva', 'Lima Metropolitana'], n),
        'sector_agrupado': np.random.choice(sectores, n),
        'grupo_ocupacional': np.random.choice(ocupaciones, n),
        'sexo':            np.random.choice(['Hombre', 'Mujer'], n),
        'grupo_etario':    np.random.choice(['Joven (14-24)', 'Adulto joven (25-44)',
                                             'Adulto (45-64)', 'Adulto mayor (65+)'], n),
        'ingreso_principal_mes': np.random.lognormal(7.2, 0.8, n),
        'horas_principales_sem': np.random.uniform(15, 60, n).round(1),
        'ratio_ingreso_rmv':     np.random.uniform(0.3, 5.0, n).round(3),
        'factor_expansion':      np.random.uniform(50, 300, n).round(2),
        'flag_formal':           np.random.choice([0, 1], n, p=[0.65, 0.35]),
        'flag_subocupado_horas': np.random.choice([0, 1], n, p=[0.85, 0.15]),
        'flag_acceso_seguro':    np.random.choice([0, 1], n, p=[0.40, 0.60]),
    })
    print("✓ Datos de ejemplo generados.")
    return df


def load_data():
    """Carga datos desde el Data Mart o genera datos de ejemplo."""
    conn = get_dm_connection()
    if conn is None:
        return create_sample_data()

    try:
        query = """
            SELECT
                COALESCE(dd.nombre_departamento, 'Sin especificar') AS departamento,
                COALESCE(dr.nombre_region, 'Sin especificar') AS dominio_desc,
                COALESCE(ds.sector_agrupado, 'Sin especificar') AS sector_agrupado,
                COALESCE(do2.grupo_ocupacional, 'Sin especificar') AS grupo_ocupacional,
                COALESCE(dtrab.sexo, 'Sin especificar') AS sexo,
                COALESCE(dtrab.grupo_etario, 'Sin especificar') AS grupo_etario,
                f.ingreso_principal_mes,
                f.horas_principales_sem,
                f.ratio_ingreso_rmv,
                f.factor_expansion,
                CAST(dte.flag_formal AS INT) AS flag_formal,
                CAST(f.flag_subocupado_horas AS INT) AS flag_subocupado_horas,
                CAST(f.flag_acceso_seguro AS INT) AS flag_acceso_seguro
            FROM dbo.Fact_Empleo_Ingreso f
            JOIN dbo.Dim_Tiempo        dt    ON f.id_tiempo        = dt.id_tiempo
            LEFT JOIN dbo.Dim_Region       dr    ON f.id_region        = dr.id_region
            LEFT JOIN dbo.Dim_Departamento dd    ON f.id_departamento  = dd.id_departamento
            LEFT JOIN dbo.Dim_Sector       ds    ON f.id_sector        = ds.id_sector
            LEFT JOIN dbo.Dim_Ocupacion    do2   ON f.id_ocupacion     = do2.id_ocupacion
            JOIN dbo.Dim_Trabajador     dtrab ON f.id_trabajador    = dtrab.id_trabajador
            JOIN dbo.Dim_Tipo_Empleo    dte   ON f.id_tipo_empleo   = dte.id_tipo_empleo
        """
        df = pd.read_sql(query, conn)
        conn.close()

        if df.empty:
            print("Data Mart vacio. Usando datos de ejemplo.")
            return create_sample_data()

        print(f"✓ {len(df):,} registros cargados desde el Data Mart.")
        return df

    except Exception as e:
        print(f"Error cargando datos: {e}")
        if conn:
            conn.close()
        return create_sample_data()


# ------------------------------ Carga inicial --------------------------------

print("Iniciando carga de datos...")
df = load_data()

# ------------------------------ App Dash -------------------------------------

app = dash.Dash(__name__)
server = app.server

# Listas para filtros
lista_deptos    = ['Todos'] + sorted(df['departamento'].dropna().unique().tolist())
lista_dominios  = ['Todos'] + sorted(df['dominio_desc'].dropna().unique().tolist())
lista_sectores  = ['Todos'] + sorted(df['sector_agrupado'].dropna().unique().tolist())
lista_ocup      = ['Todos'] + sorted(df['grupo_ocupacional'].dropna().unique().tolist())

# Layout
app.layout = html.Div([
    # Encabezado
    html.Div([
        html.H1("Dashboard de Calidad del Empleo e Ingresos Laborales",
                style={'textAlign': 'center', 'marginBottom': 10, 'color': '#1a5276'}),
        html.H4("Ministerio de Trabajo y Promocion del Empleo - Peru",
                style={'textAlign': 'center', 'color': '#7f8c8d', 'marginBottom': 5}),
        html.P("Fuente: ENAHO 2024, Modulo 500 - Empleo e Ingresos",
               style={'textAlign': 'center', 'color': '#95a5a6', 'marginBottom': 30})
    ]),

    # Filtros
    html.Div([
        html.Div([
            html.Label("Departamento:", style={'fontWeight': 'bold'}),
            dcc.Dropdown(id='filtro-depto', options=[{'label': d, 'value': d} for d in lista_deptos],
                         value='Todos', clearable=False)
        ], style={'width': '24%', 'display': 'inline-block', 'marginRight': '1%'}),
        html.Div([
            html.Label("Dominio:", style={'fontWeight': 'bold'}),
            dcc.Dropdown(id='filtro-dominio', options=[{'label': d, 'value': d} for d in lista_dominios],
                         value='Todos', clearable=False)
        ], style={'width': '24%', 'display': 'inline-block', 'marginRight': '1%'}),
        html.Div([
            html.Label("Sector:", style={'fontWeight': 'bold'}),
            dcc.Dropdown(id='filtro-sector', options=[{'label': s, 'value': s} for s in lista_sectores],
                         value='Todos', clearable=False)
        ], style={'width': '24%', 'display': 'inline-block', 'marginRight': '1%'}),
        html.Div([
            html.Label("Grupo Ocupacional:", style={'fontWeight': 'bold'}),
            dcc.Dropdown(id='filtro-ocupacion', options=[{'label': o, 'value': o} for o in lista_ocup],
                         value='Todos', clearable=False)
        ], style={'width': '24%', 'display': 'inline-block'})
    ], style={'backgroundColor': '#f4f6f6', 'padding': '15px', 'borderRadius': '10px', 'marginBottom': '20px'}),

    # KPI Cards - Fila 1
    html.Div([
        html.Div(id='kpi-informalidad', style={'textAlign': 'center', 'padding': '20px',
                  'backgroundColor': 'white', 'borderRadius': '10px',
                  'boxShadow': '0 2px 6px rgba(0,0,0,0.1)'}),
        html.Div(id='kpi-ingreso', style={'textAlign': 'center', 'padding': '20px',
                  'backgroundColor': 'white', 'borderRadius': '10px',
                  'boxShadow': '0 2px 6px rgba(0,0,0,0.1)'}),
        html.Div(id='kpi-ratio-rmv', style={'textAlign': 'center', 'padding': '20px',
                  'backgroundColor': 'white', 'borderRadius': '10px',
                  'boxShadow': '0 2px 6px rgba(0,0,0,0.1)'}),
    ], style={'display': 'grid', 'gridTemplateColumns': 'repeat(3, 1fr)', 'gap': '15px', 'marginBottom': '15px'}),

    # KPI Cards - Fila 2
    html.Div([
        html.Div(id='kpi-subocupacion', style={'textAlign': 'center', 'padding': '20px',
                  'backgroundColor': 'white', 'borderRadius': '10px',
                  'boxShadow': '0 2px 6px rgba(0,0,0,0.1)'}),
        html.Div(id='kpi-seguro', style={'textAlign': 'center', 'padding': '20px',
                  'backgroundColor': 'white', 'borderRadius': '10px',
                  'boxShadow': '0 2px 6px rgba(0,0,0,0.1)'}),
        html.Div(id='kpi-horas', style={'textAlign': 'center', 'padding': '20px',
                  'backgroundColor': 'white', 'borderRadius': '10px',
                  'boxShadow': '0 2px 6px rgba(0,0,0,0.1)'}),
    ], style={'display': 'grid', 'gridTemplateColumns': 'repeat(3, 1fr)', 'gap': '15px', 'marginBottom': '20px'}),

    # Graficos - Fila 1
    html.Div([
        html.Div([dcc.Graph(id='chart-informalidad')],
                 style={'width': '49%', 'display': 'inline-block'}),
        html.Div([dcc.Graph(id='chart-ingreso-sector')],
                 style={'width': '49%', 'float': 'right', 'display': 'inline-block'}),
    ]),

    # Graficos - Fila 2
    html.Div([
        html.Div([dcc.Graph(id='chart-ratio-rmv')],
                 style={'width': '49%', 'display': 'inline-block'}),
        html.Div([dcc.Graph(id='chart-seguro')],
                 style={'width': '49%', 'float': 'right', 'display': 'inline-block'}),
    ], style={'marginTop': '20px'}),

    # Graficos - Fila 3
    html.Div([
        html.Div([dcc.Graph(id='chart-subocupacion')],
                 style={'width': '49%', 'display': 'inline-block'}),
        html.Div([dcc.Graph(id='chart-horas')],
                 style={'width': '49%', 'float': 'right', 'display': 'inline-block'}),
    ], style={'marginTop': '20px'}),

    # Footer
    html.Div([
        html.P("Los indicadores se calculan ponderados por el factor de expansion (FAC500A).",
               style={'color': '#95a5a6', 'fontSize': '12px', 'textAlign': 'center'}),
        html.P("Datos actualizados a ENAHO 2024. | RMV 2024: S/ 1,025 | UIT 2024: S/ 5,150 | CBC per capita: S/ 465",
               style={'color': '#95a5a6', 'fontSize': '11px', 'textAlign': 'center'})
    ], style={'marginTop': '30px', 'padding': '10px', 'backgroundColor': '#f4f6f6', 'borderRadius': '8px'})
])


# ------------------------------ Callback unico -------------------------------

@app.callback(
    [Output('kpi-informalidad',   'children'),
     Output('kpi-ingreso',        'children'),
     Output('kpi-ratio-rmv',      'children'),
     Output('kpi-subocupacion',   'children'),
     Output('kpi-seguro',         'children'),
     Output('kpi-horas',          'children'),
     Output('chart-informalidad', 'figure'),
     Output('chart-ingreso-sector', 'figure'),
     Output('chart-ratio-rmv',    'figure'),
     Output('chart-seguro',       'figure'),
     Output('chart-subocupacion', 'figure'),
     Output('chart-horas',        'figure')],
    [Input('filtro-depto',     'value'),
     Input('filtro-dominio',   'value'),
     Input('filtro-sector',    'value'),
     Input('filtro-ocupacion', 'value')]
)
def update_dashboard(depto, dominio, sector, ocupacion):
    # Filtrar
    dff = df.copy()
    if depto and depto != 'Todos':
        dff = dff[dff['departamento'] == depto]
    if dominio and dominio != 'Todos':
        dff = dff[dff['dominio_desc'] == dominio]
    if sector and sector != 'Todos':
        dff = dff[dff['sector_agrupado'] == sector]
    if ocupacion and ocupacion != 'Todos':
        dff = dff[dff['grupo_ocupacional'] == ocupacion]

    if dff.empty:
        empty_kpi = html.Div([html.H3("--", style={'margin': '0'}), html.P("Sin datos")])
        empty_fig = go.Figure()
        empty_fig.update_layout(title="Sin datos disponibles", xaxis={'visible': False}, yaxis={'visible': False})
        return empty_kpi, empty_kpi, empty_kpi, empty_kpi, empty_kpi, empty_kpi, empty_fig, empty_fig, empty_fig, empty_fig, empty_fig, empty_fig

    factor = dff['factor_expansion'].fillna(0)
    factor_sum = factor.sum()

    # --- KPI: Tasa de informalidad (%) ---
    informal = dff[dff['flag_formal'] == 0]['factor_expansion'].sum()
    tasa_informal = (informal / factor_sum * 100) if factor_sum > 0 else 0

    kpi_inf = html.Div([
        html.H3(f"{tasa_informal:.1f}%", style={'color': '#c0392b', 'margin': '0', 'fontSize': '28px'}),
        html.P("Tasa de Informalidad Laboral", style={'color': '#7f8c8d', 'margin': '5px 0', 'fontWeight': 'bold'}),
        html.P(f"{informal/1e6:,.1f}M informales (pond.)", style={'color': '#95a5a6', 'margin': '0', 'fontSize': '12px'})
    ])

    # --- KPI: Ingreso promedio mensual (S/.) ---
    ingresos_validos = dff['ingreso_principal_mes'].fillna(0)
    ingresos_validos = ingresos_validos[ingresos_validos > 0]
    
    # Winsorización (p1 - p99)
    p1 = ingresos_validos.quantile(0.05)
    p99 = ingresos_validos.quantile(0.95)
    
    dff_ing = dff.copy()
    dff_ing['ingreso_ajustado'] = dff_ing['ingreso_principal_mes'].clip(lower=p1, upper=p99)
    
    # Promedio ponderado robusto
    ingresos_pond = (dff_ing['ingreso_ajustado'].fillna(0) * factor).sum()
    ingreso_prom = ingresos_pond / factor_sum if factor_sum > 0 else 0

    kpi_ing = html.Div([
        html.H3(f"S/ {ingreso_prom:,.0f}", style={'color': '#27ae60', 'margin': '0', 'fontSize': '28px'}),
        html.P("Ingreso Promedio Mensual", style={'color': '#7f8c8d', 'margin': '5px 0', 'fontWeight': 'bold'}),
        html.P(f"Mediana: S/ {dff['ingreso_principal_mes'].median():,.0f}", style={'color': '#95a5a6', 'margin': '0', 'fontSize': '12px'})
    ])

    # --- KPI: Ratio ingreso / RMV ---
    RMV = 1025

    dff_ing['ratio_ajustado_rmv'] = dff_ing['ingreso_ajustado'] / RMV
    
    ratio_pond = (dff_ing['ratio_ajustado_rmv'] * factor).sum()
    ratio_prom = ratio_pond / factor_sum if factor_sum > 0 else 0

    kpi_rmv = html.Div([
        html.H3(f"{ratio_prom:.2f}x", style={'color': '#2980b9', 'margin': '0', 'fontSize': '28px'}),
        html.P("Ratio Ingreso / RMV", style={'color': '#7f8c8d', 'margin': '5px 0', 'fontWeight': 'bold'}),
        html.P(f"< 1 RMV: {(dff['ratio_ingreso_rmv'] < 1).sum()/len(dff)*100:.1f}% de trabajadores",
               style={'color': '#95a5a6', 'margin': '0', 'fontSize': '12px'})
    ])

    # --- KPI: Tasa de subocupacion (%) ---
    suboc_pond = dff[dff['flag_subocupado_horas'] == 1]['factor_expansion'].sum()
    tasa_suboc = (suboc_pond / factor_sum * 100) if factor_sum > 0 else 0

    kpi_sub = html.Div([
        html.H3(f"{tasa_suboc:.1f}%", style={'color': '#e67e22', 'margin': '0', 'fontSize': '28px'}),
        html.P("Tasa de Subocupacion Visible", style={'color': '#7f8c8d', 'margin': '5px 0', 'fontWeight': 'bold'}),
        html.P("Por horas (quiere y puede trabajar mas)", style={'color': '#95a5a6', 'margin': '0', 'fontSize': '12px'})
    ])

    # --- KPI: Cobertura seguro de salud (%) ---
    seguro_pond = dff[dff['flag_acceso_seguro'] == 1]['factor_expansion'].sum()
    tasa_seguro = (seguro_pond / factor_sum * 100) if factor_sum > 0 else 0

    kpi_seg = html.Div([
        html.H3(f"{tasa_seguro:.1f}%", style={'color': '#8e44ad', 'margin': '0', 'fontSize': '28px'}),
        html.P("Cobertura de Seguro de Salud", style={'color': '#7f8c8d', 'margin': '5px 0', 'fontWeight': 'bold'}),
        html.P(f"{seguro_pond/1e6:,.1f}M asegurados (pond.)", style={'color': '#95a5a6', 'margin': '0', 'fontSize': '12px'})
    ])

    # --- KPI: Promedio horas semanales ---
    horas_pond = (dff['horas_principales_sem'].fillna(0) * factor).sum()
    horas_prom = horas_pond / factor_sum if factor_sum > 0 else 0

    kpi_hrs = html.Div([
        html.H3(f"{horas_prom:.1f}", style={'color': '#16a085', 'margin': '0', 'fontSize': '28px'}),
        html.P("Promedio Horas Semanales", style={'color': '#7f8c8d', 'margin': '5px 0', 'fontWeight': 'bold'}),
        html.P("En ocupacion principal", style={'color': '#95a5a6', 'margin': '0', 'fontSize': '12px'})
    ])

    # --- GRAFICOS ---

    # 1. Informalidad por Departamento
    inf_depto = dff.groupby('departamento').apply(
        lambda g: pd.Series({
            'tasa_informalidad': g[g['flag_formal']==0]['factor_expansion'].sum() / g['factor_expansion'].sum() * 100
            if g['factor_expansion'].sum() > 0 else 0
        })).reset_index().sort_values('tasa_informalidad', ascending=True)

    fig_inf = px.bar(inf_depto.tail(15), x='tasa_informalidad', y='departamento',
                     orientation='h', title='Tasa de Informalidad Laboral por Departamento (%)',
                     color='tasa_informalidad', color_continuous_scale='Reds',
                     text=inf_depto.tail(15)['tasa_informalidad'].apply(lambda x: f'{x:.1f}%'))
    fig_inf.update_layout(yaxis={'categoryorder': 'total ascending'}, coloraxis_showscale=False)
    fig_inf.update_traces(textposition='outside')

    # 2. Ingreso promedio por Sector
    ing_sec = dff.groupby('sector_agrupado').apply(
        lambda g: pd.Series({
            'ingreso_prom': (g['ingreso_principal_mes'].fillna(0) * g['factor_expansion']).sum()
                           / g['factor_expansion'].sum()
                           if g['factor_expansion'].sum() > 0 else 0
        })).reset_index().sort_values('ingreso_prom', ascending=True)

    fig_ing = px.bar(ing_sec, x='ingreso_prom', y='sector_agrupado',
                     orientation='h', title='Ingreso Promedio Mensual por Sector (S/.)',
                     color='ingreso_prom', color_continuous_scale='Greens',
                     text=ing_sec['ingreso_prom'].apply(lambda x: f'S/ {x:,.0f}'))
    fig_ing.update_layout(yaxis={'categoryorder': 'total ascending'}, coloraxis_showscale=False)
    fig_ing.update_traces(textposition='outside')

    # 3. Ratio Ingreso/RMV por Grupo Ocupacional
    rmv_ocup = dff_ing.groupby('grupo_ocupacional').apply(
    lambda g: pd.Series({
        'ratio_rmv_prom': (
            g['ratio_ajustado_rmv'].fillna(0) * g['factor_expansion']
        ).sum() / g['factor_expansion'].sum()
        if g['factor_expansion'].sum() > 0 else 0
    })
    ).reset_index().sort_values('ratio_rmv_prom', ascending=True)

    fig_rmv = px.bar(rmv_ocup, x='ratio_rmv_prom', y='grupo_ocupacional',
                     orientation='h', title='Ratio Ingreso / RMV por Grupo Ocupacional',
                     color='ratio_rmv_prom', color_continuous_scale='Blues',
                     text=rmv_ocup['ratio_rmv_prom'].apply(lambda x: f'{x:.2f}x'))
    fig_rmv.update_layout(yaxis={'categoryorder': 'total ascending'}, coloraxis_showscale=False)
    fig_rmv.update_traces(textposition='outside')
    fig_rmv.add_vline(x=1, line_dash='dash', line_color='red',
                      annotation_text='RMV (=1)', annotation_position='top right')

    # 4. Cobertura de Seguro por Departamento
    seg_depto = dff.groupby('departamento').apply(
        lambda g: pd.Series({
            'tasa_seguro': g[g['flag_acceso_seguro']==1]['factor_expansion'].sum() / g['factor_expansion'].sum() * 100
            if g['factor_expansion'].sum() > 0 else 0
        })).reset_index().sort_values('tasa_seguro', ascending=True)

    fig_seg = px.bar(seg_depto.tail(15), x='tasa_seguro', y='departamento',
                     orientation='h', title='Cobertura de Seguro de Salud por Departamento (%)',
                     color='tasa_seguro', color_continuous_scale='Purples',
                     text=seg_depto.tail(15)['tasa_seguro'].apply(lambda x: f'{x:.1f}%'))
    fig_seg.update_layout(yaxis={'categoryorder': 'total ascending'}, coloraxis_showscale=False)
    fig_seg.update_traces(textposition='outside')

    # 5. Subocupacion por Sexo y Grupo Etario
    suboc_demo = dff.groupby(['sexo', 'grupo_etario']).apply(
        lambda g: pd.Series({
            'tasa_suboc': g[g['flag_subocupado_horas']==1]['factor_expansion'].sum() / g['factor_expansion'].sum() * 100
            if g['factor_expansion'].sum() > 0 else 0
        })).reset_index()

    fig_sub = px.bar(suboc_demo, x='grupo_etario', y='tasa_suboc', color='sexo',
                     barmode='group',
                     title='Tasa de Subocupacion Visible por Sexo y Grupo Etario (%)',
                     color_discrete_sequence=['#e74c3c', '#3498db'],
                     text=suboc_demo['tasa_suboc'].apply(lambda x: f'{x:.1f}%'))
    fig_sub.update_traces(textposition='outside')
    fig_sub.update_layout(xaxis_title='Grupo Etario', yaxis_title='Tasa de Subocupacion (%)')

    # 6. Horas promedio por Sector
    hrs_sec = dff.groupby('sector_agrupado').apply(
        lambda g: pd.Series({
            'horas_prom': (g['horas_principales_sem'].fillna(0) * g['factor_expansion']).sum()
                         / g['factor_expansion'].sum()
                         if g['factor_expansion'].sum() > 0 else 0
        })).reset_index().sort_values('horas_prom', ascending=True)

    fig_hrs = px.bar(hrs_sec, x='horas_prom', y='sector_agrupado',
                     orientation='h', title='Promedio de Horas Semanales por Sector',
                     color='horas_prom', color_continuous_scale='Teal',
                     text=hrs_sec['horas_prom'].apply(lambda x: f'{x:.1f}h'))
    fig_hrs.update_layout(yaxis={'categoryorder': 'total ascending'}, coloraxis_showscale=False)
    fig_hrs.update_traces(textposition='outside')
    fig_hrs.add_vline(x=48, line_dash='dash', line_color='orange',
                      annotation_text='Jornada legal (48h)', annotation_position='top right')

    return (kpi_inf, kpi_ing, kpi_rmv, kpi_sub, kpi_seg, kpi_hrs,
            fig_inf, fig_ing, fig_rmv, fig_seg, fig_sub, fig_hrs)


# ------------------------------ Main -----------------------------------------

if __name__ == '__main__':
    print("\n" + "=" * 60)
    print(" DASHBOARD DE CALIDAD DEL EMPLEO E INGRESOS")
    print(" Accede en: http://localhost:8050")
    print("=" * 60)
    app.run(debug=False, port=8050)
