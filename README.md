# Datamart de Calidad del Empleo e Ingresos Laborales

> **Propuesta de Proyecto — Business Intelligence**  

---

## 1. Descripción del Cliente

El cliente ficticio propuesto para este proyecto es el **Ministerio de Trabajo y Promoción del Empleo del Perú (MTPE)**. Esta entidad es la responsable de formular, coordinar y supervisar las políticas nacionales en materia de empleo, capacitación laboral, seguridad social y fomento de la formalización del trabajo.

### 1.1 Contexto y necesidad

El MTPE maneja anualmente grandes volúmenes de información estadística sobre el mercado laboral peruano, principalmente a través de la Encuesta Nacional de Hogares (ENAHO) producida por el INEI. Sin embargo, el acceso a estos datos se realiza comúnmente mediante consulta directa de microdatos crudos, sin un sistema analítico que permita responder preguntas operativas de manera ágil y consistente.

Los equipos técnicos del Ministerio requieren cruzar variables de empleo, ingresos, formalidad, tipo de contrato y cobertura de seguridad social con información geográfica y sectorial — tareas que actualmente consumen tiempo excesivo y generan inconsistencias entre áreas.

### 1.2 Preguntas de negocio que guían el proyecto

El producto final debe permitir al cliente responder, de manera rápida e interactiva, las siguientes preguntas clave:

- ¿En qué departamentos y dominios geográficos (urbano/rural) se concentra la mayor tasa de empleo informal?
- ¿Cuál es el ingreso mensual promedio por sector económico, categoría ocupacional y tipo de contrato?
- ¿Qué proporción de trabajadores percibe ingresos por debajo de la Remuneración Mínima Vital (RMV)?
- ¿Qué tan extendida está la subocupación por horas (trabajadores que desean laborar más horas de las que trabajan)?
- ¿Cómo varía el acceso a seguro de salud y AFP según el tamaño de empresa y la formalidad tributaria?
- ¿Cómo han evolucionado estos indicadores a lo largo del tiempo, comparando periodos anuales?

---

## 2. Planteamiento del Problema

> **Enunciado del problema:** El MTPE requiere un sistema analítico que permita monitorear la calidad del empleo y los niveles de ingreso laboral en el Perú, a partir de los microdatos de la ENAHO 2024 (Módulo 500: Empleo e Ingresos), complementados con indicadores macroeconómicos de referencia (RMV, UIT, Canasta Básica de Consumo). El datamart debe responder preguntas sobre informalidad laboral, subocupación por horas, distribución del ingreso relativo a la RMV y acceso a beneficios laborales, segmentadas por ocupación, sector económico, territorio y perfil demográfico del trabajador.

Este planteamiento determina cuatro componentes fundamentales que el datamart debe cubrir:

- **Proceso de negocio:** Seguimiento de la situación laboral e ingresos de los trabajadores peruanos encuestados por ENAHO.
- **Sujeto de análisis:** Persona ocupada o en búsqueda de empleo, con información de su ocupación principal y secundaria.
- **Métricas principales:** Ingreso mensual en ocupación principal, horas trabajadas por semana, ratio ingreso/RMV y acceso a beneficios laborales.
- **Ejes de análisis (dimensiones):** Tiempo, geografía, tipo de empleo, sector económico, ocupación, perfil del trabajador y referencia económica.

---

## 3. Fuentes de Datos

### 3.1 Fuente principal: ENAHO 2024, Módulo 500

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
|---|---|---|
| `UBIGEO`, `DOMINIO`, `ESTRATO` | `Dim_Geografia` | Ubigeo (6 dígitos), dominio geográfico (Lima Met., resto urbano, rural, selva) y estrato. |
| `P505R4` | `Dim_Ocupacion` | Código y descripción de la ocupación principal según Clasificación Nacional de Ocupaciones (CNO-2015). |
| `P506R4` | `Dim_Sector` | Actividad económica del empleador según CIIU revisión 4. Incluye sector agrupado. |
| `P507`, `P510`, `P510A1`, `P511A`, `P512A` | `Dim_Tipo_Empleo` | Categoría ocupacional, tipo de empleador, formalidad SUNAT, tipo de contrato y tamaño de empresa. |
| `P203`, `P204`, `P208A` | `Dim_Trabajador` | Sexo, edad, nivel educativo. Datos del módulo de características del miembro del hogar. |
| `ANIO`, `MES` | `Dim_Tiempo` | Año y mes de la encuesta. Permite análisis de tendencias temporales. |

