import json
import os
import threading
import time

import grabar, convertir, correccion, gem, reproducir, esp32, proyectos, sugerencia

CONFIG = "config.json"

# Canal MIDI de cada tipo de pista (ver Multipista con FluidSynth). La primera melodía y el
# primer teclado usan estos canales; las grabaciones siguientes, el primero que esté libre
# (proyectos.canal_libre). La sugerencia de la IA es una sola y siempre va al canal 2.
CANAL_MELODIA = 0
CANAL_TECLADO = 1
CANAL_IA = 2

proyecto = None            # proyecto abierto (archivo MIDI multipista) o None en la pantalla de inicio
nombre = None              # nombre del archivo del proyecto, sin .mid
ultima_propuesta = ""      # última idea que propuso la IA, por si el usuario la acepta
ultima_melodia = CANAL_MELODIA   # canal de la última melodía grabada: la IA acompaña a esa
grabacion_teclado = None   # notas tocadas mientras se graba el teclado (None = no se está grabando)
inicio_teclado = 0.0


# =====================================================================
#  Configuración (primer inicio)
# =====================================================================

def cargar_config():
    if not os.path.exists(CONFIG):
        return None  # no existe: es el primer inicio
    with open(CONFIG, encoding="utf-8") as f:
        return json.load(f)


def guardar_config(usuario, voz):
    with open(CONFIG, "w", encoding="utf-8") as f:
        json.dump({"usuario": usuario, "voz": voz}, f, ensure_ascii=False)


def primer_inicio():
    """Bienvenida -> elegir la voz de la IA -> decir el nombre del usuario. Se hace una sola vez."""
    esp32.enviar("PANTALLA:BIENVENIDA")
    voz = esp32.esperar_voz()   # después de elegirla, el ESP32 muestra solo la pantalla del micrófono
    gem.voz_actual = voz
    # Siempre es la misma frase: se reproduce el audio ya grabado con la voz elegida.
    gem.decir_frase("bienvenida", "[warmly] Hola, voy a ser tu asistente musical. ¿Cómo te llamas? "
                    "Presiona el botón de chat, dime tu nombre y vuelve a presionarlo.")
    usuario = proyectos.pedir_nombre("usuario")   # micrófono y "¿Es correcto?"
    guardar_config(usuario, voz)
    return {"usuario": usuario, "voz": voz}


# =====================================================================
#  Programa principal
# =====================================================================

def main():
    if not esp32.conectar():
        print("No se encontró el ESP32 (revisa PUERTO en esp32.py). El instrumento no funciona sin él.")
        return

    # El teclado suena en segundo plano mientras se graba, se conversa o se reproduce el proyecto.
    reproducir.elegir_instrumento(esp32.instrumento_teclado)
    threading.Thread(target=tocar_teclado, daemon=True).start()

    # Python le indica al ESP32 qué pantalla mostrar, porque los datos guardados están en la computadora.
    config = cargar_config()
    if config is None:
        config = primer_inicio()
    else:
        gem.voz_actual = config["voz"]
    esp32.enviar(f"PANTALLA:INICIO:{proyectos.sin_tildes(config['usuario'])}")
    gem.leer(f"[warmly] Hola, {config['usuario']}. ¿Qué vamos a componer hoy?", expresar=False)

    try:
        while True:
            pedido = esp32.leer_pedido()
            if pedido is not None:
                atender(pedido, config)
    except KeyboardInterrupt:
        print("Saliendo...")
    finally:
        if proyecto is not None:
            proyectos.guardar(proyecto, nombre)
        reproducir.cerrar()


def atender(pedido, config):
    """Hace lo que se pidió desde el ESP32 (botones y opciones del menú)."""
    global proyecto, nombre, ultima_melodia
    tipo = pedido[0]

    # ----- Pantalla de inicio -----
    if tipo == "NUEVO":
        nombre = proyectos.preguntar_nombre_proyecto()   # "¿Deseas ponerle un nombre al proyecto?"
        proyecto = proyectos.nuevo()
        ultima_melodia = CANAL_MELODIA
        proyectos.guardar(proyecto, nombre)
        abrir_pantalla_principal()

    elif tipo == "ABRIR":
        nombres = proyectos.listar()
        if pedido[1] < len(nombres):
            nombre = nombres[pedido[1]]
            proyecto = proyectos.abrir(nombre)
            ultima_melodia = CANAL_MELODIA
            abrir_pantalla_principal()
            reproducir.reproducir_proyecto(proyecto)

    elif tipo == "RENOMBRAR":
        nombres = proyectos.listar()
        if pedido[1] < len(nombres):
            nuevo = proyectos.limpiar_nombre(proyectos.pedir_nombre("proyecto"))
            proyectos.renombrar(nombres[pedido[1]], nuevo)
            esp32.enviar("LISTA:" + ",".join(proyectos.listar()))   # vuelve a Proyectos

    elif tipo == "VOZ":   # Ajustes > Voz de la IA (esp32.py ya cambió gem.voz_actual)
        config["voz"] = pedido[1]
        guardar_config(config["usuario"], config["voz"])
        gem.decir_frase("nueva_voz", "[cheerfully] ¡Hola! Así suena mi nueva voz.")

    # ----- Dentro de un proyecto -----
    elif proyecto is None:
        return   # el resto de los pedidos solo sirven con un proyecto abierto

    elif tipo == "BOTON":
        atender_boton(pedido)

    elif tipo == "PLAY":
        reproducir.reproducir_proyecto(proyecto)

    elif tipo == "MOVER":   # MOVER:canal:tiempos
        proyectos.mover_pista(proyecto, pedido[1], pedido[2])
        proyectos.guardar(proyecto, nombre)

    elif tipo == "PISTA":   # PISTA:canal:accion[:valor]
        atender_pista(pedido[1], pedido[2], pedido[3])

    elif tipo == "CERRAR":  # Ajustes > Volver al inicio
        proyectos.guardar(proyecto, nombre)
        proyecto = None


