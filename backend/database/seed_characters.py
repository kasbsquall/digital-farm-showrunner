"""Seed the base farm cast so Agent 1 has continuity from day one.

Run:  python -m database.seed_characters
"""
from database.db import Base, engine, SessionLocal
from database.models import Character

BASE_CAST = [
    {
        "name": "Bruno",
        "species": "gallo",
        "personality": "Líder sindical incansable, siempre organizando huelgas y asambleas por el bien del gallinero.",
        "visual_desc": "Gallo robusto de plumaje rojo intenso, cresta enorme, siempre con una pequeña pancarta bajo el ala.",
    },
    {
        "name": "Lola",
        "species": "vaca",
        "personality": "Romántica empedernida, perdidamente enamorada del tractor que nunca le corresponde.",
        "visual_desc": "Vaca blanca con manchas negras, ojos grandes y soñadores, a menudo con una flor en la oreja.",
    },
    {
        "name": "Tractor",
        "species": "tractor",
        "personality": "Máquina sin sentimientos, indiferente y monosilábico, jamás corresponde a Lola.",
        "visual_desc": "Tractor rojo viejo y oxidado, faros que parecen ojos vacíos, humo saliendo del tubo de escape.",
    },
    {
        "name": "Pepe",
        "species": "cerdo",
        "personality": "Filósofo del lodo, comenta todo con frases profundas que no tienen ningún sentido real.",
        "visual_desc": "Cerdo rosado rechoncho y pensativo, siempre recostado en el barro con una brizna de paja en la boca.",
    },
    {
        "name": "Nina",
        "species": "gallina",
        "personality": "Reportera del gallinero, documenta cada evento como noticia de última hora.",
        "visual_desc": "Gallina marrón pequeña y nerviosa, con una libretita y un lápiz atado a la pata.",
    },
]


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        added = 0
        for data in BASE_CAST:
            exists = db.query(Character).filter_by(name=data["name"]).first()
            if exists:
                continue
            db.add(Character(**data))
            added += 1
        db.commit()
        print(f"Seed completo. Personajes nuevos añadidos: {added}. Total en la granja: {db.query(Character).count()}")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
