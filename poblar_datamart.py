# -*- coding: utf-8 -*-
"""
Paso 2: Construir y poblar el Data Mart (Esquema Estrella).

Lee los datos desde la base de datos staging (ENAHO_Staging),
transforma y construye las dimensiones y la tabla de hechos
en la base de datos del datamart (EmpleoIngresos_DM).

Dimensiones (segun README seccion 5, geografia separada):
  Dim_Tiempo, Dim_Region, Dim_Departamento, Dim_Provincia,
  Dim_Distrito, Dim_Ocupacion, Dim_Sector, Dim_Tipo_Empleo,
  Dim_Trabajador, Dim_Ref_Economica

Hechos:
  Fact_Empleo_Ingreso
"""

import pyodbc
import pandas as pd
import numpy as np
import os

# ------------------------------ Configuracion --------------------------------

SERVER = 'localhost'
UID = 'sa'
PWD = '1234567890'
STAGING_DB = 'ENAHO_Staging'
DATAMART_DB = 'EmpleoIngresos_DM'
REF_EXCEL = r"C:\Users\ea.alvarezh\Downloads\data_rmv_cbc_uit.xlsx"

CONN_STR_MASTER = (f'DRIVER={{ODBC Driver 17 for SQL Server}};'
                   f'SERVER={SERVER};UID={UID};PWD={PWD}')

CONN_STR_STAGING = CONN_STR_MASTER.replace('}', f';DATABASE={STAGING_DB}}}').replace('}}', f';DATABASE={STAGING_DB}}}')

# Corregir: construir correctamente
CONN_STR_STAGING = (f'DRIVER={{ODBC Driver 17 for SQL Server}};'
                    f'SERVER={SERVER};DATABASE={STAGING_DB};UID={UID};PWD={PWD}')

CONN_STR_DM = (f'DRIVER={{ODBC Driver 17 for SQL Server}};'
               f'SERVER={SERVER};DATABASE={DATAMART_DB};UID={UID};PWD={PWD}')

# ------------------------------ UBIGEO Lookup --------------------------------

DEPARTAMENTOS = {
    '01': 'Amazonas',      '02': 'Ancash',          '03': 'Apurimac',
    '04': 'Arequipa',      '05': 'Ayacucho',        '06': 'Cajamarca',
    '07': 'Callao',        '08': 'Cusco',           '09': 'Huancavelica',
    '10': 'Huanuco',       '11': 'Ica',             '12': 'Junin',
    '13': 'La Libertad',   '14': 'Lambayeque',      '15': 'Lima',
    '16': 'Loreto',        '17': 'Madre de Dios',   '18': 'Moquegua',
    '19': 'Pasco',         '20': 'Piura',           '21': 'Puno',
    '22': 'San Martin',    '23': 'Tacna',           '24': 'Tumbes',
    '25': 'Ucayali',
}

# Mapeo departamento -> macro-region
DEPTO_A_REGION = {
    '01': 'Sierra/Selva',  '02': 'Costa/Sierra',   '03': 'Sierra',
    '04': 'Costa/Sierra',  '05': 'Sierra',          '06': 'Sierra',
    '07': 'Costa',         '08': 'Sierra',          '09': 'Sierra',
    '10': 'Sierra/Selva',  '11': 'Costa',           '12': 'Sierra/Selva',
    '13': 'Costa/Sierra',  '14': 'Costa',           '15': 'Costa',
    '16': 'Selva',         '17': 'Selva',           '18': 'Costa/Sierra',
    '19': 'Sierra/Selva',  '20': 'Costa',           '21': 'Sierra',
    '22': 'Selva',         '23': 'Costa/Sierra',    '24': 'Costa',
    '25': 'Selva',
}

# Mapeo DOMINIO
DOMINIO_DESC = {
    1: 'Costa Norte',
    2: 'Costa Centro',
    3: 'Costa Sur',
    4: 'Sierra Norte',
    5: 'Sierra Centro',
    6: 'Sierra Sur',
    7: 'Selva',
    8: 'Lima Metropolitana',
}

# Categorias ocupacionales (P507)
CAT_OCUPACIONAL = {
    1: 'Empleador',
    2: 'Trabajador independiente',
    3: 'Empleado',
    4: 'Obrero',
    5: 'TFNR',
    6: 'Trabajador del hogar',
}

# Tipo de empleador (P510)
TIPO_EMPLEADOR = {
    1: 'FFAA/PNP',
    2: 'Administracion Publica',
    3: 'Empresa Publica',
    4: 'Empresa Privada',
    5: 'Empresa Privada',  # Agrupado
    6: 'SERVICE',
    7: 'Otro',
}

# Formalidad SUNAT (P510A1)
FORMALIDAD_SUNAT = {
    1: 'Persona Juridica',
    2: 'Persona Natural con RUC',
    3: 'No registrado',
}

# Tipo de contrato (P511A)
TIPO_CONTRATO = {
    1: 'Indefinido',
    2: 'Plazo fijo',
    3: 'Periodo de prueba',
    4: 'CAS',
    5: 'Locacion de servicios',
    6: 'Regimen especial',
    7: 'Sin contrato',
    8: 'Otro',
}

# Tamano de empresa (P512A)
TAMANIO_EMPRESA = {
    1: 'Hasta 20',
    2: '21-50',
    3: '51-100',
    4: '101-500',
    5: 'Mas de 500',
}

# Nivel educativo (P209)
NIVEL_EDUCATIVO = {
    1: 'Sin nivel',
    2: 'Primaria',
    3: 'Secundaria',
    4: 'Superior tecnica',
    5: 'Superior universitaria',
    6: 'Postgrado',
}

