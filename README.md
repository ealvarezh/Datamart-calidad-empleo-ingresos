# Datamart de Calidad del Empleo e Ingresos Laborales

---


# 1. Marco teórico

La *Inteligencia de Negocios* o Business Intelligence (BI) se entiende como el conjunto de procesos y tecnologías que permiten recolectar, gestionar y analizar datos para generar información útil en la toma de decisiones (IBM, s. f.). Asimismo, Oracle sostiene que la BI permite a las organizaciones tomar mejores decisiones, actuar con información y mejorar sus procesos mediante datos presentados de forma comprensible y oportuna (Oracle, 2021).

Un *data warehouse* es un repositorio centralizado diseñado para integrar datos provenientes de distintas fuentes y facilitar actividades de análisis, consulta y reportería. Su función principal no es registrar operaciones diarias, sino almacenar información histórica y organizada para apoyar la toma de decisiones estratégicas (Oracle, 2023).

Un *datamart* es una forma más específica de data warehouse, enfocada en un área, departamento o tema particular. A diferencia del data warehouse, que abarca múltiples áreas de la organización, el datamart tiene un alcance más limitado y permite responder necesidades analíticas concretas de un grupo de usuarios o línea de negocio (Oracle, s. f.; IBM, s. f.).

Los principales elementos de una solución de BI son las *fuentes de datos, los **procesos ETL, el **almacenamiento analítico, el **modelo dimensional, los **indicadores* y las *herramientas de visualización*. Dentro del modelo dimensional, el esquema estrella organiza la información mediante tablas de hechos y dimensiones, lo que facilita el filtrado, agrupamiento y análisis de métricas en herramientas como Power BI (Microsoft, 2024).

## 2. Descripción de la empresa

La empresa propuesta para este proyecto es el **Ministerio de Trabajo y Promoción del Empleo del Perú (MTPE)**. Esta entidad es la responsable de formular, coordinar y supervisar las políticas nacionales en materia de empleo, capacitación laboral, seguridad social y fomento de la formalización del trabajo. El MTPE maneja anualmente grandes volúmenes de información estadística sobre el mercado laboral peruano, principalmente a través de la Encuesta Nacional de Hogares (ENAHO) producida por el INEI. Sin embargo, el acceso a estos datos se realiza comúnmente mediante consulta directa de microdatos crudos, sin un sistema analítico que permita responder preguntas operativas de manera ágil y consistente. Los equipos técnicos del Ministerio requieren cruzar variables de empleo, ingresos, formalidad, tipo de contrato y cobertura de seguridad social con información geográfica y sectorial — tareas que actualmente consumen tiempo excesivo y generan inconsistencias entre áreas. Los servidores públicos necesitan responder, de manera rápida e interactiva, las siguientes preguntas clave:

- ¿En qué departamentos y dominios geográficos (urbano/rural) se concentra la mayor tasa de empleo informal?
- ¿Cuál es el ingreso mensual promedio por sector económico, categoría ocupacional y tipo de contrato?
- ¿Qué proporción de trabajadores percibe ingresos por debajo de la Remuneración Mínima Vital (RMV)?
- ¿Qué tan extendida está la subocupación por horas (trabajadores que desean laborar más horas de las que trabajan)?
- ¿Cómo varía el acceso a seguro de salud y AFP según el tamaño de empresa y la formalidad tributaria?
- ¿Cómo han evolucionado estos indicadores a lo largo del tiempo, comparando periodos anuales?

A partir de estas preguntas clave, se formaliza el problema de negocio, se identifican las fuentes de datos requeridas, y se propone una solución basada en Business Intelligence.

## 3. Planteamiento del Problema
El MTPE requiere un sistema analítico que permita monitorear la calidad del empleo y los niveles de ingreso laboral en el Perú, a partir de los microdatos de la ENAHO 2024 (Módulo 500: Empleo e Ingresos), complementados con indicadores macroeconómicos de referencia (RMV, UIT, Canasta Básica de Consumo). El datamart debe responder preguntas sobre informalidad laboral, subocupación por horas, distribución del ingreso relativo a la RMV y acceso a beneficios laborales, segmentadas por ocupación, sector económico, territorio y perfil demográfico del trabajador.
Este planteamiento determina cuatro componentes fundamentales que el datamart debe cubrir:

