# -*- coding: utf-8 -*-
"""
Paso 1: Poblar base de datos destino (Staging) desde CSV ENAHO 2024.

Lee el archivo CSV de ENAHO 2024 Modulo 500 (260 MB, 1425 columnas),
selecciona solo las columnas necesarias para el datamart y las carga
en una tabla staging en SQL Server.

BD origen : CSV 2024Empleo e Ingresos.csv
BD destino: ENAHO_Staging (tabla ena2024_500)
"""

import pyodbc
import pandas as pd
import os

# ------------------------------ Configuracion --------------------------------

CSV_PATH = r'C:\estela\github\Datamart-calidad-empleo-ingresos\2024Empleo e Ingresos.csv'
SERVER = 'localhost'
UID = 'sa'
PWD = '1234567890'
STAGING_DB = 'ENAHO_Staging'
TABLE_NAME = 'ena2024_500'
CHUNKSIZE = 50000

# Columnas necesarias para el datamart (segun README seccion 4.1)
USE_COLS = [
    'UBIGEO', 'DOMINIO', 'ESTRATO',       # Dim_Geografia (separada)
    'AÑO', 'MES',                           # Dim_Tiempo
    'P524A1', 'P524B1',                    # Ingresos (principal, secundario)
    'I513T', 'P518', 'P520',               # Horas trabajadas
    'FAC500A',                              # Factor de expansion
    'P521', 'P521A',                        # Subocupacion (flag)
    'P505R4', 'P506R4',                    # Ocupacion (CNO), Sector (CIIU)
    'P507', 'P510', 'P510A1', 'P511A', 'P512A',  # Tipo de empleo
    'P203', 'P207', 'P208A', 'P209',        # Datos del trabajador
    'P5581A','P5582A','P5583A','P5584A','P5585A',  # Seguro de salud
    'P5586A','P5587A','P5588A','P5589A','P55810A',
]

# ------------------------------ Conexion SQL --------------------------------

def get_master_connection():
    """Conecta al servidor (sin base de datos especifica) para crear DBs."""
    return pyodbc.connect(
        f'DRIVER={{ODBC Driver 17 for SQL Server}};'
        f'SERVER={SERVER};'
        f'UID={UID};'
        f'PWD={PWD}',
        autocommit=True
    )

def get_staging_connection():
    """Conecta a la base de datos de staging."""
    return pyodbc.connect(
        f'DRIVER={{ODBC Driver 17 for SQL Server}};'
        f'SERVER={SERVER};'
        f'DATABASE={STAGING_DB};'
        f'UID={UID};'
        f'PWD={PWD}'
    )

def setup_staging_db():
    """Crea la base de datos de staging si no existe."""
    print("Configurando base de datos de staging...")
    master_conn = get_master_connection()
    cursor = master_conn.cursor()

    cursor.execute(f"""
        IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = '{STAGING_DB}')
        BEGIN
            CREATE DATABASE [{STAGING_DB}];
            PRINT 'Base de datos {STAGING_DB} creada.';
        END
        ELSE
            PRINT 'Base de datos {STAGING_DB} ya existe.';
    """)
    master_conn.close()
    print(f"✓ Base de datos {STAGING_DB} lista.")

def create_staging_table(cursor):
    """Crea la tabla de staging con todas las columnas necesarias."""
    drop_sql = f"""
        IF OBJECT_ID('dbo.{TABLE_NAME}', 'U') IS NOT NULL
            DROP TABLE dbo.{TABLE_NAME};
    """
    cursor.execute(drop_sql)

    create_sql = f"""
        CREATE TABLE dbo.{TABLE_NAME} (
            ubigeo          VARCHAR(6)   NULL,
            dominio         INT          NULL,
            estrato         INT          NULL,
            anio            INT          NULL,
            mes             INT          NULL,
            ingreso_principal_mes  DECIMAL(10,2) NULL,
            ingreso_secundario_mes DECIMAL(10,2) NULL,
            horas_principales_sem  DECIMAL(5,1)  NULL,
            horas_secundaria_sem   DECIMAL(5,1)  NULL,
            horas_normales_sem     DECIMAL(5,1)  NULL,
            factor_expansion       DECIMAL(12,4) NULL,
            flag_quiere_mas_horas      INT  NULL,
            flag_disponible_mas_horas  INT  NULL,
            cod_ocupacion_cno     VARCHAR(10) NULL,
            cod_sector_ciiu       VARCHAR(10) NULL,
            categoria_ocupacional INT  NULL,
            tipo_empleador        INT  NULL,
            formalidad_sunat      INT  NULL,
            tipo_contrato         INT  NULL,
            tamanio_empresa       INT  NULL,
            relacion_parentesco   INT  NULL,
            sexo                  INT  NULL,
            edad                  INT  NULL,
            nivel_educativo       INT  NULL,
            -- Seguros de salud (flag: 1=afiliado, 2=no afiliado)
            seguro_sis            INT  NULL,
            seguro_essalud        INT  NULL,
            seguro_ffaa_pnp       INT  NULL,
            seguro_privado        INT  NULL,
            seguro_eps            INT  NULL,
            seguro_universitario  INT  NULL,
            seguro_escolar        INT  NULL,
            seguro_otro           INT  NULL,
            seguro_no_tiene       INT  NULL,
            seguro_no_sabe        INT  NULL
        );
    """
    cursor.execute(create_sql)
    cursor.commit()
    print(f"✓ Tabla dbo.{TABLE_NAME} creada.")

def safe_float(val):
    """Convierte un valor a float, retornando None si es invalido o vacio."""
    if val is None or (isinstance(val, str) and val.strip() == ''):
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None

def safe_int(val):
    """Convierte un valor a int, retornando None si es invalido o vacio."""
    if val is None or (isinstance(val, str) and val.strip() == ''):
        return None
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return None

