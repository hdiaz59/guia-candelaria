"""Guía de La Candelaria: reconoce sitios del centro histórico de Bogotá con Azure Custom Vision.

Ejecutar:  .venv/bin/streamlit run app.py
Llaves: archivo .env (local) o st.secrets (Streamlit Community Cloud).
"""
import base64, html, io, json, os, zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

AQUI = Path(__file__).parent
EXT = (".jpg", ".jpeg", ".png", ".bmp")
INFO = json.loads((AQUI / "sitios_info.json").read_text(encoding="utf-8"))
FOTOS = AQUI / "assets"
CREDITOS = json.loads((FOTOS / "creditos_fotos.json").read_text(encoding="utf-8"))
RECORRIDO = ["catedral_primada", "capitolio", "plaza_bolivar", "palacio_lievano", "casa_narino", "san_francisco"]
UBICACION = {
    "catedral_primada": "Plaza de Bolívar · costado oriental",
    "capitolio": "Plaza de Bolívar · costado sur",
    "plaza_bolivar": "Carrera 7 con calle 10",
    "palacio_lievano": "Plaza de Bolívar · costado occidental",
    "casa_narino": "Carrera 8 con calle 7",
    "san_francisco": "Avenida Jiménez con carrera 7",
}

st.set_page_config(page_title="Guía de La Candelaria", page_icon="🏛️", layout="wide",
                   initial_sidebar_state="collapsed")


# ---------- estilo ----------
@st.cache_data
def foto_b64(nombre):
    ruta = FOTOS / f"{nombre}.jpg"
    return base64.b64encode(ruta.read_bytes()).decode() if ruta.exists() else ""


