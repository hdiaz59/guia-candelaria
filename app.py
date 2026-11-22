"""Guía de La Candelaria: reconoce sitios del centro histórico de Bogotá con Azure Custom Vision.

Ejecutar:  .venv/bin/streamlit run app.py
Llaves: archivo .env (local) o st.secrets (Streamlit Community Cloud).
"""
import io, json, os, zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

AQUI = Path(__file__).parent
EXT = (".jpg", ".jpeg", ".png", ".bmp")
INFO = json.loads((AQUI / "sitios_info.json").read_text(encoding="utf-8"))

st.set_page_config(page_title="Guía de La Candelaria", page_icon="🏛️", layout="centered")


# ---------- conexión con Custom Vision ----------
def config(nombre):
    try:
        if nombre in st.secrets:
            return st.secrets[nombre]
    except Exception:
        pass
    return os.environ.get(nombre)


@st.cache_resource
def cliente():
    from dotenv import load_dotenv
    from msrest.authentication import ApiKeyCredentials
    from azure.cognitiveservices.vision.customvision.prediction import CustomVisionPredictionClient
    load_dotenv(AQUI / ".env")
    return CustomVisionPredictionClient(
        config("CV_PREDICTION_ENDPOINT"),
        ApiKeyCredentials(in_headers={"Prediction-key": config("CV_PREDICTION_KEY")}))


def predecir(datos: bytes) -> dict:
    """Devuelve {etiqueta: probabilidad} ordenado de mayor a menor."""
    r = cliente().classify_image(config("CV_PROJECT_ID"), config("CV_PUBLISH_NAME"), datos)
    return dict(sorted(((p.tag_name, p.probability) for p in r.predictions), key=lambda x: -x[1]))


def preparar(datos: bytes) -> bytes:
    """Reduce fotos grandes de celular para respetar el límite de 4 MB."""
    if len(datos) <= 3_500_000:
        return datos
    from PIL import Image, ImageOps
    im = ImageOps.exif_transpose(Image.open(io.BytesIO(datos))).convert("RGB")
    im.thumbnail((1600, 1600))
    buf = io.BytesIO(); im.save(buf, "JPEG", quality=85)
    return buf.getvalue()


def nombre(tag):
    return INFO.get(tag, {}).get("nombre", tag)


def leer_en_voz_alta(texto):
    texto_js = json.dumps(texto)
    components.html(f"""
    <button id="b" style="font-size:16px;padding:8px 14px;border-radius:8px;border:1px solid #888;cursor:pointer">
      🔊 Escuchar descripción</button>
    <script>
    document.getElementById('b').onclick = () => {{
      speechSynthesis.cancel();
      const u = new SpeechSynthesisUtterance({texto_js});
      u.lang = 'es-CO'; u.rate = 0.95;
      speechSynthesis.speak(u);
    }};
    </script>""", height=50)


# ---------- interfaz ----------
st.title("🏛️ Guía de La Candelaria")
st.write("Toma o sube una foto de un sitio del centro histórico de Bogotá y te diré qué es.")

with st.sidebar:
    st.header("Ajustes")
    umbral = st.slider("Confianza mínima para responder", 0.3, 0.95, 0.6, 0.05,
                       help="Si la confianza es menor, la app responde «no reconozco este lugar».")
    st.caption("Modelo: Azure Custom Vision, dominio Landmarks.")
    st.subheader("Sitios que reconoce")
    st.markdown("\n".join(f"- {INFO[t]['nombre']}" for t in
                          ["catedral_primada", "capitolio", "plaza_bolivar", "casa_narino",
                           "palacio_lievano", "san_francisco"]))

tab_foto, tab_lote = st.tabs(["📷 Una foto", "🗂️ Evaluar un lote (ZIP)"])

with tab_foto:
    origen = st.radio("¿Cómo quieres agregar la foto?", ["Subir archivo", "Usar la cámara"], horizontal=True)
    archivo = (st.file_uploader("Foto del sitio", type=["jpg", "jpeg", "png", "bmp"])
               if origen == "Subir archivo" else st.camera_input("Toma la foto"))

    if archivo:
        datos = archivo.getvalue()
        st.image(datos, use_container_width=True)
        with st.spinner("Analizando la foto..."):
            probs = predecir(preparar(datos))
        tag, conf = next(iter(probs.items()))

        if conf < umbral or tag == "otro_lugar":
            st.warning(f"**No reconozco este lugar.** {INFO['otro_lugar']['descripcion']}")
            if tag != "otro_lugar":
                st.caption(f"Lo más parecido: {nombre(tag)} ({conf:.0%}), por debajo del umbral de {umbral:.0%}.")
        else:
            sitio = INFO[tag]
            st.success(f"### {sitio['nombre']}\nConfianza: **{conf:.0%}**")
            st.write(sitio["descripcion"])
            if sitio["dato_curioso"]:
                st.info(f"💡 {sitio['dato_curioso']}")
            leer_en_voz_alta(f"{sitio['nombre']}. {sitio['descripcion']} {sitio['dato_curioso']}")

        with st.expander("Ver todas las probabilidades"):
            df = pd.DataFrame({"Sitio": [nombre(t) for t in probs], "Probabilidad": list(probs.values())})
            st.bar_chart(df.set_index("Sitio"), horizontal=True)

