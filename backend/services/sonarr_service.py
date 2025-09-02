import logging
import os
import requests
from typing import Dict, List, Optional

# --- Caching Integration ---
# Import the central cache instance and timeout setting for our application
from .cache_service import cache, CACHE_TIMEOUT

logger = logging.getLogger(__name__)

class SonarrAPI:
    """Encapsulates direct API communication with the Sonarr server."""
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({'X-Api-Key': api_key})

    def get_episode_files_for_series(self, series_id: int) -> List[Dict]:
        """Gets all episode files for a single series."""
        try:
            response = self.session.get(f'{self.base_url}/api/v3/episodefile', params={'seriesId': series_id})
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.warning(f"Could not fetch episode files for seriesId {series_id}: {e}")
            return []        
    def get_all_series(self) -> List[Dict]:
        try:
            response = self.session.get(f'{self.base_url}/api/v3/series')
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Sonarr API error fetching series: {e}", exc_info=True)
            return []
    def get_series_by_id(self, series_id: int) -> Optional[Dict]:
        """Get a single series by ID"""
        try:
            response = self.session.get(f'{self.base_url}/api/v3/series/{series_id}')
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.warning(f"Could not fetch series with ID {series_id}: {e}")
            return None


    def get_all_episode_files(self) -> List[Dict]:
        """Gets ALL episode files for the entire library in a single API call."""
        try:
            response = self.session.get(f'{self.base_url}/api/v3/episodefile')
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Could not fetch all episode files from Sonarr: {e}", exc_info=True)
            return []

# Instantiate the API client for reuse within this module
BASE_URL = os.getenv('SONARR_URL')
API_KEY = os.getenv('SONARR_API_KEY')
sonarr_api = SonarrAPI(BASE_URL, API_KEY) if BASE_URL and API_KEY else None


# --- NEW FUNCTION ---
def _get_root_folders() -> List[dict]: # Changed return type hint
    """Fetches all configured root folder objects from Sonarr."""
    if not sonarr_api:
        logger.warning("Cannot get Sonarr root folders: service not configured.")
        return []
    try:
        logger.debug("Fetching Sonarr root folders.")
        response = sonarr_api.session.get(f'{sonarr_api.base_url}/api/v3/rootfolder')
        response.raise_for_status()
        # --- FIX: Return the full list of folder objects ---
        return response.json()
    except Exception as e:
        logger.error(f"Failed to fetch Sonarr root folders: {e}", exc_info=True)
        return []


def get_root_folders() -> List[dict]:
    cache_key = "cache_sonarr_folders"

    # Try to get the data from the cache first
    cached_data = cache.get(cache_key)
    
    if cached_data is not None:
        logger.info("✅ Cache HIT! Returning Sonarr summary from cache.")
        return cached_data
    
    # If not in cache, it's a "miss"
    logger.warning("⚠️  Cache MISS for Sonarr summary. Fetching fresh data...")
    
    # Perform the slow calculation
    fresh_data = _get_root_folders()
    
    # Store the fresh data in the cache for next time
    if fresh_data:
        logger.info(f"Storing Sonarr folder in cache for {CACHE_TIMEOUT} seconds.")
        cache.set(cache_key, fresh_data, timeout=CACHE_TIMEOUT)
        #cache.set(cache_test, fresh_data['seriesData'], timeout=CACHE_TIMEOUT)
        
    return fresh_data

def _calculate_fresh_summary() -> Dict:
    """
    Performs the slow, uncached calculation by hitting the Sonarr API.
    This should only be called by the public function on a cache miss.
    """
    if not sonarr_api:
        return {'total_gb': 0.0, 'total_episodes': 0, 'series_details': []}

    logger.warning("--- Performing SLOW Sonarr library scan ---")
    
    #all_series = sonarr_api.get_all_series()
   # all_episode_files = sonarr_api.get_all_episode_files()

   # if not all_episode_files:
 #       return {'total_gb': 0.0, 'total_episodes': 0, 'total_series': 0}
 #       
 #   series_lookup = {series['id']: series for series in all_series}
 #   series_stats = {}