# Grupo ocupacional (primer digito CNO)
GRUPO_OCUPACIONAL = {
    '1': 'Directivos y gerentes',
    '2': 'Profesionales',
    '3': 'Tecnicos',
    '4': 'Apoyo administrativo',
    '5': 'Servicios y vendedores',
    '6': 'Agricultores y pesqueros',
    '7': 'Oficiales y operarios',
    '8': 'Operadores de maquinaria',
    '9': 'Ocupaciones elementales',
}

# Sector agrupado (primeros 2 digitos CIIU)
def get_sector_agrupado(ciiu):
    if not ciiu or not isinstance(ciiu, str):
        return 'No especificado'
    try:
        code = int(ciiu[:2])
    except ValueError:
        return 'No especificado'
    if 1 <= code <= 3:
        return 'Agropecuario/Pesca'
    elif 5 <= code <= 9:
        return 'Mineria'
    elif 10 <= code <= 33:
        return 'Manufactura'
    elif 35 <= code <= 39:
        return 'Electricidad/Gas/Agua'
    elif 41 <= code <= 43:
        return 'Construccion'
    elif 45 <= code <= 47 or 55 <= code <= 56:
        return 'Comercio'
    elif 49 <= code <= 53 or 58 <= code <= 99:
        return 'Servicios'
    else:
        return 'No especificado'

# Grupo etario
def get_grupo_etario(edad):
    if edad is None:
        return None
    if edad < 14:
        return 'Nino'
    elif edad < 25:
        return 'Joven (14-24)'
    elif edad < 45:
        return 'Adulto joven (25-44)'
    elif edad < 65:
        return 'Adulto (45-64)'
    else:
        return 'Adulto mayor (65+)'


# ------------------------------ Conexiones SQL --------------------------------

def get_master_connection():
    return pyodbc.connect(
        f'DRIVER={{ODBC Driver 17 for SQL Server}};'
        f'SERVER={SERVER};UID={UID};PWD={PWD}',
        autocommit=True
    )

def get_staging_connection():
    return pyodbc.connect(CONN_STR_STAGING)

def get_dm_connection():
    return pyodbc.connect(CONN_STR_DM)


def setup_datamart_db():
    """Crea la base de datos del datamart si no existe."""
    print("Configurando base de datos del datamart...")
    conn = get_master_connection()
    cursor = conn.cursor()
    cursor.execute(f"""
        IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = '{DATAMART_DB}')
        BEGIN
            CREATE DATABASE [{DATAMART_DB}];
            PRINT 'Base de datos {DATAMART_DB} creada.';
        END
        ELSE
            PRINT 'Base de datos {DATAMART_DB} ya existe.';
    """)
    conn.close()
    print(f"✓ Base de datos {DATAMART_DB} lista.")


