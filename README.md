# practica_agentes

Equipo de agentes (Claude) que construye y compara modelos de predicción con **Spark MLlib**.

**Problema:** predecir la duración de los viajes en taxi amarillo de Nueva York (datos oficiales de la NYC TLC, enero-marzo 2024, ~9,5 millones de viajes).

## Puesta en marcha

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/descargar_datos.py
```

Requiere Java (para Spark). Los datos se guardan en `data/raw/` y no se suben a git.
