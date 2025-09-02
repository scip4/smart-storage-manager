# backend/services/plex_service.py
import os
import logging
import requests
from plexapi.server import PlexServer
from models import Show, Movie, SMovie, SShow, Availability, Media
from services import sonarr_service, radarr_service
from .cache_service import cache, CACHE_TIMEOUT

logger = logging.getLogger(__name__)

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
        all_providers = provider_names
        # Filter by STREAMING_PROVIDERS if set
        streaming_providers_env = os.getenv('STREAMING_PROVIDERS')
        if streaming_providers_env:
            # Split, trim, and lowercase for case-insensitive matching
            allowed_providers = [p.strip().lower() for p in streaming_providers_env.split(',')]
            # Filter provider names
            provider_names = [name for name in provider_names
                             if name.strip().lower() in allowed_providers]
        
        return Availability(provider_names, all_providers)
    except Exception as e:
        print(f"Error checking streaming availability: {e}")
        return Availability([], [])

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
        sona
        return True, f"Successfully deleted media with ID {media_id}"
    except Exception as e:
        error_msg = f"Error deleting media with ID {media_id}: {str(e)}"
        print(error_msg)
        return False, error_msg

def get_plex_library():
    """
    Public function to get Sonarr stats. It uses a cache to avoid repeated slow API calls.
    """
    cache_key = "plex_media"
    cache_key_card = "streaming_card"
    # Try to get the data from the cache first
    cached_data = cache.get(cache_key)
    cache_card_data = cache.get(cache_key_card)
    if cached_data is not None:
        logger.info("✅ Cache HIT! Returning Plex media from cache.")
        return cached_data
    
    # If not in cache, it's a "miss"
    logger.warning("⚠️  Cache MISS for Plex media. Fetching fresh data...")
    """  datac = _get_plex_library()
    # Perform the slow calculation
    fresh_data = datac.all_media
    fresh_card_data = datac.streaming_media
    
    # Store the fresh data in the cache for next time
    if fresh_data and len(fresh_data) > 0:
        logger.info(f"Storing Plex Mediain cache for {CACHE_TIMEOUT} seconds.")
        cache.set(cache_key, fresh_data, timeout=CACHE_TIMEOUT)
        
    return fresh_data """


     # --- MODIFIED PART ---
    # Call the internal function and get the full Media object
    fresh_data_object = _get_plex_library()
    
    # Store the entire object in the cache
    if fresh_data_object and fresh_data_object.all_media:
        logger.info(f"Storing full Plex Media object in cache for {CACHE_TIMEOUT} seconds.")
        cache.set(cache_key, fresh_data_object, timeout=CACHE_TIMEOUT)
        
    return fresh_data_object

def _get_plex_library():
    plex = get_plex_connection()
    if not plex: return []

    all_media = []
    # Get title-to-ID mappings for shows and movies

    streaming_media = []

    sonarr_title_id_map = sonarr_service.get_series_title_id_map()
    radarr_title_id_map = radarr_service.get_movie_title_id_map()
    cached_sonarr_data = cache.get("sonarr_summary_raw")
    cached_radarr_data = cache.get("radarr_summary_raw")

    for section in plex.library.sections():
        if section.type == 'movie':
            for movie in section.all():
                size_gb = movie.media[0].parts[0].size / (1024**3) if movie.media else 0
                movie_id = radarr_title_id_map.get(movie.title)
                spath = '/'   # default root path
                if movie_id is not None:
                    # Safely get the moviePath dictionary from cached_radarr_data
                    movie_paths = cached_radarr_data.get('moviePath', {})
                    # If we have a non-None value for this movie_id, use it
                    if movie_id in movie_paths and movie_paths[movie_id] is not None:
                        spath = movie_paths[movie_id]
                # Check streaming availability
                streaming_services = ''
                if size_gb > 15:
                      ss = check_streaming_availability(movie.title, 'movie')
                      streaming_services = ss.provider
                      if ss.all is not None:
                        streaming_media.append(SMovie(
                            id=movie.ratingKey,
                            title=movie.title,
                            size=size_gb,
                            streamingServices=ss.all,
                            filePath=movie.media[0].parts[0].file if movie.media else None,
                            rootFolderPath=spath
                      ))
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
                        #Cace series Data Test
                        #show_size = 
                        show_size = 0
                        if cached_sonarr_data is not None:
                            # Safely get the seriesSize dictionary from cached_sonarr_data
                            series_size_dict = cached_sonarr_data.get('seriesSize', {})
                            # If we have a value for this sonarr_id, use it
                            if sonarr_id in series_size_dict and series_size_dict[sonarr_id] is not None:
                                show_size = series_size_dict[sonarr_id]
                        if show_size == 0:
                            # Only fetch from Sonarr if we don't have a cached value
                            show_size = sonarr_service.get_series_size(sonarr_id) or 0
                        size_gb = show_size / (1024**3) if show_size else 0
                        try:
                            sonarr_show = sonarr_service.sonarr_api.get_series_by_id(sonarr_id)
                            if sonarr_show:
                                show_status = sonarr_show.get('status')
                        except Exception as e:
                            print(f"Error getting Sonarr show data: {e}")
                            show_status = None
                    except Exception as e:
                        print(f"Error getting Sonarr data for show {show.title}: {e}")
                
                # If size wasn't set, use default 0
                if size_gb == 0:
                    size_gb = sonarr_service.get_series_size(sonarr_id) / (1024**3) if sonarr_id else 0
                
                # Check streaming availability
                if size_gb >=10:
                    stv = check_streaming_availability(show.title, 'tv')
                    streaming_services = stv.provider
                    if len(stv.all) > 0:
                        streaming_media.append(SShow(
                        id=show.ratingKey,
                        title=show.title,
                        size=size_gb,
                        streamingServices=stv.all,
                        filePath=show.locations[0] if show.locations else None,
                        rootFolderPath=spath
                        ))

                else:
                    streaming_services = 'TV Show under 10GB'    
                
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
    return Media(all_media, streaming_media)