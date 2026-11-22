# Guía de La Candelaria

App web que reconoce sitios del centro histórico de Bogotá a partir de una foto, usando un modelo de clasificación entrenado en Azure Custom Vision (dominio Landmarks), y muestra una descripción de cada sitio.

- Pestaña **Una foto**: sube o toma una foto y obtén el sitio, la confianza y su descripción.
- Pestaña **Evaluar un lote (ZIP)**: calcula precisión, recall, F1, matriz de confusión y curvas ROC.

Las llaves de Azure se configuran en los *Secrets* de Streamlit (`CV_PREDICTION_ENDPOINT`, `CV_PREDICTION_KEY`, `CV_PROJECT_ID`, `CV_PUBLISH_NAME`).