### 3.2 Fuente complementaria: RMV, UIT y Canasta Básica

Para enriquecer el análisis e incorporar referencia macroeconómica, se integra una tabla de indicadores de referencia económica construida a partir de fuentes públicas oficiales:

- **Remuneración Mínima Vital (RMV):** Publicada por el MTPE. Permite calcular el ratio ingreso/RMV por trabajador, que mide la suficiencia del ingreso laboral frente al piso legal.
- **Unidad Impositiva Tributaria (UIT):** Publicada por la SUNAT y el MEF. Referencia para clasificar a trabajadores en tramos de ingreso tributario.
- **Canasta Básica de Consumo (CBC):** Publicada por el INEI con frecuencia anual. Permite calcular cuántas canastas básicas cubre el ingreso del trabajador.

Esta información se integra como `Dim_Ref_Economica` y permite al ETL calcular directamente en la tabla de hechos las métricas derivadas `ratio_ingreso_rmv` y `ratio_ingreso_cbc` sin necesidad de lógica adicional en Power BI.

#### Dónde obtener estas fuentes

| Indicador | Fuente | URL |
|---|---|---|
| RMV histórica | MTPE | gob.pe/mtpe → buscar "remuneración mínima vital" |
| UIT histórica | SUNAT / MEF | sunat.gob.pe → buscar "UIT" |
| Canasta Básica de Consumo | INEI | inei.gob.pe → Estadísticas → Condiciones de vida y pobreza |

---

## 4. Modelo Dimensional

### 4.1 Tipo de modelo y granularidad

El modelo adoptado es el **esquema estrella (star schema)**, con una tabla de hechos central y siete dimensiones conectadas directamente. Este diseño garantiza óptimo rendimiento en consultas analíticas y máxima simplicidad para el usuario final en Power BI.

- **Proceso de negocio:** Registro de la situación laboral e ingreso de un trabajador en un periodo de encuesta.
- **Granularidad:** Una fila en la tabla de hechos equivale a un trabajador en su ocupación principal, en un mes y año de encuesta específico. Este es el nivel más atómico que permite el Módulo 500.

### 4.2 Tabla de hechos: `Fact_Empleo_Ingreso`

| Columna | Tipo | Descripción |
|---|---|---|
| `id_tiempo` (FK) | INTEGER | Llave foránea a Dim_Tiempo |
| `id_geografia` (FK) | INTEGER | Llave foránea a Dim_Geografia |
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

### 4.3 Dimensiones

#### `Dim_Tiempo`

| Columna | Descripción |
|---|---|
| `id_tiempo` (PK) | Llave surrogada |
| `anio` | Año de la encuesta (2024, 2023, ...) |
| `mes` | Mes de la encuesta (1–12) |
| `trimestre` | Trimestre derivado del mes |
| `rmv_vigente` | RMV en soles vigente en ese mes/año (fuente: MTPE) |

#### `Dim_Geografia`

Se opta por una única dimensión geográfica con todos los niveles jerárquicos, dado que el cliente analiza principalmente por departamento y dominio (urbano/rural) y no requiere filtrar por nivel de región o provincia de forma independiente. Si el cliente lo requiriese en el futuro, esta dimensión puede descomponerse en `Dim_Region` y `Dim_Departamento`.

| Columna | Descripción |
|---|---|
| `id_geografia` (PK) | Llave surrogada |
| `ubigeo` | Código UBIGEO de 6 dígitos (región + departamento + provincia + distrito) |
| `region` | Región macrogeográfica del Perú |
| `departamento` | Departamento (nivel principal de análisis del MTPE) |
| `provincia` | Provincia dentro del departamento |
| `dominio` | Dominio geográfico: Lima Metropolitana, Costa urbana, Sierra urbana, Selva urbana, Rural sierra, Rural selva |
| `area` | Urbano / Rural |
| `estrato` | Estrato socioeconómico del conglomerado |