def create_datamart_schema(cursor):
    """Crea todas las tablas del esquema estrella."""
    print("\nCreando esquema del Data Mart...")

    # Dropear en orden: primero hechos, luego dimensiones
    drop_statements = [
        "IF OBJECT_ID('dbo.Fact_Empleo_Ingreso', 'U') IS NOT NULL DROP TABLE dbo.Fact_Empleo_Ingreso",
        "IF OBJECT_ID('dbo.Dim_Tiempo', 'U') IS NOT NULL DROP TABLE dbo.Dim_Tiempo",
        "IF OBJECT_ID('dbo.Dim_Region', 'U') IS NOT NULL DROP TABLE dbo.Dim_Region",
        "IF OBJECT_ID('dbo.Dim_Departamento', 'U') IS NOT NULL DROP TABLE dbo.Dim_Departamento",
        "IF OBJECT_ID('dbo.Dim_Provincia', 'U') IS NOT NULL DROP TABLE dbo.Dim_Provincia",
        "IF OBJECT_ID('dbo.Dim_Distrito', 'U') IS NOT NULL DROP TABLE dbo.Dim_Distrito",
        "IF OBJECT_ID('dbo.Dim_Ocupacion', 'U') IS NOT NULL DROP TABLE dbo.Dim_Ocupacion",
        "IF OBJECT_ID('dbo.Dim_Sector', 'U') IS NOT NULL DROP TABLE dbo.Dim_Sector",
        "IF OBJECT_ID('dbo.Dim_Tipo_Empleo', 'U') IS NOT NULL DROP TABLE dbo.Dim_Tipo_Empleo",
        "IF OBJECT_ID('dbo.Dim_Trabajador', 'U') IS NOT NULL DROP TABLE dbo.Dim_Trabajador",
        "IF OBJECT_ID('dbo.Dim_Ref_Economica', 'U') IS NOT NULL DROP TABLE dbo.Dim_Ref_Economica",
    ]

    create_statements = [
        """CREATE TABLE dbo.Dim_Tiempo (
            id_tiempo       INT IDENTITY(1,1) PRIMARY KEY,
            anio            INT NOT NULL,
            mes             INT NOT NULL,
            trimestre       INT NOT NULL,
            rmv_vigente     DECIMAL(10,2) NULL,
            UNIQUE (anio, mes)
        )""",
        """CREATE TABLE dbo.Dim_Region (
            id_region       INT PRIMARY KEY,
            nombre_region   NVARCHAR(100) NOT NULL
        )""",
        """CREATE TABLE dbo.Dim_Departamento (
            id_departamento     INT PRIMARY KEY,
            cod_departamento    CHAR(2) NOT NULL,
            nombre_departamento NVARCHAR(100) NOT NULL,
            macro_region        NVARCHAR(50) NULL
        )""",
        """CREATE TABLE dbo.Dim_Provincia (
            id_provincia        INT PRIMARY KEY,
            cod_provincia       CHAR(4) NOT NULL,
            nombre_provincia    NVARCHAR(100) NULL,
            id_departamento     INT NULL
        )""",
        """CREATE TABLE dbo.Dim_Distrito (
            id_distrito     INT PRIMARY KEY,
            ubigeo          CHAR(6) NOT NULL,
            nombre_distrito NVARCHAR(100) NULL,
            dominio         INT NULL,
            dominio_desc    NVARCHAR(100) NULL,
            area            NVARCHAR(10) NULL,
            estrato         INT NULL,
            id_departamento INT NULL,
            id_provincia    INT NULL
        )""",
        """CREATE TABLE dbo.Dim_Ocupacion (
            id_ocupacion            INT IDENTITY(1,1) PRIMARY KEY,
            cod_ocupacion_cno       VARCHAR(10) NOT NULL,
            descripcion_ocupacion   NVARCHAR(200) NULL,
            grupo_ocupacional       NVARCHAR(100) NULL,
            UNIQUE (cod_ocupacion_cno)
        )""",
        """CREATE TABLE dbo.Dim_Sector (
            id_sector               INT IDENTITY(1,1) PRIMARY KEY,
            cod_ciiu_r4             VARCHAR(10) NOT NULL,
            descripcion_actividad   NVARCHAR(200) NULL,
            sector_agrupado         NVARCHAR(100) NULL,
            tipo_sector             NVARCHAR(20) NULL,
            UNIQUE (cod_ciiu_r4)
        )""",
        """CREATE TABLE dbo.Dim_Tipo_Empleo (
            id_tipo_empleo          INT IDENTITY(1,1) PRIMARY KEY,
            categoria_ocupacional   NVARCHAR(100) NULL,
            tipo_empleador          NVARCHAR(100) NULL,
            formalidad_sunat        NVARCHAR(100) NULL,
            tipo_contrato           NVARCHAR(100) NULL,
            tamanio_empresa         NVARCHAR(50)  NULL,
            flag_formal             BIT NOT NULL DEFAULT 0,
            UNIQUE (categoria_ocupacional, tipo_empleador, formalidad_sunat,
                    tipo_contrato, tamanio_empresa)
        )""",
        """CREATE TABLE dbo.Dim_Trabajador (
            id_trabajador           INT IDENTITY(1,1) PRIMARY KEY,
            sexo                    NVARCHAR(20) NULL,
            edad                    INT NULL,
            grupo_etario            NVARCHAR(50) NULL,
            nivel_educativo         NVARCHAR(50) NULL,
            jefe_de_hogar           BIT NOT NULL DEFAULT 0
        )""",
        """CREATE TABLE dbo.Dim_Ref_Economica (
            id_ref_economica    INT IDENTITY(1,1) PRIMARY KEY,
            anio                INT NOT NULL,
            mes                 INT NOT NULL,
            rmv_soles           DECIMAL(10,2) NOT NULL,
            uit_soles           DECIMAL(12,2) NOT NULL,
            cbc_per_capita      DECIMAL(10,2) NULL,
            UNIQUE (anio, mes)
        )""",
        """CREATE TABLE dbo.Fact_Empleo_Ingreso (
            id_tiempo           INT NOT NULL,
            id_region           INT NULL,
            id_departamento     INT NULL,
            id_provincia        INT NULL,
            id_distrito         INT NULL,
            id_ocupacion        INT NULL,
            id_sector           INT NOT NULL,
            id_tipo_empleo      INT NOT NULL,
            id_trabajador       INT NOT NULL,
            id_ref_economica    INT NULL,
            ingreso_principal_mes   DECIMAL(10,2) NULL,
            horas_principales_sem   DECIMAL(5,1) NULL,
            horas_secundaria_sem    DECIMAL(5,1) NULL,
            horas_normales_sem      DECIMAL(5,1) NULL,
            ratio_ingreso_rmv       DECIMAL(10,3) NULL,
            ratio_ingreso_cbc       DECIMAL(10,3) NULL,
            factor_expansion        DECIMAL(16,4) NULL,
            flag_subocupado_horas   BIT NOT NULL DEFAULT 0,
            flag_acceso_seguro      BIT NOT NULL DEFAULT 0,
            FOREIGN KEY (id_tiempo)        REFERENCES dbo.Dim_Tiempo(id_tiempo),
            FOREIGN KEY (id_region)        REFERENCES dbo.Dim_Region(id_region),
            FOREIGN KEY (id_departamento)  REFERENCES dbo.Dim_Departamento(id_departamento),
            FOREIGN KEY (id_provincia)     REFERENCES dbo.Dim_Provincia(id_provincia),
            FOREIGN KEY (id_distrito)      REFERENCES dbo.Dim_Distrito(id_distrito),
            FOREIGN KEY (id_ocupacion)     REFERENCES dbo.Dim_Ocupacion(id_ocupacion),
            FOREIGN KEY (id_sector)        REFERENCES dbo.Dim_Sector(id_sector),
            FOREIGN KEY (id_tipo_empleo)   REFERENCES dbo.Dim_Tipo_Empleo(id_tipo_empleo),
            FOREIGN KEY (id_trabajador)    REFERENCES dbo.Dim_Trabajador(id_trabajador),
            FOREIGN KEY (id_ref_economica) REFERENCES dbo.Dim_Ref_Economica(id_ref_economica)
        )""",
    ]

    for stmt in drop_statements:
        cursor.execute(stmt)
        cursor.commit()

    for stmt in create_statements:
        cursor.execute(stmt)
        cursor.commit()

    print("✓ Esquema completo del Data Mart creado.")