def abrir_pantalla_principal():
    global ultima_propuesta
    gem.reiniciar_contexto_musical()
    ultima_propuesta = ""
    enviar_pistas()
    esp32.enviar(f"PANTALLA:PRINCIPAL:{nombre}")


def enviar_pistas():
    """Le manda al ESP32 las pistas del proyecto, cada una con su canal y su nombre,
    por ejemplo PISTAS:0=Melodia,3=Melodia 2,2=Sugerencia IA."""
    esp32.enviar("PISTAS:" + ",".join(f"{canal}={proyectos.sin_tildes(nombre_pista)}"
                                      for canal, nombre_pista in proyectos.nombres(proyecto)))


def agregar_pista(pista):
    """Pone la pista en el proyecto (reemplaza la que había en ese canal) y guarda."""
    proyectos.poner_pista(proyecto, pista)
    proyectos.guardar(proyecto, nombre)   # se guarda cada vez que se agrega una pista
    enviar_pistas()


def canal_para_grabar(preferido):
    """Canal libre para una grabación nueva, o None (y lo avisa) si el proyecto ya está lleno."""
    canal = proyectos.canal_libre(proyecto, preferido)
    if canal is None:
        gem.leer("Este proyecto ya no tiene lugar para más pistas. Borra alguna y vuelve a grabar.",
                 expresar=False)
    return canal


# =====================================================================
#  Botones de grabación
# =====================================================================

def atender_boton(pedido):
    global grabacion_teclado, inicio_teclado
    _, boton, encendido = pedido

    if boton == "teclado":
        # El teclado sigue sonando como siempre; mientras tanto se anotan las notas con su tiempo.
        if encendido:
            inicio_teclado = time.time()
            grabacion_teclado = []
        elif grabacion_teclado is not None:
            guardar_pista_teclado()

    elif encendido:
        # grabar.py espera el toque que empieza la grabación: se le devuelve el que ya llegó.
        esp32.devolver(pedido)
        tipo = grabar.grabar()   # graba hasta que se vuelve a tocar el mismo botón
        if tipo == "melodia":
            procesar_melodia()
        elif tipo == "chat":
            procesar_chat()


def procesar_melodia():
    global ultima_propuesta, ultima_melodia
    canal = canal_para_grabar(CANAL_MELODIA)   # cada melodía va a una pista nueva
    if canal is None:
        return
    archivo_midi = convertir.conversion("grabacion_melodia.wav")   # Basic Pitch
    tonalidad = correccion.detectar_tonalidad(archivo_midi)        # music21
    # A chromatic note is not necessarily a transcription error. Preserve the
    # original by default; old scale-snapping is an explicit experimental option.
    if os.getenv("CORREGIR_ESCALA", "0") == "1":
        correccion.corregir(archivo_midi, tonalidad)

    # La pista se crea con el instrumento elegido en ese momento para el micrófono.
    pista = proyectos.midi_a_pista(archivo_midi, proyectos.nombre_libre(proyecto, "Melodia"), canal,
                                   esp32.instrumento_microfono, proyecto.ticks_per_beat)
    agregar_pista(pista)
    ultima_melodia = canal
    reproducir.reproducir_proyecto(proyecto)

    ultima_propuesta = gem.analizar_midi(correccion.midi_txt(archivo_midi),
                                         correccion.texto_tonalidad(tonalidad))


def procesar_chat():
    global ultima_propuesta
    resultado = gem.responder("grabacion_chat.wav")
    if resultado is None:
        return   # no se entendió nada
    mensaje, respuesta = resultado

    # Si el usuario acepta la idea que propuso la IA, o pide directamente una sugerencia,
    # se arma y se reproduce. Se pasa también su mensaje, por si pidió algo puntual
    # (por ejemplo "que no sea de piano"), y la respuesta que la IA le acaba de dar.
    if gem.acepto_sugerencia(ultima_propuesta, mensaje):
        generar_sugerencia(f"Propuesta anterior de la IA: {ultima_propuesta}\n"
                           f"Pedido del usuario: {mensaje}\n"
                           f"Respuesta de la IA a ese pedido: {respuesta}")
        ultima_propuesta = ""
    else:
        ultima_propuesta = respuesta


