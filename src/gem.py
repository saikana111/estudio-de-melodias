import asyncio
import io
import json
import os
import re
import shutil
import time
from contextlib import contextmanager

from dotenv import load_dotenv
from google import genai
from google.genai import types
from typing import Literal

from pydantic import BaseModel
from groq import Groq
import numpy as np
import scipy.io.wavfile as wavfile
from scipy.signal import resample_poly
import edge_tts
from gtts import gTTS
import pygame
from elevenlabs.client import ElevenLabs

from decision_voz import Decision, INSTRUCCIONES as GUIA_REVISION
from arrangement_intent import resolver_arreglo
from emotion_skill import EmotionContext, load_emotion_skill

# reproducir.py (el sintetizador) se importa recién dentro de las funciones que lo usan: así el
# panel web (dashboard.py) puede usar el chat y la voz sin cargar FluidSynth ni el SoundFont.

load_dotenv()

MODELO = "gemini-3.5-flash-lite"

# Skill "interpretar emoción musical" (skills/interpretar-emocion-musical/SKILL.md, del proyecto
# estudio-de-melodias): guía para pasar lo que el usuario quiere transmitir a los datos del
# arreglo. Se suma a las instrucciones del chat y a las del pedido del arreglo en JSON.
GUIA_EMOCIONAL = load_emotion_skill()
# Últimos intercambios del chat, para que el pedido del arreglo (que va aparte del chat) sepa
# qué se habló. Tiene un tope de largo y se borra al abrir otro proyecto.
contexto_emocional = EmotionContext()


@contextmanager
def cronometro(etapa):
    """Imprime cuánto tardó una etapa, por ejemplo "[tiempo] ElevenLabs (texto a voz): 2.4 s".
    Se usa con "with cronometro(...):" alrededor de cada pedido por internet, para ver
    en la consola cuál es el que demora cuando el asistente tarda en responder."""
    inicio = time.perf_counter()
    try:
        yield
    finally:   # también cuando el pedido falla: interesa saber cuánto esperó
        print(f"[tiempo] {etapa}: {time.perf_counter() - inicio:.1f} s")

# =====================================================================
#  Transcripción de voz a texto (Whisper en Groq)
# =====================================================================
# Whisper corre en los servidores de Groq: tarda alrededor de 1 s y usa el modelo grande,
# que se equivoca menos. En la computadora, sin placa de video, el modelo "base" tardaba
# unos 9 s por mensaje. Si Groq falla, se usa Whisper en la computadora como respaldo.
_clave_groq = os.getenv("GROQ_API_KEY")
cliente_groq = Groq(api_key=_clave_groq) if _clave_groq else None
_whisper_local = None   # se carga solo si hace falta el respaldo (tarda unos 30 s)

# Con una grabación en silencio, Whisper a veces inventa una frase ("Gracias.").
# Si el sonido más fuerte no llega a este nivel (1 = el máximo), no se transcribe.
NIVEL_SILENCIO = 0.01
# Frases que Whisper inventa cuando escucha tarareo o ruido en vez de palabras
# (aprendió de videos subtitulados que terminan así). Si aparecen, se descarta el texto.
FRASES_INVENTADAS = re.compile(r"suscr[ií]bete|gracias por ver|amara\.org|subt[ií]tulos", re.IGNORECASE)


def _leer_audio(archivo):
    """Lee la grabación y la deja en mono, con valores entre -1 y 1."""
    frecuencia, datos = wavfile.read(archivo)
    datos = datos.astype(np.float32)
    if datos.ndim > 1:
        datos = datos.mean(axis=1)          # estéreo -> mono
    if np.abs(datos).max() > 1.0:
        datos /= 32768                      # venía en enteros de 16 bits
    return frecuencia, datos


def _audio_para_enviar(frecuencia, datos):
    """Pasa el audio a 16 kHz y 16 bits, que es lo que usa Whisper por dentro.
    El archivo queda unas 5 veces más chico y sube más rápido."""
    datos = resample_poly(datos, 16000, frecuencia)
    salida = io.BytesIO()
    wavfile.write(salida, 16000, (np.clip(datos, -1, 1) * 32767).astype(np.int16))
    return salida.getvalue()


