// Guía de La Candelaria sin conexión: el modelo ONNX corre en el teléfono.
const RECORRIDO = ["catedral_primada", "capitolio", "plaza_bolivar", "palacio_lievano", "casa_narino", "san_francisco"];
const UBICACION = {
  catedral_primada: "Plaza de Bolívar · costado oriental", capitolio: "Plaza de Bolívar · costado sur",
  plaza_bolivar: "Carrera 7 con calle 10", palacio_lievano: "Plaza de Bolívar · costado occidental",
  casa_narino: "Carrera 8 con calle 7", san_francisco: "Avenida Jiménez con carrera 7",
};
const $ = s => document.querySelector(s);
const esc = t => String(t).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
let INFO = {}, PRE = null, sesion = null;

function estado(txt, listo) { $("#estado-txt").textContent = txt; $("#estado").classList.toggle("listo", !!listo); }

async function iniciar() {
  [INFO, PRE] = await Promise.all([fetch("sitios_info.json").then(r => r.json()), fetch("modelo/preproceso.json").then(r => r.json())]);
  pintarGaleria();
  ort.env.wasm.wasmPaths = "vendor/";
  ort.env.wasm.numThreads = 1;
  sesion = await ort.InferenceSession.create("modelo/modelo_web.onnx", { executionProviders: ["wasm"] });
  await registrarSW();
}

async function registrarSW() {
  if (!("serviceWorker" in navigator)) { estado("Lista. Este navegador no guarda la guía para usarla sin internet.", true); return; }
  try {
    const reg = await navigator.serviceWorker.register("sw.js");
    await navigator.serviceWorker.ready;
    const ok = await caches.has("guia-candelaria-v1");
    estado(ok ? "Lista para usar sin internet ✓" : "Lista. Guardando la guía para usarla sin internet…", true);
    if (!ok) setTimeout(registrarSW, 3000);
    return reg;
  } catch (e) { estado("Lista para usar con conexión. No se pudo guardar para usarla sin internet.", true); }
}

function pintarGaleria() {
  $("#grid").innerHTML = RECORRIDO.map(t => `
    <article class="card"><div class="img" style="background-image:url('img/${t}.jpg')" role="img" aria-label="${esc(INFO[t].nombre)}"></div>
    <div class="txt"><h3>${esc(INFO[t].nombre)}</h3><p>📍 ${esc(UBICACION[t])}</p></div></article>`).join("");
}

// Igual que Custom Vision: lado corto a 256 px, recorte central de 224 px, BGR con valores de 0 a 255.
function aTensor(img) {
  const k = 256 / Math.min(img.naturalWidth, img.naturalHeight);
  const w = Math.max(256, Math.round(img.naturalWidth * k)), h = Math.max(256, Math.round(img.naturalHeight * k));
  const c = document.createElement("canvas"); c.width = 224; c.height = 224;
  const x = c.getContext("2d", { willReadFrequently: true });
  x.imageSmoothingQuality = "high";
  x.drawImage(img, -(w - 224) / 2, -(h - 224) / 2, w, h);
  const d = x.getImageData(0, 0, 224, 224).data, n = 224 * 224, out = new Float32Array(3 * n);
  const orden = PRE.bgr ? [2, 1, 0] : [0, 1, 2];
  for (let i = 0; i < n; i++) for (let ch = 0; ch < 3; ch++) out[ch * n + i] = d[i * 4 + orden[ch]] / PRE.escala;
  return new ort.Tensor("float32", out, [1, 3, 224, 224]);
}

async function analizar(archivo) {
  if (!archivo) return;
  const url = URL.createObjectURL(archivo);
  $("#salida").innerHTML = `<p class="cargando">Analizando la foto en tu teléfono…</p>`;
  const img = new Image(); img.src = url; await img.decode();
  if (!sesion) await new Promise(r => { const t = setInterval(() => { if (sesion) { clearInterval(t); r(); } }, 200); });
  const res = await sesion.run({ data: aTensor(img) });
  const p = Array.from(Object.values(res)[0].data);
  const orden = PRE.etiquetas.map((t, i) => [t, p[i]]).sort((a, b) => b[1] - a[1]);
  mostrar(url, orden);
}

function mostrar(url, orden) {
  const umbral = parseFloat($("#umbral").value);
  const [tag, conf] = orden[0];
  const probs = `<div class="probs">${orden.map(([t, v]) => `<div><span>${esc(INFO[t]?.nombre || t)}</span><i style="width:${(v * 100).toFixed(0)}%"></i><span>${(v * 100).toFixed(0)} %</span></div>`).join("")}</div>`;
  let tarjeta;
  if (conf < umbral || tag === "otro_lugar") {
    const parecido = tag !== "otro_lugar" ? `<p class="probs">Lo más parecido: ${esc(INFO[tag].nombre)} (${(conf * 100).toFixed(0)} %).</p>` : "";
    tarjeta = `<div class="tarjeta"><div class="etq">Resultado</div><h2>No reconozco este lugar</h2>
      <span class="pildora gris">Confianza ${(conf * 100).toFixed(0)} %</span><div class="dato">${esc(INFO.otro_lugar.descripcion)}</div>${parecido}${probs}</div>`;
  } else {
    const s = INFO[tag];
    tarjeta = `<div class="tarjeta"><div class="etq">📍 ${esc(UBICACION[tag] || "La Candelaria, Bogotá")}</div><h2>${esc(s.nombre)}</h2>
      <span class="pildora">Confianza ${(conf * 100).toFixed(0)} %</span><div class="barra"><b style="width:${(conf * 100).toFixed(0)}%"></b></div>
      <p>${esc(s.descripcion)}</p>${s.dato_curioso ? `<div class="dato">💡 ${esc(s.dato_curioso)}</div>` : ""}
      <button class="boton sec" id="escuchar" type="button">🔊 Escuchar</button>${probs}</div>`;
  }
  $("#salida").innerHTML = `<div class="resultado"><img src="${url}" alt="Tu foto"><div>${tarjeta}</div></div>`;
  const b = $("#escuchar");
  if (b) b.onclick = () => {
    const s = INFO[tag]; speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(`${s.nombre}. ${s.descripcion} ${s.dato_curioso}`);
    u.lang = "es-CO"; u.rate = 0.95; speechSynthesis.speak(u);
  };
  $("#salida").scrollIntoView({ behavior: "smooth", block: "start" });
}

$("#camara").onchange = e => analizar(e.target.files[0]);
$("#galeria").onchange = e => analizar(e.target.files[0]);
$("#umbral").oninput = e => { $("#umbral-v").textContent = Math.round(e.target.value * 100) + " %"; };
iniciar().catch(e => estado("No se pudo cargar el modelo: " + e.message, false));