# ------------------------------ Carga de Datos --------------------------------

def load_dim_region(cursor, conn):
    """Carga Dim_Region desde los valores unicos de DOMINIO."""
    print("\nCargando Dim_Region...")
    for cod, desc in DOMINIO_DESC.items():
        cursor.execute(
            "INSERT INTO dbo.Dim_Region (id_region, nombre_region) VALUES (?, ?)",
            cod, desc
        )
    conn.commit()
    print(f"✓ {len(DOMINIO_DESC)} regiones cargadas.")


def load_dim_departamento(cursor, conn):
    """Carga Dim_Departamento desde el lookup de UBIGEO."""
    print("\nCargando Dim_Departamento...")
    for cod, nombre in DEPARTAMENTOS.items():
        cod_int = int(cod)
        macro = DEPTO_A_REGION.get(cod, 'No especificada')
        cursor.execute(
            "INSERT INTO dbo.Dim_Departamento (id_departamento, cod_departamento, nombre_departamento, macro_region) VALUES (?, ?, ?, ?)",
            cod_int, cod, nombre, macro
        )
    conn.commit()
    print(f"✓ {len(DEPARTAMENTOS)} departamentos cargados.")


def load_dim_provincia(cursor, staging_conn, dm_conn):
    """Extrae provincias unicas del staging y las carga a Dim_Provincia."""
    print("\nCargando Dim_Provincia...")
    df = pd.read_sql("""
        SELECT DISTINCT
            LEFT(ubigeo, 4) AS cod_provincia,
            LEFT(ubigeo, 2) AS cod_departamento
        FROM ena2024_500
        WHERE ubigeo IS NOT NULL AND LEN(ubigeo) >= 4
    """, staging_conn)
    df = df.drop_duplicates(subset=['cod_provincia'])  # <-- fix aquí

    count = 0
    for _, r in df.iterrows():
        cod_prov = r['cod_provincia']
        cod_dept = r['cod_departamento']
        id_prov = int(cod_prov)
        id_dept = int(cod_dept) if cod_dept and str(cod_dept).strip().isdigit() else None
        cursor.execute(
            "INSERT INTO dbo.Dim_Provincia (id_provincia, cod_provincia, nombre_provincia, id_departamento) VALUES (?, ?, ?, ?)",
            id_prov, cod_prov, f"Provincia {cod_prov}", id_dept
        )
        count += 1

    dm_conn.commit()
    print(f"✓ {count} provincias cargadas.")