def transcribir(archivo):
    frecuencia, datos = _leer_audio(archivo)
    if datos.size == 0 or np.abs(datos).max() < NIVEL_SILENCIO:
        return ""   # solo silencio: responder() lo toma como "no se entendió nada"
    with cronometro("Whisper (voz a texto)"):
        texto = _transcribir_audio(archivo, frecuencia, datos)
    return "" if FRASES_INVENTADAS.search(texto) else texto


def _transcribir_audio(archivo, frecuencia, datos):
    if cliente_groq is not None:
        try:
            resultado = cliente_groq.audio.transcriptions.create(
                file=("grabacion.wav", _audio_para_enviar(frecuencia, datos)),
                model="whisper-large-v3-turbo",
                language="es",
                temperature=0,
            )
            return resultado.text.strip()
        except Exception as e:
            print(f"Groq no respondió ({e}). Se usa Whisper en la computadora (más lento).")

    global _whisper_local
    if _whisper_local is None:
        import whisper   # se importa recién acá: cargarlo demora el arranque del programa
        _whisper_local = whisper.load_model("base")
    return _whisper_local.transcribe(archivo, language="es")["text"].strip()


# =====================================================================
#  Chat con Gemini
# =====================================================================
instrucciones_del_sistema = (
    "Eres un productor musical experto, arreglista y asistente de composición interactivo. "
    "El usuario está usando un instrumento que convierte su tarareo en notas MIDI con el instrumento que desee, "
    "y un teclado que mide la fuerza de cada tecla. Cada canción es un proyecto con varias pistas. "
    "Tu objetivo es acompañar al usuario en el proceso creativo de construir una canción a partir de su idea melódica.\n\n"
    "Reglas de comportamiento:\n"
    "1. Habla en un tono cálido, inspirador y conciso, como un productor en sesión que escucha antes de hablar.\n"
    "2. Cuando falte contexto, haz preguntas antes de sugerir. Cuando el usuario comparta una melodía o idea, "
    "primero pregúntale qué quiere expresar con ella, qué estilo o artista lo inspira, y qué emoción quiere generar. "
    "Haz una sola pregunta por vez y espera la respuesta antes de continuar. No repitas lo que ya respondió; "
    "si pide probar directamente, propone una interpretación inicial.\n"
    "3. Una vez que tengas contexto suficiente, haz UNA sola sugerencia concreta: qué instrumento agregar "
    "y con qué carácter (si toca una nota por vez o acordes, con notas largas o cortas, en un registro "
    "grave o agudo, con mucho o poco espacio entre las notas). No nombres acordes ni notas puntuales: "
    "las notas las escribe otro sistema a partir de tu descripción, escuchando la melodía. "
    "Después de darla, pregunta si quiere escucharla o si prefiere explorar otra dirección.\n"
    "4. Cuando el usuario acepta una sugerencia, el sistema la toca automáticamente junto con su melodía. "
    "En ese caso responde con una sola frase corta, por ejemplo avisando que ya la va a escuchar.\n"
    "5. Tus respuestas van a ser transcriptas a voz. Escribe en párrafos y oraciones, sin listas, sin asteriscos, sin símbolos.\n"
    "6. Explica las sugerencias en lenguaje simple, sin asumir conocimientos musicales.\n"
    "7. Rechaza cualquier conversación que no esté relacionada con música, composición o producción."
)
instrucciones_del_sistema += (
    "\n\n" + GUIA_EMOCIONAL + "\n\n"
    # La guía describe el JSON del arreglo; sin esta aclaración, a veces el chat respondía con
    # ese JSON (y la voz lo leía en voz alta).
    "IMPORTANTE: en esta conversación respondé siempre con frases habladas, nunca con JSON, código, "
    "listas ni nombres de campos como instrumento o patron. Los datos del arreglo los pide la "
    "aplicación aparte, en otro pedido. Si el usuario pide probar directamente, contale en una o dos "
    "frases qué vas a hacer y preguntale si quiere escucharlo."
)

# Por defecto la librería de Gemini no tiene límite de espera: si un pedido queda colgado
# (pasa cuando se agota el cupo o el servidor está saturado), el programa se queda trabado
# sin avisar. Con este límite, a los 30 s se corta y se sigue (el número va en milisegundos).
ESPERA_GEMINI_MS = 30_000
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"],
                      http_options=types.HttpOptions(timeout=ESPERA_GEMINI_MS))