#### `Dim_Tipo_Empleo`

Esta dimensión concentra los atributos que determinan la calidad formal del vínculo laboral. Todas estas variables son características del puesto (no métricas numerables), por lo que no van en la tabla de hechos.

| Columna | Descripción |
|---|---|
| `id_tipo_empleo` (PK) | Llave surrogada |
| `categoria_ocupacional` | Empleador, Trabajador independiente, Empleado, Obrero, TFNR, Trabajador del hogar |
| `tipo_empleador` | Fuerzas Armadas/PNP, Administración Pública, Empresa Pública, Empresa Privada, SERVICE |
| `formalidad_sunat` | Persona Jurídica, Persona Natural con RUC, No registrado. Indicador de formalidad tributaria. |
| `tipo_contrato` | Indefinido, Plazo fijo, CAS, Locación de servicios, Sin contrato, Otro |
| `tamanio_empresa` | Hasta 20, 21–50, 51–100, 101–500, Más de 500 trabajadores |
| `flag_formal` | Indicador derivado: empleo formal si tiene contrato escrito Y empresa registrada en SUNAT |

#### `Dim_Ocupacion`

| Columna | Descripción |
|---|---|
| `id_ocupacion` (PK) | Llave surrogada |
| `cod_ocupacion_cno` | Código CNO-2015 de la ocupación principal |
| `descripcion_ocupacion` | Descripción de la ocupación según CNO-2015 |
| `grupo_ocupacional` | Agrupación de primer dígito CNO: Profesionales, Técnicos, Operarios, etc. |

#### `Dim_Sector`

| Columna | Descripción |
|---|---|
| `id_sector` (PK) | Llave surrogada |
| `cod_ciiu_r4` | Código CIIU revisión 4 de la actividad económica del empleador |
| `descripcion_actividad` | Descripción de la actividad económica |
| `sector_agrupado` | Agrupación macrosectorial: Agropecuario, Minería, Manufactura, Comercio, Servicios, Construcción |
| `tipo_sector` | Público / Privado |

#### `Dim_Trabajador`

Esta dimensión almacena el perfil demográfico del trabajador encuestado, que proviene del Módulo 200 (Características de los miembros del hogar) de ENAHO, cruzado por conglomerado, vivienda, hogar y persona.

| Columna | Descripción |
|---|---|
| `id_trabajador` (PK) | Llave surrogada |
| `sexo` | Masculino / Femenino |
| `edad` | Edad en años cumplidos al momento de la encuesta |
| `grupo_etario` | Joven (14–24), Adulto joven (25–44), Adulto (45–64), Adulto mayor (65+) |
| `nivel_educativo` | Sin nivel, Primaria, Secundaria, Superior técnica, Superior universitaria, Postgrado |
| `jefe_de_hogar` | Indicador si la persona es jefe o jefa del hogar |

#### `Dim_Ref_Economica`

Dimensión externa construida a partir de publicaciones oficiales del MEF, SUNAT e INEI. Actúa como tabla de referencia temporal para calcular métricas de suficiencia de ingresos directamente en el proceso ETL.

| Columna | Descripción |
|---|---|
| `id_ref_economica` (PK) | Llave surrogada |
| `anio` | Año de vigencia del indicador |
| `mes` | Mes de vigencia (para RMV con vigencia mensual) |
| `rmv_soles` | Remuneración Mínima Vital vigente en soles. Fuente: MTPE. |
| `uit_soles` | Unidad Impositiva Tributaria vigente. Fuente: MEF / SUNAT. |
| `cbc_per_capita` | Canasta Básica de Consumo per cápita mensual en soles. Fuente: INEI. |

---

## 5. Decisiones de Diseño del Modelo

