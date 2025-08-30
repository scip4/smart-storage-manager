# backend/services/radarr_service.py
import logging
import os
import requests
from typing import Dict, List, Optional
# --- Caching Integration ---
# Import the central cache instance and timeout setting for our application
from .cache_service import cache, CACHE_TIMEOUT


logger = logging.getLogger(__name__)

# --- Radarr API for Movies ---
class RadarrAPI:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({'X-Api-Key': api_key})

    def get_all_movies(self) -> List[Dict]:
        try:
            response = self.session.get(f'{self.base_url}/api/v3/movie')
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Radarr API error fetching movies: {e}", exc_info=True)
            return []
            
    def get_movie_by_id(self, movie_id: int) -> Optional[Dict]:
        """Get a single movie by ID"""
        try:
            response = self.session.get(f'{self.base_url}/api/v3/movie/{movie_id}')
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.warning(f"Could not fetch movie with ID {movie_id}: {e}")
            return None
            
    def get_root_folders(self) -> List[Dict]:
        """Get all root folders from Radarr"""
        try:
            response = self.session.get(f'{self.base_url}/api/v3/rootfolder')
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting Radarr root folders: {e}")
            return []

    def get_movie_files_for_movie(self, movie_id: int) -> List[Dict]:
        """Gets all movie files for a single movie."""
        try:
            response = self.session.get(f'{self.base_url}/api/v3/moviefile', params={'movieId': movie_id})
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.warning(f"Could not fetch movie files for movieId {movie_id}: {e}")
            return []

# --- Instantiate the API client at the module level for reuse ---
BASE_URL = os.getenv('RADARR_URL')
API_KEY = os.getenv('RADARR_API_KEY')

radarr_api = None
if BASE_URL and API_KEY:
    radarr_api = RadarrAPI(BASE_URL, API_KEY)
else:
    logger.warning("Radarr URL or API Key not configured in .env file.")

# --- Public functions for the rest of the application to use ---

def get_movie_size(movie_id: int) -> int:
    """
    Get the size on disk for a specific movie from Radarr
    
    Args:
        movie_id: Radarr movie ID
        
    Returns:
        Size on disk in bytes (0 if not found)
    """
    movie = radarr_api.get_movie_by_id(movie_id)
    if not movie:
        return 0
        
    movie_files = radarr_api.get_movie_files_for_movie(movie_id)
    return sum(f.get('size', 0) for f in movie_files)

def get_root_folders() -> List[Dict]:
    """Get all root folders from Radarr"""
    if not radarr_api:
        return []
    return radarr_api.get_root_folders()

def get_movie_title_id_map() -> Dict[str, int]:
    """
    Returns a dictionary mapping movie titles to their Radarr IDs.
    
    Returns:
        Dictionary of {title: id}
    """
    cached_movie_data = cache.get("Radarr_all_movies")
    #cache.set(cache_test, all_series, timeout=CACHE_TIMEOUT)



    if cached_movie_data is not None:
        logger.info("✅ Cache HIT! Returning Sonarr series from cache.")
        movies = cached_movie_data
        #return cached_data
    else:
        movies = radarr_api.get_all_movies()
    
    return {movie['title']: movie['id'] for movie in movies}
def get_library_summary() -> Dict:
    """
    Public function to get Sonarr stats. It uses a cache to avoid repeated slow API calls.
    """
    cache_key = "radarr_library_summary"
    
    # Try to get the data from the cache first
    cached_data = cache.get(cache_key)
    
    if cached_data is not None:
        logger.info("✅ Cache HIT! Returning Radarr summary from cache.")
        return cached_data
    
    # If not in cache, it's a "miss"
    logger.warning("⚠️  Cache MISS for Radarr summary. Fetching fresh data...")
    
    # Perform the slow calculation
    fresh_data = _get_library_summary()
    
    # Store the fresh data in the cache for next time
    if fresh_data and fresh_data['total_movies'] > 0:
        logger.info(f"Storing Radadd summary in cache for {CACHE_TIMEOUT} seconds.")
        cache.set(cache_key, fresh_data, timeout=CACHE_TIMEOUT)
        
    return fresh_data
