# backend/services/plex_service.py
import os
import logging
import requests
from plexapi.server import PlexServer
from models import Show, Movie, SMovie, SShow, Availability, Media
from services import sonarr_service, radarr_service
from .cache_service import cache, CACHE_TIMEOUT
from .settings_service import load_settings
logger = logging.getLogger(__name__)


_plex_client = None

def get_plex_connection():
    """Singleton factory for the PlexServer connection."""
    global _plex_client
    
    if _plex_client is None:
        logger.debug("Initializing Plex connection for the first time.")
        baseurl = os.getenv('PLEX_URL')
        token = os.getenv('PLEX_TOKEN')
        if not baseurl or not token:
            logger.warning("Cannot connect to Plex: PLEX_URL or PLEX_TOKEN not set.")
            return None
        try:
            _plex_client = PlexServer(baseurl, token)
        except Exception as e:
            logger.error(f"Failed to connect to Plex server: {e}")
            return None
            
    return _plex_client



def is_tv_archive_folder(path: str) -> bool:
    """Check if a path is listed in TV_ARCHIVE_FOLDERS environment variable"""
    if not path:
        return False
    settings = load_settings()
    tv_folders = settings.get('TV_ARCHIVE_FOLDERS', []) # Get the list from settings    
    #tv_folders = os.getenv('TV_ARCHIVE_FOLDERS', '')
    if not tv_folders:
        return False
    
    # Normalize paths for comparison
    normalized_path = os.path.normpath(path)
    #archive_paths = [os.path.normpath(f.strip()) for f in tv_folders.split(',') if f.strip()]
    archive_paths = [os.path.normpath(f.strip()) for f in tv_folders if f.strip()]
    return normalized_path in archive_paths

def is_movie_archive_folder(path: str) -> bool:
    """Check if a path is listed in MOVIE_ARCHIVE_FOLDERS environment variable"""
    if not path:
        return False
    settings = load_settings()
    movie_folders = settings.get('MOVIE_ARCHIVE_FOLDERS', [])    
    #movie_folders = os.getenv('MOVIE_ARCHIVE_FOLDERS', '')
    if not movie_folders:
        return False
    
    # Normalize paths for comparison
    normalized_path = os.path.normpath(path)
    archive_paths = [os.path.normpath(f.strip()) for f in movie_folders if f.strip()]
    #archive_paths = [os.path.normpath(f.strip()) for f in movie_folders.split(',') if f.strip()]
    
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

    settings = load_settings()
    API_KEY = settings.get('TMDB_API_KEY')
    #API_KEY = os.getenv('TMDB_API_KEY')
    if not API_KEY:
        return Availability([], [])
    
    # First, search for the media ID
    search_url = f"https://api.themoviedb.org/3/search/{media_type}"
    params = {'api_key': API_KEY, 'query': title}
    try:
        response = requests.get(search_url, params=params)
        response.raise_for_status()
        results = response.json().get('results', [])
        if not results:
            return Availability([], [])
        
        # Get the first result
        media_id = results[0]['id']
        
        # Get streaming providers
        providers_url = f"https://api.themoviedb.org/3/{media_type}/{media_id}/watch/providers"
        response = requests.get(providers_url, params={'api_key': API_KEY})
        response.raise_for_status()
        providers = response.json().get('results', {}).get('US', {}).get('flatrate', [])
        provider_names = [provider['provider_name'] for provider in providers]
        
        all_provider_names = [p['provider_name'] for p in providers]
        
        # --- Use preferred providers from settings ---
        preferred_providers = settings.get('STREAMING_PROVIDERS', [])
        
        if preferred_providers:
            allowed_providers_lower = {p.strip().lower() for p in preferred_providers}
            filtered_provider_names = [name for name in all_provider_names if name.strip().lower() in allowed_providers_lower]
            return Availability(filtered_provider_names, all_provider_names)
        else:
            # If no providers are selected in settings, return none as "preferred"
            return Availability([], all_provider_names)
        
        
        
        # all_providers = provider_names
        # # Filter by STREAMING_PROVIDERS if set
        # streaming_providers_env = os.getenv('STREAMING_PROVIDERS')
        #  preferred_providers = settings.get('STREAMING_PROVIDERS', [])
        # if streaming_providers_env:
        #     # Split, trim, and lowercase for case-insensitive matching
        #     allowed_providers = [p.strip().lower() for p in streaming_providers_env.split(',')]
        #     # Filter provider names
        #     provider_names = [name for name in provider_names
        #                      if name.strip().lower() in allowed_providers]
        
        # return Availability(provider_names, all_providers)
    except Exception as e:
        print(f"Error checking streaming availability: {e}")
        return Availability([], [])





# def get_plex_connection():
#     # ... (no changes to this function)
#     baseurl = os.getenv('PLEX_URL')
#     token = os.getenv('PLEX_TOKEN')
#     logger.warning(f"⚠️  .env load check...{baseurl}  {token}")
#     if not baseurl or not token: return  None #print("Successfully connected to Plex server!") #None
#     try: return PlexServer(baseurl, token)
#     #except Exception: return None
    