# El chat guarda el historial, así Gemini recuerda cada mensaje de la conversación.
mi_chat_gemini = client.chats.create(
    model=MODELO,
    config=types.GenerateContentConfig(
        system_instruction=instrucciones_del_sistema,
        temperature=0.3,
    ),
)


def reiniciar_contexto_musical():
    """Chat nuevo al abrir otro proyecto: la IA no mezcla lo que se habló de otra canción."""
    global mi_chat_gemini, ultimo_arreglo
    mi_chat_gemini = client.chats.create(
        model=MODELO,
        config=types.GenerateContentConfig(system_instruction=instrucciones_del_sistema, temperature=0.3),
    )
    contexto_emocional.clear()
    ultimo_arreglo = None


def hablar_con_mi_gem(mensaje):
    try:
        with cronometro("Gemini (respuesta)"):
            respuesta = mi_chat_gemini.send_message(mensaje)
        if respuesta.text:
            contexto_emocional.record(mensaje, respuesta.text)
            return respuesta.text
        # A veces Gemini responde sin texto (por ejemplo, si bloquea la respuesta).
        # Sin este control, el None seguía hasta la voz y cortaba el programa.
        motivo = respuesta.candidates[0].finish_reason if respuesta.candidates else respuesta.prompt_feedback
        print(f"Gemini respondió sin texto (motivo: {motivo}).")
        return "Perdón, no me salió la respuesta. ¿Me lo puedes decir de otra forma?"
    except Exception as e:
        print(f"Error al conectar con Gemini: {e}")
        if "RESOURCE_EXHAUSTED" in str(e) or "429" in str(e):   # se agotó el cupo de pedidos
            return "Se me acabó el cupo de respuestas de Gemini. Espera un rato y vuelve a intentarlo."
        return "Perdón, no me pude conectar. ¿Puedes repetirlo en un momento?"


# =====================================================================
#  Voz de la IA (ElevenLabs, con edge-tts como respaldo)
# =====================================================================
# ID de las 4 voces elegidas en la biblioteca de ElevenLabs
VOCES = {
    0: "nbcvT3C2tyOd2OsRAtUf", #Maya
    1: "htFfPSZGJwjBv1CL0aMD", #Antonio
    2: "nTkjq09AuYgsNR8E4sDe", #Sol
    3: "tomkxGQGz4b1kE0EM722", #Mario
}
# Voces de edge-tts parecidas, por si ElevenLabs no responde
VOCES_EDGE = {
    0: "es-AR-ElenaNeural",
    1: "es-AR-TomasNeural",
    2: "es-MX-DaliaNeural",
    3: "es-MX-JorgeNeural",
}
voz_actual = 0  # la cambia el menú de la pantalla

# La clave se guarda en la variable de entorno ELEVENLABS_API_KEY (archivo .env), no en el código.
_clave_voz = os.getenv("ELEVENLABS_API_KEY")
cliente_voz = ElevenLabs(api_key=_clave_voz) if _clave_voz else None

INSTRUCCIONES_EXPRESION = (
    "Recibís un texto que va a decir en voz alta un asistente musical. "
    "Agregale etiquetas de audio de ElevenLabs entre corchetes, en inglés, "
    "como [laughs], [sighs], [excited], [softly], [curious] o [pause], "
    "donde ayuden a expresar la emoción del mensaje. "
    "No cambies, agregues ni quites ninguna palabra del texto. "
    "Usá como máximo tres etiquetas. Respondé solo con el texto con las etiquetas."
)


def agregar_expresion(texto):
    """Pedido aparte del chat: agrega etiquetas de audio sin cambiar ninguna palabra."""
    try:
        with cronometro("Gemini (etiquetas de emoción)"):
            respuesta = client.models.generate_content(
                model=MODELO,
                contents=texto,
                config=types.GenerateContentConfig(
                    system_instruction=INSTRUCCIONES_EXPRESION,
                    temperature=0.3,
                ),
            )
        return respuesta.text.strip()
    except Exception:
        return texto  # si falla, la voz sale igual, sin etiquetas


