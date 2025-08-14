# backend/services/plex_service.py
import os
from plexapi.server import PlexServer
from models import Show, Movie
from services import sonarr_service, radarr_service

def get_plex_connection():
    # ... (no changes to this function)
    baseurl = os.getenv('PLEX_URL')
    token = os.getenv('PLEX_TOKEN')
    if not baseurl or not token: return  None #print("Successfully connected to Plex server!") #None
    try: return PlexServer(baseurl, token)
    #except Exception: return None
     
    # You can now interact with your Plex server using the 'plex' objec
    except Exception as e:
       print(f"Error connecting to Plex server: {e}")
       return None

def get_plex_library():
    plex = get_plex_connection()
    if not plex: return []

    all_media = []
    for section in plex.library.sections():
        if section.type == 'movie':
            for movie in section.all():
                size_gb = movie.media[0].parts[0].size / (1024**3) if movie.media else 0
                all_media.append(Movie(
                    id=movie.ratingKey,
                    title=movie.title, year=movie.year, size=round(size_gb, 2),
                    lastWatched=movie.lastViewedAt.strftime('%Y-%m-%d') if movie.lastViewedAt else None,
                    watchCount=movie.viewCount,
                    filePath=movie.media[0].parts[0].file if movie.media else None,
                    radarrId=None # In a real app, you would map this
                ))
        elif section.type == 'show':
            for show in section.all():
                size_gb = 0 #show.sizeOnDisk / (1024**3)
                # --- NEW: Simulate mapping a Sonarr ID for testing the archive feature ---
                # A real implementation requires a robust mapping strategy (e.g., query Sonarr by title/year)
                sonarr_id_for_item = None
                if 'CSI' in show.title:
                    sonarr_id_for_item = 1 # Example ID, change to a real ID from your Sonarr instance
                tes = sonarr_service.get_series_info(1)
                all_media.append(Show(
                    id=show.ratingKey,
                    title=show.title, seasons=show.childCount, episodes=show.leafCount, size=round(size_gb, 2),
                    lastWatched=show.lastViewedAt.strftime('%Y-%m-%d') if show.lastViewedAt else None,
                    watchCount=show.viewCount,
                    filePath=show.locations[0] if show.locations else None,
                    sonarrId=sonarr_id_for_item # --- NEW ---
                ))
    return all_media