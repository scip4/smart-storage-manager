# backend/services/analysis_service.py
import logging
from datetime import datetime, timedelta
# --- Caching Integration ---
# Import the central cache instance and timeout setting for our application
from .cache_service import cache, CACHE_TIMEOUT

logger = logging.getLogger(__name__)

def _cache_media_rules(media_list, settings):
    """
    Analyzes a list of media items and updates their status based on rules.
    This is the core logic engine.
    """
    now = datetime.now()
    
    for item in media_list:
        # Rule: Keep Forever
        if item.rule == 'keep-forever':
            item.status = 'protected'
            continue
        if item.rootFolderPath is None:
            item.status = 'Not Monitored'
            item.reason = 'Media not monitored in Sonarr or Radarr'
            continue
        # Rule: Archive ended shows
        if item.type == 'tv' and item.size >= 8 and (item.status == 'ended' or item.status == 'Ended') and item.rootFolderPath is not None and item.rule in ['archive-ended', 'auto-manage']:
            #(item.status == 'ended' or item.status == 'Ended') 
            item.status = 'candidate-archive'
            item.reason = 'TV show ended and size is over 8GB'
            continue
            
        # Rule: Delete if on a preferred streaming service
        if item.rule == 'delete-if-streaming' and item.streamingServices:
            # A more robust check would see if it's on a *preferred* service
            item.status = 'candidate-delete'
            item.reason = f'Media status is available on {item.streamingServices}'
            continue
            
        # Rule: Archive after X months
        archive_months = settings.get('archiveAfterMonths', 6)
        if item.lastWatched and item.rule in ['archive-after-6months', 'auto-manage']:
            last_watched_date = datetime.strptime(item.lastWatched, '%Y-%m-%d')
            if last_watched_date < (now - timedelta(days=archive_months * 30)):
                item.status = 'candidate-archive'
                continue

        # Rule: Delete after watched (e.g., after 30 days)
        delete_days = settings.get('autoDeleteAfterDays', 30)
        if item.lastWatched and item.watchCount > 0 and item.rule in ['delete-after-watched', 'auto-manage']:
             last_watched_date = datetime.strptime(item.lastWatched, '%Y-%m-%d')
             if last_watched_date < (now - timedelta(days=delete_days)):
                # This rule is more applicable to episodes, but we apply to shows/movies for demo
                item.status = 'candidate-delete'
                continue

    return media_list


def apply_rules_to_media(media_list, settings):
    """
    Public function to get Sonarr stats. It uses a cache to avoid repeated slow API calls.
    """
    cache_key = "analyzed_media"
    
    # Try to get the data from the cache first
    cached_data = cache.get(cache_key)
    
    if cached_data is not None:
        logger.info("✅ Cache HIT! Returning analyzed media from cache.")
        return cached_data
    
    # If not in cache, it's a "miss"
    logger.warning("⚠️  Cache MISS for analyzed media. Fetching fresh data...")
    
    # Perform the slow calculation
    fresh_data = _cache_media_rules(media_list, settings)
    
    # Store the fresh data in the cache for next time
    if fresh_data and len(fresh_data) > 0:
        logger.info(f"Storing Sonarr summary in cache for {CACHE_TIMEOUT} seconds.")
        cache.set(cache_key, fresh_data, timeout=CACHE_TIMEOUT)
        
    return fresh_data