def generar_sugerencia(idea, canal=None):
    """Gemini interpreta la intención y el motor de ensamble genera por defecto.
    Los motores tonal y MIDI-GPT siguen disponibles mediante configuración.
    canal = pista a la que acompaña (de ahí sale el pulso); sin canal, la última melodía grabada."""
    if canal is None or canal == CANAL_IA:
        canal = ultima_melodia
    if any(p.name.startswith("Sugerencia IA") and proyectos.canal_de_pista(p) == canal
           for p in proyecto.tracks):
        canal = ultima_melodia
    motor = os.getenv("ACOMPANAMIENTO_MOTOR", "ensemble")
    try:
        if motor not in ("midigpt", "tonal", "ensemble", "ensamble"):
            raise ValueError(f"Motor desconocido: {motor}")
        archivo = os.path.join(proyectos.CARPETA, nombre + ".mid")
        tonalidad = correccion.texto_tonalidad(correccion.detectar_tonalidad(archivo))
        melodia_txt = correccion.midi_txt(archivo, canal)
        try:
            datos = gem.pedir_arreglo_json(idea, melodia_txt, tonalidad)
            configuracion = os.getenv("ARREGLO_CONFIG")
            if configuracion and motor != "midigpt":
                with open(configuracion, encoding="utf-8") as f:
                    datos.update(json.load(f))
            print(f"Arreglo pedido a {motor}: {datos}")
            if motor in ("ensemble", "ensamble"):
                datos.setdefault("ritmo_armonico", "libre")
                prueba, informe = sugerencia.ensamble(datos, proyecto, canal)
                sugerencia.proponer_ensamble(prueba, informe, proyecto, nombre)
                enviar_pistas()
                return
            if motor == "tonal":
                pista = sugerencia.pista_tonal(datos, proyecto, canal)
            else:
                pista = sugerencia.pista_con_midigpt(datos, proyecto, canal)
        except Exception as e:
            if motor != "midigpt":
                raise  # Do not disguise a rejected tonal brief as another generator.
            print(f"MIDI-GPT no pudo generar ({e}). Se usan los acordes de Gemini.")
            datos = gem.pedir_sugerencia_json(idea, melodia_txt, tonalidad)
            pista = sugerencia.pista_con_acordes(datos, proyecto, canal)
        sugerencia.proponer_sugerencia(pista, proyecto, nombre)   # "¿Aceptar sugerencia?" Sí / No
        enviar_pistas()
    except Exception as e:
        print(f"No se pudo generar la sugerencia: {e}")
        esp32.enviar("PANTALLA:PRINCIPAL")
        gem.leer("Perdón, no pude preparar la sugerencia. Probemos de nuevo en un momento.", expresar=False)


# =====================================================================
#  Opciones de una pista (Pistas > pista elegida)
# =====================================================================

def atender_pista(canal, accion, valor):
    if accion == "SOLA":       # Reproducir sola
        reproducir.reproducir_pista(proyecto, canal)

    elif accion == "INST" and valor is not None:   # Instrumento
        proyectos.cambiar_instrumento(proyecto, canal, valor)
        proyectos.guardar(proyecto, nombre)

    elif accion == "IA":       # Generar con IA
        generar_sugerencia(f"Un acompañamiento de acordes para la pista "
                           f"{proyectos.nombre_de(proyecto, canal)}", canal)

    elif accion == "BORRAR":   # Borrar
        proyectos.borrar_pista(proyecto, canal)
        proyectos.guardar(proyecto, nombre)
        enviar_pistas()


# =====================================================================
#  Teclado
# =====================================================================

def tocar_teclado():
    """Corre en su propio hilo: cada tecla suena al instante con el velocity que midió el ESP32."""
    while True:
        evento = esp32.leer_tecla()
        if evento is None:
            continue
        tipo, nota, velocidad = evento
        if tipo == "on":
            reproducir.tocar_nota(nota, velocidad)
        else:
            reproducir.soltar_nota(nota)

        grabacion = grabacion_teclado   # copia local: el hilo principal la puede cambiar a None
        if grabacion is not None:
            grabacion.append((time.time() - inicio_teclado, tipo, nota, velocidad))


def guardar_pista_teclado():
    global grabacion_teclado
    eventos, grabacion_teclado = grabacion_teclado, None
    if not eventos:
        return   # no se tocó nada
    canal = canal_para_grabar(CANAL_TECLADO)   # cada grabación del teclado va a una pista nueva
    if canal is None:
        return
    pista = proyectos.teclado_a_pista(eventos, proyectos.nombre_libre(proyecto, "Teclado"), canal,
                                      esp32.instrumento_teclado, proyecto.ticks_per_beat)
    agregar_pista(pista)


if __name__ == "__main__":
    main()