- **Proceso de negocio:** Seguimiento de la situación laboral e ingresos de los trabajadores peruanos encuestados por ENAHO.
- **Sujeto de análisis:** Persona ocupada o en búsqueda de empleo, con información de su ocupación principal y secundaria.
- **Métricas principales:** Ingreso mensual en ocupación principal, horas trabajadas por semana, ratio ingreso/RMV y acceso a beneficios laborales.
- **Ejes de análisis (dimensiones):** Tiempo, geografía, tipo de empleo, sector económico, ocupación, perfil del trabajador y referencia económica.

---

## 4. Fuentes de Datos

### 4.1 Fuente principal: ENAHO 2024, Módulo 500

La Encuesta Nacional de Hogares (ENAHO) es producida anualmente por el Instituto Nacional de Estadística e Informática (INEI). El **Módulo 500** corresponde a Empleo e Ingresos y recoge información a nivel de persona sobre situación laboral, ocupación, tipo de contrato, ingresos, horas trabajadas y acceso a beneficios.

El archivo utilizado es `ENAHO01A-2024-500.SAV` (disponible en formato CSV como `2024Empleo_e_Ingresos.csv`), con **85,994 registros** y **1,421 columnas**. El tamaño anual de muestra es de 36,594 viviendas particulares a nivel nacional.

#### Variables seleccionadas para la tabla de hechos

| Variable ENAHO | Nombre descriptivo | Descripción / Uso |
|---|---|---|
| `P524A1` / `P524B1` | `ingreso_principal_mes` | Ingreso total en ocupación principal (sueldo, comisiones, bonificaciones). Base de la métrica central. |
| `I513T` | `horas_principales_sem` | Total de horas trabajadas en ocupación principal (versión imputada). Permite calcular subocupación. |
| `P518` | `horas_secundaria_sem` | Horas en ocupaciones secundarias. Complementa el total de horas laboradas. |
| `P520` | `horas_normales_todas` | Horas normales semanales en todas las ocupaciones (declaradas por el encuestado). |
| `FAC500A` | `factor_expansion` | Factor de expansión muestral. Imprescindible para que los resultados sean representativos a nivel nacional. |
| `P521` / `P521A` | `flag_subocupado_horas` | Indicador derivado: quería trabajar más horas y estaba disponible. Identifica subempleo visible. |
| `P5111` - `P5119` | `tipo_remuneracion` | Tipo de pago recibido: sueldo, salario, honorarios, comisión, ingreso por negocio, en especie, etc. |

#### Variables seleccionadas para dimensiones

| Variable ENAHO | Dimensión destino | Descripción |
|---|---|---|---|
| `UBIGEO` | `Dim_Departamento`, `Dim_Provincia`, `Dim_Distrito` | Código UBIGEO de 6 dígitos. Se descompone en: primeros 2 dígitos → departamento, 4 dígitos → provincia, 6 dígitos → distrito. |
| `DOMINIO` | `Dim_Region`, `Dim_Distrito` | Dominio geográfico (1=Costa Norte, 2=Costa Centro, 3=Costa Sur, 4=Sierra Norte, 5=Sierra Centro, 6=Sierra Sur, 7=Selva, 8=Lima Metropolitana). Base para `Dim_Region`. |
| `ESTRATO` | `Dim_Distrito` | Estrato socioeconómico del conglomerado muestral. |
| `P505R4` | `Dim_Ocupacion` | Código de la ocupación principal según Clasificación Nacional de Ocupaciones (CNO-2015). |
| `P506R4` | `Dim_Sector` | Código de la actividad económica del empleador según CIIU revisión 4. |
| `P507`, `P510`, `P510A1`, `P511A`, `P512A` | `Dim_Tipo_Empleo` | Categoría ocupacional, tipo de empleador, formalidad SUNAT, tipo de contrato y tamaño de empresa. |
| `P203`, `P207`, `P208A`, `P209` | `Dim_Trabajador` | Relación de parentesco (jefe de hogar), sexo, edad en años, nivel educativo. |
| `AÑO`, `MES` | `Dim_Tiempo` | Año y mes de la encuesta. |
| `P5581A`–`P55810A` | `Fact_Empleo_Ingreso` | Afiliación a seguros de salud (SIS, ESSALUD, FFAA/PNP, privado, EPS, etc.). Derivado: `flag_acceso_seguro`. |

### 4.2 Fuente complementaria: RMV, UIT y Canasta Básica

Para complementar el análisis e incluir los datos requeridos para responder las preguntas clave, se integra una tabla de indicadores de referencia económica construida a partir de fuentes públicas oficiales:

