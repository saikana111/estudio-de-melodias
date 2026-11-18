// Hablar con la IA y grabar una melodía desde el panel. El micrófono se graba en el navegador,
// se pasa a WAV y se manda al servidor (src/estudio_ia.py), que usa Whisper, Gemini, la voz de
// ElevenLabs y Basic Pitch igual que la app con el ESP32. Usa upload, busy, accept() y sync()
// de app.js.

// ---------- Grabar el micrófono ----------
let grabacion = null;   // {stream, ctx, proc, partes} mientras se graba

async function empezarGrabacion() {
  const stream = await navigator.mediaDevices.getUserMedia({audio: {echoCancellation: false, noiseSuppression: false}});
  // 22 050 Hz alcanza para la voz y para Basic Pitch, y el archivo queda la mitad de pesado.
  const ctx = new AudioContext({sampleRate: 22050});
  const fuente = ctx.createMediaStreamSource(stream);
  const proc = ctx.createScriptProcessor(4096, 1, 1);
  const partes = [];
  proc.onaudioprocess = e => partes.push(new Float32Array(e.inputBuffer.getChannelData(0)));
  fuente.connect(proc);
  proc.connect(ctx.destination);   // sin esto el navegador no procesa el audio (sale en silencio)
  grabacion = {stream, ctx, proc, partes};
}

async function terminarGrabacion() {
  const g = grabacion;
  grabacion = null;
  g.proc.disconnect();
  g.stream.getTracks().forEach(t => t.stop());
  await g.ctx.close();
  return wavBase64(g.partes, g.ctx.sampleRate);
}

// Arma un WAV de 16 bits mono (cabecera de 44 bytes + las muestras) y lo pasa a base64.
function wavBase64(partes, frecuencia) {
  const n = partes.reduce((total, p) => total + p.length, 0);
  const buffer = new ArrayBuffer(44 + n * 2), v = new DataView(buffer);
  const texto = (pos, s) => [...s].forEach((c, i) => v.setUint8(pos + i, c.charCodeAt(0)));
  texto(0, 'RIFF'); v.setUint32(4, 36 + n * 2, true); texto(8, 'WAVE');
  texto(12, 'fmt '); v.setUint32(16, 16, true); v.setUint16(20, 1, true); v.setUint16(22, 1, true);
  v.setUint32(24, frecuencia, true); v.setUint32(28, frecuencia * 2, true); v.setUint16(32, 2, true); v.setUint16(34, 16, true);
  texto(36, 'data'); v.setUint32(40, n * 2, true);
  let pos = 44;
  for (const p of partes) for (const x of p) { v.setInt16(pos, Math.max(-1, Math.min(1, x)) * 32767, true); pos += 2; }
  const bytes = new Uint8Array(buffer);
  let s = '';
  for (let i = 0; i < bytes.length; i += 0x8000) s += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
  return btoa(s);
}

// ---------- Chat ----------
function burbuja(texto, quien) {
  const p = document.createElement('p');
  p.className = quien;
  p.textContent = texto;
  $('chatLog').append(p);
  $('chatLog').scrollTop = $('chatLog').scrollHeight;
  return p;
}

function decir(audio) {
  stop();   // corta lo que estuviera sonando en la sala de escucha (app.js)
  const voz = $('vozIA');
  voz.src = audio;
  voz.play().catch(() => {});
}

let iaOcupada = false;
function ocupar(si, estado) {
  iaOcupada = si;
  $('chatEstado').textContent = estado;
  for (const id of ['hablar', 'enviar', 'grabarMelodia']) $(id).disabled = si && !grabacion;
}

async function pedirIA(ruta, cuerpo) {
  const r = await fetch(ruta, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(cuerpo)});
  const d = await r.json();
  if (!r.ok) throw Error(d.error || 'No se pudo completar el pedido');
  return d;
}

async function mandarMensaje(cuerpo, burbujaPropia) {
  ocupar(true, 'PENSANDO');
  try {
    const d = await pedirIA('/api/hablar', {...cuerpo, midi: upload ? upload.midi : null});
    burbujaPropia.textContent = d.mensaje;
    burbuja(d.respuesta, 'ia');
    decir(d.audio);
    if (d.arreglo) usarArreglo(d.arreglo);
    else if (!upload) burbuja('(Para que pueda generar algo, primero grabá o abrí una melodía.)', 'ia muted');
  } catch (e) {
    burbujaPropia.remove();
    burbuja(e.message, 'ia error');
  } finally {
    ocupar(false, 'GEMINI');
  }
}

