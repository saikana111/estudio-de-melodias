# Guía emocional para Gemini

La skill [interpretar-emocion-musical](../skills/interpretar-emocion-musical/SKILL.md)
convierte la investigación previa en criterios de diálogo y elección de controles.
Es texto de instrucciones suministrado a Gemini, no entrenamiento de sus pesos.

`src/emotion_skill.py` carga el cuerpo de la skill **y todo el contenido Markdown
y JSON de `knowledge/`**, desde rutas relativas al repositorio. Los concatena en
un único texto: Gemini recibe los datos, no instrucciones para buscar archivos.
`src/gem.py` lo incorpora a las instrucciones del chat original y a
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

## Contenido y crecimiento

- `SKILL.md`: procedimiento de selección, prioridades y contrato de salida.
- `knowledge/01-parametros.md`: elección de cada control, combinaciones reales,
  fórmula de intervalos entre ataques y tabla de revisiones mínimas.
- `knowledge/02-perfiles.json`: 40 perfiles de intención con condiciones de uso,
  criterio, ajustes sobre una base completa y errores que evitar.
- `knowledge/03-estilos-y-composicion.md`: 16 orientaciones de estilo, mezclas de
  intención, recorridos y 12 técnicas de desarrollo con estado de implementación.

Para extender un perfil, editar sus condiciones/criterio/ajustes. Para agregar
uno, usar un identificador único y solo claves del esquema `Arreglo`. Para ampliar
conocimiento, agregar archivos `.md` o `.json` dentro de `knowledge/`; se incluyen
automáticamente al reiniciar, también en subcarpetas. No poner allí credenciales,
notas privadas, borradores contradictorios ni bibliografía que solo sirve al equipo:
**todo ese directorio se envía al proveedor de Gemini**.

La carga es completa y local; no hay búsqueda web ni recuperación que pueda omitir
una regla por fallar palabras clave. Al crecer la base aumentan los tokens/costo y
posiblemente la latencia de cada petición. No se midió ese impacto con Gemini.
Si deja de ser manejable, introducir selección local de fichas con evaluación de
cobertura, preservando reglas generales y restricciones; no truncar silenciosamente.
El cargador falla ante archivos vacíos, JSON inválido o ausencia de conocimiento.

Los perfiles no se aplican automáticamente por coincidencia de texto: Gemini
interpreta el contexto y los usa como hipótesis editables. No son 40 clasificaciones
psicológicas validadas ni 40 garantías de efectos distintos. La escucha puede
revelar que dos perfiles necesitan diferenciarse o que una combinación no funciona.

## Procedencia para mantenimiento (no enviada como instrucciones)

La revisión y los enlaces están en [Música y emoción](MUSICA_Y_EMOCION.md).
Eerola, Friberg y Bresin orientan la combinación de actividad, dinámica,
articulación, modo, timbre y registro; Smit et al. respaldan la cautela cultural
con mayor/menor; Cheung et al. aportan la relación contextual entre expectativa y
placer; McAdams et al. motivan distinguir instrumento, registro y ejecución;
Juslin orienta atención a referencias y recuerdos. Ninguno prescribe los valores
MIDI de este catálogo. Los perfiles, rangos de velocity y guías de estilo son
decisiones de diseño por evaluar, y las fórmulas/limitaciones proceden del código.
Agregar futuras fuentes aquí con alcance, límites y regla concreta que motivan;
incorporar el conocimiento operativo al directorio `knowledge`, sin obligar al
modelo a consultar los enlaces.

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
También comprueban que todos los perfiles usan el esquema actual y generan en dos
melodías de prueba sin modificar el original (80 combinaciones), y que archivos
nuevos se incorporan al contexto sin herramientas de lectura o navegación.

Prueba manual con las credenciales y el instrumento habituales:

1. Pedir «triste pero con esperanza; conservá mi melodía», aceptar una propuesta
   y comprobar el JSON impreso y la escucha.
2. Pedir «más tensión, sin subir volumen». Verificar que conserva intensidad y
   curva dinámica y cambia una dimensión pertinente, sin prometer una emoción.
3. Pedir «menos notas» y comprobar si distingue densidad de acordes y ataques.
4. Abrir otro proyecto y comprobar que no hereda las preferencias anteriores.

Evaluar por separado adecuación del JSON, efecto audible y preferencia del usuario.
No se realizó una evaluación en vivo de Gemini ni del dispositivo en este cambio.