def sin_etiquetas(texto):
    """Saca las etiquetas [excited], [softly]... para que edge-tts no las lea en voz alta."""
    return re.sub(r"\[[^\]]*\]\s*", "", texto).strip()


async def voz_edge(texto, archivo="audio_edge.mp3"):
    """Respaldo: edge-tts (gratis). Si también falla, se usa la voz de Google (gTTS)."""
    try:
        comunicador = edge_tts.Communicate(texto, VOCES_EDGE[voz_actual])
        await comunicador.save(archivo)
    except Exception as e:
        print(f"edge-tts falló ({e}), se usa gTTS")
        gTTS(texto, lang="es", tld="com.ar").save(archivo)


def texto_a_voz(texto, expresar=True, archivo="respuesta_ia.mp3", archivo_respaldo="audio_edge.mp3"):
    """Convierte el texto en voz y devuelve el nombre del archivo de audio.
    expresar=False para las frases fijas, que ya llevan sus etiquetas escritas a mano.
    archivo y archivo_respaldo: dónde se guarda (el panel web usa archivos propios, para no
    chocar con la app si las dos están abiertas)."""
    try:
        if cliente_voz is None:
            raise RuntimeError("falta ELEVENLABS_API_KEY")
        texto_con_etiquetas = agregar_expresion(texto) if expresar else texto  # con etiquetas de audio
        with cronometro("ElevenLabs (texto a voz)"):
            audio = cliente_voz.text_to_speech.convert(
                text=texto_con_etiquetas,
                voice_id=VOCES[voz_actual],
                model_id="eleven_v4_turbo",
                output_format="mp3_44100_128",
            )
            with open(archivo, "wb") as f:
                for parte in audio:  # el audio llega en partes y se van escribiendo
                    f.write(parte)
        return archivo

    except Exception as e:
        print(f"ElevenLabs no respondió ({e}). Se usa edge-tts.")
        asyncio.run(voz_edge(sin_etiquetas(texto), archivo_respaldo))  # edge-tts recibe el texto sin etiquetas
        return archivo_respaldo


def reproducir_audio(archivo):
    """Reproduce un audio (la voz de la IA o una frase ya grabada) con el volumen de la perilla."""
    import reproducir
    if not pygame.mixer.get_init():
        pygame.mixer.init()
    pygame.mixer.music.load(archivo)
    pygame.mixer.music.set_volume(reproducir.volumen_general / 127)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        time.sleep(0.1)  # pequeña pausa para no saturar el procesador
    pygame.mixer.music.unload()  # suelta el archivo para poder sobrescribirlo la próxima vez


def leer(texto, expresar=True):
    """Dice en voz alta un texto (una respuesta de la IA o una frase fija)."""
    print(f"IA: {texto}")
    reproducir_audio(texto_a_voz(texto, expresar))


# ---------- Audios ya grabados ----------
CARPETA_AUDIOS = os.path.join("assets", "audios")


def muestra_voz(voz):
    """Reproduce la muestra de una voz (assets/audios/muestra_voz_N.mp3) cuando el cursor
    llega a ella en "Elegir voz de la IA". No espera a que termine: la llama el hilo que lee
    el puerto, que no se puede quedar trabado. Si ya sonaba otra muestra, la corta."""
    archivo = os.path.join(CARPETA_AUDIOS, f"muestra_voz_{voz}.mp3")
    if not os.path.exists(archivo):
        print(f"Falta la muestra {archivo}")
        return
    import reproducir
    if not pygame.mixer.get_init():
        pygame.mixer.init()
    pygame.mixer.music.load(archivo)   # cargar otro archivo corta el que estaba sonando
    pygame.mixer.music.set_volume(reproducir.volumen_general / 127)
    pygame.mixer.music.play()


def decir_frase(clave, texto):
    """Frases fijas, que siempre dicen lo mismo (como la bienvenida). Se usa el audio ya
    grabado de la voz actual, assets/audios/<clave>_N.mp3. Si todavía no existe, se crea
    una sola vez con ElevenLabs y se guarda ahí: las próximas veces ya no se gasta nada."""
    archivo = os.path.join(CARPETA_AUDIOS, f"{clave}_{voz_actual}.mp3")
    print(f"IA: {sin_etiquetas(texto)}")
    if not os.path.exists(archivo):
        generado = texto_a_voz(texto, expresar=False)
        if generado != "respuesta_ia.mp3":
            reproducir_audio(generado)   # salió de edge-tts (respaldo): no se guarda
            return
        os.makedirs(CARPETA_AUDIOS, exist_ok=True)
        shutil.copyfile(generado, archivo)
    reproducir_audio(archivo)