def load_dim_distrito(cursor, staging_conn, dm_conn):
    """Extrae distritos unicos del staging (con area derivada de DOMINIO)."""
    print("\nCargando Dim_Distrito...")
    df = pd.read_sql("""
        SELECT
            ubigeo,
            MAX(dominio)  AS dominio,
            MAX(estrato)  AS estrato,
            LEFT(ubigeo, 2) AS cod_departamento,
            LEFT(ubigeo, 4) AS cod_provincia
        FROM ena2024_500
        WHERE ubigeo IS NOT NULL AND LEN(ubigeo) = 6
        GROUP BY ubigeo, LEFT(ubigeo, 2), LEFT(ubigeo, 4)
    """, staging_conn)

    count = 0
    for _, r in df.iterrows():
        ubigeo  = str(r['ubigeo']).strip()
        dominio = int(r['dominio']) if pd.notna(r['dominio']) else None
        estrato = int(r['estrato']) if pd.notna(r['estrato']) else None
        id_dist = int(ubigeo)
        id_dept = int(str(r['cod_departamento']).strip()) if str(r['cod_departamento']).strip().isdigit() else None
        id_prov = int(str(r['cod_provincia']).strip())    if str(r['cod_provincia']).strip().isdigit() else None
        dominio_desc = DOMINIO_DESC.get(dominio)
        area = 'Urbano' if dominio and dominio <= 8 else 'Rural'

        cursor.execute(
            """INSERT INTO dbo.Dim_Distrito
               (id_distrito, ubigeo, nombre_distrito, dominio, dominio_desc,
                area, estrato, id_departamento, id_provincia)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            id_dist, ubigeo, f"Distrito {ubigeo}", dominio, dominio_desc,
            area, estrato, id_dept, id_prov
        )
        count += 1

    dm_conn.commit()
    print(f"✓ {count} distritos cargados.")
def load_dim_ocupacion(cursor, staging_conn, dm_conn):
    """Extrae ocupaciones CNO unicas."""
    print("\nCargando Dim_Ocupacion...")
    df = pd.read_sql("""
        SELECT DISTINCT cod_ocupacion_cno
        FROM ena2024_500
        WHERE cod_ocupacion_cno IS NOT NULL AND cod_ocupacion_cno != ''
    """, staging_conn)

    count = 0
    for _, r in df.iterrows():
        cod = r['cod_ocupacion_cno']
        grupo = GRUPO_OCUPACIONAL.get(cod[0] if cod else '', 'No clasificado')
        cursor.execute(
            "INSERT INTO dbo.Dim_Ocupacion (cod_ocupacion_cno, descripcion_ocupacion, grupo_ocupacional) VALUES (?, ?, ?)",
            cod, f"Ocupacion CNO {cod}", grupo
        )
        count += 1

    dm_conn.commit()
    print(f"✓ {count} ocupaciones cargadas.")


def load_dim_sector(cursor, staging_conn, dm_conn):
    """Extrae sectores CIIU unicos y los carga con sector_agrupado."""
    print("\nCargando Dim_Sector...")
    df = pd.read_sql("""
        SELECT
            cod_sector_ciiu,
            MAX(tipo_empleador) AS tipo_empleador
        FROM ena2024_500
        WHERE cod_sector_ciiu IS NOT NULL AND cod_sector_ciiu != ''
        GROUP BY cod_sector_ciiu
    """, staging_conn)

    count = 0
    for _, r in df.iterrows():
        cod      = str(r['cod_sector_ciiu']).strip()
        agrupado = get_sector_agrupado(cod)
        tipo_emp = r['tipo_empleador']
        tipo_sec = 'Publico' if (pd.notna(tipo_emp) and int(tipo_emp) == 2) else 'Privado'
        cursor.execute(
            "INSERT INTO dbo.Dim_Sector (cod_ciiu_r4, descripcion_actividad, sector_agrupado, tipo_sector) VALUES (?, ?, ?, ?)",
            cod, f"Actividad CIIU {cod}", agrupado, tipo_sec
        )
        count += 1

    dm_conn.commit()
    print(f"✓ {count} sectores cargados.")

def load_dim_tipo_empleo(cursor, staging_conn, dm_conn):
    """Extrae combinaciones unicas de tipo de empleo y calcula flag_formal."""
    print("\nCargando Dim_Tipo_Empleo...")
    df = pd.read_sql("""
        SELECT DISTINCT
            categoria_ocupacional, tipo_empleador, formalidad_sunat,
            tipo_contrato, tamanio_empresa
        FROM ena2024_500
        WHERE ingreso_principal_mes IS NOT NULL
    """, staging_conn)

    count = 0
    for _, r in df.iterrows():
        cat  = CAT_OCUPACIONAL.get(int(r['categoria_ocupacional']), None) if pd.notna(r['categoria_ocupacional']) else None
        tip  = TIPO_EMPLEADOR.get(int(r['tipo_empleador']), None) if pd.notna(r['tipo_empleador']) else None
        form = FORMALIDAD_SUNAT.get(int(r['formalidad_sunat']), None) if pd.notna(r['formalidad_sunat']) else None
        cont = TIPO_CONTRATO.get(int(r['tipo_contrato']), None) if pd.notna(r['tipo_contrato']) else None
        tam  = TAMANIO_EMPRESA.get(int(r['tamanio_empresa']), None) if pd.notna(r['tamanio_empresa']) else None

        # flag_formal: contrato escrito (indefinido, plazo fijo, CAS) Y registrado en SUNAT (Persona Juridica o PN con RUC)
        contrato_formal = int(r['tipo_contrato']) in [1, 2, 4] if pd.notna(r['tipo_contrato']) else False
        sunat_formal    = int(r['formalidad_sunat']) in [1, 2] if pd.notna(r['formalidad_sunat']) else False
        flag_formal = 1 if (contrato_formal and sunat_formal) else 0

        try:
            cursor.execute(
                """INSERT INTO dbo.Dim_Tipo_Empleo
                   (categoria_ocupacional, tipo_empleador, formalidad_sunat,
                    tipo_contrato, tamanio_empresa, flag_formal)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                cat, tip, form, cont, tam, flag_formal
            )
            count += 1
        except Exception:
            # Duplicado por UNIQUE constraint, ignorar
            dm_conn.rollback()
            continue

    dm_conn.commit()
    print(f"✓ {count} combinaciones de tipo empleo cargadas.")


def load_dim_trabajador(cursor, staging_conn, dm_conn):
    """Carga trabajadores unicos con perfil demografico."""
    print("\nCargando Dim_Trabajador...")
    df = pd.read_sql("""
        SELECT DISTINCT sexo, edad, nivel_educativo, relacion_parentesco
        FROM ena2024_500
        WHERE ingreso_principal_mes IS NOT NULL
    """, staging_conn)

    count = 0
    for _, r in df.iterrows():
        sexo     = 'Hombre' if (pd.notna(r['sexo']) and int(r['sexo']) == 1) else ('Mujer' if pd.notna(r['sexo']) and int(r['sexo']) == 2 else None)
        edad     = int(r['edad']) if pd.notna(r['edad']) else None
        grupo    = get_grupo_etario(edad)
        nivel    = NIVEL_EDUCATIVO.get(int(r['nivel_educativo']), None) if pd.notna(r['nivel_educativo']) else None
        jefe     = 1 if (pd.notna(r['relacion_parentesco']) and int(r['relacion_parentesco']) == 1) else 0

        cursor.execute(
            """INSERT INTO dbo.Dim_Trabajador
               (sexo, edad, grupo_etario, nivel_educativo, jefe_de_hogar)
               VALUES (?, ?, ?, ?, ?)""",
            sexo, edad, grupo, nivel, jefe
        )
        count += 1

    dm_conn.commit()
    print(f"✓ {count} trabajadores cargados.")


def load_dim_tiempo(cursor, staging_conn, dm_conn):
    """Carga Dim_Tiempo desde anio/mes unicos en staging, mas RMV desde Ref_Economica."""
    print("\nCargando Dim_Tiempo...")
    df = pd.read_sql("""
        SELECT DISTINCT anio, mes FROM ena2024_500
        WHERE anio IS NOT NULL AND mes IS NOT NULL
    """, staging_conn)

    # Cargar RMV desde Excel para obtener RMV por mes
    try:
        xl = pd.read_excel(REF_EXCEL, sheet_name='Hoja1')
        xl['Fecha'] = pd.to_datetime(xl['Fecha'], errors='coerce')
        xl_r = xl.dropna(subset=['Fecha'])
        rmv_map = {}
        for _, row in xl_r.iterrows():
            key = (int(row['Fecha'].year), int(row['Fecha'].month))
            if key not in rmv_map:
                rmv_map[key] = float(row['Remuneración Mínima Vital - Nominal (S/)'])
    except Exception as e:
        print(f"  Advertencia: No se pudo cargar RMV desde Excel ({e}). Usando RMV=1025.")
        rmv_map = {}

    count = 0
    for _, r in df.iterrows():
        anio = int(r['anio'])
        mes  = int(r['mes'])
        trim = (mes - 1) // 3 + 1
        rmv  = rmv_map.get((anio, mes), 1025.00)  # Default RMV 2024
        cursor.execute(
            "INSERT INTO dbo.Dim_Tiempo (anio, mes, trimestre, rmv_vigente) VALUES (?, ?, ?, ?)",
            anio, mes, trim, rmv
        )
        count += 1

    dm_conn.commit()
    print(f"✓ {count} periodos cargados en Dim_Tiempo.")


