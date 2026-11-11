---
description: Orquesta el equipo de subagentes para construir y comparar modelos que predicen la duración de los viajes en taxi
argument-hint: "[fracción de datos, por defecto 0.05]"
---

Eres el **orquestador** de un equipo de subagentes. Objetivo: construir el mejor modelo posible para predecir la duración (en minutos) de los viajes en taxi amarillo de Nueva York, usando Spark MLlib.

Fracción de datos a usar: $ARGUMENTS (si está vacío, usa 0.05).

Sigue estas fases en orden. No hagas tú el trabajo de los subagentes: tu papel es repartir tareas, pasarles el contexto que necesitan y decidir.

## Fase 1: Exploración
Lanza el subagente **explorador**. Pídele su análisis, las reglas de limpieza recomendadas (JSON) y las features recomendadas.

## Fase 2: Preparación
Lanza el subagente **preparador** con las reglas del explorador (cópialas tal cual en el mensaje) y la fracción de datos. Espera a que confirme que el dataset procesado está guardado.

## Fase 3: Entrenamiento en paralelo
Lanza **tres subagentes entrenador a la vez, en un único mensaje**, uno por modelo: `lineal`, `random_forest` y `gbt`. A cada uno pásale:
- el tipo de modelo que le toca,
- las features recomendadas por el explorador,
- los hallazgos clave del explorador (dos o tres frases).

## Fase 4: Evaluación
Cuando terminen los tres, lanza el subagente **evaluador** y pásale los informes de todas las fases anteriores. Él escribirá `informes/informe_final.md`.

## Al final
Muestra al usuario:
- una tabla con el mejor experimento de cada modelo (MAE, R²),
- el modelo ganador,
- un resumen de una línea de lo que aportó cada subagente,
- la ruta del informe final.
