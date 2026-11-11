"""Línea de comandos para las herramientas de Spark.

Es la forma en que los subagentes de Claude Code usan Spark: ejecutan un
comando y leen el resultado en JSON.

Comandos:
    python scripts/cli.py info
    python scripts/cli.py perfilar [--fraccion 0.05]
    python scripts/cli.py agrupar --columna pu_borough [--fraccion 0.05]
    python scripts/cli.py preparar [--fraccion 0.05] [--reglas '{"duracion_min_max": 120}']
    python scripts/cli.py entrenar --modelo gbt --features trip_distance,hora,pu_borough \\
                                   [--params '{"maxDepth": 6}'] [--nombre gbt_v1]
    python scripts/cli.py resultados
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import herramientas_spark as hs  # noqa: E402

RESULTADOS = hs.RAIZ / "resultados"


def imprimir(datos) -> None:
    print(json.dumps(datos, indent=2, ensure_ascii=False, default=str))


def cmd_info(_args) -> None:
    imprimir({
        "features_disponibles": hs.FEATURES_DISPONIBLES,
        "modelos_disponibles": hs.MODELOS_DISPONIBLES,
        "reglas_limpieza_por_defecto": hs.REGLAS_POR_DEFECTO,
        "datos_procesados_listos": hs.DATOS_PROCESADOS.exists(),
    })


def cmd_perfilar(args) -> None:
    imprimir(hs.perfilar_datos(hs.cargar_datos(args.fraccion)))


def cmd_agrupar(args) -> None:
    df = hs.crear_features(hs.cargar_datos(args.fraccion))
    imprimir(hs.duracion_por_grupo(df, args.columna))


def cmd_preparar(args) -> None:
    reglas = json.loads(args.reglas) if args.reglas else None
    limpio, info = hs.limpiar_datos(hs.cargar_datos(args.fraccion), reglas)
    info["fraccion"] = args.fraccion
    info["guardado_en"] = hs.guardar_procesado(hs.crear_features(limpio))
    imprimir(info)


def cmd_entrenar(args) -> None:
    features = [f.strip() for f in args.features.split(",") if f.strip()]
    params = json.loads(args.params) if args.params else {}
    train, test = hs.dividir_train_test(hs.cargar_procesado())
    resultado = hs.entrenar_y_evaluar(train, test, args.modelo, features, params)

    nombre = args.nombre or f"{args.modelo}_{datetime.now():%H%M%S}"
    resultado["nombre"] = nombre
    resultado["fecha"] = datetime.now().isoformat(timespec="seconds")
    RESULTADOS.mkdir(exist_ok=True)
    (RESULTADOS / f"{nombre}.json").write_text(json.dumps(resultado, indent=2, ensure_ascii=False))
    imprimir(resultado)


def cmd_resultados(_args) -> None:
    filas = []
    for f in sorted(RESULTADOS.glob("*.json")):
        r = json.loads(f.read_text())
        filas.append({k: r.get(k) for k in ("nombre", "modelo", "mae_min", "rmse_min", "r2", "params", "features")})
    imprimir(sorted(filas, key=lambda r: r["mae_min"] if r["mae_min"] is not None else 1e9))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="comando", required=True)

    sub.add_parser("info", help="Features, modelos y reglas disponibles").set_defaults(func=cmd_info)

    p = sub.add_parser("perfilar", help="Resumen y problemas de los datos en bruto")
    p.add_argument("--fraccion", type=float, default=0.05)
    p.set_defaults(func=cmd_perfilar)

    p = sub.add_parser("agrupar", help="Duración media agrupada por una columna")
    p.add_argument("--columna", required=True)
    p.add_argument("--fraccion", type=float, default=0.05)
    p.set_defaults(func=cmd_agrupar)

    p = sub.add_parser("preparar", help="Limpia, crea features y guarda el dataset procesado")
    p.add_argument("--fraccion", type=float, default=0.05)
    p.add_argument("--reglas", help="JSON con reglas de limpieza")
    p.set_defaults(func=cmd_preparar)

    p = sub.add_parser("entrenar", help="Entrena y evalúa un modelo con los datos procesados")
    p.add_argument("--modelo", required=True, choices=list(hs.MODELOS_DISPONIBLES))
    p.add_argument("--features", required=True, help="Lista separada por comas")
    p.add_argument("--params", help="JSON con hiperparámetros")
    p.add_argument("--nombre", help="Nombre del experimento (fichero en resultados/)")
    p.set_defaults(func=cmd_entrenar)

    sub.add_parser("resultados", help="Tabla de todos los experimentos, ordenada por MAE").set_defaults(
        func=cmd_resultados
    )

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
