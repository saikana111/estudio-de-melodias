"""Translate an accepted musical direction into the instrument host's settings."""
def resolver_arreglo(plan):
    rock = plan.get("estilo") == "rock"
    defaults = dict(instrumento=27 if rock else 0, instrumento_bajo=34 if rock else 43,
                    respuestas=not rock, instrumento_respuestas=73, voces=3,
                    patron="bloques" if rock else "sostenido", notas="medias" if rock else "largas",
                    espacio="poco" if rock else "medio", bateria="rock" if rock else "ninguna")
    datos = {**defaults, **{k: v for k, v in plan.items() if v is not None}}
    datos["rasgueo"] = (24 <= datos["instrumento"] <= 31 and datos["voces"] > 1
                        and datos["patron"] != "arpegio")
    datos["progresion_rock"] = rock and plan.get("armonia") != "libre"
    return datos