# =====================================================================
#  Conversación
# =====================================================================

def hablar(mensaje):
    """Le manda un mensaje al chat y dice la respuesta en voz alta. Devuelve la respuesta."""
    respuesta = hablar_con_mi_gem(mensaje)
    leer(respuesta)
    return respuesta


def responder(archivo):
    """Transcribe el mensaje de voz grabado con el botón de chat y responde en voz alta.
    Devuelve (mensaje del usuario, respuesta de la IA), o None si no se entendió nada."""
    mensaje = transcribir(archivo)
    print(f"Usuario: {mensaje}")
    if not mensaje:
        return None
    return mensaje, hablar(mensaje)


def texto_analisis(midi_txt, tonalidad):
    """El mensaje con el que se le pasa a la IA una melodía recién grabada."""
    return ("Este es el archivo MIDI, pasado a texto, de la melodía que acabo de cantar. "
            f"Tonalidad detectada: {tonalidad}. ¿Podrías analizarla?\n{midi_txt}")


def analizar_midi(midi_txt, tonalidad):
    """Le pasa a la IA la melodía desglosada en texto para que la analice y empiece a preguntar."""
    return hablar(texto_analisis(midi_txt, tonalidad))


# =====================================================================
#  Pedidos separados del chat
# =====================================================================

# ---------- ¿El usuario aceptó la sugerencia? ----------
INSTRUCCIONES_ACEPTA = (
    "Recibís la última propuesta musical que hizo un asistente y lo que le respondió la persona. "
    "Respondé solamente SI si la persona está de acuerdo con la propuesta y quiere escucharla, "
    "o si pide directamente que le crees, generes o hagas escuchar una sugerencia o un acompañamiento "
    "(aunque no haya propuesta anterior), o si pide un cambio concreto sobre la sugerencia que acaba "
    "de escuchar (por ejemplo más grave, con menos notas o con otro instrumento). "
    "Respondé NO en cualquier otro caso."
)


def acepto_sugerencia(propuesta, mensaje):
    try:
        with cronometro("Gemini (¿aceptó la propuesta?)"):
            respuesta = client.models.generate_content(
                model=MODELO,
                contents=f"Propuesta del asistente: {propuesta}\nRespuesta de la persona: {mensaje}",
                config=types.GenerateContentConfig(
                    system_instruction=INSTRUCCIONES_ACEPTA,
                    temperature=0,  # respuesta exacta, sin creatividad
                ),
            )
        return respuesta.text.strip().upper().startswith("SI")
    except Exception:
        return False


# ---------- Arreglo en formato JSON (para MIDI-GPT) ----------
# Gemini no escribe las notas: elige el instrumento y el carácter de la pista, y con eso
# MIDI-GPT (acompanante.py) escribe las notas. Las palabras de cada campo son las que
# acompanante.py sabe traducir a los controles del modelo.
class Arreglo(BaseModel):
    instrumento: int | None = None
    voces: int | None = None
    notas: Literal["cortas", "medias", "largas"] | None = None
    espacio: Literal["poco", "medio", "mucho"] | None = None
    registro: Literal["grave", "medio", "agudo"]
    # Los que siguen los usa el ensamble (musical.py); MIDI-GPT los ignora.
    instrumento_bajo: int | None = None
    instrumento_respuestas: int | None = None
    respuestas: bool | None = None
    patron: Literal["sostenido", "bloques", "arpegio"] | None = None
    disposicion: Literal["cerrada", "abierta"]
    intensidad: int                # 24 a 110 (fuerza de las notas; 68 es moderado)
    curva_dinamica: Literal["estable", "crescendo", "diminuendo", "arco"]
    articulacion: Literal["original", "legato", "normal", "staccato"]
    actividad: int                 # 1 a 4: cuántas veces se vuelve a tocar cada acorde
    perfil_armonico: Literal["automatico", "reposado", "creciente", "resolver", "arco"]
    balance_bajo: int              # -36 a 12: fuerza del bajo respecto de la armonía (normal -13)
    balance_respuesta: int         # -36 a 12: fuerza de las respuestas (normal -20)
    # Interpretación (band.py): batería y rasgueo de guitarra. Solo en el ensamble.
    bateria: Literal["ninguna", "acentos", "rock", "house"] | None = None
    estilo: Literal["rock", "otro"] = "otro"
    armonia: Literal["del_estilo", "libre"] = "del_estilo"