with tab_lote:
    st.write("Sube un ZIP con fotos. Si las fotos están en **carpetas con el nombre del sitio** "
             "(por ejemplo `capitolio/foto1.jpg`), la app calcula precisión, recall, F1, "
             "la matriz de confusión y las curvas ROC.")
    with st.expander("Nombres de carpeta válidos"):
        st.code("\n".join(INFO.keys()))
    zip_file = st.file_uploader("Archivo ZIP", type=["zip"], key="zip")

    if zip_file and st.button("Analizar lote", type="primary"):
        z = zipfile.ZipFile(io.BytesIO(zip_file.getvalue()))
        fotos = [n for n in z.namelist()
                 if n.lower().endswith(EXT) and not Path(n).name.startswith(".") and "__MACOSX" not in n]
        if not fotos:
            st.error("El ZIP no tiene fotos .jpg, .png o .bmp.")
            st.stop()
        filas, barra = [], st.progress(0.0, text="Analizando fotos...")
        for i, n in enumerate(fotos):
            probs = predecir(preparar(z.read(n)))
            tag, conf = next(iter(probs.items()))
            carpeta = Path(n).parent.name
            filas.append({"archivo": n, "real": carpeta if carpeta in INFO else None,
                          "predicha": tag, "confianza": conf,
                          "respuesta": nombre(tag) if conf >= umbral and tag != "otro_lugar" else "No reconocido",
                          **{f"p_{t}": p for t, p in probs.items()}})
            barra.progress((i + 1) / len(fotos), text=f"Analizando fotos... {i + 1}/{len(fotos)}")
        barra.empty()
        df = pd.DataFrame(filas)
        st.session_state["lote"] = df

    if "lote" in st.session_state:
        df = st.session_state["lote"]
        st.subheader(f"Resultados de {len(df)} fotos")
        st.dataframe(df[["archivo", "real", "predicha", "confianza", "respuesta"]],
                     use_container_width=True, hide_index=True,
                     column_config={"confianza": st.column_config.ProgressColumn(format="%.2f", min_value=0, max_value=1)})
        st.download_button("Descargar resultados (CSV)", df.to_csv(index=False).encode("utf-8"),
                           "resultados_lote.csv", "text/csv")

        clases = sorted(c[2:] for c in df.columns if c.startswith("p_"))
        con_carpeta = df.dropna(subset=["real"])
        etiquetadas = con_carpeta[con_carpeta["real"].isin(clases)]
        if len(etiquetadas):
            import matplotlib.pyplot as plt
            from sklearn.metrics import (accuracy_score, classification_report, confusion_matrix,
                                         ConfusionMatrixDisplay, roc_curve, auc)
            from sklearn.preprocessing import label_binarize

            y, yp = etiquetadas["real"], etiquetadas["predicha"]
            st.subheader("Métricas")
            fuera = len(con_carpeta) - len(etiquetadas)
            if fuera:
                st.caption(f"{fuera} fotos son de sitios que este modelo aún no reconoce "
                           f"({', '.join(sorted(set(con_carpeta['real']) - set(clases)))}); no cuentan en las métricas.")
            c1, c2 = st.columns(2)
            c1.metric("Exactitud", f"{accuracy_score(y, yp):.1%}")
            rep = classification_report(y, yp, labels=clases, output_dict=True, zero_division=0)
            c2.metric("F1 macro", f"{rep['macro avg']['f1-score']:.2f}")
            tabla = pd.DataFrame({nombre(c): rep[c] for c in clases if rep[c]["support"] > 0}).T
            tabla = tabla.rename(columns={"precision": "Precisión", "recall": "Recall",
                                          "f1-score": "F1", "support": "Fotos"})
            st.dataframe(tabla.style.format({"Precisión": "{:.2f}", "Recall": "{:.2f}", "F1": "{:.2f}", "Fotos": "{:.0f}"}),
                         use_container_width=True)

            fig, ax = plt.subplots(figsize=(7, 6))
            presentes = [c for c in clases if c in set(y) | set(yp)]
            ConfusionMatrixDisplay(confusion_matrix(y, yp, labels=presentes),
                                   display_labels=[nombre(c) for c in presentes]).plot(
                ax=ax, xticks_rotation=60, colorbar=False, cmap="Blues")
            ax.set_title("Matriz de confusión"); fig.tight_layout()
            st.pyplot(fig)

            P = etiquetadas[[f"p_{c}" for c in clases]].fillna(0).to_numpy()
            Y = label_binarize(y, classes=clases)
            fig, ax = plt.subplots(figsize=(7, 6))
            aucs = []
            for i, c in enumerate(clases):
                if 0 < Y[:, i].sum() < len(Y):
                    fpr, tpr, _ = roc_curve(Y[:, i], P[:, i]); a = auc(fpr, tpr); aucs.append(a)
                    ax.plot(fpr, tpr, label=f"{nombre(c)} (AUC {a:.2f})")
            if aucs:
                ax.plot([0, 1], [0, 1], "k--", lw=1)
                ax.set_xlabel("Tasa de falsos positivos"); ax.set_ylabel("Tasa de verdaderos positivos")
                ax.set_title(f"Curvas ROC (AUC promedio {np.mean(aucs):.2f})"); ax.legend(fontsize=8)
                fig.tight_layout(); st.pyplot(fig)
            else:
                st.caption("Las curvas ROC necesitan fotos de al menos dos sitios distintos.")
        else:
            st.caption("Las fotos no estaban en carpetas con nombre de sitio, así que solo se muestran las predicciones.")
