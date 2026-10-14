from pydantic import BaseModel, ConfigDict


class MediaIn(BaseModel):
    type: str = "video"
    url: str
    title: str = ""


class MediaOut(MediaIn):
    model_config = ConfigDict(from_attributes=True)
    id: int


class ArtworkIn(BaseModel):
    slug: str
    title: str
    description: str = ""
    image_path: str = ""
    aspect: float = 1.0
    status: str = "published"


class ArtworkOut(ArtworkIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
    media: list[MediaOut] = []


class ScanIn(BaseModel):
    slug: str