- **Remuneración Mínima Vital (RMV):** Publicada por el MTPE. Permite calcular el ratio ingreso/RMV por trabajador, que mide la suficiencia del ingreso laboral frente al piso legal.
- **Unidad Impositiva Tributaria (UIT):** Publicada por la SUNAT y el MEF. Referencia para clasificar a trabajadores en tramos de ingreso tributario.
- **Canasta Básica de Consumo (CBC):** Publicada por el INEI con frecuencia anual. Permite calcular cuántas canastas básicas cubre el ingreso del trabajador.

Esta información se integra en el modelo de datos como la dimensión `Dim_Ref_Economica` y permite al sistema calcular directamente en la fact table las métricas derivadas `ratio_ingreso_rmv` y `ratio_ingreso_cbc`.

---

## 5. Modelamiento de data dimensional

### 5.1 Tipo de modelo y granularidad

El modelo adoptado es el **esquema estrella (star schema)**, con una fact table central y diez dimensiones conectadas directamente. La dimensión geográfica se ha modelado de forma desagregada en cuatro dimensiones independientes (`Dim_Region`, `Dim_Departamento`, `Dim_Provincia`, `Dim_Distrito`) para permitir análisis jerárquico a cualquier nivel de detalle territorial. Este diseño garantiza óptimo rendimiento en consultas analíticas y máxima flexibilidad para el usuario final en una plataforma de análisis visual como Power BI.

- **Proceso de negocio:** Registro de la situación laboral e ingreso de un trabajador en un periodo de encuesta.
- **Granularidad:** Una fila en la tabla de hechos equivale a un trabajador en su ocupación principal, en un mes y año de encuesta específico. Este es el nivel más atómico que permite el Módulo 500.

### 5.2 Fact table: `Fact_Empleo_Ingreso`

| Columna | Tipo | Descripción |
|---|---|---|
| `id_tiempo` (FK) | INTEGER | Llave foránea a Dim_Tiempo |
| `id_region` (FK) | INTEGER | Llave foránea a Dim_Región |
| `id_departamento` (FK) | INTEGER | Llave foránea a Dim_Departamento |
| `id_provincia` (FK) | INTEGER | Llave foránea a Dim_Provincia |
| `id_distrito` (FK) | INTEGER | Llave foránea a Dim_Distrito (opcional) |
| `id_ocupacion` (FK) | INTEGER | Llave foránea a Dim_Ocupacion |
| `id_sector` (FK) | INTEGER | Llave foránea a Dim_Sector |
| `id_tipo_empleo` (FK) | INTEGER | Llave foránea a Dim_Tipo_Empleo |
| `id_trabajador` (FK) | INTEGER | Llave foránea a Dim_Trabajador |
| `id_ref_economica` (FK) | INTEGER | Llave foránea a Dim_Ref_Economica |
| `ingreso_principal_mes` | DECIMAL(10,2) | Ingreso total mensual en ocupación principal (soles) |
| `horas_principales_sem` | DECIMAL(5,1) | Horas trabajadas en ocupación principal (versión imputada) |
| `horas_secundaria_sem` | DECIMAL(5,1) | Horas trabajadas en ocupación(es) secundaria(s) |
| `horas_normales_sem` | DECIMAL(5,1) | Horas normales declaradas en todas las ocupaciones |
| `ratio_ingreso_rmv` | DECIMAL(6,3) | Cociente: `ingreso_principal_mes` / RMV vigente ese mes. Métrica de suficiencia salarial. |
| `ratio_ingreso_cbc` | DECIMAL(6,3) | Cociente: `ingreso_principal_mes` / Canasta Básica de Consumo per cápita |
| `factor_expansion` | DECIMAL(12,4) | Peso muestral. Imprescindible para estimar totales nacionales representativos. |
| `flag_subocupado_horas` | BOOLEAN | 1 si el trabajador quería y podía laborar más horas (subempleo visible). |
| `flag_acceso_seguro` | BOOLEAN | 1 si el trabajador declara tener acceso a seguro de salud por el trabajo. |

### 5.3 Descripción de las dimensiones

#### `Dim_Tiempo`

| Columna | Descripción |
|---|---|
| `id_tiempo` (PK) | Llave primaria |
| `anio` | Año de la encuesta (2024, 2023, ...) |
| `mes` | Mes de la encuesta (1–12) |
| `trimestre` | Trimestre derivado del mes |
| `rmv_vigente` | RMV en soles vigente en ese mes/año (fuente: MTPE) |

#### `Dim_Región`