#
#    for file in all_episode_files:
#        series_id = file.get('seriesId')
#        if not series_id: continue
#        if series_id not in series_stats:
#            series_stats[series_id] = {'total_size_bytes': 0, 'episode_count': 0}
#        series_stats[series_id]['total_size_bytes'] += file.get('size', 0)
#        series_stats[series_id]['episode_count'] += 1
#
#    series_details = []
#    total_size_bytes = 0
#    total_episodes = 0
#    total_series =0
#    for series_id, stats in series_stats.items():
#        total_size_bytes += stats['total_size_bytes']
#        total_episodes += stats['episode_count']
#        total_series += total_series + 1

 #   total_gb = total_size_bytes / (1024**3)
 
    all_series = sonarr_api.get_all_series()
#Store in CACHE
    cache_test = "Sonarr_all_series"
    # Try to get the data from the cache first
    #cached_data = cache.get(cache_key)
    cache.set(cache_test, all_series, timeout=CACHE_TIMEOUT)

    if not all_series:
        return {'total_gb': 0.0, 'total_episodes': 0}

    total_size_bytes = 0
    total_episodes = 0
    seriesData = {}
    seriesSize = {}

    for i, series in enumerate(all_series):
        series_id = series['id']
        episode_files = sonarr_api.get_episode_files_for_series(series_id)
        seriesData[series_id] = episode_files
        series_size = sum(f.get('size', 0) for f in episode_files)
        seriesSize[series_id] = series_size
        series_ep_count = len(episode_files)

        total_size_bytes += series_size
        total_episodes += series_ep_count
        
        if (i + 1) % 25 == 0:
            logger.debug(f"Processed {i+1}/{len(all_series)} series for size calculation...")
    total_series = len(all_series)
    total_gb = total_size_bytes / (1024**3)
    logger.info(f"Sonarr library calculation complete. Total Size: {total_gb:.2f} GB, Total Episodes: {total_episodes}")

    #return {
    #    'total_gb': round(total_gb, 2),
    #    'total_episodes': total_episodes,
    #    'total_series': total_series
    #}
 
 
 
 
 
 
 
 
    logger.info(f"Sonarr fresh scan complete. Total Size: {total_gb:.2f} GB")

    return {
        'total_gb': round(total_gb, 2),
        'total_episodes': total_episodes, 'total_series': total_series,
         'seriesData': seriesData, 'seriesSize': seriesSize
         #, 'total_series': len(series_stats)
    }
def get_series_title_id_map() -> Dict[str, int]:
    """
    Returns a dictionary mapping series titles to their Sonarr IDs.
    
    Returns:
        Dictionary of {title: id}
    """
    cached_series_data = cache.get("Sonarr_all_series")
    #cache.set(cache_test, all_series, timeout=CACHE_TIMEOUT)



    if cached_series_data is not None:
        logger.info("✅ Cache HIT! Returning Sonarr series from cache.")
        series_list = cached_series_data
        #return cached_data
    else:
        series_list = sonarr_api.get_all_series()
    
    return {series['title']: series['id'] for series in series_list}

def get_library_summary() -> Dict:
    """
    Public function to get Sonarr stats. It uses a cache to avoid repeated slow API calls.
    """
    cache_key = "sonarr_library_summary"
    cache_test = "series_data"
    # Try to get the data from the cache first
    cached_data = cache.get(cache_key)
    
    if cached_data is not None:
        logger.info("✅ Cache HIT! Returning Sonarr summary from cache.")
        return cached_data
    
    # If not in cache, it's a "miss"
    logger.warning("⚠️  Cache MISS for Sonarr summary. Fetching fresh data...")
    
    # Perform the slow calculation
    fresh_data = _calculate_fresh_summary()
    
    # Store the fresh data in the cache for next time
    if fresh_data and fresh_data['total_episodes'] > 0:
        logger.info(f"Storing Sonarr summary in cache for {CACHE_TIMEOUT} seconds.")
        cache.set(cache_key, fresh_data, timeout=CACHE_TIMEOUT)
        cache.set(cache_test, fresh_data['seriesData'], timeout=CACHE_TIMEOUT)
        
    return fresh_data


