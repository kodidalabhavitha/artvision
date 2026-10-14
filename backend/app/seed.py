"""Import frontend/paintings.json into the database: python -m app.seed"""
import json
from sqlalchemy import select
from . import models
from .database import Base, SessionLocal, engine

Base.metadata.create_all(bind=engine)
items = json.load(open("/frontend/paintings.json"))
with SessionLocal() as db:
    for p in items:
        if db.scalar(select(models.Artwork).where(models.Artwork.slug == p["slug"])):
            print("exists:", p["slug"])
            continue
        art = models.Artwork(slug=p["slug"], title=p["title"],
                             image_path=p["image"], aspect=p["aspect"])
        art.media.append(models.Media(type="video", url=p["video"], title=p["title"]))
        db.add(art)
        print("added:", p["slug"])
    db.commit()
