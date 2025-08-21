# backend/services/plex_service.py
import os
import requests
from plexapi.server import PlexServer
from models import Show, Movie
from services import sonarr_service, radarr_service

def is_tv_archive_folder(path: str) -> bool:
    """Check if a path is listed in TV_ARCHIVE_FOLDERS environment variable"""
    if not path:
        return False
        
    tv_folders = os.getenv('TV_ARCHIVE_FOLDERS', '')
    if not tv_folders:
        return False
    
    # Normalize paths for comparison
    normalized_path = os.path.normpath(path)
    archive_paths = [os.path.normpath(f.strip()) for f in tv_folders.split(',') if f.strip()]
    
    return normalized_path in archive_paths

def is_movie_archive_folder(path: str) -> bool:
    """Check if a path is listed in MOVIE_ARCHIVE_FOLDERS environment variable"""
    if not path:
        return False
        
    movie_folders = os.getenv('MOVIE_ARCHIVE_FOLDERS', '')
    if not movie_folders:
        return False
    
    # Normalize paths for comparison
    normalized_path = os.path.normpath(path)
    archive_paths = [os.path.normpath(f.strip()) for f in movie_folders.split(',') if f.strip()]
    
    return normalized_path in archive_paths

# Helper function to check streaming availability
def check_streaming_availability(title: str, media_type: str) -> list:
    """
    Check if a title is available on popular streaming services.
    Uses The Movie Database (TMDB) API to find streaming providers.
    
    Args:
        title: Title of the media
        media_type: 'movie' or 'tv'
        
    Returns:
        List of streaming service names where the title is available
    """
    API_KEY = os.getenv('TMDB_API_KEY')
    if not API_KEY:
        return []
    
    # First, search for the media ID
    search_url = f"https://api.themoviedb.org/3/search/{media_type}"
    params = {'api_key': API_KEY, 'query': title}
    try:
        response = requests.get(search_url, params=params)
        response.raise_for_status()
        results = response.json().get('results', [])
        if not results:
            return []
        
        # Get the first result
        media_id = results[0]['id']
        
        # Get streaming providers
        providers_url = f"https://api.themoviedb.org/3/{media_type}/{media_id}/watch/providers"
        response = requests.get(providers_url, params={'api_key': API_KEY})
        response.raise_for_status()
        providers = response.json().get('results', {}).get('US', {}).get('flatrate', [])
        provider_names = [provider['provider_name'] for provider in providers]
        
        # Filter by STREAMING_PROVIDERS if set
        streaming_providers_env = os.getenv('STREAMING_PROVIDERS')
        if streaming_providers_env:
            # Split, trim, and lowercase for case-insensitive matching
            allowed_providers = [p.strip().lower() for p in streaming_providers_env.split(',')]
            # Filter provider names
            provider_names = [name for name in provider_names
                             if name.strip().lower() in allowed_providers]
        
        return provider_names
    except Exception as e:
        print(f"Error checking streaming availability: {e}")
        return []

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
    # Get title-to-ID mappings for shows and movies
    sonarr_title_id_map = sonarr_service.get_series_title_id_map()
    radarr_title_id_map = radarr_service.get_movie_title_id_map()
    
    for section in plex.library.sections():
        if section.type == 'movie':
            for movie in section.all():
                size_gb = movie.media[0].parts[0].size / (1024**3) if movie.media else 0
                movie_id = radarr_title_id_map.get(movie.title)
                spath = radarr_service.get_movie_root_folder(movie_id)
                # Check streaming availability
                streaming_services = check_streaming_availability(movie.title, 'movie')
                
                all_media.append(Movie(
                    id=movie.ratingKey,
                    title=movie.title, year=movie.year, size=round(size_gb, 2),
                    lastWatched=movie.lastViewedAt.strftime('%Y-%m-%d') if movie.lastViewedAt else None,
                    watchCount=movie.viewCount,
                    filePath=movie.media[0].parts[0].file if movie.media else None,
                    radarrId=radarr_title_id_map.get(movie.title),
                    rootFolderPath=spath,
                    streamingServices=streaming_services,
                    rule= 'delete-if-streaming' if streaming_services else None,
                    #status=movie.status
                ))
        elif section.type == 'show':
            for show in section.all():
                sonarr_id = sonarr_title_id_map.get(show.title)
                show_status = None
                size_gb = 0
                spath = sonarr_service.get_series_root_folder(sonarr_id)
                # Get show status from Sonarr if available
                if sonarr_id:
                    try:
                        # Get size and status in one call
                        show_size = sonarr_service.get_series_size(sonarr_id)
                        size_gb = show_size / (1024**3) if show_size else 0
                        sonarr_show = sonarr_service.sonarr_api.get_series_by_id(sonarr_id)
                        if sonarr_show:
                            show_status = sonarr_show.get('status')
                    except Exception as e:
                        print(f"Error getting Sonarr data for show {show.title}: {e}")
                
                # If size wasn't set, use default 0
                if size_gb == 0:
                    size_gb = sonarr_service.get_series_size(sonarr_id) / (1024**3) if sonarr_id else 0
                
                # Check streaming availability
                streaming_services = check_streaming_availability(show.title, 'tv')
                
                all_media.append(Show(
                    id=show.ratingKey,
                    title=show.title,
                    seasons=show.childCount,
                    episodes=show.leafCount,
                    size=round(size_gb, 2),
                    lastWatched=show.lastViewedAt.strftime('%Y-%m-%d') if show.lastViewedAt else None,
                    watchCount=show.viewCount,
                    filePath=show.locations[0] if show.locations else None,
                    rootFolderPath=spath,
                    sonarrId=sonarr_id,
                    streamingServices=streaming_services,
                    status= 'archive-ended' if is_tv_archive_folder(spath) == True else show_status
                ))
    return all_media