def _get_library_summary() -> Dict:
    """
    Calculates total size and movie count for the Radarr movie library.
    This uses the optimized method for accuracy by summing movie files.
    """
    if not radarr_api:
        return {'total_gb': 0.0, 'total_movies': 0}

    logger.info("Calculating Radarr movie library size using accurate movie file summation.")


    all_movies = radarr_api.get_all_movies()
    cache_test = "Radarr_all_movies"

    cache_root_path = "Movie_root_path"
    # Try to get the data from the cache first
    #cached_data = cache.get(cache_key)
    cache.set(cache_test, all_movies, timeout=CACHE_TIMEOUT)
    if not all_movies:
        return {'total_gb': 0.0, 'total_movies': 0}

    total_size_bytes = 0
    movies_with_files = 0
    movie_data = {}
    movie_path = {}
    for i, movie in enumerate(all_movies):
        movie_id = movie['id']
        movie_files = radarr_api.get_movie_files_for_movie(movie_id)
        movie_data[movie_id] = movie_files
        movie_path[movie_id] = get_movie_root_folder(movie_id)
        if movie_files:  # Only count movies that have files
            movie_size = sum(f.get('size', 0) for f in movie_files)
            total_size_bytes += movie_size
            movies_with_files += 1
        
        if (i + 1) % 25 == 0:
            logger.debug(f"Processed {i+1}/{len(all_movies)} movies for size calculation...")

    total_gb = total_size_bytes / (1024**3)
    logger.info(f"Radarr movie library calculation complete. Total Size: {total_gb:.2f} GB, Movies with Files: {movies_with_files}")

    return {
        'total_gb': round(total_gb, 2),
        'total_movies': movies_with_files,
        'movieData': movie_data, 'moviePath': movie_path
    }

def update_movie_root_folder(movie_id: int, new_root_folder_path: str):
    """Updates a movie in Radarr to point to a new root folder."""
    if not radarr_api:
        return False, "Radarr not configured."
    
    try:
        logger.info(f"Updating Radarr: moving movie ID {movie_id} to root folder '{new_root_folder_path}'.")
        # Use the session from our API class
        movie_res = radarr_api.session.get(f'{radarr_api.base_url}/api/v3/movie/{movie_id}')
        movie_res.raise_for_status()
        movie_data = movie_res.json()

        movie_data["rootFolderPath"] = new_root_folder_path
        
        update_res = radarr_api.session.put(f'{radarr_api.base_url}/api/v3/movie/{movie_id}', json=movie_data)
        update_res.raise_for_status()
        
        radarr_api.session.post(f'{radarr_api.base_url}/api/v3/command', json={'name': 'RescanMovie', 'movieIds': [movie_id]})
        
        logger.info(f"Successfully updated movie ID {movie_id} in Radarr and triggered rescan.")
        return True, "Successfully updated movie's root folder in Radarr."
    except Exception as e:
        logger.error(f"Failed to update movie ID {movie_id} in Radarr: {e}", exc_info=True)
        return False, f"Failed to update movie in Radarr: {e}"
def get_movie_root_folder(movie_id: int) -> Optional[str]:
    """Get the root folder path for a specific Radarr movie"""
    if not radarr_api:
        return None
    try:
        # Fetch movie details
        response = radarr_api.session.get(f"{radarr_api.base_url}/api/v3/movie/{movie_id}")
        if response.status_code == 200:
            movie_data = response.json()
            return movie_data.get('rootFolderPath')
        else:
            logger.error(f"Failed to get movie data for ID {movie_id}: {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"Error fetching movie root folder: {e}", exc_info=True)
        return None

def move_radarr_movie(current_path, archive_root_path, movie_id):
    """Updates a movie's root folder path and triggers a file move in Radarr."""
    if not radarr_api:
        return False, "Radarr not configured."
    
    try:
        # Get the movie data
        movie_res = radarr_api.session.get(f'{radarr_api.base_url}/api/v3/movie/{movie_id}')
        movie_res.raise_for_status()
        movie_data = movie_res.json()
        movie_title = movie_data['title']
        
        # Update the movie_data with the new path and root folder
        movie_data['rootFolderPath'] = archive_root_path
        movie_data["path"] = f"{archive_root_path}/{movie_title}"
        
        # Use the radarr_api session to update
        update_res = radarr_api.session.put(
            f'{radarr_api.base_url}/api/v3/movie/{movie_id}',
            json=movie_data,
            params={'moveFiles': 'true'},
            timeout=60
        )
        update_res.raise_for_status()
        logger.info(f"Successfully moved movie '{movie_title}' to {archive_root_path}")
        return True, f"Successfully moved movie '{movie_title}'"
    except Exception as e:
        logger.error(f"Failed to move movie ID {movie_id}: {e}", exc_info=True)
        return False, f"Failed to move movie: {e}"
def get_upcoming_movies():
    # Placeholder - this function can remain for future use
    return []