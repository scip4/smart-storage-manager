# backend/services/sonarr_service.py
import logging
import os
import requests
from dotenv import load_dotenv
from typing import Dict, List, Optional

load_dotenv()

logger = logging.getLogger(__name__)

# --- Logic adapted from the provided sonarr_sizes.py script ---
class SonarrAPI:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({'X-Api-Key': api_key})

    def get_all_series(self) -> List[Dict]:
        try:
            response = self.session.get(f'{self.base_url}/api/v3/series')
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Sonarr API error fetching series: {e}", exc_info=True)
            return []
            
    def get_episode_files_for_series(self, series_id: int) -> List[Dict]:
        """Gets all episode files for a single series."""
        try:
            response = self.session.get(f'{self.base_url}/api/v3/episodefile', params={'seriesId': series_id})
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.warning(f"Could not fetch episode files for seriesId {series_id}: {e}")
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

# --- Instantiate the API client at the module level for reuse ---
BASE_URL = os.getenv('SONARR_URL')
API_KEY = os.getenv('SONARR_API_KEY')

sonarr_api = None
if BASE_URL and API_KEY:
    sonarr_api = SonarrAPI(BASE_URL, API_KEY)
else:
    logger.warning("Sonarr URL or API Key not configured in .env file.")

# --- Public functions for the rest of the application to use ---
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


def get_library_summary() -> Dict:
    """
    Calculates total size and episode count for the Sonarr library.
    This uses the 'Optimized Method' from the provided script for accuracy.
    """
    if not sonarr_api:
        return {'total_gb': 0.0, 'total_episodes': 0}

    logger.info("Calculating Sonarr library size using accurate episode file summation.")
    all_series = sonarr_api.get_all_series()
    if not all_series:
        return {'total_gb': 0.0, 'total_episodes': 0}

    total_size_bytes = 0
    total_episodes = 0

    for i, series in enumerate(all_series):
        series_id = series['id']
        episode_files = sonarr_api.get_episode_files_for_series(series_id)
        
        series_size = sum(f.get('size', 0) for f in episode_files)
        series_ep_count = len(episode_files)

        total_size_bytes += series_size
        total_episodes += series_ep_count
        
        if (i + 1) % 25 == 0:
            logger.debug(f"Processed {i+1}/{len(all_series)} series for size calculation...")
    total_series = len(all_series)
    total_gb = total_size_bytes / (1024**3)
    logger.info(f"Sonarr library calculation complete. Total Size: {total_gb:.2f} GB, Total Episodes: {total_episodes}")

    return {
        'total_gb': round(total_gb, 2),
        'total_episodes': total_episodes,
        'total_series': total_series
    }


def move_sonarr_series(current_path, archive_root_path, show_id):
    """Updates a series's root folder path and triggers a file move in Sonarr."""
    if not sonarr_api:
        return False, "Sonarr not configured."
    
    try:
        # Get the show data
        show_res = sonarr_api.session.get(f'{sonarr_api.base_url}/api/v3/series/{show_id}')
        show_res.raise_for_status()
        show_data = show_res.json()
        series_title = show_data['title']  # Fixed: use show_data instead of show_res
        
        # Update the show_data with the new path and root folder
        show_data['rootFolderPath'] = archive_root_path
        show_data["path"] = f"{archive_root_path}/{series_title}"
        
        # Use the sonarr_api session to update
        update_res = sonarr_api.session.put(
            f'{sonarr_api.base_url}/api/v3/series/{show_id}',
            json=show_data,
            params={'moveFiles': 'true'},
            timeout=60
        )
        update_res.raise_for_status()
        logger.info(f"Successfully moved series '{series_title}' to {archive_root_path}")
        return True, f"Successfully moved series '{series_title}'"
    except Exception as e:
        logger.error(f"Failed to move series ID {show_id}: {e}", exc_info=True)
        return False, f"Failed to move series: {e}"


def update_show_root_folder(show_id: int, new_root_folder_path: str):
    """Updates a show in Sonarr to point to a new root folder."""
    if not sonarr_api:
        return False, "Sonarr not configured."
    
    try:
        logger.info(f"Updating Sonarr: moving show ID {show_id} to root folder '{new_root_folder_path}'.")
        # Use the session from our API class
        show_res = sonarr_api.session.get(f'{sonarr_api.base_url}/api/v3/series/{show_id}')
        show_res.raise_for_status()
        show_data = show_res.json()

        show_data["rootFolderPath"] = new_root_folder_path
        
        update_res = sonarr_api.session.put(f'{sonarr_api.base_url}/api/v3/series/{show_id}', json=show_data)
        update_res.raise_for_status()
        
        sonarr_api.session.post(f'{sonarr_api.base_url}/api/v3/command', json={'name': 'RescanSeries', 'seriesId': show_id})
        
        logger.info(f"Successfully updated show ID {show_id} in Sonarr and triggered rescan.")
        return True, "Successfully updated show's root folder in Sonarr."
    except Exception as e:
        logger.error(f"Failed to update show ID {show_id} in Sonarr: {e}", exc_info=True)
        return False, f"Failed to update show in Sonarr: {e}"

def get_series_title_id_map() -> Dict[str, int]:
    """
    Returns a dictionary mapping series titles to their Sonarr IDs.
    
    Returns:
        Dictionary of {title: id}
    """
    series_list = sonarr_api.get_all_series()
    return {series['title']: series['id'] for series in series_list}

def get_root_folders() -> List[Dict]:
    """Get all root folders from Sonarr"""
    if not sonarr_api:
        return []
    try:
        response = sonarr_api.session.get(f'{sonarr_api.base_url}/api/v3/rootfolder')
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error getting Sonarr root folders: {e}", exc_info=True)
        return []

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
    # Placeholder - this function can remain for future use
    return []