def process_and_load():
    """Lee el CSV en chunks, transforma y carga a la tabla staging."""
    conn = get_staging_connection()
    cursor = conn.cursor()

    create_staging_table(cursor)

    insert_sql = f"""
        INSERT INTO dbo.{TABLE_NAME} (
            ubigeo, dominio, estrato, anio, mes,
            ingreso_principal_mes, ingreso_secundario_mes,
            horas_principales_sem, horas_secundaria_sem, horas_normales_sem,
            factor_expansion,
            flag_quiere_mas_horas, flag_disponible_mas_horas,
            cod_ocupacion_cno, cod_sector_ciiu,
            categoria_ocupacional, tipo_empleador, formalidad_sunat,
            tipo_contrato, tamanio_empresa,
            relacion_parentesco, sexo, edad, nivel_educativo,
            seguro_sis, seguro_essalud, seguro_ffaa_pnp, seguro_privado,
            seguro_eps, seguro_universitario, seguro_escolar,
            seguro_otro, seguro_no_tiene, seguro_no_sabe
        ) VALUES (?,?,?,?,?, ?,?,?,?,?, ?,?,?, ?,?, ?,?,?,?,?,?,?,?,?, ?,?,?,?,?,?,?,?,?,?)
    """

    col_map = {
        'ubigeo':        'UBIGEO',   'dominio':    'DOMINIO',
        'estrato':       'ESTRATO',  'anio':       'AÑO',
        'mes':           'MES',
        'ingreso_principal_mes':  'P524A1',
        'ingreso_secundario_mes':  'P524B1',
        'horas_principales_sem':   'I513T',
        'horas_secundaria_sem':    'P518',
        'horas_normales_sem':      'P520',
        'factor_expansion':        'FAC500A',
        'flag_quiere_mas_horas':    'P521',
        'flag_disponible_mas_horas': 'P521A',
        'cod_ocupacion_cno':      'P505R4',
        'cod_sector_ciiu':        'P506R4',
        'categoria_ocupacional':  'P507',
        'tipo_empleador':         'P510',
        'formalidad_sunat':       'P510A1',
        'tipo_contrato':          'P511A',
        'tamanio_empresa':        'P512A',
        'relacion_parentesco':    'P203',
        'sexo':                   'P207',
        'edad':                   'P208A',
        'nivel_educativo':        'P209',
        'seguro_sis':             'P5581A',
        'seguro_essalud':         'P5582A',
        'seguro_ffaa_pnp':        'P5583A',
        'seguro_privado':         'P5584A',
        'seguro_eps':             'P5585A',
        'seguro_universitario':   'P5586A',
        'seguro_escolar':         'P5587A',
        'seguro_otro':            'P5588A',
        'seguro_no_tiene':        'P5589A',
        'seguro_no_sabe':         'P55810A',
    }

    print(f"\nLeyendo CSV: {CSV_PATH}")
    print(f"Columnas a extraer: {len(USE_COLS)} de {len(USE_COLS)} necesarias")
    print("Cargando en chunks...")

    total_rows = 0
    reader = pd.read_csv(
        CSV_PATH,
        usecols=USE_COLS,
        encoding='latin-1',
        chunksize=CHUNKSIZE,
        dtype=str,               # leer todo como string para manejo uniforme
        na_filter=False          # no auto-detectar NaN
    )

    for i, chunk in enumerate(reader):
        rows_inserted = 0
        for _, row in chunk.iterrows():
            vals = (
                str(row.get('UBIGEO', '')).strip() or None,
                safe_int(row.get('DOMINIO')),
                safe_int(row.get('ESTRATO')),
                safe_int(row.get('AÑO')),
                safe_int(row.get('MES')),
                safe_float(row.get('P524A1')),
                safe_float(row.get('P524B1')),
                safe_float(row.get('I513T')),
                safe_float(row.get('P518')),
                safe_float(row.get('P520')),
                safe_float(row.get('FAC500A')),
                safe_int(row.get('P521')),
                safe_int(row.get('P521A')),
                str(row.get('P505R4', '')).strip() or None,
                str(row.get('P506R4', '')).strip() or None,
                safe_int(row.get('P507')),
                safe_int(row.get('P510')),
                safe_int(row.get('P510A1')),
                safe_int(row.get('P511A')),
                safe_int(row.get('P512A')),
                safe_int(row.get('P203')),
                safe_int(row.get('P207')),
                safe_int(row.get('P208A')),
                safe_int(row.get('P209')),
                safe_int(row.get('P5581A')),
                safe_int(row.get('P5582A')),
                safe_int(row.get('P5583A')),
                safe_int(row.get('P5584A')),
                safe_int(row.get('P5585A')),
                safe_int(row.get('P5586A')),
                safe_int(row.get('P5587A')),
                safe_int(row.get('P5588A')),
                safe_int(row.get('P5589A')),
                safe_int(row.get('P55810A')),
            )
            try:
                cursor.execute(insert_sql, vals)
                rows_inserted += 1
            except Exception as e:
                print(f"  Error insertando fila: {e}")
                continue

        conn.commit()
        total_rows += rows_inserted
        print(f"  Chunk {i+1}: {rows_inserted} filas insertadas")

    conn.close()

    # Resumen
    print(f"\n{'='*60}")
    print(f" CARGA COMPLETADA")
    print(f" Total de registros cargados en {STAGING_DB}.dbo.{TABLE_NAME}: {total_rows:,}")
    print(f"{'='*60}")


if __name__ == '__main__':
    print("=" * 60)
    print(" POBLAR BASE DE DATOS DESTINO (STAGING)")
    print(" CSV ENAHO 2024 → SQL Server")
    print("=" * 60)

    setup_staging_db()
    process_and_load()
