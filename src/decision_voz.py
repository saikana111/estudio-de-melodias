from typing import Literal

from pydantic import BaseModel


class Decision(BaseModel):
    accion: Literal["guardar", "descartar", "repetir", "quitar", "dinamica",
                    "terminar", "generar", "aclarar"]
    pistas: list[str]
    cambio_velocity: int
    formato: Literal["ensamble", "cancion"]
    respuesta: str


INSTRUCCIONES = """Interpretá la transcripción en español según la propuesta audible,
las pistas, la última parte aceptada y la conversación reciente. La persona puede hablar
con sus propias palabras. Una aprobación clara de lo escuchado significa guardar.
Si pide pasar a la siguiente sin conservar la actual, descartá. Si quiere oírla
otra vez, repetí. Para cambios de fuerza de una parte elegí dinamica con un entero
entre -30 y 30. Para quitar partes elegí quitar. En ambos casos devolvé sus nombres
exactos del inventario. Ante un pronombre usá el foco de la escucha. Si hay varias
interpretaciones razonables preguntá cuál en respuesta y elegí aclarar. Una consulta,
una transcripción dudosa o un elogio ambiguo no autorizan guardar. Si aprueba con
una modificación, priorizá la modificación para que escuche antes de guardar.
Terminar cierra la escucha conservando las decisiones anteriores. Para otro arreglo,
o la intención musical inicial, generar; elegí ensamble salvo que pida desarrollar
una canción larga. Para cambios fuera del editor podés proponer generar un arreglo
nuevo; pedí aclaración si eso cambiaría más de lo pedido. Para acciones sin pistas
usá lista vacía, para acciones sin dinámica usá 0. Respondé brevemente en español
si hace falta aclarar. No declares que ya hiciste cambios."""
