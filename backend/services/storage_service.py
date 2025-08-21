# backend/services/storage_service.py
import shutil
import os
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

def get_drive_usage(path: str) -> Dict:
    """Gets disk usage statistics for a given path in bytes."""
    try:
        # shutil.disk_usage returns a tuple (total, used, free)
        usage = shutil.disk_usage(path)
        return {
            'total': usage.total,
            'used': usage.used,
            'free': usage.free,
        }
    except FileNotFoundError:
        logger.error(f"Storage path not found: {path}")
        return None
    except Exception as e:
        logger.error(f"Could not get disk usage for '{path}': {e}", exc_info=True)
        return None
def get_archive_stats() -> Dict:
    archive_drive_str= os.getenv('ARCHIVE_DRIVE', '')
    return get_drive_usage(archive_drive_str)


def get_combined_disk_usage() -> Dict:
    """
    Checks paths defined in the .env file and returns their combined disk usage.
    """
    # Parse mount points from environment variables
    mount_points_str = os.getenv('MOUNT_POINTS', '')
    paths_to_check = [p.strip() for p in mount_points_str.split(',') if p.strip()]

    if not paths_to_check:
        logger.warning("MOUNT_POINTS not defined in .env file. Storage stats will be inaccurate. Defaulting to root '/'.")
        paths_to_check = ['/'] # Fallback to checking the root directory

    logger.info(f"Checking disk usage for paths: {paths_to_check}")

    total_space = 0
    total_used = 0
    total_free = 0
    
    for path in paths_to_check:
        usage = get_drive_usage(path)
        if usage:
            # We add the total space of each unique filesystem.
            # If two paths are on the same drive, this logic correctly
            # handles the summation without double-counting.
            total_space += usage['total']
            total_used += usage['used']
            # Note: Total free space is more complex for combined drives.
            # We sum the free space available on each.
            total_free += usage['free']
        else:
            logger.warning(f"Skipping path '{path}' due to read error.")

    # The logic above might double-count if paths are on the same device.
    # A more accurate method is to find the unique devices and sum their usage.
    unique_devices = set()
    total_space, total_used, total_free = 0, 0, 0

    for path in paths_to_check:
        try:
            device = os.stat(path).st_dev
            if device not in unique_devices:
                usage = get_drive_usage(path)
                if usage:
                    logger.debug(f"Adding stats for device {device} from path '{path}'")
                    total_space += usage['total']
                    total_used += usage['used']
                    total_free += usage['free']
                    unique_devices.add(device)
            else:
                logger.debug(f"Skipping path '{path}' as its device ({device}) has already been counted.")
        except FileNotFoundError:
             logger.error(f"Path '{path}' not found when checking for unique devices.")

    return {
        'total': total_space,
        'used': total_used,
        'free': total_free,
    }