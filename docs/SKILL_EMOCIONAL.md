# Guía emocional para Gemini

La skill [interpretar-emocion-musical](../skills/interpretar-emocion-musical/SKILL.md)
convierte la investigación previa en criterios de diálogo y elección de controles.
Es texto de instrucciones suministrado a Gemini, no entrenamiento de sus pesos.

`src/emotion_skill.py` carga el cuerpo del archivo desde una ruta relativa al
repositorio. `src/gem.py` lo incorpora a las instrucciones del chat original y a
`pedir_arreglo_json`. No requiere nuevas dependencias ni llamadas adicionales.
Se mantiene `GEMINI_MODEL`, el esquema `Arreglo` y su validación Pydantic.

El planificador recibe también intercambios recientes de la sesión y el arreglo
anterior para conservar matices que no caben en «sí, quiero piano». Ese contexto
adicional está limitado a unos 24.000 caracteres; los intercambios antiguos se
descartan. No es memoria persistente ni un resumen garantizado de toda la charla.
Abrir o crear un proyecto reinicia chat, contexto y último arreglo. Las preferencias
no se restauran al reabrir el proyecto. Fallos de respuesta no se guardan como diálogo.

La skill distingue hallazgos generales de hipótesis de orquestación. Sus ejemplos
son puntos de partida revisables: «triste» no impone menor ni un preset obligatorio.
Describe límites reales, por ejemplo que `espacio` no introduce silencios en un
patrón sostenido, y que `actividad` no cambia el tempo de la melodía.

El flujo original sigue ofreciendo el ensamble y la escucha/aceptación existentes.
El instrumento elegido por Gemini controla la armonía; bajo y respuestas mantienen
los instrumentos del adaptador. No se añadió chat al dashboard ni un planificador
de canciones largas. El modo MIDI-GPT opcional no tiene las mismas garantías de
interpretación de controles que el motor tonal/ensamble.

Para cambiar la guía, editar `SKILL.md` y reiniciar la aplicación. No hace falta
instalarla en una cuenta de Gemini: el código la envía por `system_instruction`.
Debe distribuirse la carpeta `skills` junto con `src`.

## Verificación

Las pruebas offline verifican que las funciones reales de chat/planificador reciben
la guía, que el matiz emocional llega al pedido JSON, que se conserva el arreglo
anterior y que cambiar de proyecto borra ese contexto. Usan un cliente simulado;
no miden razonamiento de Gemini ni calidad perceptual.

Prueba manual con las credenciales y el instrumento habituales:

1. Pedir «triste pero con esperanza; conservá mi melodía», aceptar una propuesta
   y comprobar el JSON impreso y la escucha.
2. Pedir «más tensión, sin subir volumen». Verificar que conserva intensidad y
   curva dinámica y cambia una dimensión pertinente, sin prometer una emoción.
3. Pedir «menos notas» y comprobar si distingue densidad de acordes y ataques.
4. Abrir otro proyecto y comprobar que no hereda las preferencias anteriores.

Evaluar por separado adecuación del JSON, efecto audible y preferencia del usuario.
No se realizó una evaluación en vivo de Gemini ni del dispositivo en este cambio.
