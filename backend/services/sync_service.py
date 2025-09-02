# backend/services/sync_service.py
import json
import logging
from .cache_service import cache, CACHE_TIMEOUT
from . import plex_service, sonarr_service, storage_service, analysis_service, radarr_service
from models import StorageInfo # Note the relative import

logger = logging.getLogger(__name__)
SETTINGS_FILE = '../../settings.json'
def get_default_settings():
    return {
        "autoDeleteAfterDays": 30, "archiveAfterMonths": 6, "keepFreeSpace": 500,
        "enableAutoActions": False, "checkStreamingAvailability": True,
        "preferredStreamingServices": [], "archiveFolderPath": "",
        "tvArchiveFolders": [],
        "movieArchiveFolders": [],  "archiveMappings": [] 
    }

def load_settings():
    try:
        with open(SETTINGS_FILE, 'r') as f:
            defaults = get_default_settings()
            #defaults
            user_settings = json.load(f)
            defaults.update(user_settings)
            return defaults
    except (FileNotFoundError, json.JSONDecodeError):
        return get_default_settings()

def perform_full_sync():
    """
    The master function that collects all data and pre-computes the dashboard.
    This is the only function that should perform slow, blocking API calls.
    It runs in the background and is triggered by the scheduler.
    """
    logger.info("--- Starting scheduled background sync ---")
    try:
        # Step 1: Fetch raw data from all sources
        # We can give these longer cache timeouts since they are only used here
        
        sonarr_summary = sonarr_service.get_library_summary()
        cache.set('sonarr_summary_raw', sonarr_summary, timeout=CACHE_TIMEOUT * 2)
        radarr_summary = radarr_service.get_library_summary()
        cache.set('radarr_summary_raw', radarr_summary, timeout=CACHE_TIMEOUT * 2)
        sonarr_folders = sonarr_service.get_root_folders()
        cache.set('cache_sonarr_folders', sonarr_folders, timeout=CACHE_TIMEOUT * 2)
        radarr_folders = radarr_service.get_root_folders()
        cache.set('cache_radarr_folders', radarr_folders, timeout=CACHE_TIMEOUT * 2)
        plex_media_object = plex_service.get_plex_library()
        all_media = plex_media_object.all_media
        streaming_media_for_card = plex_media_object.streaming_media

        cache.set('plex_library_raw', plex_media_object, timeout=CACHE_TIMEOUT * 2)
        analyzed_media = analysis_service.apply_rules_to_media(all_media, load_settings())
        cache.set('analyzed_media_raw', analyzed_media, timeout=CACHE_TIMEOUT * 2)
        
        disk_stats_bytes = storage_service.get_combined_disk_usage()
        cache.set('storage_info_raw', disk_stats_bytes, timeout=CACHE_TIMEOUT * 2)
        candidates = [item.__dict__ for item in analyzed_media if item.status and 'candidate' in item.status]
        cache.set('canidates_info_raw', candidates, timeout=CACHE_TIMEOUT * 2)
        potential_savings = sum(c['size'] for c in candidates)
        cache.set('potential_info_raw', potential_savings, timeout=CACHE_TIMEOUT * 2)
        logger.info("Raw data sources have been fetched and cached.")
        archive_drive_stats = storage_service.get_archive_stats()
        cache.set('archive_info_raw', archive_drive_stats, timeout=CACHE_TIMEOUT * 2)
        # --- REAL STORAGE DATA ---
        # Call our new service to get actual disk usage in bytes
        #disk_stats_bytes = storage_service.get_combined_disk_usage()
        # Convert bytes to Gigabytes for the API response
        storage_data = StorageInfo(
            total=disk_stats_bytes['total'] / (1024**3),
            used=disk_stats_bytes['used'] / (1024**3),
            available=disk_stats_bytes['free'] / (1024**3)
        )
    
        # Get archive drive stats with error handling
        
        if archive_drive_stats:
            archive_data = StorageInfo(
                total=archive_drive_stats['total'] / (1024**3),
                used=archive_drive_stats['used'] / (1024**3),
                available=archive_drive_stats['free'] / (1024**3)
            )
        else:
            # Default to zero values if archive stats unavailable
            archive_data = StorageInfo(total=0, used=0, available=0)
        # Get media library stats (this is separate from total disk usage)
        #sonarr_summary = sonarr_service.get_library_summary()
        tv_shows_size_gb = sonarr_summary['total_gb']
        tv_shows_episodes = sonarr_summary['total_episodes']
        tv_shows = sonarr_summary['total_series']
        #radarr_summary = radarr_service.get_library_summary()
        movies_size_gb = radarr_summary['total_gb'] 
        movies = radarr_summary['total_movies'] 
        #movies_size_gb = sum(m.size for m in all_media if m.type == 'movie')
    
        upcoming = sonarr_service.get_upcoming_shows()
        # Calculate total size for series data
  

        #for size in sonarr_summary['seriesData'][6]
        """  for series_id, series_data in sonarr_summary['seriesData'].items():
            sz += series_data['size_gb'] * (1024**3)  # Convert GB to bytes
        dattest = sz / (1024**3)  # Convert back to GB for consistency
        """
    # Recommended actions: largest ended shows and largest movies on streaming
        ended_shows = [item for item in analyzed_media
                    if item.type == 'tv' and item.status == 'ended' and sonarr_summary['seriesSize'][item.sonarrId] >= 55]
        ended_shows_sorted = sorted(ended_shows, key=lambda x: x.size, reverse=True)[:5]
    
        streaming_movies = [item for item in analyzed_media
                        if item.type == 'movie' and item.status =='delete-if-streaming']
        streaming_movies_sorted = sorted(streaming_movies, key=lambda x: x.size, reverse=True)[:5]



        large_movies = [item for item in analyzed_media
                            if item.type == 'movie' and item.status !='archive'] # and item.rootFolderPath.find('4K') == -1]
        large_movies_sorted = sorted(large_movies, key=lambda x: x.size, reverse=True)[:10]
        streaming_media_for_card_sorted = sorted(streaming_media_for_card, key=lambda x: x.size, reverse=True)

        dashboard_data = {
            'storageData': storage_data.__dict__,
            'archiveData': archive_data.__dict__,
            'potentialSavings': round(potential_savings, 2),
            'candidates': candidates,
            'largeMovies': [item.__dict__ for item in large_movies_sorted],
            'upcomingReleases': upcoming,
            'libraryStats': {
                'tv': tv_shows,
                'tv_size': round(tv_shows_size_gb, 1),
                'tv_episodes': tv_shows_episodes,
                'movies': movies,
                'movies_size': round(movies_size_gb, 1),
                'onStreaming': len([m for m in plex_media_object.all_media if m.streamingServices]),
            },
            'streamingMedia': [sm.__dict__ for sm in streaming_media_for_card_sorted],
            'recommendedActions': {
                'endedShows': [item.__dict__ for item in ended_shows_sorted],
                'streamingMovies': [item.__dict__ for item in streaming_movies_sorted]
            }
        }
        
        
        
        
        """ 
        # Step 2: Pre-compute the dashboard data using the raw fetched data
        # In a real app, you would load settings here, but for simplicity we assume defaults
        settings = {} # In a real app: load_settings() from app.py
        analyzed_media = analysis_service.apply_rules_to_media(plex_data, settings)
        candidates = [item.__dict__ for item in analyzed_media if 'candidate' in item.status]
        
        storage_data = StorageInfo(
            total=disk_stats_bytes['total'] / (1024**3),
            used=disk_stats_bytes['used'] / (1024**3),
            available=disk_stats_bytes['free'] / (1024**3)
        )

        dashboard_data = {
            'storageData': storage_data.__dict__,
            'potentialSavings': round(sum(c['size'] for c in candidates), 2),
            'candidates': candidates,
            'upcomingReleases': [], # or sonarr_service.get_upcoming_shows()
            'libraryStats': {
                'tv': len([m for m in plex_data if m.type == 'tv']),
                'tv_size': round(sonarr_summary['total_gb'], 1),
                'tv_episodes': sonarr_summary['total_episodes'],
                'movies': len([m for m in plex_data if m.type == 'movie']),
                'movies_size': round(sum(m.size for m in plex_data if m.type == 'movie'), 1),
                'onStreaming': 0 # Placeholder for streaming check
            }
        }
    """  
    
       
        # Step 3: Store the final, computed dashboard object in the cache
        cache.set('dashboard_data', dashboard_data, timeout=CACHE_TIMEOUT)
        logger.info("--- Background sync completed: Dashboard data is now cached. ---")

    except Exception as e:
        logger.error(f"Background sync failed: {e}", exc_info=True)