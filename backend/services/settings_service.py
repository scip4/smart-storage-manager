# backend/services/settings_service.py
import os
import json
import logging

logger = logging.getLogger(__name__)

# --- Paths and ENV_KEYS are unchanged ---
APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(APP_ROOT, 'data')
SETTINGS_FILE = os.path.join(DATA_DIR, 'settings.json')

ENV_KEYS_TO_MERGE = [
    'PLEX_URL', 'PLEX_TOKEN', 'SONARR_URL', 'SONARR_API_KEY',
    'RADARR_URL', 'RADARR_API_KEY', 'TMDB_API_KEY', 'MOUNT_POINTS',
    'TV_ARCHIVE_FOLDERS', 'MOVIE_ARCHIVE_FOLDERS','STREAMING_PROVIDERS',
    'AVAILABLE_STREAMING_PROVIDERS', 'DATA_UPDATE_INTERVAL','ARCHIVE_DRIVE',
]

def get_default_settings():
    """Returns the hardcoded default settings for the application."""
    # This provides the basic structure
    return {
        "enableAutoActions": False,
        "archiveMappings": [],
        "preferredStreamingServices": [],
        **{key: "" for key in ENV_KEYS_TO_MERGE}, # Ensure keys exist
        "TV_ARCHIVE_FOLDERS": [], # Ensure these are lists
        "MOVIE_ARCHIVE_FOLDERS": [],
        "MOUNT_POINTS": [],
        "STREAMING_PROVIDERS": [],
        "AVAILABLE_STREAMING_PROVIDERS": []
    }

def save_settings(settings_data):
    """Saves the provided settings dictionary ONLY to settings.json."""
    try:
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings_data, f, indent=4)
        logger.info(f"Settings saved successfully to {SETTINGS_FILE}.")
        return True
    except Exception as e:
        logger.error(f"Failed to save settings to {SETTINGS_FILE}: {e}", exc_info=True)
        return False

def load_settings():
    """
    Loads settings with a per-variable priority:
    1. A non-empty value in settings.json takes highest priority.
    2. If the value in settings.json is missing or empty, it falls back to the .env file.
    3. If neither has a value, a hardcoded default is used.
    """
    # 1. Load settings from the environment file first, as our base.
    env_settings = {}
    for key in ENV_KEYS_TO_MERGE:
        env_value = os.getenv(key)
        if env_value is not None:
            if key in ['MOUNT_POINTS', 'TV_ARCHIVE_FOLDERS', 'MOVIE_ARCHIVE_FOLDERS', 'STREAMING_PROVIDERS','AVAILABLE_STREAMING_PROVIDERS']:
                env_settings[key] = [v.strip() for v in env_value.split(',') if v.strip()]
            else:
                env_settings[key] = env_value
    
    # 2. Load user settings from the JSON file.
    user_settings = {}
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r') as f:
                user_settings = json.load(f)
                logger.debug(f"Successfully loaded settings from {SETTINGS_FILE}.")
    except (FileNotFoundError, json.JSONDecodeError):
        logger.warning(f"{SETTINGS_FILE} not found or is invalid. Will proceed with .env values.")
        pass

    # 3. Merge the settings with the correct priority.
    # Start with the defaults to ensure all keys exist.
    final_settings = get_default_settings()

    # Apply environment settings first.
    final_settings.update(env_settings)
    
    # Now, intelligently apply user settings. A non-empty user setting overrides the environment setting.
    for key, user_value in user_settings.items():
        # This is the core logic: if the user has provided a value (even a boolean false),
        # it should take priority. We only ignore it if it's an empty string or empty list.
        is_value_present = user_value not in [None, "", []]
        
        if is_value_present:
            final_settings[key] = user_value
            
    # Bootstrap settings.json if it doesn't exist on the first run
    if not os.path.exists(SETTINGS_FILE):
        logger.warning(f"{SETTINGS_FILE} not found. Bootstrapping new settings from merged config.")
        save_settings(final_settings)
        
    return final_settings

# def load_settings():
#     """
#     Loads settings with a priority system:
#     1. Base defaults.
#     2. Fallback values from the .env file.
#     3. User-specific values from settings.json (highest priority).
#     """
#     # 1. Start with hardcoded defaults
#     settings = get_default_settings()

#     # 2. Load values from the environment file as a fallback layer.
#     # This will populate keys like PLEX_URL, MOUNT_POINTS, etc.
#     for key in settings:
#         env_value = os.getenv(key)
#         if env_value is not None:
#             # Handle comma-separated lists for array types
#             if key in ['MOUNT_POINTS', 'TV_ARCHIVE_FOLDERS', 'MOVIE_ARCHIVE_FOLDERS', 'STREAMING_PROVIDERS']:
#                 settings[key] = [v.strip() for v in env_value.split(',') if v.strip()]
#             else:
#                 settings[key] = env_value
    
#     # Special handling for archive mappings from env
#     env_mappings = _load_mappings_from_env()
#     if env_mappings:
#         settings['archiveMappings'] = env_mappings

#     # 3. Load user settings from JSON, which will override defaults and .env values
#     try:
#         if not os.path.exists(DATA_DIR):
#             os.makedirs(DATA_DIR)
            
#         with open(SETTINGS_FILE, 'r') as f:
#             user_settings = json.load(f)
#             settings.update(user_settings)
#             logger.debug("Successfully loaded and merged settings from settings.json.")
#     except (FileNotFoundError, json.JSONDecodeError):
#         logger.debug("settings.json not found or invalid. Using defaults and .env fallbacks.")
#         # If the file doesn't exist, we just proceed with env/default values
#         pass

#     return settings

def save_settings(settings_data):
    """Saves the provided settings dictionary to settings.json."""
            # Also save environment variables to .env file
    env_vars = [
        'PLEX_URL', 'PLEX_TOKEN',
        'SONARR_URL', 'SONARR_API_KEY',
        'RADARR_URL', 'RADARR_API_KEY',
        'TMDB_API_KEY', 'MOUNT_POINTS',
        'ARCHIVE_DRIVE', 'STREAMING_PROVIDERS',
        'TV_ARCHIVE_FOLDERS', 'MOVIE_ARCHIVE_FOLDERS',
        'DATA_UPDATE_INTERVAL','AVAILABLE_STREAMING_PROVIDERS','ENABLE_AUTO_ACTIONS',
    ]
        
    env_lines = []
    for var in env_vars:
        value = settings_data.get(var, '')
        # For array values, join with commas
    if isinstance(value, list):
        value = ','.join(value)
        env_lines.append(f"{var}={value}")
    
    # Write to .env file
    #with open('.env', 'w') as f:
    #    f.write('\n'.join(env_lines))
    try:
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings_data, f, indent=4)
        logger.info("Settings saved successfully to settings.json.")
        return True
    except Exception as e:
        logger.error(f"Failed to save settings to {SETTINGS_FILE}: {e}", exc_info=True)
        return False