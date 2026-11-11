# Informe final: predicción de la duración de viajes en taxi (NYC TLC, enero-marzo 2024)

## 1. Resumen

El mejor modelo es **gbt_v4**: un Gradient Boosted Trees de Spark MLlib con 60 iteraciones, profundidad 8 y stepSize 0,2. Se equivoca de media en **3,2 minutos** por viaje (MAE 3,21; RMSE 5,27; R² 0,81). En la práctica, si un viaje dura 15 minutos, el modelo suele predecir entre unos 12 y unos 18 minutos. Explica alrededor del 81 % de la variación en la duración de los viajes. Comete un 32 % menos de error que la regresión lineal y un 8 % menos que el mejor random forest, y se entrena en unos 36 segundos.

## 2. Datos y limpieza

- **Fuente**: viajes de taxi amarillo de NYC TLC de enero a marzo de 2024, con una muestra del **5 %** (fracción 0,05).
- **Filas en bruto**: 477.769.
- **Problemas detectados por el explorador**:
  - 7,84 % de nulos en passenger_count y RatecodeID.
  - 2,28 % de viajes con distancia 0.
  - 1,44 % de viajes con tarifa negativa.
  - Valores extremos: duraciones de hasta 9.455 minutos y distancias de hasta 35.547 millas.
- **Reglas de limpieza aplicadas** (las recomendadas, sin cambios):

| Regla | Valor |
|---|---|
| Duración mínima | 1 min |
| Duración máxima | 120 min |
| Distancia mínima | 0,1 millas |
| Distancia máxima | 60 millas |
| Velocidad máxima | 60 mph |

- **Resultado**: de 477.769 a **464.206 filas**. Se eliminaron 13.563 filas (el 2,84 %). El dataset limpio está en `data/procesado/viajes.parquet`.
- **Incidencias**:
  - Las tarifas negativas no se filtran de forma explícita porque la CLI no tiene una regla para ello. Una parte probablemente cae con las demás reglas.
  - Cuando falta passenger_count, se imputa con 1.

**Hallazgos de la exploración que guiaron las features**:
- Los viajes entre distritos distintos duran casi 3 veces más que los que se quedan en el mismo distrito (36,4 frente a 13,2 min de media).
- Los viajes de aeropuerto también duran mucho más (35,9 frente a 14,1 min).
- La hora tiene un efecto no lineal: 12,5 min de media a las 3 h frente a 18,7 min a las 15 h.
- hora_punta y passenger_count aportan poca señal.

**Conjuntos de features**:
- **Base** (todos los modelos): trip_distance, mismo_barrio, es_aeropuerto, pu_borough, do_borough, hora, dia_semana.
- **F10** (modelos de árboles): la base más PULocationID, DOLocationID y es_finde.

## 3. Comparación de modelos

Todos los experimentos ordenados por MAE (minutos). Todos se evaluaron con la misma partición de test.