def load_dim_ref_economica(cursor, dm_conn):
    """Carga Dim_Ref_Economica desde el archivo Excel de referencia."""
    print("\nCargando Dim_Ref_Economica...")
    try:
        xl = pd.read_excel(REF_EXCEL, sheet_name='Hoja1')
        xl['Fecha'] = pd.to_datetime(xl['Fecha'], errors='coerce')
        xl = xl.dropna(subset=['Fecha'])
        xl['anio'] = xl['Fecha'].dt.year.astype(int)
        xl['mes']  = xl['Fecha'].dt.month.astype(int)
        xl['rmv']  = xl['Remuneración Mínima Vital - Nominal (S/)']
        xl['uit']  = xl['UIT']
        xl['cbc']  = xl['CBC']

        grouped = xl.groupby(['anio', 'mes']).agg(
            rmv=('rmv', 'first'), uit=('uit', 'first'), cbc=('cbc', 'first')
        ).reset_index()

        count = 0
        for _, r in grouped.iterrows():
            cursor.execute(
                """INSERT INTO dbo.Dim_Ref_Economica (anio, mes, rmv_soles, uit_soles, cbc_per_capita)
                   VALUES (?, ?, ?, ?, ?)""",
                int(r['anio']), int(r['mes']),
                float(r['rmv']), float(r['uit']),
                float(r['cbc']) if pd.notna(r['cbc']) else None
            )
            count += 1

        dm_conn.commit()
        print(f"✓ {count} registros de referencia economica cargados.")
    except Exception as e:
        print(f"  Error cargando Dim_Ref_Economica: {e}")
        print("  Insertando datos minimos para 2024...")
        for m in range(1, 13):
            cursor.execute(
                "INSERT INTO dbo.Dim_Ref_Economica (anio, mes, rmv_soles, uit_soles, cbc_per_capita) VALUES (?, ?, ?, ?, ?)",
                2024, m, 1025.00, 5150.00, 465.00
            )
        dm_conn.commit()
        print(f"✓ 12 registros minimos cargados.")


