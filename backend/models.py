# backend/models.py
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class MediaItem:
    id: str
    #type: str
    title: str
    size: float
    lastWatched: Optional[str]
    watchCount: int
    status: str = 'active'
    rule: str = 'auto-manage'
    streamingAvailability: List[str] = field(default_factory=list)
    filePath: Optional[str] = None

@dataclass
class Show(MediaItem):
    type: str = 'tv'
    seasons: int = 0
    episodes: int = 0
    sonarrId: Optional[int] = None  # --- NEW ---

@dataclass
class Movie(MediaItem):
    type: str = 'movie'
    year: Optional[int] = None
    radarrId: Optional[int] = None  # --- NEW ---

@dataclass
class UpcomingRelease:
    type: str
    title: str
    estimatedSize: float
    releaseDate: str

@dataclass
class StorageInfo:
    total: float
    used: float
    available: float

@dataclass
class Show(MediaItem):
    type: str = 'tv'
    seasons: int = 0
    episodes: int = 0
    sonarrId: Optional[int] = None
    totalEpisodes: Optional[int] = 0 # --- NEW ---