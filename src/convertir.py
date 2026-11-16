
import os
from basic_pitch.inference import predict_and_save
from basic_pitch import ICASSP_2022_MODEL_PATH


# input_audio = "grabacion.wav"
output_dir = "midi/"

# Verificar que el archivo de audio realmente exista

def conversion(input_audio):
    if not os.path.exists(input_audio):
        raise FileNotFoundError(f"No se encontró el archivo de audio: {input_audio}")
    os.makedirs(output_dir, exist_ok=True)

# Llamada correcta con todos los argumentos requeridos
    predict_and_save(
    audio_path_list=[input_audio],      # Lista con las rutas de audio
    output_directory=output_dir,       # Carpeta de destino
    save_midi=True,                    # Crear archivo MIDI
    sonify_midi=False,                 # No generar el audio WAV del MIDI
    save_model_outputs=False,          # (Obligatorio) No guardar archivo NPZ crudo
    save_notes=False,                  # (Obligatorio) No guardar CSV de eventos de notas
    model_or_model_path=str(ICASSP_2022_MODEL_PATH), # (Obligatorio) Cargar el modelo base

    #Parametros para canto
    onset_threshold=0.7, # evita notas falsas por respiracion
    frame_threshold=0.3, #mantiene notas largas o suaves
    #include_pitch_bend=True, #captura vibratos y portamentos
    minimum_note_length=150,
    multiple_pitch_bends=False, #Desactivado porque es una voz(monofonica)
    minimum_frequency=80.0, #filtra ruidos muy graves
    maximum_frequency=1200.0, #filtra armonicos muy agudos
      )

    # 2. Nombre exacto que la librería le pone por defecto
    # Si metés "grabacion_melodia.wav", la librería genera "grabacion_melodia_basic_pitch.mid"
    nombre_base_audio = os.path.splitext(os.path.basename(input_audio))[0]
    nombre_por_defecto = f"{nombre_base_audio}_basic_pitch.mid"
    ruta_por_defecto = os.path.join(output_dir, nombre_por_defecto)
    
    # 3. Buscar el siguiente número disponible en la carpeta
    contador = 1
    while True:
        nuevo_nombre = f"{nombre_base_audio}_basic_pitch{contador}.mid"
        ruta_nueva = os.path.join(output_dir, nuevo_nombre)
        
        if not os.path.exists(ruta_nueva):
            break
        contador += 1
        
    # 4. Renombrar el archivo recién creado al nombre con número
    if os.path.exists(ruta_por_defecto):
        os.rename(ruta_por_defecto, ruta_nueva)
        print(f"¡Conversión completada! Guardado como: '{nuevo_nombre}' en '{output_dir}'.")
    else:
        raise FileNotFoundError(f"Basic Pitch no generó {ruta_por_defecto}")

    nombre_archivo = f"{output_dir}{nuevo_nombre}" 
    return nombre_archivo

# pruebas
#nombre = conversion("grabacion_melodia.wav")
#print(nombre)