Se crea una dimensión para representar los dominios geográficos de la ENAHO, derivados de la variable `DOMINIO`. Esta dimensión permite agrupar por dominio geográfico (Costa Norte, Costa Centro, Costa Sur, Sierra Norte, Sierra Centro, Sierra Sur, Selva, Lima Metropolitana) y realizar análisis comparativos entre estas macrozonas. No existen llaves foráneas; toda la información está directamente disponible para análisis.

| Columna | Descripción |
|---|---|
| `id_region` (PK) | Llave primaria (1–8, corresponde al código DOMINIO) |
| `nombre_region` | Nombre del dominio geográfico (Costa Norte, Costa Centro, etc.) |

#### `Dim_Departamento`

Esta dimensión representa los 25 departamentos del Perú, mapeados desde los primeros 2 dígitos del código UBIGEO. Incluye una clasificación en macro-región (Costa, Sierra, Selva, o combinaciones) para facilitar análisis agregados. No existen llaves foráneas; toda la información está directamente disponible para análisis.

| Columna | Descripción |
|---|---|
| `id_departamento` (PK) | Llave primaria (código UBIGEO de 2 dígitos: 01–25) |
| `cod_departamento` | Código de departamento de 2 caracteres (ej. '15' = Lima) |
| `nombre_departamento` | Nombre del departamento |
| `macro_region` | Macro-región geográfica: Costa, Sierra, Selva, o combinaciones |

#### `Dim_Provincia`

La dimensión de provincia se construye a partir de los primeros 4 dígitos del UBIGEO (departamento + provincia). Cada provincia se asocia al departamento correspondiente permitiendo navegación jerárquica. Los nombres de provincia se almacenan como código descriptivo; para nombres oficiales se requiere un catálogo UBIGEO externo del INEI.

| Columna | Descripción |
|---|---|
| `id_provincia` (PK) | Llave primaria (código UBIGEO de 4 dígitos) |
| `cod_provincia` | Código de provincia de 4 caracteres |
| `nombre_provincia` | Nombre descriptivo (basado en código UBIGEO) |
| `id_departamento` | Llave foránea opcional a `Dim_Departamento` |

#### `Dim_Distrito`

Esta dimensión incluye los distritos con información a nivel de código UBIGEO completo (6 dígitos), dominio geográfico, área (Urbano/Rural derivado del dominio) y estrato socioeconómico. Los distritos se vinculan jerárquicamente a provincia y departamento.

| Columna | Descripción |
|---|---|
| `id_distrito` (PK) | Llave primaria (código UBIGEO de 6 dígitos) |
| `ubigeo` | Código UBIGEO completo (6 dígitos) |
| `nombre_distrito` | Nombre descriptivo (basado en código UBIGEO) |
| `dominio` | Código de dominio geográfico (1–8) |
| `dominio_desc` | Descripción del dominio (Costa Norte, Lima Metropolitana, etc.) |
| `area` | Urbano / Rural (derivado: dominios 1–8 = Urbano, otros = Rural) |
| `estrato` | Estrato socioeconómico del conglomerado |
| `id_departamento` | Llave foránea opcional a `Dim_Departamento` |
| `id_provincia` | Llave foránea opcional a `Dim_Provincia` |

#### `Dim_Tipo_Empleo`

Esta dimensión concentra los atributos que determinan la calidad formal del vínculo laboral. Todas estas variables son características del puesto (no métricas numerables), por lo que no van en la tabla de hechos.

| Columna | Descripción |
|---|---|
| `id_tipo_empleo` (PK) | Llave primaria |
| `categoria_ocupacional` | Empleador, Trabajador independiente, Empleado, Obrero, TFNR, Trabajador del hogar |
| `tipo_empleador` | Fuerzas Armadas/PNP, Administración Pública, Empresa Pública, Empresa Privada, SERVICE |
| `formalidad_sunat` | Persona Jurídica, Persona Natural con RUC, No registrado. Indicador de formalidad tributaria. |
| `tipo_contrato` | Indefinido, Plazo fijo, CAS, Locación de servicios, Sin contrato, Otro |
| `tamanio_empresa` | Hasta 20, 21–50, 51–100, 101–500, Más de 500 trabajadores |
| `flag_formal` | Indicador derivado: empleo formal si tiene contrato escrito Y empresa registrada en SUNAT |

#### `Dim_Ocupacion`