#     # You can now interact with your Plex server using the 'plex' objec
#     except Exception as e:
#        print(f"Error connecting to Plex server: {e}")
#        return None
def delete_media_from_plex(media_id: str) -> tuple[bool, str]:
    """
    Delete media from Plex by its media ID (ratingKey)
    
    Args:
        media_id: The ratingKey of the media item to delete
        
    Returns:
        Tuple (success: bool, message: str)
    """
    plex = get_plex_connection()
    if not plex:
        return False, "Failed to connect to Plex server"
        
    try:
        key = f'/library/metadata/{media_id}'
        media_item = plex.fetchItem(key)
        media_item.delete()
        return True, f"Successfully deleted media with ID {media_id}"
    except Exception as e:
        error_msg = f"Error deleting media with ID {media_id}: {str(e)}"
        print(error_msg)
        return False, error_msg

# --- CORRECTED Caching and Public Function ---
def get_plex_library(sonarr_map=None):
    """
    Public function to get all Plex media, using a cache.
    This function CONSISTENTLY returns the full Media object.
    """
    cache_key = "plex_media_data_full"
    
    cached_data = cache.get(cache_key)
    if cached_data is not None:
        logger.info("✅ Cache HIT! Returning full Plex media object from cache.")
        return cached_data
    
    logger.warning("⚠️ Cache MISS for full Plex media object. Fetching fresh data...")
    
    fresh_data_object = _get_plex_library(sonarr_map=sonarr_map)
    
    if fresh_data_object and fresh_data_object.all_media:
        logger.info(f"Storing full Plex Media object in cache for {CACHE_TIMEOUT} seconds.")
        cache.set(cache_key, fresh_data_object, timeout=CACHE_TIMEOUT)
        
    return fresh_data_object


# --- REFACTORED AND CORRECTED Internal Function ---
def _get_plex_library(sonarr_map=None):
    """
    Internal function to perform the actual library scan.
    It relies on the sonarr_map passed from sync_service for all Sonarr data.
    """
    plex = get_plex_connection()
    if not plex:
        return Media([], []) # Return an empty Media object on failure

    # If no map is provided (e.g., direct call), fetch a basic one as a fallback.
    if sonarr_map is None:
        logger.warning("No sonarr_map provided to _get_plex_library, fetching fallback map.")
        sonarr_summary = sonarr_service.get_library_summary()
        sonarr_map = sonarr_summary.get('series_map', {})

    all_media = []
    streaming_media = []

    # Get title-to-ID mappings once
    sonarr_title_id_map = {details['title']: sid for sid, details in sonarr_map.items()}
    radarr_title_id_map = radarr_service.get_movie_title_id_map() # Assuming this works

    logger.info("Starting Plex library scan...")
    for section in plex.library.sections():
        if section.type == 'movie':
            logger.debug(f"Scanning movie section: {section.title}")
            for movie in section.all():
                size_gb = movie.media[0].parts[0].size / (1024**3) if movie.media else 0
                radarr_id = radarr_title_id_map.get(movie.title)
                spath = radarr_service.get_movie_root_folder(radarr_id) # Assumes this function exists
                
                streaming_info = check_streaming_availability(movie.title, 'movie')
                
                if size_gb > 15 and streaming_info.all:
                    streaming_media.append(SMovie(
                        id=movie.ratingKey, title=movie.title, size=size_gb,
                        streamingServices=streaming_info.all,
                        filePath=movie.media[0].parts[0].file if movie.media else None,
                        rootFolderPath=spath
                    ))
                    
                all_media.append(Movie(
                    id=movie.ratingKey, title=movie.title, year=movie.year, size=round(size_gb, 2),
                    lastWatched=movie.lastViewedAt.strftime('%Y-%m-%d') if movie.lastViewedAt else None,
                    watchCount=movie.viewCount,
                    filePath=movie.media[0].parts[0].file if movie.media else None,
                    radarrId=radarr_id,
                    rootFolderPath=spath,
                    streamingServices=streaming_info.provider,
                    rule='delete-if-streaming' if streaming_info.provider else None,
                ))

        elif section.type == 'show':
            logger.debug(f"Scanning TV section: {section.title}")
            for show in section.all():
                sonarr_id = sonarr_title_id_map.get(show.title)
                
                # --- SIMPLIFIED AND CORRECTED LOGIC ---
                show_status = None
                size_gb = 0
                spath = None

                if sonarr_id and sonarr_id in sonarr_map:
                    sonarr_details = sonarr_map[sonarr_id]
                    show_status = sonarr_details.get('status')
                    size_bytes = sonarr_details.get('sizeOnDisk', 0)
                    size_gb = size_bytes / (1024**3)
                    spath = sonarr_details.get('path')
                else:
                    logger.debug(f"Show '{show.title}' not found in Sonarr map.")

                streaming_info = check_streaming_availability(show.title, 'tv')
                
                if size_gb >= 10 and streaming_info.all:
                    streaming_media.append(SShow(
                        id=show.ratingKey, title=show.title, size=size_gb,
                        streamingServices=streaming_info.all,
                        filePath=show.locations[0] if show.locations else None,
                        rootFolderPath=spath
                    ))
                
                all_media.append(Show(
                    id=show.ratingKey, title=show.title, seasons=show.childCount,
                    episodes=show.leafCount, size=round(size_gb, 2),
                    lastWatched=show.lastViewedAt.strftime('%Y-%m-%d') if show.lastViewedAt else None,
                    watchCount=show.viewCount,
                    filePath=show.locations[0] if show.locations else None,
                    rootFolderPath=spath,
                    sonarrId=sonarr_id,
                    streamingServices=streaming_info.provider,
                    status='archived' if is_tv_archive_folder(spath) else show_status
                ))

    logger.info("Plex library scan finished.")
    return Media(all_media, streaming_media)