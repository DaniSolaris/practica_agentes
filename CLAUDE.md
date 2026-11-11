# practica_agentes

Equipo de subagentes de Claude Code que construye y compara modelos de predicción con Spark MLlib.
Problema: predecir la duración (minutos) de los viajes en taxi amarillo de Nueva York (NYC TLC, enero-marzo 2024).

## Cómo se ejecuta

Desde Claude Code, en la carpeta del proyecto: `/construir-modelo` (o `/construir-modelo 0.1` para usar el 10 % de los datos).

## Python

Usa siempre el Python del entorno virtual del proyecto:
- Linux / Mac: `.venv/bin/python`
- Windows: `.venv\Scripts\python.exe`

Cuando las instrucciones de un agente digan `python scripts/cli.py ...`, sustituye `python` por el de arriba.
Si no existe `.venv` o faltan los datos en `data/raw/`, sigue la "Puesta en marcha" del README antes de nada.

## Estructura

- `src/herramientas_spark.py`: toda la lógica de Spark (carga, limpieza, features, entrenamiento).
- `scripts/cli.py`: línea de comandos sobre esas herramientas; los subagentes solo usan esto. Todo sale en JSON.
- `scripts/descargar_datos.py`: descarga los datos a `data/raw/` (no se sube a git).
- `.claude/agents/`: subagentes `explorador`, `preparador`, `entrenador` y `evaluador`.
- `.claude/commands/construir-modelo.md`: el orquestador que coordina a los subagentes.
- `resultados/`: un JSON por experimento. `informes/`: informe final.

## Reglas

- Los subagentes no escriben código de Spark propio: usan `scripts/cli.py`. Si falta una capacidad, se añade en `src/herramientas_spark.py` y se expone en la CLI.
- Varios entrenamientos en paralelo: limitar recursos con `SPARK_CORES=1 SPARK_MEMORIA=2g`.
