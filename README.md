# practica_agentes

Equipo de **subagentes de Claude Code** que construye y compara modelos de predicción con **Spark MLlib**.

**Problema:** predecir la duración de los viajes en taxi amarillo de Nueva York (datos oficiales de la NYC TLC, enero-marzo 2024, ~9,5 millones de viajes).

## El equipo

| Agente | Papel |
|---|---|
| Orquestador (`/construir-modelo`) | Reparte el trabajo entre los subagentes y decide |
| `explorador` | Analiza los datos, detecta problemas y propone limpieza y variables |
| `preparador` | Limpia los datos y genera el dataset con las variables |
| `entrenador` ×3 (en paralelo) | Cada uno ajusta un modelo: regresión lineal, Random Forest y Gradient Boosting |
| `evaluador` | Compara los experimentos y escribe el informe final |

Los subagentes no escriben código de Spark: usan las herramientas de `scripts/cli.py`, que devuelven JSON.

```
explorador ──► preparador ──┬──► entrenador (lineal)        ──┐
                            ├──► entrenador (random_forest) ──┼──► evaluador ──► informes/informe_final.md
                            └──► entrenador (gbt)           ──┘
```

## Puesta en marcha

Requiere Python 3.10+ (recomendado 3.12) y Java 17+ (para Spark).

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python scripts/descargar_datos.py
```

Con [uv](https://docs.astral.sh/uv/) (descarga Python 3.12 automáticamente):

```bash
uv venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
uv pip install -r requirements.txt
python scripts/descargar_datos.py
```

Los datos se guardan en `data/raw/` y no se suben a git.

## Uso

Abre la carpeta con Claude Code (terminal o extensión de VS Code) y ejecuta:

```
/construir-modelo
```

Opcionalmente indica la fracción de datos: `/construir-modelo 0.1` (10 %).

También se pueden usar las herramientas a mano:

```bash
python scripts/cli.py info
python scripts/cli.py perfilar
python scripts/cli.py preparar
python scripts/cli.py entrenar --modelo gbt --features trip_distance,hora,pu_borough,do_borough
python scripts/cli.py resultados
```