| Columna | Descripción |
|---|---|
| `id_ocupacion` (PK) | Llave primaria |
| `cod_ocupacion_cno` | Código CNO-2015 de la ocupación principal |
| `descripcion_ocupacion` | Descripción de la ocupación según CNO-2015 |
| `grupo_ocupacional` | Agrupación de primer dígito CNO: Profesionales, Técnicos, Operarios, etc. |

#### `Dim_Sector`

| Columna | Descripción |
|---|---|
| `id_sector` (PK) | Llave primaria |
| `cod_ciiu_r4` | Código CIIU revisión 4 de la actividad económica del empleador |
| `descripcion_actividad` | Descripción de la actividad económica |
| `sector_agrupado` | Agrupación macrosectorial: Agropecuario, Minería, Manufactura, Comercio, Servicios, Construcción |
| `tipo_sector` | Público / Privado |

#### `Dim_Trabajador`

Esta dimensión almacena el perfil demográfico del trabajador encuestado, utilizando variables del Módulo 200 (Características de los miembros del hogar) de ENAHO presentes en el dataset combinado. Las variables mapeadas son: `P203` (relación de parentesco → jefe de hogar), `P207` (sexo), `P208A` (edad en años) y `P209` (nivel educativo).

| Columna | Descripción |
|---|---|
| `id_trabajador` (PK) | Llave primaria |
| `sexo` | Hombre / Mujer |
| `edad` | Edad en años cumplidos al momento de la encuesta |
| `grupo_etario` | Joven (14–24), Adulto joven (25–44), Adulto (45–64), Adulto mayor (65+) |
| `nivel_educativo` | Sin nivel, Primaria, Secundaria, Superior técnica, Superior universitaria, Postgrado |
| `jefe_de_hogar` | Indicador si la persona es jefe o jefa del hogar (P203 = 1) |

#### `Dim_Ref_Economica`

Dimensión externa construida a partir de publicaciones oficiales del MEF, SUNAT e INEI. Actúa como tabla de referencia temporal para calcular métricas de suficiencia de ingresos directamente en el proceso ETL.

| Columna | Descripción |
|---|---|
| `id_ref_economica` (PK) | Llave primaria |
| `anio` | Año de vigencia del indicador |
| `mes` | Mes de vigencia (para RMV con vigencia mensual) |
| `rmv_soles` | Remuneración Mínima Vital vigente en soles. Fuente: MTPE. |
| `uit_soles` | Unidad Impositiva Tributaria vigente. Fuente: MEF / SUNAT. |
| `cbc_per_capita` | Canasta Básica de Consumo per cápita mensual en soles. Fuente: INEI. |

---

## 6. Decisiones de Diseño del Modelo

Las decisiones de diseño del datamart están orientadas por las necesidades específicas del MTPE. La geografía se modela en cuatro dimensiones desagregadas (`Dim_Region`, `Dim_Departamento`, `Dim_Provincia`, `Dim_Distrito`), siguiendo la jerarquía natural del UBIGEO peruano. Esta separación permite análisis a cualquier nivel de granularidad territorial (desde macro-región hasta distrito) sin perder flexibilidad. `Dim_Region` se deriva de la variable `DOMINIO` de ENAHO (8 dominios geográficos), mientras que `Dim_Departamento`, `Dim_Provincia` y `Dim_Distrito` se extraen del código `UBIGEO` de 6 dígitos (descomposición posicional). Los nombres de los 25 departamentos provienen de un lookup interno incluido en el código ETL; para nombres oficiales de provincias y distritos se requiere el catálogo UBIGEO del INEI. La condición de formalidad (formal/informal) es una característica cualitativa del puesto de trabajo, no una métrica numérica aditiva. Por ello se ubica en `Dim_Tipo_Empleo` como atributo derivado (combinación de contrato escrito + registro SUNAT), lo que permite filtrar y segmentar, pero no sumar. Las columnas `ratio_ingreso_rmv` y `ratio_ingreso_cbc` se calculan durante el proceso de carga y se almacenan en la tabla de hechos. Esto evita cálculos en tiempo de consulta en Power BI y garantiza consistencia en todos los reportes. Además, para las horas trabajadas se utiliza la versión imputada (`I513T`) en lugar de la cruda (`P513T`), dado que el INEI aplica procedimientos estadísticos para completar valores faltantes de forma consistente con el diseño muestral. La variable `FAC500A` se incluye como métrica en la tabla de hechos y su uso es obligatorio en todas las medidas agregadas del dashboard. Sin este factor, los resultados no son representativos a nivel nacional ni departamental.

---

