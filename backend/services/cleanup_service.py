# backend/services/cleanup_service.py
import logging
import os
from .settings_service import load_settings  # Now we can import directly
from . import plex_service, sonarr_service, radarr_service, file_service, analysis_service
from .cache_service import cache

logger = logging.getLogger(__name__)

def perform_cleanup_actions(dry_run=False):
    """
    Master function for cleanup. Now with robust error handling.
    """
    run_mode = "DRY RUN" if dry_run else "LIVE RUN"
    log_messages = [f"--- Starting cleanup job ({run_mode}) ---"]
    logger.info(log_messages[-1])
    
    try: # --- MASTER TRY/EXCEPT BLOCK ---
        settings = load_settings()
        if not settings.get('enableAutoActions', False) and not dry_run:
            msg = "Automatic actions are disabled in settings. Cleanup job exiting."
            logger.info(msg)
            log_messages.append(msg)
            return log_messages

        log_messages.append("Fetching latest library data for cleanup analysis...")
        plex_media_object = plex_service._get_plex_library()
        
        # --- Safety Check: Ensure plex_media_object is valid ---
        if not plex_media_object or not hasattr(plex_media_object, 'all_media'):
             raise ValueError("Failed to retrieve a valid media object from Plex service.")

        all_media = plex_media_object.all_media
        analyzed_media = analysis_service.apply_rules_to_media(all_media, settings)
        candidates = [item for item in analyzed_media if getattr(item, 'status', None) and 'candidate' in item.status]

        if not candidates:
            msg = "No cleanup candidates found. Job finished."
            logger.info(msg)
            log_messages.append(msg)
            return log_messages

        msg = f"Found {len(candidates)} candidates for automated cleanup."
        logger.warning(msg)
        log_messages.append(msg)
        
        mapping_dict = {os.path.normpath(m['source']): os.path.normpath(m['destination']) for m in settings.get('archiveMappings', [])}
        success_count = 0

        for item in candidates:
            # --- Defensive attribute access using getattr ---
            item_title = getattr(item, 'title', 'Unknown Title')
            
            if item.status == 'candidate-archive':
                item_root_path = getattr(item, 'rootFolderPath', None)
                item_file_path = getattr(item, 'filePath', None)

                if not item_root_path or not item_file_path:
                    msg = f"[SKIP] Cannot archive '{item_title}': Item is missing critical path information."
                    logger.error(msg)
                    log_messages.append(msg)
                    continue
                rootpath = item_root_path.split('/')
                destination_path = mapping_dict.get(os.path.normpath("/" + rootpath[1]))
                #destination_path = mapping_dict.get(os.path.normpath(item_root_path))
                if not destination_path:
                    msg = f"[SKIP] Cannot archive '{item_title}': No mapping for source '{item_root_path}'."
                    logger.error(msg)
                    log_messages.append(msg)
                    continue

                log_messages.append(f"[ARCHIVE] Proposing to move '{item_title}' to '{destination_path}'.")
                if not dry_run:
                    # ... (live run archive logic) ...
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
                    pass
            
            elif item.status == 'candidate-delete':
                log_messages.append(f"[DELETE] Proposing to delete '{item_title}'.")
                if not dry_run:
                    # ... (live run delete logic) ...
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
                    pass

        final_msg = f"--- Cleanup job finished ({run_mode}). Proposed actions for {len(candidates)} items. ---"
        logger.info(final_msg)
        log_messages.append(final_msg)
        return log_messages

    except Exception as e:
        # Catch any unexpected error during the process
        msg = f"FATAL ERROR during cleanup job: {e}"
        logger.error(msg, exc_info=True)
        log_messages.append(msg)
        return log_messages