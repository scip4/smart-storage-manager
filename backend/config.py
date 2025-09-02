import os
import logging
import json
from pathlib import Path


SETTINGS_FILE = 'settings.json'

def _load_mappings_from_env() -> list:
    """
    Parses the ARCHIVE_MAPPINGS_ENV environment variable into a list of mapping objects.
    """
    mappings_str = os.getenv('ARCHIVE_MAPPINGS_ENV')
    if not mappings_str:
        return []

    env_mappings = []
    # Split mappings by semicolon
    raw_mappings = [m.strip() for m in mappings_str.split(';') if m.strip()]
    
    for mapping_str in raw_mappings:
        # Split each mapping by pipe
        parts = [p.strip() for p in mapping_str.split('|')]
        if len(parts) == 3:
            mapping_type, source, destination = parts
            if mapping_type in ['tv', 'movie'] and source and destination:
                env_mappings.append({
                    "type": mapping_type,
                    "source": source,
                    "destination": destination
                })
            else:
                logging.warning(f"Skipping invalid environment archive mapping: {mapping_str}")
        else:
            logging.warning(f"Skipping invalid environment archive mapping format: {mapping_str}")
            
    if env_mappings:
        logging.info(f"Loaded {len(env_mappings)} archive mappings from .env file.")
        
    return env_mappings

def get_default_settings():
    return {
        "autoDeleteAfterDays": 30, "archiveAfterMonths": 6, "keepFreeSpace": 500,
        "enableAutoActions": False, "checkStreamingAvailability": True,
        "preferredStreamingServices": [],
        "archiveMappings": []
    }

def load_settings():
    """Load settings from environment variables and settings.json"""
    settings = {}
        # 1. Start with hardcoded defaults
    settings = get_default_settings()

    # 2. Load mappings from the environment file as a fallback
    env_mappings = _load_mappings_from_env()
    if env_mappings:
        settings['archiveMappings'] = env_mappings

    # 3. Load user settings from JSON, which will override defaults and .env values
    try:
        with open(SETTINGS_FILE, 'r') as f:
            user_settings = json.load(f)
            # The update() method merges the dictionaries, with user_settings taking precedence.
            # If user_settings has an 'archiveMappings' key, it will replace the one from the environment.
            settings.update(user_settings)
            logging.debug("Successfully loaded and merged settings from settings.json.")
    except (FileNotFoundError, json.JSONDecodeError):
        logging.debug("settings.json not found or invalid. Using defaults and .env fallbacks.")
        pass # It's okay if the file doesn't exist, we'll use the defaults.

    return settings
    # # Load from environment variables
    # env_settings = {
    #     'DATA_UPDATE_INTERVAL': os.getenv('DATA_UPDATE_INTERVAL'),
    #     'PLEX_URL': os.getenv('PLEX_URL'),
    #     'PLEX_TOKEN': os.getenv('PLEX_TOKEN'),
    #     'SONARR_URL': os.getenv('SONARR_URL'),
    #     'SONARR_API_KEY': os.getenv('SONARR_API_KEY'),
    #     'RADARR_URL': os.getenv('RADARR_URL'),
    #     'RADARR_API_KEY': os.getenv('RADARR_API_KEY'),
    #     'TV_ARCHIVE_FOLDERS': os.getenv('TV_ARCHIVE_FOLDERS'),
    #     'MOVIE_ARCHIVE_FOLDERS': os.getenv('MOVIE_ARCHIVE_FOLDERS'),
    #     'STREAMING_PROVIDERS': os.getenv('STREAMING_PROVIDERS'),
    #     'TMDB_API_KEY': os.getenv('TMDB_API_KEY'),
    #     'enableAutoActions': os.getenv('ENABLE_AUTO_ACTIONS', 'false').lower() == 'true',
    # }
    
    # # Load from settings.json if exists
    # settings_path = Path(__file__).parent / 'settings.json'
    # if settings_path.exists():
    #     with open(settings_path, 'r') as f:
    #         file_settings = json.load(f)
    #         # Merge file settings with environment settings
    #         for key, value in file_settings.items():
    #             # Only use file setting if env var is not set
    #             if env_settings.get(key) is None:
    #                 env_settings[key] = value
    
    # # Convert comma-separated strings to lists
    # for key in ['TV_ARCHIVE_FOLDERS', 'MOVIE_ARCHIVE_FOLDERS', 'STREAMING_PROVIDERS']:
    #     if isinstance(env_settings.get(key), str):
    #         env_settings[key] = [item.strip() for item in env_settings[key].split(',') if item.strip()]
    
    # return env_settings