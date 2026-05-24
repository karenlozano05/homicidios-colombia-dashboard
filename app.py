
#Con %%writefile creamos un archivo llamado app.py con el siguiente
#contenido, que es el código de nuestro dashboard en Streamlit: 

import streamlit as st
import geopandas as gpd
import plotly.express as px
import pandas as pd
import json

# 1. Configuración de la página de Streamlit

st.set_page_config(
    page_title="Homicidios en Colombia en una Serie de tiempo de 2003 hasta 2026",
    page_icon="📊",
    layout="wide"
)

st.title("Homicidios en Colombia en una Serie de tiempo de 2003 hasta 2026 📊")
st.markdown("Análisis geoespacial de homicidios en Colombia utilizando datos abiertos de la Policía Nacional y cartografía del DANE.")

# 2. Creamos una función optimizada para cargar los datos con el motor Pyogrio
@st.cache_data # Con esto se mantienen los datos en caché para evitar lentitud en recargas posteriores
def cargar_datos_geo():
    archivo_geojson = "homicidios_colombia.geojson"
    # Usamos pyogrio para evitar incompatibilidades con fiona en Windows
    gdf = gpd.read_file(archivo_geojson, engine='pyogrio')

    gdf['ano'] = gdf['ano'].astype(int)
    gdf['total_homicidios'] = gdf['total_homicidios'].astype(int)

    geojson_dict = json.loads(gdf.to_json())
    return gdf, geojson_dict

try:
    with st.spinner("Cargando mapas y datos estructurados..."):
        mapa_homicidios, geojson_colombia = cargar_datos_geo()
    st.success("✅ Datos cargados correctamente.")
except Exception as e:
    st.error(f"❌ Error al cargar los datos. Asegúrate de haber corrido las fases anteriores. Detalle: {e}")
    st.stop()

# 3. Interfaz de usuario - Filtros Interactivos en la barra lateral
st.sidebar.header(" Filtros de Análisis") # Aquí estas creando el filtro con sidebar

# Selector de años (Aquí lo ordenas de más reciente al más antiguo)
lista_anos = sorted(mapa_homicidios['ano'].unique(), reverse=True)
ano_seleccionado = st.sidebar.selectbox("Selecciona el Año a evaluar:", lista_anos)

# Aquí filtras de forma dinamica según el año seleccionado
datos_filtrados = mapa_homicidios[mapa_homicidios['ano'] == ano_seleccionado]

# Creamos un selector de municipios
municipios_disponibles = sorted(datos_filtrados['nombre_municipio'].unique())
municipio_buscar = st.sidebar.multiselect("Filtrar por municipio específico:", municipios_disponibles)

if municipio_buscar:
    datos_filtrados = datos_filtrados[datos_filtrados['nombre_municipio'].isin(municipio_buscar)]

# 4. Resumen con KPIs Principales
st.markdown("### 📌 Resumen del Año Seleccionado")
col1, col2, col3 = st.columns(3)

total_casos = datos_filtrados['total_homicidios'].sum()
municipio_max = datos_filtrados.loc[datos_filtrados['total_homicidios'].idxmax()] if not datos_filtrados.empty else None

# Calcular variacion porcentual respecto al año inmediatamente anterior
ano_anterior = ano_seleccionado - 1
datos_ano_anterior = mapa_homicidios[mapa_homicidios['ano'] == ano_anterior]
if municipio_buscar:
    datos_ano_anterior = datos_ano_anterior[datos_ano_anterior['nombre_municipio'].isin(municipio_buscar)]
total_anterior = int(datos_ano_anterior['total_homicidios'].sum()) if not datos_ano_anterior.empty else 0

if total_anterior > 0:
    variacion_pct = ((total_casos - total_anterior) / total_anterior) * 100
    delta_texto = f"{variacion_pct:+.1f}% vs {ano_anterior}"
else:
    delta_texto = "Sin datos del año anterior"

with col1:
    st.metric(
        label="❌ Total de Homicidios",
        value=f"{total_casos:,}",
        delta=delta_texto,
        delta_color="inverse"
    )
