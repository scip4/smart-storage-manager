import logging
import os
import sys
from pathlib import Path

# Add parent directory to Python path
sys.path.append(str(Path(__file__).parent.parent))
from config import load_settings  # Now we can import directly
from . import plex_service, sonarr_service, radarr_service, file_service, analysis_service
from .cache_service import cache

logger = logging.getLogger(__name__)

def perform_cleanup_actions():
    """
    This is the master function for automated cleanup, triggered by the scheduler.
    It finds media that matches rules for deletion or archival and executes those actions
    using the configured archive path mappings.
    """
    logging.info("--- Starting scheduled cleanup job ---")
    
    # --- CRITICAL SAFETY CHECK ---
    # Load the latest settings at the start of the job.
    settings = load_settings()
    if not settings.get('enableAutoActions', False):
        logger.info("Automatic actions are disabled in settings. Cleanup job exiting.")
        return

    try:
        # Step 1: Get all media and apply the analysis rules.
        # We use the internal, uncached _get_plex_library() to ensure we have the absolute latest data.
        logger.info("Fetching latest library data for cleanup analysis...")
        all_media = plex_service._get_plex_library().all_media
        
        analyzed_media = analysis_service.apply_rules_to_media(all_media, settings)

        # Step 2: Filter for items that are candidates for an action.
        candidates = [item for item in analyzed_media if 'candidate' in item.status]

        if not candidates:
            logger.info("No cleanup candidates found. Job finished.")
            return

        logger.warning(f"Found {len(candidates)} candidates for automated cleanup.")

        # Step 3: Load archive mappings and create a quick lookup dictionary.
        # Normalize paths for reliable matching.
        archive_mappings = settings.get('archiveMappings', [])
        mapping_dict = {
            os.path.normpath(m['source']): os.path.normpath(m['destination'])
            for m in archive_mappings if m.get('source') and m.get('destination')
        }

        success_count = 0
        for item in candidates:
            item_title = item.title
            
            # --- Handle Archival Candidates ---
            if item.status == 'candidate-archive':
                item_root_path = getattr(item, 'rootFolderPath', None)
                if not item_root_path:
                    logger.error(f"Cannot archive '{item_title}': Item is missing its rootFolderPath.")
                    continue

                normalized_item_root = os.path.normpath(item_root_path)
                destination_path = mapping_dict.get(normalized_item_root)

                if not destination_path:
                    logger.error(f"Cannot archive '{item_title}': No archive mapping found for source folder '{item_root_path}'. Please configure it in Settings.")
                    continue
                
                logger.warning(f"ARCHIVING '{item_title}' from '{item_root_path}' to '{destination_path}'...")
                
                current_folder_path = os.path.dirname(item.filePath)
                #move_success, move_result = file_service.move_to_archive(current_folder_path, destination_path)
                
                if move_success:
                    success_count += 1
                    # Update Sonarr or Radarr with the new location
                    if item.type == 'tv' and hasattr(item, 'sonarrId'):
                        sonarr_service.update_show_root_folder(item.sonarrId, move_result)
                    elif item.type == 'movie' and hasattr(item, 'radarrId'):
                       radarr_service.update_movie_root_folder(item.radarrId, move_result)
                else:
                    logger.error(f"Failed to complete archive for '{item_title}'. Move operation failed: {move_result}")

            # --- Handle Deletion Candidates ---
            elif item.status == 'candidate-delete':
                logger.warning(f"DELETING '{item_title}' (Plex ID: {item.id})...")
                success, msg = plex_service.delete_media_from_plex(item.id)
                
                if success:
                    success_count += 1
                    # Also tell Sonarr/Radarr to stop monitoring to prevent re-download
                    if item.type == 'tv' and hasattr(item, 'sonarrId'):
                        sonarr_service.unmonitor_show(item.sonarrId) # Assumes this function exists
                    elif item.type == 'movie' and hasattr(item, 'radarrId'):
                        radarr_service.unmonitor_movie(item.radarrId) # Assumes this function exists
                else:
                    logger.error(f"Failed to delete '{item_title}': {msg}")

        # Step 4: After actions are done, invalidate caches so the UI reflects changes.
        if success_count > 0:
            logger.info(f"Cleanup actions performed on {success_count} item(s). Clearing data caches.")
            cache.delete('dashboard_data')
            cache.delete('plex_media_data_full')
            cache.delete('sonarr_library_summary')
            # Add other cache keys here if you have them (e.g., 'radarr_library_summary')
            
        logger.info(f"--- Cleanup job finished. Successfully processed {success_count}/{len(candidates)} items. ---")

    except Exception as e:
        logger.error(f"An unexpected error occurred during the cleanup job: {e}", exc_info=True)