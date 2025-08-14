# backend/services/file_service.py
import os
import shutil
import logging

logger = logging.getLogger(__name__)

def move_to_archive(current_path, archive_root_path):
    if not current_path or not os.path.exists(current_path):
        msg = f"Source path does not exist: {current_path}"
        logger.error(msg)
        return False, msg
    
    if not archive_root_path or not os.path.isdir(archive_root_path):
        msg = f"Archive path is not a valid directory: {archive_root_path}"
        logger.error(msg)
        return False, msg

    item_name = os.path.basename(current_path)
    new_path = os.path.join(archive_root_path, item_name)

    if os.path.exists(new_path):
        msg = f"Destination path already exists: {new_path}"
        logger.warning(msg)
        return False, msg

    try:
        logger.info(f"Moving '{current_path}' to '{new_path}'...")
        shutil.move(current_path, new_path)
        logger.info(f"Move successful for '{item_name}'.")
        return True, new_path
    except Exception as e:
        logger.error(f"Error moving directory from '{current_path}' to '{new_path}': {e}", exc_info=True)
        return False, str(e)