def load_fact_empleo_ingreso(cursor, staging_conn, dm_conn):
    """Construye y carga la tabla de hechos Fact_Empleo_Ingreso usando mapeo por diccionarios."""
    print("\nConstruyendo tabla de hechos Fact_Empleo_Ingreso...")

    # Leer datos de staging
    df = pd.read_sql("""
        SELECT
            ubigeo, dominio, estrato, anio, mes,
            ingreso_principal_mes, horas_principales_sem,
            horas_secundaria_sem, horas_normales_sem,
            factor_expansion,
            flag_quiere_mas_horas, flag_disponible_mas_horas,
            cod_ocupacion_cno, cod_sector_ciiu,
            categoria_ocupacional, tipo_empleador, formalidad_sunat,
            tipo_contrato, tamanio_empresa,
            sexo, edad, nivel_educativo, relacion_parentesco,
            seguro_sis, seguro_essalud, seguro_ffaa_pnp, seguro_privado,
            seguro_eps, seguro_universitario, seguro_escolar,
            seguro_otro, seguro_no_tiene, seguro_no_sabe
        FROM ena2024_500
        WHERE ingreso_principal_mes IS NOT NULL
    """, staging_conn)

    print(f"  Registros con ingreso valido: {len(df):,}")
    if df.empty:
        print("  No hay registros para cargar en la tabla de hechos.")
        return

    # --- Construir diccionarios de mapeo desde las dimensiones ---

    # Tiempo: (anio, mes) -> id_tiempo
    df_t = pd.read_sql("SELECT id_tiempo, anio, mes FROM dbo.Dim_Tiempo", dm_conn)
    map_tiempo = {(int(r.anio), int(r.mes)): int(r.id_tiempo) for _, r in df_t.iterrows()}

    # Departamento: cod_dep (str) -> id_departamento
    df_d = pd.read_sql("SELECT id_departamento, cod_departamento FROM dbo.Dim_Departamento", dm_conn)
    map_depto = {str(r.cod_departamento).strip(): int(r.id_departamento) for _, r in df_d.iterrows()}

    # Provincia: cod_prov (str, 4 digitos) -> id_provincia
    df_p = pd.read_sql("SELECT id_provincia, cod_provincia FROM dbo.Dim_Provincia", dm_conn)
    map_prov = {str(r.cod_provincia).strip(): int(r.id_provincia) for _, r in df_p.iterrows()}

    # Distrito: ubigeo (str, 6 digitos) -> id_distrito
    df_dist = pd.read_sql("SELECT id_distrito, ubigeo FROM dbo.Dim_Distrito", dm_conn)
    map_dist = {str(r.ubigeo).strip(): int(r.id_distrito) for _, r in df_dist.iterrows()}

    # Ocupacion: cod_cno -> id_ocupacion
    df_o = pd.read_sql("SELECT id_ocupacion, cod_ocupacion_cno FROM dbo.Dim_Ocupacion", dm_conn)
    map_ocup = {str(r.cod_ocupacion_cno).strip(): int(r.id_ocupacion) for _, r in df_o.iterrows()}

    # Sector: cod_ciiu -> id_sector
    df_s = pd.read_sql("SELECT id_sector, cod_ciiu_r4 FROM dbo.Dim_Sector", dm_conn)
    map_sector = {str(r.cod_ciiu_r4).strip(): int(r.id_sector) for _, r in df_s.iterrows()}

    # Tipo Empleo: tupla de 5 atributos -> id_tipo_empleo
    df_te = pd.read_sql("""
        SELECT id_tipo_empleo, categoria_ocupacional, tipo_empleador,
               formalidad_sunat, tipo_contrato, tamanio_empresa
        FROM dbo.Dim_Tipo_Empleo
    """, dm_conn)
    map_tipo_e = {}
    for _, r in df_te.iterrows():
        key = (str(r.categoria_ocupacional or ''), str(r.tipo_empleador or ''),
               str(r.formalidad_sunat or ''), str(r.tipo_contrato or ''),
               str(r.tamanio_empresa or ''))
        map_tipo_e[key] = int(r.id_tipo_empleo)

    # Trabajador: (sexo_str, edad_int, nivel_edu_str, jefe_int) -> id_trabajador
    df_tr = pd.read_sql("""
        SELECT id_trabajador, sexo, ISNULL(edad,0) AS edad,
               ISNULL(nivel_educativo,'') AS nivel_educativo,
               CAST(jefe_de_hogar AS INT) AS jefe_de_hogar
        FROM dbo.Dim_Trabajador
    """, dm_conn)
    map_trab = {}
    for _, r in df_tr.iterrows():
        key = (str(r.sexo or ''), int(r.edad or 0),
               str(r.nivel_educativo or ''), int(r.jefe_de_hogar or 0))
        map_trab[key] = int(r.id_trabajador)

    # Ref Economica: (anio, mes) -> id_ref_economica + rmv + cbc
    df_ref = pd.read_sql("""
        SELECT id_ref_economica, anio, mes, rmv_soles, ISNULL(cbc_per_capita, 0) AS cbc_per_capita
        FROM dbo.Dim_Ref_Economica
    """, dm_conn)
    map_ref = {}
    map_rmv = {}
    map_cbc = {}
    for _, r in df_ref.iterrows():
        key = (int(r.anio), int(r.mes))
        map_ref[key] = int(r.id_ref_economica)
        map_rmv[key] = float(r.rmv_soles)
        map_cbc[key] = float(r.cbc_per_capita) if r.cbc_per_capita else 0.0

    # --- Calcular columnas derivadas para el mapeo ---

    # Convertir tipos
    df['anio_int'] = pd.to_numeric(df['anio'], errors='coerce').fillna(0).astype(int)
    df['mes_int']  = pd.to_numeric(df['mes'], errors='coerce').fillna(0).astype(int)

    df['cod_dep'] = df['ubigeo'].astype(str).str.strip().str[:2]
    df['cod_prov'] = df['ubigeo'].astype(str).str.strip().str[:4]
    df['ubigeo_str'] = df['ubigeo'].astype(str).str.strip()

    df['cod_cno'] = df['cod_ocupacion_cno'].astype(str).str.strip()
    df['cod_ciiu'] = df['cod_sector_ciiu'].astype(str).str.strip()

    # Describir tipo de empleo (para match con Dim_Tipo_Empleo)
    def safe_desc(val, mapping):
        if pd.isna(val) or (isinstance(val, str) and val.strip() == ''):
            return ''
        try:
            return mapping.get(int(float(val)), '')
        except (ValueError, TypeError):
            return ''

    df['_cat']  = df['categoria_ocupacional'].apply(lambda x: safe_desc(x, CAT_OCUPACIONAL))
    df['_tip']  = df['tipo_empleador'].apply(lambda x: safe_desc(x, TIPO_EMPLEADOR))
    df['_form'] = df['formalidad_sunat'].apply(lambda x: safe_desc(x, FORMALIDAD_SUNAT))
    df['_cont'] = df['tipo_contrato'].apply(lambda x: safe_desc(x, TIPO_CONTRATO))
    df['_tam']  = df['tamanio_empresa'].apply(lambda x: safe_desc(x, TAMANIO_EMPRESA))

    # Describir trabajador
    df['_sexo'] = df['sexo'].apply(lambda x: 'Hombre' if pd.notna(x) and float(x)==1 else ('Mujer' if pd.notna(x) and float(x)==2 else ''))
    df['_edad'] = pd.to_numeric(df['edad'], errors='coerce').fillna(0).astype(int)
    df['_nivel'] = df['nivel_educativo'].apply(lambda x: safe_desc(x, NIVEL_EDUCATIVO))
    df['_jefe']  = df['relacion_parentesco'].apply(lambda x: 1 if (pd.notna(x) and float(x)==1) else 0)

    # --- Insertar en lotes ---
    insert_sql = """
        INSERT INTO dbo.Fact_Empleo_Ingreso (
            id_tiempo, id_region, id_departamento, id_provincia, id_distrito,
            id_ocupacion, id_sector, id_tipo_empleo, id_trabajador, id_ref_economica,
            ingreso_principal_mes, horas_principales_sem, horas_secundaria_sem,
            horas_normales_sem, ratio_ingreso_rmv, ratio_ingreso_cbc,
            factor_expansion, flag_subocupado_horas, flag_acceso_seguro
        ) VALUES (?,?,?,?,?, ?,?,?,?,?, ?,?,?,?,?,?, ?,?,?)
    """

    seguro_cols = ['seguro_sis','seguro_essalud','seguro_ffaa_pnp','seguro_privado',
                   'seguro_eps','seguro_universitario','seguro_escolar','seguro_otro']

    count = 0
    batch_size = 1000
    records = []

    for _, r in df.iterrows():
        try:
            anio_i = r['anio_int']
            mes_i  = r['mes_int']

            # Mapear IDs
            id_tiempo = map_tiempo.get((anio_i, mes_i))
            id_region = int(r['dominio']) if pd.notna(r['dominio']) and int(r['dominio']) in DOMINIO_DESC else None
            id_depto  = map_depto.get(r['cod_dep'])
            id_prov   = map_prov.get(r['cod_prov'])
            id_dist   = map_dist.get(r['ubigeo_str'])
            id_ocup   = map_ocup.get(r['cod_cno'])
            id_sec    = map_sector.get(r['cod_ciiu'])
            id_te     = map_tipo_e.get((r['_cat'], r['_tip'], r['_form'], r['_cont'], r['_tam']))
            id_trab   = map_trab.get((r['_sexo'], r['_edad'], r['_nivel'], r['_jefe']))
            id_ref    = map_ref.get((anio_i, mes_i))

            # Metricas
            ingreso  = float(r['ingreso_principal_mes']) if pd.notna(r['ingreso_principal_mes']) else None
            h_princ  = float(r['horas_principales_sem']) if pd.notna(r['horas_principales_sem']) else None
            h_sec    = float(r['horas_secundaria_sem']) if pd.notna(r['horas_secundaria_sem']) else None
            h_norm   = float(r['horas_normales_sem']) if pd.notna(r['horas_normales_sem']) else None
            fac_exp  = float(r['factor_expansion']) if pd.notna(r['factor_expansion']) else None

            rmv_v = map_rmv.get((anio_i, mes_i), 0)
            cbc_v = map_cbc.get((anio_i, mes_i), 0)
            ratio_rmv = round(ingreso / rmv_v, 3) if ingreso and rmv_v > 0 else None
            ratio_cbc = round(ingreso / cbc_v, 3) if ingreso and cbc_v > 0 else None

            # Flags
            sub_flag  = 1 if (pd.notna(r['flag_quiere_mas_horas']) and int(r['flag_quiere_mas_horas']) == 1
                             and pd.notna(r['flag_disponible_mas_horas']) and int(r['flag_disponible_mas_horas']) == 1) else 0

            seguro_flag = 0
            for sc in seguro_cols:
                if pd.notna(r[sc]) and int(r[sc]) == 1:
                    seguro_flag = 1
                    break
            rmv_v = map_rmv.get((anio_i, mes_i), 0)
            cbc_v = map_cbc.get((anio_i, mes_i), 0)
            ratio_rmv = round(ingreso / rmv_v, 3) if ingreso and rmv_v > 0 else None
            ratio_cbc = round(ingreso / cbc_v, 3) if ingreso and cbc_v > 0 else None
            
            # Agregar estos caps justo después:
            ratio_rmv = min(ratio_rmv, 9999999.999) if ratio_rmv is not None else None
            ratio_cbc = min(ratio_cbc, 9999999.999) if ratio_cbc is not None else None

            records.append((
                id_tiempo, id_region, id_depto, id_prov, id_dist,
                id_ocup, id_sec, id_te, id_trab, id_ref,
                ingreso, h_princ, h_sec, h_norm, ratio_rmv, ratio_cbc,
                fac_exp, sub_flag, seguro_flag
            ))
            count += 1

            if len(records) >= batch_size:
                cursor.executemany(insert_sql, records)
                dm_conn.commit()
                records = []

        except Exception:
            continue

    # Insertar el remanente
    if records:
        cursor.executemany(insert_sql, records)
        dm_conn.commit()

    print(f"✓ {count:,} registros de hechos cargados en Fact_Empleo_Ingreso.")


