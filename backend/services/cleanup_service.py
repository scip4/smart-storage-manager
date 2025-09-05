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

def perform_cleanup_actions(dry_run=False):
    """
    Master function for cleanup. If dry_run is True, it only logs proposed actions.
    
    Args:
        dry_run (bool): If True, no files will be moved or deleted.
        
    Returns:
        A list of log messages detailing the proposed or executed actions.
    """
    run_mode = "DRY RUN" if dry_run else "LIVE RUN"
    log_messages = [f"--- Starting scheduled cleanup job ({run_mode}) ---"]
    logger.info(log_messages[-1])
    
    settings = load_settings()
    if not settings.get('enableAutoActions', False) and not dry_run:
        msg = "Automatic actions are disabled in settings. Cleanup job exiting."
        logger.info(msg)
        log_messages.append(msg)
        return log_messages

    try:
        log_messages.append("Fetching latest library data for cleanup analysis...")
        logger.info(log_messages[-1])
        all_media = plex_service._get_plex_library().all_media
        
        analyzed_media = analysis_service.apply_rules_to_media(all_media, settings)
        sonarr_title_id_map = sonarr_service.get_series_title_id_map()
        radarr_title_id_map = radarr_service.get_movie_title_id_map() #item_to_action.get('id', f"ID {media_id}")
        # Step 2: Filter for items that are candidates for an action.
        candidates = [item for item in analyzed_media if item.status and 'candidate' in item.status]

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
            if item.status == 'candidate-archive':
                ####Add condition to check root folder path if show is in plex but not sonarr or radarr

                destination_path = mapping_dict.get(os.path.normpath(item.rootFolderPath))
                if not destination_path:
                    msg = f"[SKIP] Cannot archive '{item.title}': No archive mapping found for source folder '{item.rootFolderPath}'."
                    logger.error(msg)
                    log_messages.append(msg)
                    continue

                log_messages.append(f"[ARCHIVE] Proposing to move '{item.title}' to '{destination_path}'.")
                if not dry_run:
                
                    plex_folder_path = os.path.dirname(item.filePath)
                    
                    
                    if item.type == 'tv':
                        item_id = sonarr_title_id_map.get(item_title)
                        move_success, move_result = file_service.move_sonarr_series(item_root_path, destination_path, item_id)
                    else: 
                        item_id = radarr_title_id_map.get(item_title)
                        move_success, move_result = file_service.move_radarr_movie(item_root_path, destination_path, item_id)
                    
                    
                    #file_service.move_to_archive(current_folder_path, destination_path)
                    
                    if move_success:
                        success_count += 1
                        # Update Sonarr or Radarr with the new location
                        if item.type == 'tv' and hasattr(item, 'sonarrId'):
                            logger.debug("TVfolder Test")
                        # sonarr_service.update_show_root_folder(item.sonarrId, move_result)
                        elif item.type == 'movie' and hasattr(item, 'radarrId'):
                            logger.debug('Movie folder test')
                        #radarr_service.update_movie_root_folder(item.radarrId, move_result)
                    else:
                        logger.error(f"Failed to complete archive for '{item_title}'. Move operation failed: {move_result}")

            # --- Handle Deletion Candidates ---
            elif item.status == 'candidate-delete':
                logger.warning(f"DELETING '{item.title}' (Plex ID: {item.id})...")
                if not dry_run:
                    logger.warning(f"EXECUTING DELETE on '{item.title}'...")
                    success, msg = plex_service.delete_media_from_plex(item.id)
                    #if success: success_count += 1                  
                    if success:
                        success_count += 1
                        # Also tell Sonarr/Radarr to stop monitoring to prevent re-download
                        if item.type == 'tv' and hasattr(item, 'sonarrId'):
                            logger.debug('unmonitor test')
                            #sonarr_service.unmonitor_show(item.sonarrId) # Assumes this function exists
                        elif item.type == 'movie' and hasattr(item, 'radarrId'):
                            logger.debug('unmonitor test')
                            #radarr_service.unmonitor_movie(item.radarrId) # Assumes this function exists
                    else:
                        logger.error(f"Failed to delete '{item_title}': {msg}")

        # Step 4: After actions are done, invalidate caches so the UI reflects changes.
        if success_count > 0 and not dry_run:
            logger.info(f"Cleanup actions performed on {success_count} item(s). Clearing data caches.")
            cache.delete('dashboard_data')
            cache.delete('plex_media_data_full')
            cache.delete('sonarr_library_summary')
            # Add other cache keys here if you have them (e.g., 'radarr_library_summary')
            
        final_msg = f"--- Cleanup job finished ({run_mode}). Processed {success_count if not dry_run else '0'}/{len(candidates)} items. ---"
        logger.info(final_msg)
        log_messages.append(final_msg)
        return log_messages

    except Exception as e:
        msg = f"An unexpected error occurred during the cleanup job: {e}"
        logger.error(msg, exc_info=True)
        log_messages.append(msg)
        return log_messages