$('hablar').onclick = async () => {
  if (grabacion && grabacion.para === 'chat') {
    $('hablar').classList.remove('grabando');
    $('hablar').textContent = '🎤 Hablar';
    const audio = await terminarGrabacion();
    return mandarMensaje({audio}, burbuja('…', 'yo'));
  }
  if (grabacion || iaOcupada) return;
  try {
    await empezarGrabacion();
    grabacion.para = 'chat';
    $('hablar').classList.add('grabando');
    $('hablar').textContent = '■ Terminar';
    $('chatEstado').textContent = 'ESCUCHANDO';
  } catch (e) {
    burbuja('No se pudo usar el micrófono: ' + e.message, 'ia error');
  }
};

$('enviar').onclick = () => {
  const texto = $('chatTexto').value.trim();
  if (!texto || iaOcupada || grabacion) return;
  $('chatTexto').value = '';
  mandarMensaje({texto}, burbuja(texto, 'yo'));
};
$('chatTexto').addEventListener('keydown', e => { if (e.key === 'Enter') $('enviar').click(); });

// ---------- Grabar una melodía ----------
$('grabarMelodia').onclick = async () => {
  if (grabacion && grabacion.para === 'melodia') {
    $('grabarMelodia').classList.remove('grabando');
    $('grabarMelodia').textContent = '🎙 Grabar melodía';
    const audio = await terminarGrabacion();
    ocupar(true, 'CONVIRTIENDO');
    $('grabarInfo').textContent = 'Pasando la melodía a MIDI con Basic Pitch…';
    try {
      const d = await pedirIA('/api/grabar-melodia', {audio});
      await accept({name: d.name, midi: d.midi});   // la carga en el panel (app.js)
      $('grabarInfo').textContent = 'Melodía cargada: ' + d.name;
      burbuja(d.respuesta, 'ia');
      decir(d.audio);
    } catch (e) {
      $('grabarInfo').textContent = e.message;
    } finally {
      ocupar(false, 'GEMINI');
    }
    return;
  }
  if (grabacion || iaOcupada || busy) return;
  try {
    await empezarGrabacion();
    grabacion.para = 'melodia';
    $('grabarMelodia').classList.add('grabando');
    $('grabarMelodia').textContent = '■ Terminar grabación';
    $('grabarInfo').textContent = 'Grabando… cantá la melodía y tocá "Terminar" al final.';
  } catch (e) {
    $('grabarInfo').textContent = 'No se pudo usar el micrófono: ' + e.message;
  }
};

// ---------- Lo que eligió Gemini -> controles del panel -> generar ----------
const NOMBRES_GM = {0: 'Piano de cola', 4: 'Piano eléctrico', 11: 'Vibráfono', 24: 'Guitarra de nylon',
  25: 'Guitarra acústica', 32: 'Bajo acústico', 33: 'Bajo eléctrico con dedos', 42: 'Violonchelo',
  43: 'Contrabajo', 48: 'Cuerdas', 71: 'Clarinete', 73: 'Flauta', 89: 'Colchón cálido'};

function elegir(id, valor) {
  const select = $(id), texto = String(valor);
  if (![...select.options].some(o => o.value === texto))
    select.add(new Option(NOMBRES_GM[valor] || ('Instrumento GM ' + valor), texto));
  select.value = texto;
}

function usarArreglo(a) {
  $('strum').checked = !!a.rasgueo;
  $('rhythm').value = (a.progresion_rock ?? (a.bateria === 'rock')) ? 'rock' : 'libre';
  elegir('harmony', a.instrumento);
  elegir('bass', a.instrumento_bajo);
  elegir('response', a.instrumento_respuestas);
  elegir('voices', Math.max(2, Math.min(4, a.voces)));
  $('responses').checked = a.respuestas;
  $('register').value = a.registro;
  $('spacing').value = a.disposicion;
  $('pattern').value = a.patron;
  $('intensity').value = a.intensidad;
  $('dynamics').value = a.curva_dinamica;
  $('articulation').value = a.articulacion;
  $('activity').value = a.actividad;
  $('tension').value = a.perfil_armonico;
  $('bassBalance').value = a.balance_bajo;
  $('responseBalance').value = a.balance_respuesta;
  extraBrief = {...extraBrief, notas: a.notas, espacio: a.espacio};   // no tienen control en el panel
  // Los mismos datos, en los controles de MIDI-GPT (por si esa es la opción marcada)
  elegir('mgInstrumento', a.instrumento);
  $('mgVoces').value = String(Math.max(1, Math.min(4, a.voces)));
  $('mgNotas').value = a.notas;
  $('mgEspacio').value = a.espacio;
  $('mgRegistro').value = a.registro;
  sync();
  const tipo = {song: 'la composición más larga', midigpt: 'la pista con MIDI-GPT'}[mode()] || 'el ensamble';
  burbuja(`(Ajustes elegidos por la IA cargados en el panel. Generando ${tipo}…)`, 'ia muted');
  $('generate').click();
}