# ------------------------------ Main --------------------------------

if __name__ == '__main__':
    print("=" * 60)
    print(" POBLAR DATA MART (ESQUEMA ESTRELLA)")
    print(f" Origen:  {STAGING_DB}.dbo.ena2024_500")
    print(f" Destino: {DATAMART_DB}")
    print("=" * 60)

    setup_datamart_db()

    staging_conn = get_staging_connection()
    dm_conn = get_dm_connection()
    dm_cursor = dm_conn.cursor()
    
    create_datamart_schema(dm_cursor)

    # Cargar dimensiones en orden
    load_dim_tiempo(dm_cursor, staging_conn, dm_conn)
    load_dim_region(dm_cursor, dm_conn)
    load_dim_departamento(dm_cursor, dm_conn)
    load_dim_provincia(dm_cursor, staging_conn, dm_conn)
    load_dim_distrito(dm_cursor, staging_conn, dm_conn)
    load_dim_ocupacion(dm_cursor, staging_conn, dm_conn)
    load_dim_sector(dm_cursor, staging_conn, dm_conn)
    load_dim_tipo_empleo(dm_cursor, staging_conn, dm_conn)
    load_dim_trabajador(dm_cursor, staging_conn, dm_conn)
    load_dim_ref_economica(dm_cursor, dm_conn)

    # Cargar tabla de hechos
    load_fact_empleo_ingreso(dm_cursor, staging_conn, dm_conn)

    staging_conn.close()
    dm_conn.close()

    print(f"\n{'='*60}")
    print(" DATA MART POBLADO EXITOSAMENTE")
    print(f"{'='*60}")
