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
    streamingServices: List[str] = field(default_factory=list)
    filePath: Optional[str] = None
    rootFolderPath: Optional[str] = None
    reason: Optional[str] = None

@dataclass
class StreamingCard:
    id: str
    title: str
    size: float
    streamingServices: List[str] = field(default_factory=list)
    filePath: Optional[str] = None
    rootFolderPath: Optional[str] = None

@dataclass
class SMovie(StreamingCard):
     type: str = 'Movie'

@dataclass
class SShow(StreamingCard):
     type: str = 'TV'

@dataclass
class Show(MediaItem):
    type: str = 'tv'
    seasons: int = 0
    episodes: int = 0
    sonarrId: Optional[int] = None
    status: Optional[str] = None  # Added for Sonarr status (e.g., 'Ended')
    
@dataclass
class Availability:
    provider: []
    all: []


@dataclass
class Media:
    all_media: []
    streaming_media: []


@dataclass
class Movie(MediaItem):
    type: str = 'movie'
    year: Optional[int] = None
    radarrId: Optional[int] = None

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