COLORES = ["#2E9B4E", "#D7263D", "#E86A92", "#2B59C3", "#5BC0EB", "#F29E38"]
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600&family=Source+Sans+3:wght@600;700;800&display=swap');
:root {{ --acento:#D81B60; --texto:#1F2328; --suave:#5F6670; --fondo-suave:#F6F4F1; }}
html, body, [class*="css"], .stMarkdown, p, li, label {{ font-family:'Poppins', sans-serif; }}
h1, h2, h3, .titulo {{ font-family:'Source Sans 3', sans-serif !important; }}
[data-testid="stHeader"] {{ background:transparent; }}
[data-testid="stAppViewBlockContainer"], .block-container {{ padding-top:0 !important; max-width:1120px; }}
.hero {{ position:relative; width:100vw; margin-left:calc(50% - 50vw); height:440px;
  background:linear-gradient(180deg, rgba(0,0,0,.05) 35%, rgba(0,0,0,.65) 100%), url('data:image/jpeg;base64,{foto_b64("hero")}') center 40%/cover no-repeat;
  display:flex; align-items:flex-end; }}
.hero-in {{ max-width:1120px; width:100%; margin:0 auto; padding:0 1.5rem 2.2rem; color:#fff; }}
.miga {{ font-size:.78rem; letter-spacing:.06em; text-transform:uppercase; opacity:.9; margin-bottom:.6rem; }}
.hero h1 {{ font-size:3.2rem; font-weight:800; line-height:1.05; margin:0 0 .8rem; color:#fff; text-shadow:0 2px 12px rgba(0,0,0,.35); }}
.chips span {{ display:inline-block; font-weight:600; font-size:.9rem; margin-right:1.2rem; text-transform:uppercase; letter-spacing:.03em; }}
.franja {{ width:100vw; margin-left:calc(50% - 50vw); height:7px; display:flex; }}
.franja i {{ flex:1; }}
.intro {{ font-size:1.05rem; color:var(--suave); max-width:760px; margin:1.8rem 0 .4rem; }}
.seccion {{ font-size:1.9rem; font-weight:800; color:var(--texto); margin:2.2rem 0 .2rem; }}
.seccion:after {{ content:''; display:block; width:56px; height:4px; background:var(--acento); margin-top:.45rem; border-radius:2px; }}
.stTabs [data-baseweb="tab-list"] {{ gap:.4rem; border-bottom:1px solid #E6E2DD; }}
.stTabs [data-baseweb="tab"] {{ font-family:'Source Sans 3', sans-serif; font-weight:700; font-size:1.05rem; padding:.6rem 1rem; }}
.stTabs [aria-selected="true"] {{ color:var(--acento) !important; }}
.resultado {{ background:#fff; border-radius:14px; box-shadow:0 6px 24px rgba(0,0,0,.08); padding:1.6rem 1.7rem; border-top:6px solid var(--acento); }}
.resultado .etq {{ font-size:.78rem; text-transform:uppercase; letter-spacing:.08em; color:var(--suave); }}
.resultado h2 {{ font-size:2.1rem; font-weight:800; margin:.2rem 0 .6rem; color:var(--texto); }}
.pildora {{ display:inline-block; background:var(--acento); color:#fff; border-radius:999px; padding:.25rem .8rem; font-size:.85rem; font-weight:600; }}
.pildora.gris {{ background:#8A9099; }}
.barra {{ height:8px; background:#EEE; border-radius:999px; margin:.7rem 0 1rem; overflow:hidden; }}
.barra b {{ display:block; height:100%; background:var(--acento); }}
.dato {{ background:var(--fondo-suave); border-left:4px solid #F29E38; padding:.8rem 1rem; border-radius:6px; margin-top:.8rem; font-size:.95rem; }}
.aviso {{ background:#FFF5F8; border-left:4px solid var(--acento); padding:1rem 1.2rem; border-radius:8px; }}
.grid {{ display:grid; grid-template-columns:repeat(3, 1fr); gap:1.3rem; margin-top:1rem; }}
.card {{ background:#fff; border-radius:14px; overflow:hidden; box-shadow:0 4px 18px rgba(0,0,0,.07); transition:transform .15s; }}
.card:hover {{ transform:translateY(-3px); }}
.card .img {{ height:190px; background-size:cover; background-position:center; position:relative; }}
.card .img span {{ position:absolute; left:.8rem; bottom:.7rem; background:rgba(0,0,0,.55); color:#fff; font-size:.72rem; padding:.2rem .55rem; border-radius:999px; }}
.card .txt {{ padding:1rem 1.1rem 1.2rem; }}
.card h3 {{ font-size:1.25rem; font-weight:800; margin:0 0 .35rem; color:var(--texto); }}
.card p {{ font-size:.86rem; color:var(--suave); margin:0; line-height:1.45; }}
.pie {{ margin-top:3rem; padding:1.4rem 0 2rem; border-top:1px solid #E6E2DD; font-size:.75rem; color:#8A9099; }}
.pie a {{ color:#8A9099; }}
@media (max-width: 800px) {{ .hero {{ height:340px; }} .hero h1 {{ font-size:2.2rem; }} .grid {{ grid-template-columns:1fr; }} }}
</style>""", unsafe_allow_html=True)


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
    <button id="b" style="font-family:Poppins,sans-serif;font-size:15px;padding:9px 18px;border-radius:999px;
      border:2px solid #D81B60;background:#fff;color:#D81B60;font-weight:600;cursor:pointer">🔊 Escuchar descripción</button>
    <script>
    document.getElementById('b').onclick = () => {{
      speechSynthesis.cancel();
      const u = new SpeechSynthesisUtterance({texto_js});
      u.lang = 'es-CO'; u.rate = 0.95;
      speechSynthesis.speak(u);
    }};
    </script>""", height=56)


# ---------- portada ----------
st.markdown(f"""
<div class="hero"><div class="hero-in">
  <div class="miga">Bogotá &nbsp;/&nbsp; Centro histórico &nbsp;/&nbsp; Guía con visión artificial</div>
  <h1>Descubre La Candelaria<br>con una foto</h1>
  <div class="chips"><span>📍 Bogotá</span><span>🏛️ {len(RECORRIDO)} sitios</span><span>📷 Azure Custom Vision</span></div>
</div></div>
<div class="franja">{''.join(f'<i style="background:{c}"></i>' for c in COLORES)}</div>
<p class="intro">Apunta tu cámara a un edificio del centro histórico y la guía te dirá qué es, su historia y un dato curioso.
Funciona con un modelo de clasificación de imágenes entrenado en Azure Custom Vision.</p>
""", unsafe_allow_html=True)

with st.sidebar:
    st.header("Ajustes")
    umbral = st.slider("Confianza mínima para responder", 0.3, 0.95, 0.6, 0.05,
                       help="Si la confianza es menor, la app responde «no reconozco este lugar».")
    st.caption("Modelo: Azure Custom Vision, dominio Landmarks.")

tab_foto, tab_lote = st.tabs(["📷  Identificar un sitio", "🗂️  Evaluar un lote (ZIP)"])

with tab_foto:
    origen = st.radio("¿Cómo quieres agregar la foto?", ["Subir archivo", "Usar la cámara"], horizontal=True)
    archivo = (st.file_uploader("Foto del sitio", type=["jpg", "jpeg", "png", "bmp"])
               if origen == "Subir archivo" else st.camera_input("Toma la foto"))

    if archivo:
        datos = archivo.getvalue()
        with st.spinner("Analizando la foto..."):
            probs = predecir(preparar(datos))
        tag, conf = next(iter(probs.items()))
        col_img, col_txt = st.columns([1, 1.15], gap="large")
        with col_img:
            st.image(datos, use_container_width=True)
        with col_txt:
            if conf < umbral or tag == "otro_lugar":
                parecido = (f"<p style='margin-top:.6rem;color:#5F6670;font-size:.9rem'>Lo más parecido: "
                            f"{html.escape(nombre(tag))} ({conf:.0%}), por debajo del umbral de {umbral:.0%}.</p>"
                            if tag != "otro_lugar" else "")
                st.markdown(f"""<div class="resultado"><div class="etq">Resultado</div>
                  <h2>No reconozco este lugar</h2><span class="pildora gris">Confianza {conf:.0%}</span>
                  <div class="aviso" style="margin-top:1rem">{html.escape(INFO['otro_lugar']['descripcion'])}</div>{parecido}</div>""",
                            unsafe_allow_html=True)
            else:
                sitio = INFO[tag]
                dato = f'<div class="dato">💡 {html.escape(sitio["dato_curioso"])}</div>' if sitio["dato_curioso"] else ""
                st.markdown(f"""<div class="resultado"><div class="etq">📍 {html.escape(UBICACION.get(tag, 'La Candelaria, Bogotá'))}</div>
                  <h2>{html.escape(sitio['nombre'])}</h2><span class="pildora">Confianza {conf:.0%}</span>
                  <div class="barra"><b style="width:{conf*100:.0f}%"></b></div>
                  <p>{html.escape(sitio['descripcion'])}</p>{dato}</div>""", unsafe_allow_html=True)
                leer_en_voz_alta(f"{sitio['nombre']}. {sitio['descripcion']} {sitio['dato_curioso']}")
            with st.expander("Ver todas las probabilidades"):
                df = pd.DataFrame({"Sitio": [nombre(t) for t in probs], "Probabilidad": list(probs.values())})
                st.bar_chart(df.set_index("Sitio"), horizontal=True, color="#D81B60")

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
        st.session_state["lote"] = pd.DataFrame(filas)

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

            g1, g2 = st.columns(2)
            with g1:
                fig, ax = plt.subplots(figsize=(7, 6))
                presentes = [c for c in clases if c in set(y) | set(yp)]
                ConfusionMatrixDisplay(confusion_matrix(y, yp, labels=presentes),
                                       display_labels=[nombre(c) for c in presentes]).plot(
                    ax=ax, xticks_rotation=60, colorbar=False, cmap="RdPu")
                ax.set_title("Matriz de confusión"); fig.tight_layout()
                st.pyplot(fig)
            with g2:
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


# ---------- sitios del recorrido ----------
def resumen(texto, n=150):
    return texto if len(texto) <= n else texto[:texto.rfind(" ", 0, n)] + "…"


tarjetas = "".join(f"""
<div class="card"><div class="img" style="background-image:url('data:image/jpeg;base64,{foto_b64(t)}')">
  <span>📍 {html.escape(UBICACION[t])}</span></div>
  <div class="txt"><h3>{html.escape(INFO[t]['nombre'])}</h3><p>{html.escape(resumen(INFO[t]['descripcion']))}</p></div></div>"""
    for t in RECORRIDO)
creditos = " · ".join(
    f'{html.escape(nombre(t) if t != "hero" else "Portada")}: {html.escape(c["autor"][:60])} '
    f'(<a href="{html.escape(c["fuente"])}" target="_blank">{html.escape(c["licencia"])}</a>)'
    for t, c in CREDITOS.items() if t in RECORRIDO or t == "hero")
st.markdown(f"""
<div class="seccion">Sitios del recorrido</div>
<p class="intro" style="margin-top:.6rem">Estos son los lugares que la guía reconoce hoy. Pronto se sumarán la Capilla del Sagrario,
el Chorro de Quevedo, la Iglesia de La Tercera y el Museo del Oro.</p>
<div class="grid">{tarjetas}</div>
<div class="pie">Proyecto académico de visión por computador. No es un sitio oficial de turismo.<br>
Fotografías de Wikimedia Commons — {creditos}.</div>
""", unsafe_allow_html=True)