def get_series_size(show_id: int) -> int:
    """
    Get the size on disk for a specific series from Sonarr
    
    Args:
        show_id: Sonarr series ID
        
    Returns:
        Size on disk in bytes (0 if not found)
    """
    series = sonarr_api.get_series_by_id(show_id)
    if not series:
        return 0
        
    statistics = series.get('statistics', {})
    return statistics.get('sizeOnDisk', 0)


def update_show_root_folder(show_id: int, new_root_folder_path: str):
    """Updates a show in Sonarr and clears the cache to reflect changes."""
    if not sonarr_api: return False, "Sonarr not configured."
    
    try:
        logger.info(f"Updating Sonarr root folder for show ID {show_id}.")
        show_res = sonarr_api.session.get(f'{sonarr_api.base_url}/api/v3/series/{show_id}')
        show_res.raise_for_status()
        show_data = show_res.json()

        show_data["rootFolderPath"] = new_root_folder_path
        
        update_res = sonarr_api.session.put(f'{sonarr_api.base_url}/api/v3/series/{show_id}', json=show_data)
        update_res.raise_for_status()
        
        sonarr_api.session.post(f'{sonarr_api.base_url}/api/v3/command', json={'name': 'RescanSeries', 'seriesId': show_id})
        
        # --- CACHE INVALIDATION ---
        # The summary is now outdated, so we must clear it.
        logger.info("Sonarr data changed. Clearing library summary cache.")
        cache.delete("sonarr_library_summary")
        
        return True, "Successfully updated show's root folder in Sonarr."
    except Exception as e:
        logger.error(f"Failed to update show ID {show_id} in Sonarr: {e}", exc_info=True)
        return False, f"Failed to update show in Sonarr: {e}"

def unmonitor_show(show_id: int):
    """Updates a show in Sonarr and clears the cache to reflect changes."""
    if not sonarr_api: return False, "Sonarr not configured."
    
    try:
        logger.info(f"Updating Sonarr root folder for show ID {show_id}.")
        show_res = sonarr_api.session.get(f'{sonarr_api.base_url}/api/v3/series/{show_id}')
        show_res.raise_for_status()
        show_data = show_res.json()

        show_data["monitored"] = false
        
        update_res = sonarr_api.session.put(f'{sonarr_api.base_url}/api/v3/series/{show_id}', json=show_data)
        update_res.raise_for_status()
        
        sonarr_api.session.post(f'{sonarr_api.base_url}/api/v3/command', json={'name': 'RescanSeries', 'seriesId': show_id})
        
        # --- CACHE INVALIDATION ---
        # The summary is now outdated, so we must clear it.
        logger.info("Sonarr data changed. Clearing library summary cache.")
        cache.delete("sonarr_library_summary")
        
        return True, "Successfully updated show's root folder in Sonarr."
    except Exception as e:
        logger.error(f"Failed to update show ID {show_id} in Sonarr: {e}", exc_info=True)
        return False, f"Failed to update show in Sonarr: {e}"


def get_series_root_folder(series_id: int) -> Optional[str]:
    """Get the root folder path for a specific Sonarr series"""
    if not sonarr_api:
        return None
    try:
        # Fetch series details
        response = sonarr_api.session.get(f"{sonarr_api.base_url}/api/v3/series/{series_id}")
        if response.status_code == 200:
            series_data = response.json()
            return series_data.get('rootFolderPath')
        else:
            logging.error(f"Failed to get series data for ID {series_id}: {response.status_code}")
            return None
    except Exception as e:
        logging.error(f"Error fetching series root folder: {e}")
        return None


def get_upcoming_shows():
    # This can also be cached if it becomes a performance issue
    return []