## 7. Indicadores Propuestos para el Dashboard

El dashboard en Power BI debe responder directamente las preguntas de negocio del MTPE. Los siguientes indicadores se derivan de las métricas de la tabla de hechos, aplicando el factor de expansión correspondiente.

| Indicador | Fórmula / Lógica | Pregunta de negocio que responde |
|---|---|---|
| **Tasa de informalidad laboral (%)** | Trabajadores con `flag_formal=0` / Total trabajadores (ponderado por `FAC500A`) | ¿Qué proporción del empleo es informal por departamento y sector? |
| **Ingreso promedio mensual (S/.)** | Promedio ponderado de `ingreso_principal_mes` usando `FAC500A` | ¿Cuánto gana en promedio un trabajador según su ocupación y sector? |
| **Ratio ingreso / RMV promedio** | Promedio ponderado de `ratio_ingreso_rmv` | ¿Cuántos trabajadores ganan por debajo de la RMV? |
| **Tasa de subocupación visible (%)** | Trabajadores con `flag_subocupado_horas=1` / Total ocupados (ponderado) | ¿Qué tan extendida está la subocupación por horas? |
| **Cobertura de seguro de salud (%)** | Trabajadores con `flag_acceso_seguro=1` / Total (ponderado) | ¿Cómo varía el acceso a seguridad social por tamaño de empresa? |
| **Promedio de horas semanales** | Promedio ponderado de `horas_principales_sem` | ¿Qué sectores tienen mayor intensidad horaria? |

---

## 8. Estrategia de Integración de Fuentes

El proceso ETL se implementa en dos etapas secuenciales, cada una con su propio script Python:

### Etapa 1: CSV → Base de Datos Staging (`poblar_db_destino.py`)

1. **Extracción** del CSV `2024Empleo e Ingresos.csv` (260 MB, 1,425 columnas, encoding Latin-1) en chunks de 50,000 filas.
2. **Selección** de las 35 columnas relevantes para el datamart (de un total de 1,425).
3. **Transformación inicial:** conversión de tipos, limpieza de valores vacíos, normalización de campos numéricos.
4. **Carga** en la base de datos `ENAHO_Staging`, tabla `ena2024_500`.

### Etapa 2: Staging → Data Mart (`poblar_datamart.py`)

5. **Creación del esquema estrella** en `EmpleoIngresos_DM` con 10 dimensiones + 1 tabla de hechos.
6. **Carga de dimensiones:**
   - `Dim_Region`: desde los 8 dominios geográficos de ENAHO.
   - `Dim_Departamento`: 25 departamentos del Perú desde lookup interno (primeros 2 dígitos UBIGEO).
   - `Dim_Provincia`: provincias únicas desde los 4 primeros dígitos UBIGEO.
   - `Dim_Distrito`: distritos (UBIGEO 6 dígitos) con dominio, área y estrato.
   - `Dim_Ocupacion`, `Dim_Sector`, `Dim_Tipo_Empleo`, `Dim_Trabajador`: desde códigos ENAHO con etiquetas descriptivas.
   - `Dim_Ref_Economica`: desde `data_rmv_cbc_uit.xlsx` (RMV, UIT, CBC históricos).
   - `Dim_Tiempo`: periodos únicos año-mes con RMV vigente.
7. **Cálculo de métricas derivadas:** `ratio_ingreso_rmv`, `ratio_ingreso_cbc`, `flag_formal`, `flag_subocupado_horas`, `flag_acceso_seguro`.
8. **Carga de la tabla de hechos** `Fact_Empleo_Ingreso` mapeando todas las llaves foráneas mediante diccionarios de lookup.
9. **Exportación** del modelo a Power BI para construcción del dashboard.

### Dashboard (`dashboard_calidad_empleo.py`)

10. **Aplicación Dash** que se conecta al Data Mart y presenta los 6 indicadores con filtros interactivos por departamento, dominio, sector y grupo ocupacional.

---

---
## 9. Referencias bibliográficas
- IBM. (s. f.). What is business intelligence (BI)? IBM Think.
- https://www.ibm.com/think/topics/business-intelligence?utm

- Microsoft. (2024). Understand star schema and the importance for Power BI. Microsoft Learn.

- Oracle. (2021). What is business intelligence? Oracle.

- Oracle. (2023). What is a data warehouse? Oracle.

- Oracle. (s. f.). Data mart concepts. Oracle Documentation.
https://docs.oracle.com/html/E10312_01/dm_concepts.htm?utm_source