Las decisiones de diseño del datamart están orientadas por las necesidades específicas del cliente y no por la estructura original de los datos fuente.

- **Dimensión geográfica unificada:** Se opta por una única `Dim_Geografia` con todos los niveles jerárquicos (región, departamento, provincia, dominio) en lugar de dimensiones separadas. El MTPE analiza principalmente a nivel de departamento y dominio geográfico, por lo que la consolidación simplifica el modelo sin perder capacidad analítica.

- **`flag_formal` como atributo de dimensión y no de hecho:** La condición de formalidad (formal/informal) es una característica cualitativa del puesto de trabajo, no una métrica numérica aditiva. Por ello se ubica en `Dim_Tipo_Empleo` como atributo derivado (combinación de contrato escrito + registro SUNAT), lo que permite filtrar y segmentar, pero no sumar.

- **Métricas derivadas calculadas en ETL:** Las columnas `ratio_ingreso_rmv` y `ratio_ingreso_cbc` se calculan durante el proceso de carga y se almacenan en la tabla de hechos. Esto evita cálculos en tiempo de consulta en Power BI y garantiza consistencia en todos los reportes.

- **Variables imputadas preferidas sobre crudas:** Para las horas trabajadas se utiliza la versión imputada (`I513T`) en lugar de la cruda (`P513T`), dado que el INEI aplica procedimientos estadísticos para completar valores faltantes de forma consistente con el diseño muestral.

- **Factor de expansión obligatorio:** La variable `FAC500A` se incluye como métrica en la tabla de hechos y su uso es obligatorio en todas las medidas agregadas del dashboard. Sin este factor, los resultados no son representativos a nivel nacional ni departamental.

---

## 6. Indicadores Propuestos para el Dashboard

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

## 7. Estrategia de Integración de Fuentes

El proceso ETL (Extracción, Transformación y Carga) sigue los pasos descritos a continuación para integrar la ENAHO con los datos externos:

1. **Extracción** del CSV de ENAHO 2024 Módulo 500 y del CSV del Módulo 200 (datos demográficos del hogar) desde el portal del INEI.

2. **Construcción manual** de la tabla `Dim_Ref_Economica` con los valores de RMV, UIT y CBC históricos por año y mes, a partir de fuentes MEF, SUNAT e INEI.

3. **Transformación:** creación de llaves surrogadas para todas las dimensiones, derivación de atributos calculados (`flag_formal`, `grupo_etario`, `sector_agrupado`) y cálculo de métricas (`ratio_ingreso_rmv`, `ratio_ingreso_cbc`, `flag_subocupado_horas`).

4. **Join** entre Módulo 500 y Módulo 200 por las claves (`CONGLOME`, `VIVIENDA`, `HOGAR`, `CODPERSO`) para incorporar datos demográficos del trabajador en `Dim_Trabajador`.

5. **Carga** en base de datos relacional (PostgreSQL o SQL Server) con el modelo estrella definido. Exportación del modelo a Power BI para construcción del dashboard.

---

## 8. Conclusión

El datamart de Calidad del Empleo e Ingresos Laborales propuesto representa una solución de inteligencia de negocios enfocada y funcional para las necesidades del MTPE. Al centrarse en un proceso de negocio bien delimitado (la situación laboral e ingresos de los trabajadores encuestados por ENAHO) y en preguntas específicas que el cliente necesita responder, el modelo logra el equilibrio entre riqueza analítica y simplicidad de uso.

La integración de indicadores macroeconómicos de referencia (RMV, UIT, Canasta Básica) como dimensión externa eleva el valor del producto más allá de un simple repositorio de microdatos: convierte los ingresos brutos en una medida relativa de suficiencia salarial, que es exactamente la métrica que los formuladores de política laboral necesitan para tomar decisiones basadas en evidencia.

El esquema estrella garantiza consultas rápidas en Power BI y un modelo que puede ser entendido y validado por usuarios técnicos y no técnicos del Ministerio, cumpliendo el principio rector del diseño dimensional: **un buen datamart no es el que tiene más datos, sino el que resuelve problemas de negocio.**
