"""Prueba rápida de las herramientas de Spark, sin agentes.

Uso:
    python scripts/probar_herramientas.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import herramientas_spark as hs  # noqa: E402


def mostrar(titulo, datos):
    print(f"\n=== {titulo} ===")
    print(json.dumps(datos, indent=2, ensure_ascii=False, default=str))


df = hs.cargar_datos(fraccion=0.02)
mostrar("Perfil de los datos", hs.perfilar_datos(df))

limpio, info = hs.limpiar_datos(df)
mostrar("Limpieza", info)

limpio = hs.crear_features(limpio)
mostrar("Duración por distrito de origen", hs.duracion_por_grupo(limpio, "pu_borough"))

train, test = hs.dividir_train_test(limpio)
features = ["trip_distance", "hora", "dia_semana", "hora_punta", "es_aeropuerto", "pu_borough", "do_borough"]

mostrar("Regresión lineal", hs.entrenar_y_evaluar(train, test, "lineal", features))
mostrar(
    "Random Forest",
    hs.entrenar_y_evaluar(train, test, "random_forest", features, {"numTrees": 30, "maxDepth": 8}),
)
