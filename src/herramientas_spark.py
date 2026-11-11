"""Herramientas de Spark que usarán los agentes.

Cada función hace una tarea concreta (explorar, limpiar, entrenar...) y
devuelve un diccionario con resultados en forma de datos sencillos, fáciles de
pasar a un agente. Los agentes deciden QUÉ hacer; estas funciones saben CÓMO
hacerlo en Spark.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

from pyspark.ml import Pipeline
from pyspark.ml.evaluation import RegressionEvaluator
from pyspark.ml.feature import OneHotEncoder, StringIndexer, VectorAssembler
from pyspark.ml.regression import (
    GBTRegressor,
    LinearRegression,
    RandomForestRegressor,
)
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

RAIZ = Path(__file__).resolve().parent.parent
DATOS_RAW = RAIZ / "data" / "raw"
DATOS_PROCESADOS = RAIZ / "data" / "procesado" / "viajes.parquet"
SEMILLA = 42

# Zonas de aeropuerto según la tabla de zonas de la TLC
ZONAS_AEROPUERTO = [1, 132, 138]  # Newark, JFK, LaGuardia

_spark: SparkSession | None = None


# ---------------------------------------------------------------------------
# Sesión y carga
# ---------------------------------------------------------------------------

def obtener_spark() -> SparkSession:
    """Devuelve la sesión de Spark (la crea la primera vez).

    Núcleos y memoria se pueden ajustar con las variables de entorno
    SPARK_CORES (por defecto todos) y SPARK_MEMORIA (por defecto 3g). Útil
    cuando varios agentes entrenan modelos a la vez.
    """
    global _spark
    if _spark is None:
        _spark = (
            SparkSession.builder.master(f"local[{os.environ.get('SPARK_CORES', '*')}]")
            .appName("practica_agentes")
            .config("spark.driver.memory", os.environ.get("SPARK_MEMORIA", "3g"))
            .config("spark.sql.session.timeZone", "UTC")
            .config("spark.ui.showConsoleProgress", "false")
            .getOrCreate()
        )
        _spark.sparkContext.setLogLevel("ERROR")
    return _spark


def cargar_datos(fraccion: float = 0.05) -> DataFrame:
    """Carga los viajes y les añade la duración (minutos) y el barrio de cada zona.

    fraccion: parte de los datos a usar (0.05 = 5 %, ~480.000 viajes). Usar una
    muestra hace que los experimentos de los agentes sean rápidos.
    """
    spark = obtener_spark()
    viajes = spark.read.parquet(str(DATOS_RAW / "yellow_tripdata_*.parquet"))
    if fraccion < 1.0:
        viajes = viajes.sample(fraction=fraccion, seed=SEMILLA)

    zonas = spark.read.csv(str(DATOS_RAW / "taxi_zone_lookup.csv"), header=True, inferSchema=True)
    origen = zonas.select(F.col("LocationID").alias("PULocationID"), F.col("Borough").alias("pu_borough"))
    destino = zonas.select(F.col("LocationID").alias("DOLocationID"), F.col("Borough").alias("do_borough"))

    return (
        viajes.withColumn(
            "duracion_min",
            (F.unix_timestamp("tpep_dropoff_datetime") - F.unix_timestamp("tpep_pickup_datetime")) / 60.0,
        )
        .join(F.broadcast(origen), "PULocationID", "left")
        .join(F.broadcast(destino), "DOLocationID", "left")
    )


# ---------------------------------------------------------------------------
# Exploración
# ---------------------------------------------------------------------------

def perfilar_datos(df: DataFrame) -> dict:
    """Resumen del dataset: filas, nulos, estadísticas y valores problemáticos."""
    n = df.count()
    numericas = ["duracion_min", "trip_distance", "passenger_count", "fare_amount", "total_amount"]

    nulos = df.select([F.sum(F.col(c).isNull().cast("int")).alias(c) for c in df.columns]).first().asDict()
    nulos = {c: v for c, v in nulos.items() if v}

    stats = {}
    for fila in df.select(numericas).summary("min", "1%", "25%", "50%", "75%", "99%", "max", "mean").collect():
        for c in numericas:
            stats.setdefault(c, {})[fila["summary"]] = round(float(fila[c]), 2) if fila[c] is not None else None

    problemas = df.select(
        F.sum((F.col("duracion_min") <= 0).cast("int")).alias("duracion_cero_o_negativa"),
        F.sum((F.col("duracion_min") > 180).cast("int")).alias("duracion_mayor_3h"),
        F.sum((F.col("trip_distance") <= 0).cast("int")).alias("distancia_cero"),
        F.sum((F.col("trip_distance") > 100).cast("int")).alias("distancia_mayor_100_millas"),
        F.sum((F.col("fare_amount") < 0).cast("int")).alias("tarifa_negativa"),
        F.sum((F.year("tpep_pickup_datetime") != 2024).cast("int")).alias("fecha_fuera_de_2024"),
    ).first().asDict()

    return {"filas": n, "nulos": nulos, "estadisticas": stats, "problemas": problemas}


def duracion_por_grupo(df: DataFrame, columna: str) -> list[dict]:
    """Duración media y mediana del viaje agrupando por una columna
    (por ejemplo 'pu_borough' o una columna de hora creada antes)."""
    filas = (
        df.groupBy(columna)
        .agg(
            F.count("*").alias("viajes"),
            F.round(F.avg("duracion_min"), 2).alias("media_min"),
            F.round(F.percentile_approx("duracion_min", 0.5), 2).alias("mediana_min"),
        )
        .orderBy(F.desc("viajes"))
        .limit(30)
        .collect()
    )
    return [f.asDict() for f in filas]


# ---------------------------------------------------------------------------
# Limpieza
# ---------------------------------------------------------------------------

REGLAS_POR_DEFECTO = {
    "duracion_min_min": 1.0,
    "duracion_min_max": 180.0,
    "distancia_min": 0.1,
    "distancia_max": 100.0,
    "velocidad_max_mph": 80.0,
}


def limpiar_datos(df: DataFrame, reglas: dict | None = None) -> tuple[DataFrame, dict]:
    """Filtra viajes imposibles según unas reglas y devuelve cuántos se eliminan.

    Reglas admitidas (las que falten usan el valor por defecto):
    duracion_min_min, duracion_min_max, distancia_min, distancia_max, velocidad_max_mph.
    """
    r = {**REGLAS_POR_DEFECTO, **(reglas or {})}
    antes = df.count()

    velocidad = F.col("trip_distance") / (F.col("duracion_min") / 60.0)
    limpio = (
        df.filter(F.year("tpep_pickup_datetime") == 2024)
        .filter(F.col("duracion_min").between(r["duracion_min_min"], r["duracion_min_max"]))
        .filter(F.col("trip_distance").between(r["distancia_min"], r["distancia_max"]))
        .filter(velocidad <= r["velocidad_max_mph"])
        .fillna({"passenger_count": 1, "pu_borough": "Unknown", "do_borough": "Unknown"})
        .cache()
    )
    despues = limpio.count()
    return limpio, {
        "reglas": r,
        "filas_antes": antes,
        "filas_despues": despues,
        "eliminadas": antes - despues,
        "porcentaje_eliminado": round(100 * (antes - despues) / antes, 2),
    }


# ---------------------------------------------------------------------------
# Variables (features)
# ---------------------------------------------------------------------------

FEATURES_DISPONIBLES = {
    "trip_distance": "Distancia del viaje (millas)",
    "hora": "Hora de recogida (0-23)",
    "dia_semana": "Día de la semana (1=domingo ... 7=sábado)",
    "es_finde": "1 si es sábado o domingo",
    "hora_punta": "1 si es día laborable de 7-10h o 16-19h",
    "passenger_count": "Número de pasajeros",
    "es_aeropuerto": "1 si el origen o el destino es un aeropuerto",
    "mismo_barrio": "1 si origen y destino están en el mismo distrito (borough)",
    "PULocationID": "ID de zona de origen (1-265, numérico)",
    "DOLocationID": "ID de zona de destino (1-265, numérico)",
    "pu_borough": "Distrito de origen (categórica, se codifica one-hot)",
    "do_borough": "Distrito de destino (categórica, se codifica one-hot)",
}
CATEGORICAS = {"pu_borough", "do_borough"}


def crear_features(df: DataFrame) -> DataFrame:
    """Añade todas las columnas de FEATURES_DISPONIBLES que no vienen en los datos."""
    hora = F.hour("tpep_pickup_datetime")
    dia = F.dayofweek("tpep_pickup_datetime")
    es_finde = dia.isin(1, 7)
    return (
        df.withColumn("hora", hora)
        .withColumn("dia_semana", dia)
        .withColumn("es_finde", es_finde.cast("int"))
        .withColumn("hora_punta", ((~es_finde) & (hora.between(7, 9) | hora.between(16, 18))).cast("int"))
        .withColumn(
            "es_aeropuerto",
            (F.col("PULocationID").isin(ZONAS_AEROPUERTO) | F.col("DOLocationID").isin(ZONAS_AEROPUERTO)).cast("int"),
        )
        .withColumn("mismo_barrio", (F.col("pu_borough") == F.col("do_borough")).cast("int"))
    )


def guardar_procesado(df: DataFrame) -> str:
    """Guarda el dataset limpio y con features para que los entrenadores lo reutilicen."""
    df.write.mode("overwrite").parquet(str(DATOS_PROCESADOS))
    return str(DATOS_PROCESADOS.relative_to(RAIZ))


def cargar_procesado() -> DataFrame:
    """Carga el dataset que dejó preparado guardar_procesado."""
    if not DATOS_PROCESADOS.exists():
        raise FileNotFoundError("No hay datos procesados. Ejecuta antes: python scripts/cli.py preparar")
    return obtener_spark().read.parquet(str(DATOS_PROCESADOS))


# ---------------------------------------------------------------------------
# Entrenamiento y evaluación
# ---------------------------------------------------------------------------

MODELOS_DISPONIBLES = {
    "lineal": "Regresión lineal. Parámetros: regParam (0-1), elasticNetParam (0-1), maxIter",
    "random_forest": "Random Forest. Parámetros: numTrees, maxDepth (máx. 15), minInstancesPerNode, subsamplingRate",
    "gbt": "Gradient Boosted Trees. Parámetros: maxIter (nº de árboles), maxDepth (máx. 10), stepSize (0-1), subsamplingRate",
}


def _crear_modelo(tipo: str, params: dict):
    base = {"featuresCol": "features", "labelCol": "duracion_min"}
    if tipo == "lineal":
        return LinearRegression(**base, **params)
    if tipo == "random_forest":
        return RandomForestRegressor(**base, seed=SEMILLA, **params)
    if tipo == "gbt":
        return GBTRegressor(**base, seed=SEMILLA, **params)
    raise ValueError(f"Modelo desconocido: {tipo}. Opciones: {list(MODELOS_DISPONIBLES)}")


def dividir_train_test(df: DataFrame, fraccion_test: float = 0.2) -> tuple[DataFrame, DataFrame]:
    """Divide en entrenamiento y test (siempre igual gracias a la semilla)."""
    train, test = df.randomSplit([1 - fraccion_test, fraccion_test], seed=SEMILLA)
    return train.cache(), test.cache()


def entrenar_y_evaluar(
    train: DataFrame,
    test: DataFrame,
    tipo: str,
    features: list[str],
    params: dict | None = None,
) -> dict:
    """Entrena un modelo con las features indicadas y lo evalúa en test.

    Devuelve RMSE, MAE (error medio en minutos), R² y, en modelos de árboles,
    la importancia de cada feature.
    """
    params = params or {}
    desconocidas = set(features) - set(FEATURES_DISPONIBLES)
    if desconocidas:
        raise ValueError(f"Features desconocidas: {sorted(desconocidas)}")

    etapas, columnas_vector = [], []
    for f in features:
        if f in CATEGORICAS:
            etapas += [
                StringIndexer(inputCol=f, outputCol=f"{f}_idx", handleInvalid="keep"),
                OneHotEncoder(inputCol=f"{f}_idx", outputCol=f"{f}_ohe"),
            ]
            columnas_vector.append(f"{f}_ohe")
        else:
            columnas_vector.append(f)
    etapas.append(VectorAssembler(inputCols=columnas_vector, outputCol="features", handleInvalid="skip"))
    etapas.append(_crear_modelo(tipo, params))

    inicio = time.time()
    modelo = Pipeline(stages=etapas).fit(train)
    segundos = round(time.time() - inicio, 1)

    pred = modelo.transform(test)
    evaluar = lambda m: round(  # noqa: E731
        RegressionEvaluator(labelCol="duracion_min", predictionCol="prediction", metricName=m).evaluate(pred), 4
    )
    resultado = {
        "modelo": tipo,
        "params": params,
        "features": features,
        "rmse_min": evaluar("rmse"),
        "mae_min": evaluar("mae"),
        "r2": evaluar("r2"),
        "segundos_entrenamiento": segundos,
    }

    final = modelo.stages[-1]
    if hasattr(final, "featureImportances"):
        resultado["importancia_features"] = _importancias(modelo, pred, final.featureImportances, features)
    return resultado


def _importancias(modelo, pred: DataFrame, importancias, features: list[str]) -> dict:
    """Suma la importancia de las columnas one-hot para que salga una cifra por feature."""
    attrs = pred.schema["features"].metadata.get("ml_attr", {}).get("attrs", {})
    nombres = {a["idx"]: a["name"] for grupo in attrs.values() for a in grupo}
    total: dict[str, float] = {f: 0.0 for f in features}
    for idx, valor in enumerate(importancias.toArray()):
        nombre = nombres.get(idx, "")
        f = next((x for x in features if nombre == x or nombre.startswith(f"{x}_")), None)
        if f:
            total[f] += float(valor)
    return dict(sorted(((k, round(v, 4)) for k, v in total.items()), key=lambda kv: -kv[1]))