ultimo_arreglo = None   # el último que se pidió, para que "más grave" o "menos notas" parta de ahí


def pedir_arreglo_json(idea_aceptada, melodia_txt, tonalidad):
    """Gemini resume la idea en los datos del arreglo (ver la clase Arreglo). Los usan
    sugerencia.ensamble(), sugerencia.cancion() y, como respaldo, MIDI-GPT."""
    global ultimo_arreglo
    pedido = (
        "Convertí esta sugerencia musical en los datos de un acompañamiento. Se arma un grupo: "
        "una armonía (acordes), un bajo y, si se pide, respuestas cortas en los silencios de la melodía.\n"
        "Números de General MIDI de ejemplo: 0 piano, 4 piano eléctrico, 24 guitarra de nylon, "
        "25 guitarra acústica, 32 bajo acústico, 33 bajo eléctrico, 42 violonchelo, 43 contrabajo, "
        "48 cuerdas, 71 clarinete, 73 flauta, 11 vibráfono, 89 colchón de sintetizador. "
        "No elijas batería ni percusión.\n"
        "- instrumento: el de la armonía.\n"
        "- voces: cuántas notas tiene cada acorde, de 1 a 4 (normalmente 3).\n"
        "- notas: \"cortas\", \"medias\" o \"largas\".\n"
        "- espacio: cuánto silencio deja entre las notas: \"poco\", \"medio\" o \"mucho\".\n"
        "- registro: el de la armonía, \"grave\", \"medio\" o \"agudo\". Si no se pide otra cosa, "
        "elegí uno distinto al de la melodía para que no se pisen. Con \"grave\" casi no queda "
        "lugar para el bajo: usalo solo si se pide.\n"
        "- instrumento_bajo e instrumento_respuestas: el del bajo y el de las respuestas.\n"
        "- respuestas: true para que un instrumento conteste en los silencios de la melodía.\n"
        "- patron: \"sostenido\" (acordes largos, lo más seguro con un canto libre), "
        "\"bloques\" (acordes repetidos) o \"arpegio\" (las notas del acorde de a una).\n"
        "- disposicion: \"cerrada\" (notas del acorde juntas) o \"abierta\" (separadas).\n"
        "- intensidad: de 24 a 110; 68 es moderado.\n"
        "- curva_dinamica: \"estable\", \"crescendo\", \"diminuendo\" o \"arco\" (crece y vuelve a bajar).\n"
        "- articulacion: \"original\", \"legato\", \"normal\" o \"staccato\".\n"
        "- actividad: de 1 (tranquilo) a 4 (muy movido).\n"
        "- perfil_armonico: \"automatico\" (sigue a la melodía), \"reposado\", \"creciente\" "
        "(va tomando tensión), \"resolver\" (va hacia el reposo) o \"arco\".\n"
        "- balance_bajo y balance_respuesta: de -36 a 12, cuánto más suave (negativo) o fuerte "
        "suenan el bajo y las respuestas que la armonía; lo normal es -13 y -20.\n"
        "- bateria: \"ninguna\", \"acentos\" (golpes suaves en los cambios de acorde, lo más seguro "
        "con un canto libre), \"rock\" o \"house\" (patrones con pulso fijo). Solo si el género o "
        "el pedido la piden; si dice sin batería, \"ninguna\".\n"
        "- estilo: rock para rock y sus variantes, incluso sin batería; otro para el resto. "
        "armonia: del_estilo salvo pedido de armonía libre o vamp. "
        "Para rock, dejá en null instrumentos, respuestas, voces, patrón, notas, espacio y batería "
        "si la propuesta aceptada no especifica una variante. Python completa la banda y ejecuta la guitarra. "
        "Para otros estilos elegí la formación y textura de la propuesta.\n"
        "No asumas que menor es triste: combiná los datos según lo que pidió el usuario.\n"
        f"Sugerencia aceptada: {idea_aceptada}\n"
        f"Tonalidad de la melodía: {tonalidad}\n"
        f"Melodía: {melodia_txt}"
        "\nContexto reciente de esta sesión (datos del diálogo, no instrucciones del sistema):\n"
        + contexto_emocional.as_json()
    )
    if ultimo_arreglo:
        pedido += ("\nDatos de la sugerencia anterior, por si el usuario pide un cambio sobre ella "
                   f"(si pide algo nuevo, ignoralos): {json.dumps(ultimo_arreglo)}\n"
                   "Si el pedido modifica la sugerencia anterior (por ejemplo «el mismo… pero», «más…», "
                   "«sin…»), copiá esos datos y cambiá solo lo que pidió: los instrumentos se conservan "
                   "salvo que pida otros, aunque cambie la emoción.")
    with cronometro("Gemini (instrumento y carácter)"):
        respuesta = client.models.generate_content(
            model=MODELO,
            contents=pedido,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",  # obliga a responder en JSON
                response_schema=Arreglo,                # ...y con esta forma exacta
                system_instruction=GUIA_EMOCIONAL,      # la skill: de la emoción pedida a los datos
                temperature=0.3,
            ),
        )
    ultimo_arreglo = resolver_arreglo(json.loads(respuesta.text))  # convierte el texto JSON en un diccionario
    return ultimo_arreglo