| Nombre | Modelo | Parámetros | Features | MAE | RMSE | R² | Segundos |
|---|---|---|---|---|---|---|---|
| **gbt_v4** | GBT | maxIter 60, maxDepth 8, stepSize 0,2 | F10 | **3,208** | **5,272** | **0,814** | 35,8 |
| gbt_v5 | GBT | maxIter 60, maxDepth 8, stepSize 0,2 | F10 + hora_punta + passenger_count | 3,222 | 5,288 | 0,813 | 35,5 |
| gbt_v3 | GBT | maxIter 60, maxDepth 8, stepSize 0,1 | F10 | 3,246 | 5,275 | 0,814 | 35,8 |
| gbt_v2 | GBT | maxIter 30, maxDepth 8, stepSize 0,1 | F10 | 3,352 | 5,401 | 0,805 | 20,3 |
| random_forest_v5 | Random forest | numTrees 30, maxDepth 12, minInstancesPerNode 10 | F10 + hora_punta | 3,491 | 5,542 | 0,795 | 21,3 |
| random_forest_v4 | Random forest | numTrees 30, maxDepth 12 | F10 + hora_punta | 3,494 | 5,544 | 0,795 | 21,2 |
| random_forest_v2 | Random forest | numTrees 30, maxDepth 12 | F10 | 3,548 | 5,609 | 0,790 | 22,8 |
| gbt_v1 | GBT | maxIter 30, maxDepth 5, stepSize 0,1 | F10 | 3,550 | 5,643 | 0,787 | 12,6 |
| random_forest_v3 | Random forest | numTrees 60, maxDepth 12 | F10 | 3,579 | 5,620 | 0,789 | 39,9 |
| random_forest_v1 | Random forest | numTrees 30, maxDepth 8 | F10 | 3,841 | 5,984 | 0,761 | 11,4 |
| lineal_v5 | Regresión lineal | regParam 0, elasticNet 0 | Base + hora_punta + es_finde + passenger_count | 4,715 | 6,969 | 0,676 | 4,4 |
| lineal_v4 | Regresión lineal | regParam 0, elasticNet 0 | Base + hora_punta + es_finde | 4,715 | 6,969 | 0,676 | 4,3 |
| lineal_v3 | Regresión lineal | regParam 0,01, elasticNet 0 | Base + hora_punta + es_finde | 4,717 | 6,969 | 0,676 | 3,8 |
| lineal_v2 | Regresión lineal | regParam 0,01, elasticNet 0 | Base + hora_punta | 4,725 | 6,985 | 0,674 | 3,0 |
| lineal_v1 | Regresión lineal | regParam 0,01, elasticNet 0 | Base | 4,755 | 7,032 | 0,670 | 4,0 |

### El mejor experimento de cada familia

| Familia | Mejor experimento | MAE | RMSE | R² | Segundos |
|---|---|---|---|---|---|
| GBT | gbt_v4 | 3,208 | 5,272 | 0,814 | 35,8 |
| Random forest | random_forest_v5 | 3,491 | 5,542 | 0,795 | 21,3 |
| Regresión lineal | lineal_v4 | 4,715 | 6,969 | 0,676 | 4,3 |

(lineal_v5 tiene un MAE 0,0002 menor que lineal_v4, pero usa una variable más. Esa diferencia es despreciable, así que se elige el modelo más sencillo.)

### El modelo ganador y por qué

Se elige **gbt_v4** por estos motivos:

- **Gana en las tres métricas.** Tiene el MAE más bajo, el RMSE más bajo y el R² más alto. No hay compromiso entre errores típicos y errores grandes.
- **La mejora es clara frente a las otras familias.**
  - Frente al mejor random forest: -0,28 min de MAE (-8 %) y -0,27 de RMSE, con 15 segundos más de entrenamiento.
  - Frente a la regresión lineal: -1,51 min de MAE (-32 %) y +0,14 de R².
  - Son diferencias mucho mayores que las que hay entre variantes de una misma familia, así que el modelo más complejo está justificado.
- **El coste es asumible.** Unos 36 segundos de entrenamiento con el 5 % de los datos.
- **Hay matices dentro de la familia GBT:**
  - gbt_v4, gbt_v5 y gbt_v3 están prácticamente empatados: 0,04 min de MAE entre ellos y el RMSE casi igual (5,272 frente a 5,275). Con una sola partición y una sola semilla, no se puede afirmar que stepSize 0,2 sea mejor que 0,1.
  - Lo que sí es claro: pasar de profundidad 5 a 8 reduce el MAE en 0,20 min, y pasar de 30 a 60 iteraciones lo reduce en 0,11 min.
  - Si se necesitara entrenar más rápido, **gbt_v2** (20 s, MAE 3,35) sigue superando a todos los random forest y tarda lo mismo que ellos.
- **Variables que no ayudaron:**
  - En GBT, añadir hora_punta y passenger_count (gbt_v5) no mejoró nada.
  - En random forest, la mejora atribuida a hora_punta (de v2 a v4) no se debe a esa variable, que tiene importancia 0. Lo más probable es que venga del muestreo aleatorio de features. Además, 60 árboles (v3) no mejoraron a 30.

## 4. Qué variables importan

