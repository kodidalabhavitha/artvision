import os
import secrets
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import models, schemas
from .database import Base, engine, get_db

Base.metadata.create_all(bind=engine)

app = FastAPI(title="ArtVision API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def require_admin(x_api_key: str = Header(default="")):
    expected = os.environ.get("ADMIN_API_KEY", "")
    if not expected or not secrets.compare_digest(x_api_key, expected):
        raise HTTPException(status_code=401, detail="Invalid API key")


def get_artwork_or_404(db: Session, slug: str) -> models.Artwork:
    art = db.scalar(select(models.Artwork).where(models.Artwork.slug == slug))
    if not art:
        raise HTTPException(status_code=404, detail="Artwork not found")
    return art


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/artworks", response_model=list[schemas.ArtworkOut])
def list_artworks(db: Session = Depends(get_db)):
    return db.scalars(select(models.Artwork).order_by(models.Artwork.id)).all()


@app.get("/artworks/{slug}", response_model=schemas.ArtworkOut)
def read_artwork(slug: str, db: Session = Depends(get_db)):
    return get_artwork_or_404(db, slug)


@app.post("/artworks", response_model=schemas.ArtworkOut, status_code=201,
          dependencies=[Depends(require_admin)])
def create_artwork(body: schemas.ArtworkIn, db: Session = Depends(get_db)):
    if db.scalar(select(models.Artwork).where(models.Artwork.slug == body.slug)):
        raise HTTPException(status_code=409, detail="Slug already exists")
    art = models.Artwork(**body.model_dump())
    db.add(art)
    db.commit()
    db.refresh(art)
    return art


@app.post("/artworks/{slug}/media", response_model=schemas.MediaOut, status_code=201,
          dependencies=[Depends(require_admin)])
def add_media(slug: str, body: schemas.MediaIn, db: Session = Depends(get_db)):
    art = get_artwork_or_404(db, slug)
    media = models.Media(artwork_id=art.id, **body.model_dump())
    db.add(media)
    db.commit()
    db.refresh(media)
    return media


@app.delete("/artworks/{slug}", status_code=204, dependencies=[Depends(require_admin)])
def delete_artwork(slug: str, db: Session = Depends(get_db)):
    db.delete(get_artwork_or_404(db, slug))
    db.commit()


@app.post("/scans", status_code=201)
def log_scan(body: schemas.ScanIn, db: Session = Depends(get_db),
             user_agent: str = Header(default="")):
    art = get_artwork_or_404(db, body.slug)
    db.add(models.Scan(artwork_id=art.id, user_agent=user_agent[:300]))
    db.commit()
    return {"logged": True}


@app.get("/stats", dependencies=[Depends(require_admin)])
def stats(db: Session = Depends(get_db)):
    rows = db.execute(
        select(models.Artwork.slug, models.Artwork.title, func.count(models.Scan.id))
        .outerjoin(models.Scan, models.Scan.artwork_id == models.Artwork.id)
        .group_by(models.Artwork.id)
        .order_by(models.Artwork.id)
    ).all()
    return [{"slug": s, "title": t, "scans": n} for s, t, n in rows]