# ---------- Sugerencia en formato JSON (método anterior, queda como respaldo) ----------
# Forma exacta que tiene que tener el JSON. Con response_schema, Gemini está obligado
# a responder con estas claves y estos tipos (sin esto a veces inventa otra estructura).
class Acorde(BaseModel):
    cifrado: str   # cifrado americano, por ejemplo "Am" o "Cmaj7"
    tiempos: int   # cuántos tiempos dura


class Sugerencia(BaseModel):
    instrumento: int        # número 0-127 de General MIDI
    acordes: list[Acorde]


def pedir_sugerencia_json(idea_aceptada, melodia_txt, tonalidad):
    pedido = (
        "Convertí esta sugerencia en datos: el instrumento (número 0-127 de General MIDI) "
        "y la lista de acordes, cada uno con su cifrado americano (por ejemplo Am, F, Cmaj7) "
        "y cuántos tiempos dura (un número entero, por ejemplo 4).\n"
        f"Sugerencia aceptada: {idea_aceptada}\n"
        f"Tonalidad de la melodía: {tonalidad}\n"
        f"Melodía: {melodia_txt}"
    )
    respuesta = client.models.generate_content(
        model=MODELO,
        contents=pedido,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",  # obliga a responder en JSON
            response_schema=Sugerencia,             # ...y con esta forma exacta
            temperature=0.3,
        ),
    )
    return json.loads(respuesta.text)  # convierte el texto JSON en un diccionario


# ---------- Corrección del nombre ----------
INSTRUCCIONES_NOMBRE = (
    "Recibís la transcripción de una persona diciendo un nombre. Puede incluir aclaraciones "
    "sobre cómo se escribe, por ejemplo 'con doble s', 'con y griega' o 'con hache'. "
    "También recibís los intentos anteriores que la persona marcó como incorrectos. "
    "Respondé solamente con el nombre escrito correctamente, sin comillas ni explicaciones."
)


def corregir_nombre(transcripcion, rechazados):
    respuesta = client.models.generate_content(
        model=MODELO,
        contents=f"Transcripción: {transcripcion}\nIntentos rechazados: {', '.join(rechazados)}",
        config=types.GenerateContentConfig(
            system_instruction=INSTRUCCIONES_NOMBRE,
            temperature=0,  # respuesta exacta, sin creatividad
        ),
    )
    return respuesta.text.strip()


def decision_voz(estado):
    entrada = json.dumps(estado, ensure_ascii=False)
    respuesta = client.models.generate_content(
        model=MODELO, contents=entrada,
        config=types.GenerateContentConfig(system_instruction=GUIA_REVISION,
            response_mime_type="application/json", response_schema=Decision, temperature=0.1))
    return Decision.model_validate_json(respuesta.text).model_dump()