Importancia de cada variable en el modelo ganador y en el mejor random forest:

| Variable | gbt_v4 | random_forest_v5 |
|---|---|---|
| trip_distance | 0,607 | 0,511 |
| hora | 0,123 | 0,067 |
| DOLocationID | 0,063 | 0,008 |
| PULocationID | 0,062 | 0,018 |
| do_borough | 0,037 | 0,058 |
| dia_semana | 0,033 | 0,010 |
| pu_borough | 0,033 | 0,111 |
| es_finde | 0,016 | 0,007 |
| es_aeropuerto | 0,015 | 0,061 |
| mismo_barrio | 0,011 | 0,150 |
| hora_punta | (no se usó) | 0,000 |

Lectura:

- **La distancia domina.** Explica entre la mitad y el 60 % de la importancia en los dos modelos, como era de esperar.
- **La hora es la segunda variable en GBT (0,12).** Esto confirma el patrón no lineal que vio el explorador. Los árboles lo capturan bien y la regresión lineal no, y esa es una de las razones de la diferencia entre ambos.
- **La geografía pesa mucho en total**, pero cada modelo la usa de forma distinta:
  - El random forest se apoya en variables gruesas: mismo_barrio, pu_borough y es_aeropuerto.
  - El GBT aprovecha las zonas concretas de origen y destino (PULocationID y DOLocationID), que tienen más detalle. Eso le permite afinar más.
- **Variables irrelevantes**: hora_punta tiene importancia 0 (su información ya está en hora) y passenger_count apenas aporta (0,007 en gbt_v5).

Nota: las importancias de los árboles reparten el mérito entre variables relacionadas entre sí (por ejemplo, borough y LocationID, o mismo_barrio y es_aeropuerto). Indican qué usa el modelo, no causalidad.

## 5. Conclusiones y próximos pasos

### Conclusiones

- Con las variables disponibles, **GBT es el mejor modelo**: unos 3,2 minutos de error medio y un R² de 0,81.
- La regresión lineal se queda en 4,7 minutos. Está agotada con la CLI actual: sus cinco variantes quedan a 0,04 min unas de otras.
- La mayor parte de la mejora viene de la capacidad del modelo (profundidad e iteraciones). Añadir variables débiles no ha ayudado.

### Limitaciones

- Solo se ha usado el **5 % de los datos** y **una única partición de train/test con una sola semilla**. Las diferencias menores de unos 0,05 min (gbt_v3, v4 y v5; random_forest_v4 y v5; las variantes lineales) no deben considerarse significativas.
- Las **tarifas negativas no se filtran** de forma explícita. Puede haber algún registro anómalo en el conjunto limpio.
- El RMSE (5,3) es bastante mayor que el MAE (3,2). Eso indica que todavía hay errores grandes en algunos viajes, probablemente por atascos, incidencias o datos dudosos que el modelo no puede ver.
- La CLI no ofrece los coeficientes de la regresión lineal, así que ese modelo no se puede interpretar.

### Próximos pasos

1. **Validar al ganador** con más datos (fracción 0,2 o 1,0) y validación cruzada o varias semillas, para confirmar el orden gbt_v4 ≈ gbt_v3 > random forest.
2. **Ajustar más el GBT**: subsamplingRate 0,8, maxDepth 9-10 y más iteraciones con stepSize 0,1, vigilando el sobreajuste.
3. **Crear nuevas features** (habría que añadirlas en `src/herramientas_spark.py` y exponerlas en la CLI):
   - el par origen-destino o la duración media histórica por par de zonas;
   - la hora en codificación cíclica;
   - interacciones de la distancia con el distrito.
4. **Mejorar la limpieza**: añadir una regla para eliminar tarifas negativas o nulas.
5. **Probar otras pérdidas u objetivos**: el logaritmo de la duración o la pérdida Huber, para reducir el efecto de los viajes extremos sobre el RMSE.
6. **Dar más opciones a la CLI**: devolver los coeficientes de la regresión lineal y el error por tramo de distancia o distrito, para saber dónde falla el modelo.