with col2:
    val_muni = str(municipio_max['nombre_municipio']) if municipio_max is not None else "N/A"
    st.metric(label="📍 Municipio con Más Casos", value=val_muni)
with col3:
    val_casos = f"{municipio_max['total_homicidios']:,}" if municipio_max is not None else "0"
    st.metric(label="🚨 Máximo de casos", value=val_casos)

st.markdown("---")

# 5. Visualizaciones (Mapa de calor coroplético y Gráfico de Barras)
col_mapa, col_grafico = st.columns([3, 2]) # Ditribuimos la pantalla (60% izq, 40% der)

with col_mapa:
    st.subheader(f"🗺️ Mapa de Intensidad (Calor por Municipio) - Año {ano_seleccionado}")
    if not datos_filtrados.empty:
        fig_mapa = px.choropleth_mapbox(
            datos_filtrados,
            geojson=geojson_colombia,
            locations='cod_muni',
            featureidkey='properties.cod_muni',
            color='total_homicidios',
            color_continuous_scale="Reds",
            range_color=(0, datos_filtrados['total_homicidios'].quantile(0.98)),
            mapbox_style="carto-positron",
            zoom=4.8,
            center={"lat": 4.5708, "lon": -74.2973},
            opacity=0.7,
            labels={'total_homicidios': 'Casos', 'nombre_municipio': 'Municipio'},
            hover_data={'cod_muni': False, 'nombre_municipio': True, 'total_homicidios': True}
        )
        fig_mapa.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, height=600)
        st.plotly_chart(fig_mapa, use_container_width=True)
    else:
        st.warning("No hay datos para mostrar.")

with col_grafico:
    st.subheader("📊 Top 10 Municipios con Más Registros")
    if not datos_filtrados.empty:
        top_10 = datos_filtrados.sort_values(by='total_homicidios', ascending=False).head(10)
        fig_barras = px.bar(
            top_10, x='total_homicidios', y='nombre_municipio',
            orientation='h', color='total_homicidios', color_continuous_scale="Reds"
        )
        fig_barras.update_layout(yaxis={'categoryorder':'total ascending'}, margin={"r":10,"t":10,"l":10,"b":10}, height=550, showlegend=False)
        fig_barras.update_coloraxes(showscale=False)
        st.plotly_chart(fig_barras, use_container_width=True)

# 6. Evolución Temporal y Tabla de Datos Estructurada
st.markdown("---")
col_linea, col_tabla = st.columns([3, 2]) # Mantenemos la proporción visual 60% y 40%

with col_linea:
    st.subheader("📈 Evolución Temporal de Homicidios Nacional")

    # Agrupamos la base maestra por año para calcular la tendencia histórica global
    evolucion_temporal = mapa_homicidios.groupby('ano')['total_homicidios'].sum().reset_index()

    fig_linea = px.line(
        evolucion_temporal,
        x='ano',
        y='total_homicidios',
        markers=True, # Añade puntos marcadores en cada año para facilitar la lectura
        labels={'ano': 'Año', 'total_homicidios': 'Casos Totales'},
        color_discrete_sequence=["#DC2626"] # Agregamos un color rojo consistente con la estética del dashboard
    )
    fig_linea.update_layout(margin={"r":20,"t":20,"l":20,"b":20}, height=400)
    st.plotly_chart(fig_linea, use_container_width=True)

with col_tabla:
    st.subheader("📋 Tabla de Datos Relevantes (Selección Actual)")
    if not datos_filtrados.empty:
        # Extraemos las 4 variables más importantes, ordenando por volumen de impacto
        tabla_relevante = (
            datos_filtrados[['ano', 'cod_muni', 'nombre_municipio', 'total_homicidios']]
            .sort_values(by='total_homicidios', ascending=False)
        )
        # Renombramos las columnas visualmente para el usuario final sin alterar el dataframe original
        st.dataframe(
            tabla_relevante,
            column_config={
                "ano": "Año",
                "cod_muni": "Código Municipio",
                "nombre_municipio": "Municipio",
                "total_homicidios": "Total Homicidios"
            },
            use_container_width=True, 
            height=400, 
            hide_index=True
        )
    else:
        st.info("No hay registros disponibles para estructurar la tabla.")
