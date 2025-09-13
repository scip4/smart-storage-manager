# # backend/app.py
# import os
# import json
# import logging
# from logging.handlers import RotatingFileHandler
# from flask import Flask, jsonify, request, send_from_directory # Add send_from_directory
# from flask_cors import CORS
# from dotenv import load_dotenv
# from apscheduler.schedulers.background import BackgroundScheduler
# import threading
# # --- Add sync_service import ---
# from services.sync_service import perform_full_sync
# from services import analysis_service, file_service, storage_service, cleanup_service#, plex_service, sonarr_service, radarr_service
# from services.cache_service import cache, CACHE_TIMEOUT
# from services.settings_service import load_settings, save_settings
# #from services import cleanup_service

# # --- NEW: SCHEDULER SETUP ---
# # This block initializes and starts the background task scheduler.
# scheduler = BackgroundScheduler(daemon=True)
# # This schedules the 'perform_full_sync' function to run at an interval of 30 minutes.
# # This is where the time is set.
# scheduler.add_job(
#     func=perform_full_sync,
#     trigger='interval',
#     minutes=30,
#     id='full_sync_job'
# )
# # We also run the job once immediately on startup so the app has data right away.
# scheduler.add_job(func=perform_full_sync, id='initial_sync_job')

# # --- NEW: SCHEDULE THE DAILY CLEANUP JOB ---
# # This schedules the cleanup function to run once per day at 3:00 AM server time.
# # scheduler.add_job(
# #     func=cleanup_service.perform_cleanup_actions,
# #     trigger='cron',
# #     hour=3,
# #     minute=0,
# #     id='daily_cleanup_job'
# # )

# # --- UPDATE Scheduled Job ---
# # The scheduled job is always a LIVE run (dry_run=False is the default)
# scheduler.add_job(
#     func=cleanup_service.perform_cleanup_actions,
#     trigger='cron',
#     hour=3,
#     minute=0,
#     id='daily_cleanup_job'
# )

# logging.info("Scheduled daily cleanup job for 3:00 AM.")

# # --- The Core Fix ---
# # Define the path to the backend directory within the container
# APP_ROOT = os.path.dirname(os.path.abspath(__file__))
# # Construct the full path to the .env file
# dotenv_path = os.path.join(APP_ROOT, '.env')
# # Explicitly load the .env file from that path
# load_dotenv(dotenv_path=dotenv_path)

# # --- Define a persistent data directory ---
# DATA_DIR = os.path.join(APP_ROOT, 'data')

# scheduler.start()
# logging.info("Background scheduler started. Sync task scheduled for every 30 minutes.")

# # Ensure the scheduler shuts down when the app exits
# import atexit
# atexit.register(lambda: scheduler.shutdown())


# load_dotenv()

# # --- Define a persistent data directory ---
# # This will point to the '/app/backend/data' folder inside the container
# DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
# if not os.path.exists(DATA_DIR):
#     os.makedirs(DATA_DIR)

# # --- Update Flask to serve the built React app from the 'dist' folder ---
# app = Flask(__name__, static_folder='dist', static_url_path='/')

# # --- Update Settings and Log paths to use the persistent data directory ---
# #SETTINGS_FILE = os.path.join(DATA_DIR, 'settings.json')


import os
import logging
import threading
from logging.handlers import RotatingFileHandler
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
import atexit

# --- Centralized Settings Service ---
# This is now the ONLY place we get settings from.
from services.settings_service import load_settings, save_settings

# --- Other Service Imports ---
from services.sync_service import perform_full_sync
from services import plex_service, sonarr_service, radarr_service, analysis_service, file_service, cleanup_service
from services.cache_service import cache

# --- Load .env file ---
# This should be done once at the very beginning.
APP_ROOT = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.join(APP_ROOT, '.env')
load_dotenv(dotenv_path=dotenv_path)

# --- Define Persistent Data Directory ---
DATA_DIR = os.path.join(APP_ROOT, 'data')
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# --- Flask App Initialization ---
app = Flask(__name__, static_folder='dist', static_url_path='/')
CORS(app, resources={r"/api/*": {"origins": "*"}})

def setup_logging():
    log_file = os.path.join(DATA_DIR, 'smart_storage.log')
    file_handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=5)
    file_handler.setLevel(logging.INFO)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    logger = logging.getLogger()
    if not logger.hasHandlers():
        logger.setLevel(logging.DEBUG)
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
    logger.info("Application starting up...")

setup_logging()

# --- Scheduler Setup ---
scheduler = BackgroundScheduler(daemon=True)
update_interval = int(os.getenv('DATA_UPDATE_INTERVAL', 30))
scheduler.add_job(func=perform_full_sync, trigger='interval', minutes=update_interval, id='full_sync_job')
scheduler.add_job(func=perform_full_sync, id='initial_sync_job')
scheduler.add_job(func=cleanup_service.perform_cleanup_actions, trigger='cron', hour=3, minute=0, id='daily_cleanup_job')
scheduler.start()
logging.info(f"Background sync scheduled for every {update_interval} minutes. Daily cleanup scheduled for 3:00 AM.")
atexit.register(lambda: scheduler.shutdown())





# def setup_logging():
#     log_file = os.path.join(DATA_DIR, 'smart_storage.log')

# # --- LOGGING SETUP ---
# #def setup_logging():
# #    log_file = 'smart_storage.log'
#     # 5 MB per file, keep last 5 files
#     file_handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=5)
#     file_handler.setLevel(logging.INFO)
#     console_handler = logging.StreamHandler()
#     console_handler.setLevel(logging.DEBUG)
#     formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
#     file_handler.setFormatter(formatter)
#     console_handler.setFormatter(formatter)
    
#     # Get the root logger and configure it
#     logger = logging.getLogger()
#     logger.setLevel(logging.DEBUG)
    
#     # Remove any existing handlers to avoid duplicates
#     for handler in logger.handlers[:]:
#         logger.removeHandler(handler)
        
#     # Add our custom handlers
#     logger.addHandler(file_handler)
#     logger.addHandler(console_handler)
    
#     logger.info("Application starting up...")

# # Initialize Flask App
# #app = Flask(__name__)
# setup_logging() # Call the logging setup

# CORS(app, resources={r"/api/*": {"origins": "*"}})

# from models import StorageInfo
# from services import plex_service, sonarr_service, radarr_service, analysis_service, file_service

# #SETTINGS_FILE = 'settings.json'

# def _load_mappings_from_env() -> list:
#     """
#     Parses the ARCHIVE_MAPPINGS_ENV environment variable into a list of mapping objects.
#     """
#     mappings_str = os.getenv('ARCHIVE_MAPPINGS_ENV')
#     if not mappings_str:
#         return []

#     env_mappings = []
#     # Split mappings by semicolon
#     raw_mappings = [m.strip() for m in mappings_str.split(';') if m.strip()]
    
#     for mapping_str in raw_mappings:
#         # Split each mapping by pipe
#         parts = [p.strip() for p in mapping_str.split('|')]
#         if len(parts) == 3:
#             mapping_type, source, destination = parts
#             if mapping_type in ['tv', 'movie'] and source and destination:
#                 env_mappings.append({
#                     "type": mapping_type,
#                     "source": source,
#                     "destination": destination
#                 })
#             else:
#                 logging.warning(f"Skipping invalid environment archive mapping: {mapping_str}")
#         else:
#             logging.warning(f"Skipping invalid environment archive mapping format: {mapping_str}")
            
#     if env_mappings:
#         logging.info(f"Loaded {len(env_mappings)} archive mappings from .env file.")
        
#     return env_mappings


def get_default_settings():
    return {
        "autoDeleteAfterDays": 30, "archiveAfterMonths": 6, "keepFreeSpace": 500,
        "enableAutoActions": False, "checkStreamingAvailability": True,
        "preferredStreamingServices": [], "archiveFolderPath": "","AVAILABLE_STREAMING_PROVIDERS": [],
        "tvArchiveFolders": [],
        "movieArchiveFolders": [],
        "archiveMappings": []  # Will be a list of {"source": "/path", "destination": "/path"}
    }

#def save_settings(settings):
#    with open(SETTINGS_FILE, 'w') as f: json.dump(settings, f, indent=2)



# --- Add this route to serve the React app's index.html ---
# This is crucial for handling browser refreshes and direct navigation in a Single Page App
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')


# --- NEW: MANUAL CLEANUP TRIGGER ENDPOINT ---
@app.route('/api/cleanup/trigger', methods=['POST'])

def trigger_manual_cleanup():
    try: # --- Add a try/except block to the endpoint ---
        data = request.get_json()
        if not data:
            return jsonify({"message": "Invalid request body. Expected JSON."}), 400
            
        is_dry_run = data.get('dryRun', False)
        run_mode = "Dry Run" if is_dry_run else "Live Run"
        
        logging.info(f"Manual cleanup ({run_mode}) triggered by user.")
        
        if is_dry_run:
            results = cleanup_service.perform_cleanup_actions(dry_run=True)
            return jsonify({"message": "Dry run complete. See results below.", "results": results}), 200
        
        # For live runs, use a background thread
        cleanup_thread = threading.Thread(target=cleanup_service.perform_cleanup_actions, args=(False,))
        cleanup_thread.start()
        return jsonify({"message": "Cleanup task started in the background. Check logs for progress."}), 202

    except Exception as e:
        # This will catch errors like failed JSON parsing or other unexpected issues
        logger.error(f"Error in /api/cleanup/trigger endpoint: {e}", exc_info=True)
        return jsonify({"message": "An internal server error occurred while trying to start the cleanup task."}), 500
# def trigger_manual_cleanup():
#     # logging.info("Manual cleanup triggered by user.")
    
#     # # Run in a background thread to return an immediate response
#     # cleanup_thread = threading.Thread(target=cleanup_service.perform_cleanup_actions)
#     # cleanup_thread.start()
    
#     # return jsonify({"message": "Cleanup task started in the background. Check logs for progress."}), 202
#     data = request.get_json()
#     is_dry_run = data.get('dryRun', False) # Get the dryRun flag from the request
#     run_mode = "Dry Run" if is_dry_run else "Live Run"
    
#     logging.info(f"Manual cleanup ({run_mode}) triggered by user.")
    
#     # We run this in the main thread for dry runs to return results directly
#     if is_dry_run:
#         results = cleanup_service.perform_cleanup_actions(dry_run=True)
#         return jsonify({"message": f"Dry run complete. See results below.", "results": results}), 200
    
#     # For live runs, use a background thread
#     cleanup_thread = threading.Thread(target=cleanup_service.perform_cleanup_actions, args=(False,))
#     cleanup_thread.start()
#     return jsonify({"message": "Cleanup task started in the background. Check logs for progress."}), 202





@app.route('/api/status')
def status():
    settings = load_settings()
    logging.debug("Connection status requested.")
    logging.warning(f"test {settings['SONARR_API_KEY']}")

    return jsonify({
        'plex': 'Connected' if plex_service.get_plex_connection() else 'Error',
        'sonarr': 'Connected' if settings['SONARR_API_KEY'] else 'Not Configured',
        'radarr': 'Connected' if settings['RADARR_API_KEY'] else 'Not Configured',
    })

@app.route('/api/logs')
def get_logs():
    logging.debug("Log data requested from UI.")
    try:
        with open('/app/backend/data/smart_storage.log', 'r') as f:
            lines = f.readlines()
            last_lines = lines[-200:]
            return jsonify("".join(last_lines))
    except FileNotFoundError:
        logging.warning("Log file not found when requesting /api/logs")
        return jsonify("Log file not found.")
    except Exception as e:
        logging.error(f"Error reading log file: {e}", exc_info=True)
        return jsonify(f"An error occurred while reading logs: {e}"), 500


# --- NEW ENDPOINT for the Settings Page ---
@app.route('/api/root-folders/all')
def get_all_root_folders():
    """
    Returns a dictionary containing lists of root folders from BOTH Sonarr and Radarr.
    This is optimized for the initial load of the settings page.
    """
    logging.debug("Combined root folder list requested from UI.")
    try:
        sonarr_folders = sonarr_service.get_root_folders()
        radarr_folders = radarr_service.get_root_folders()
        return jsonify({
            "sonarr": sonarr_folders,
            "radarr": radarr_folders
        })
    except Exception as e:
        logging.error(f"Error fetching all root folders: {e}", exc_info=True)
        return jsonify({"message": "Failed to retrieve root folders."}), 500



@app.route('/api/root-folders', methods=['GET'])

def get_root_folders_by_type():
    """
    Returns a list of root folders for a specific type ('sonarr' or 'radarr').
    Used by the archive dialog.
    """
    folder_type = request.args.get('type')
    if not folder_type:
        return jsonify({"message": "A 'type' query parameter of 'sonarr' or 'radarr' is required."}), 400
    
    try:
        folders = []
        if folder_type == 'sonarr':
            folders = sonarr_service.get_root_folders()
        elif folder_type == 'radarr':
            folders = radarr_service.get_root_folders()
        return jsonify({"folders": folders})
    except Exception as e:
        logging.error(f"Error fetching root folders for type '{folder_type}': {e}", exc_info=True)
        return jsonify({"message": f"Failed to retrieve {folder_type} root folders."}), 500

# # --- NEW ENDPOINT ---
# @app.route('/api/root-folders')
# def get_all_root_folders():
#     """
#     Returns a list of root folders for a specific type ('sonarr' or 'radarr').
#     """
#     folder_type = request.args.get('type') # e.g., /api/root-folders?type=sonarr
#     logging.debug(f"Root folder list requested from UI for type: {folder_type}")
    
#     try:
#         folders = []
#         if folder_type == 'sonarr':
#             folders = sonarr_service.get_root_folders()
#         elif folder_type == 'radarr':
#             folders = radarr_service.get_root_folders()
#         else:
#             return jsonify({"message": "A 'type' query parameter of 'sonarr' or 'radarr' is required."}), 400

#         # The response now sends the list directly under a 'folders' key
#         return jsonify({"folders": folders})
#     except Exception as e:
#         logger.error(f"Error fetching root folders for type '{folder_type}': {e}", exc_info=True)
#         return jsonify({"message": f"Failed to retrieve {folder_type} root folders."}), 500



@app.route('/api/dashboard')
def get_dashboard_data():
    """
    This endpoint is now extremely fast. It ONLY reads from the cache,
    which is populated by the background sync task.
    """
    logging.info("Dashboard data requested by user.")
    
    # Try to get the pre-computed dashboard data from the cache.
    dashboard_data = cache.get('dashboard_data')
    
    if dashboard_data:
        logging.info("Returning pre-computed dashboard data from cache.")
        return jsonify(dashboard_data)
    else:
        # This case happens if the app has just started and the initial sync hasn't finished.
        # We can return a loading state or even trigger a sync manually here as a fallback.
        logging.warning("Dashboard data not yet available in cache. The initial sync might be running.")
        return jsonify({
            "message": "Data is being gathered in the background. Please try again in a moment."
        }), 202 # HTTP 202 Accepted status






    """ logging.info("Dashboard data requested.")

        # --- Caching Logic ---
    # Try to get the fully computed dashboard data from the cache first
    cached_data = cache.get('dashboard_data')
    if cached_data:
        logging.info("Returning dashboard data from cache.")
        return jsonify(cached_data)

    logging.info("Cache miss. Re-computing dashboard data.")
    settings = load_settings()
    all_media = plex_service.get_plex_library()
    analyzed_media = analysis_service.apply_rules_to_media(all_media, settings)
    
    candidates = [item.__dict__ for item in analyzed_media if item.status and 'candidate' in item.status]
    potential_savings = sum(c['size'] for c in candidates)
    
    # --- REAL STORAGE DATA ---
    # Call our new service to get actual disk usage in bytes
    disk_stats_bytes = storage_service.get_combined_disk_usage()
    # Convert bytes to Gigabytes for the API response
    storage_data = StorageInfo(
        total=disk_stats_bytes['total'] / (1024**3),
        used=disk_stats_bytes['used'] / (1024**3),
        available=disk_stats_bytes['free'] / (1024**3)
    )
    
    # Get archive drive stats with error handling
    archive_drive_stats = storage_service.get_archive_stats()
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
    sonarr_summary = sonarr_service.get_library_summary()
    tv_shows_size_gb = sonarr_summary['total_gb']
    tv_shows_episodes = sonarr_summary['total_episodes']
    tv_shows = sonarr_summary['total_series']
    radarr_summary = radarr_service.get_library_summary()
    movies_size_gb = radarr_summary['total_gb'] 
    movies = radarr_summary['total_movies'] 
    #movies_size_gb = sum(m.size for m in all_media if m.type == 'movie')
    
    upcoming = sonarr_service.get_upcoming_shows()
    
    # Recommended actions: largest ended shows and largest movies on streaming
    ended_shows = [item for item in analyzed_media
                   if item.type == 'tv' and item.status == 'ended']
    ended_shows_sorted = sorted(ended_shows, key=lambda x: x.size, reverse=True)[:5]
    
    streaming_movies = [item for item in analyzed_media
                        if item.type == 'movie' and item.status =='delete-if-streaming']
    streaming_movies_sorted = sorted(streaming_movies, key=lambda x: x.size, reverse=True)[:5]



    large_movies = [item for item in analyzed_media
                        if item.type == 'movie' and item.status !='archive'] # and item.rootFolderPath.find('4K') == -1]
    large_movies_sorted = sorted(large_movies, key=lambda x: x.size, reverse=True)[:10]

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
            'onStreaming': len([m for m in all_media if m.streamingServices]),
        },
        'recommendedActions': {
            'endedShows': [item.__dict__ for item in ended_shows_sorted],
            'streamingMovies': [item.__dict__ for item in streaming_movies_sorted]
        }
    } """
        # --- Store the result in the cache for next time ---
    cache.set('dashboard_data', dashboard_data, timeout=CACHE_TIMEOUT)


    return jsonify(dashboard_data)



@app.route('/api/sync/trigger', methods=['POST'])
def trigger_manual_sync():
    """
    Manually triggers the background sync task.
    It runs the sync in a separate thread so the user's request
    doesn't have to wait for the entire sync to finish.
    """
    logging.info("Manual sync triggered by user from the settings page.")
    
    # Check if a sync is already running to prevent duplicates
    # (APScheduler is smart about this, but this is an extra layer of safety)
    if cache.get('is_syncing'):
        logging.warning("Sync request denied: a sync is already in progress.")
        # Return a 429 Too Many Requests status
        return jsonify({"message": "A sync is already in progress. Please wait."}), 429

    try:
        # Set a flag in the cache to indicate a sync is running
        cache.set('is_syncing', True, timeout=1800) # Timeout after 30 mins just in case

        # Run the sync function in a non-blocking background thread
        # This makes the API endpoint return immediately for the user
        sync_thread = threading.Thread(target=perform_full_sync_and_clear_flag)
        sync_thread.start()

        # Immediately return a success response to the user
        return jsonify({"message": "Sync started in the background. Dashboard will update shortly."}), 202
    except Exception as e:
        logging.error(f"Failed to start manual sync thread: {e}", exc_info=True)
        # Clear the flag on error
        cache.delete('is_syncing')
        return jsonify({"message": "An error occurred while trying to start the sync."}), 500

def perform_full_sync_and_clear_flag():
    """
    A helper function to run the sync and ensure the 'is_syncing'
    flag in the cache is cleared, even if the sync fails.
    """
    try:
        perform_full_sync()
    finally:
        # This `finally` block ensures the flag is always removed
        cache.delete('is_syncing')
        logging.info("Sync finished, 'is_syncing' flag cleared.")

# Removed duplicate route definition

@app.route('/api/content')
def get_content_data():
    logging.info("Full content list requested.")
    from config import load_settings
    settings = load_settings()
    all_media = plex_service.get_plex_library()
    analyzed_media = analysis_service.apply_rules_to_media(all_media, settings)
    return jsonify([item.__dict__ for item in analyzed_media])

@app.route('/api/settings', methods=['GET', 'POST'])
def handle_settings():
    if request.method == 'POST':
        new_settings = request.json
        logging.info("Saving settings.")
        save_settings(new_settings)
        


        # --- NEW: Parse and add the available archive destination folders ---
        # tv_archive_str = os.getenv('TV_ARCHIVE_FOLDERS', '')
        # movie_archive_str = os.getenv('MOVIE_ARCHIVE_FOLDERS', '')
        
        # new_settings['availableTvArchiveFolders'] = [p.strip() for p in tv_archive_str.split(',') if p.strip()]
        # new_settings['availableMovieArchiveFolders'] = [p.strip() for p in movie_archive_str.split(',') if p.strip()]

        # Also add the available streaming providers (from previous implementation)
        providers_str = os.getenv('AVAILABLE_STREAMING_PROVIDERS', '')
        new_settings['AVAILABLE_STREAMING_PROVIDERS'] = [p.strip() for p in providers_str.split(',') if p.strip()]
        
        # Also save environment variables to .env file
        # env_vars = [
        #     'PLEX_URL', 'PLEX_TOKEN',
        #     'SONARR_URL', 'SONARR_API_KEY',
        #     'RADARR_URL', 'RADARR_API_KEY',
        #     'TMDB_API_KEY', 'MOUNT_POINTS',
        #     'ARCHIVE_DRIVE', 'STREAMING_PROVIDERS',
        #     'TV_ARCHIVE_FOLDERS', 'MOVIE_ARCHIVE_FOLDERS',
        #     'DATA_UPDATE_INTERVAL','AVAILABLE_STREAMING_PROVIDERS','ENABLE_AUTO_ACTIONS',
        # ]
        
        # env_lines = []
        # for var in env_vars:
        #     value = new_settings.get(var, '')
        #     # For array values, join with commas
        #     if isinstance(value, list):
        #         value = ','.join(value)
        #     env_lines.append(f"{var}={value}")
        
        # # Write to .env file
        # with open('.env', 'w') as f:
        #     f.write('\n'.join(env_lines))
        
        # return jsonify(new_settings)
    
    logging.debug("Settings data requested.")
    #from config import load_settings
    settings = load_settings()
    logging.warning(f"settings TEST 5 {settings.get('PLEX_URL','') }")
    # Get TV and movie archive folders from environment variables
    # Add all relevant environment variables to the settings response
    # env_vars = ['Streaming Preferences',
    #     'PLEX_URL', 'PLEX_TOKEN',
    #     'SONARR_URL', 'SONARR_API_KEY',
    #     'RADARR_URL', 'RADARR_API_KEY',
    #     'TMDB_API_KEY', 'MOUNT_POINTS',
    #     'ARCHIVE_DRIVE', 'STREAMING_PROVIDERS','AVAILABLE_STREAMING_PROVIDERS',
    #     'TV_ARCHIVE_FOLDERS', 'MOVIE_ARCHIVE_FOLDERS','DATA_UPDATE_INTERVAL'
    # ]
    # #if settings.get('PLEX_URL','') is None:
    # for var in env_vars:
    #     value = os.getenv(var, '')
    #     # For comma-separated values, split into arrays
    #     if var in ['MOUNT_POINTS', 'STREAMING_PROVIDERS', 'TV_ARCHIVE_FOLDERS', 'MOVIE_ARCHIVE_FOLDERS']:
    #         settings[var] = [v.strip() for v in value.split(',') if v.strip()]
    #     else:
    #         settings[var] = value
    #         # --- NEW: Add the available providers list to the settings response ---
    #     providers_str = os.getenv('AVAILABLE_STREAMING_PROVIDERS', '')
    #     available_providers = [p.strip() for p in providers_str.split(',') if p.strip()]

    # #else:


    return jsonify(settings)




def get_service_root_folders():
    service_type = request.args.get('type')
    if service_type == 'sonarr':
        # Get root folders from Sonarr
        return jsonify({'folders': get_sonarr_root_folders()})
    elif service_type == 'radarr':
        # Get root folders from Radarr
        return jsonify({'folders': get_radarr_root_folders()})
    else:
        return jsonify({'error': 'Invalid service type'}), 400

def get_sonarr_root_folders():
    """Get TV archive folders from environment variable"""
    folders = os.getenv('TV_ARCHIVE_FOLDERS', '')
    if folders:
        return [{'path': f.strip()} for f in folders.split(',') if f.strip()]
    return []

def get_radarr_root_folders():
    """Get movie archive folders from environment variable"""
    folders = os.getenv('MOVIE_ARCHIVE_FOLDERS', '')
    if folders:
        return [{'path': f.strip()} for f in folders.split(',') if f.strip()]
    return []

@app.route('/api/content/<media_id>/action', methods=['POST'])
def handle_action(media_id):
    data = request.json
    action = data.get('action')
    item_to_action = data.get('item', {})
    item_title = item_to_action.get('title', f"ID {media_id}")
    item_type = item_to_action.get('type')
    
    logging.info(f"Action '{action}' requested for item '{item_title}'")
    
    if action == 'delete':
        success, message = plex_service.delete_media_from_plex(media_id)
        if success:
            # Invalidate cache after a successful action
            cache.delete('dashboard_data')
            cache.delete('plex_media_data_full')
            return jsonify({'status': 'success', 'message': message})
        return jsonify({'status': 'error', 'message': message}), 500
            
    elif action == 'archive':
        # 1. Load settings using the central service.
        settings = load_settings()
        
        # 2. Get the selected archive path from the request body.
        selected_archive_folder = data.get('archivePath')
        item_id = None # Placeholder for sonarr/radarr ID

        # 3. Determine which list of valid archive folders to use based on media type.
        if item_type == 'tv':
            valid_archive_folders = settings.get('TV_ARCHIVE_FOLDERS', [])
            item_id = item_to_action.get('sonarrId')
        else: # Assumes 'movie'
            valid_archive_folders = settings.get('MOVIE_ARCHIVE_FOLDERS', [])
            item_id = item_to_action.get('radarrId')

        # 4. Perform validation.
        if not selected_archive_folder:
            error_msg = "No archive folder was selected in the request."
            logging.error(f"Archive failed for '{item_title}': {error_msg}")
            return jsonify({'status': 'error', 'message': error_msg}), 400
        
        if not valid_archive_folders:
            error_msg = f"No archive folders are configured for {item_type}s. Please set them in the settings."
            logging.error(f"Archive failed for '{item_title}': {error_msg}")
            return jsonify({'status': 'error', 'message': error_msg}), 400
            
        if selected_archive_folder not in valid_archive_folders:
            error_msg = f"Security error: The selected folder is not in the list of pre-configured archive folders."
            logging.error(f"Archive failed for '{item_title}': {error_msg}")
            return jsonify({'status': 'error', 'message': error_msg}), 400
            
        if not item_to_action.get('filePath'):
            return jsonify({'status': 'error', 'message': 'Could not find media item file path.'}), 404

        current_folder_path = os.path.dirname(item_to_action['filePath'])
        
        # 5. Execute the file move.
        if item_type == 'tv':
            move_success, move_result = file_service.move_sonarr_series(current_folder_path, selected_archive_folder, item_id)
        else:
            move_success, move_result = file_service.move_radarr_movie(current_folder_path, selected_archive_folder, item_id)
        
        if not move_success:
            return jsonify({'status': 'error', 'message': f"File move failed: {move_result}"}), 500
        
        # 6. Invalidate caches on success
        cache.delete('dashboard_data')
        cache.delete('plex_media_data_full')
        
        return jsonify({'status': 'success', 'message': f"Successfully archived '{item_title}'."})
        
    return jsonify({'status': 'error', 'message': 'Invalid action'}), 400


# @app.route('/api/content/<media_id>/action', methods=['POST'])
# def handle_action(media_id):
#     data = request.json
#     action = data.get('action')
#     item_to_action = data.get('item', {})
#     item_title = item_to_action.get('title', f"ID {media_id}")
#     item_type = item_to_action.get('type')
#     plex_id = item_to_action.get('ID', f"ID {media_id}")
#     if item_type == 'tv':
#         sonarr_title_id_map = sonarr_service.get_series_title_id_map()
#         item_id = sonarr_title_id_map.get(item_title)
#     else: 
#         radarr_title_id_map = radarr_service.get_movie_title_id_map() #item_to_action.get('id', f"ID {media_id}")
#         item_id = radarr_title_id_map.get(item_title)
#     #item_id = sonarr_service.get_series_title_id_map() s if item_type == 'tv' else item_to_action.get('id', f"ID {media_id}")
#     logging.info(f"Action '{action}' requested for item '{item_title}'")
    
#     if action == 'delete':
#         success, message = plex_service.delete_media_from_plex(media_id)
#         if success: return jsonify({'status': 'success', 'message': message})
#         return jsonify({'status': 'error', 'message': message}), 500
            
#     elif action == 'archive':
#         #from config import load_settings
#         settings = load_settings()
#         settings['tvArchiveFolders'] =  [f for f in os.getenv('TV_ARCHIVE_FOLDERS', '').split(',') if f]
#         settings['movieArchiveFolders'] = [f for f in os.getenv('MOVIE_ARCHIVE_FOLDERS', '').split(',') if f]
 
#         # Get the item type from the item_to_action
        
#         # Now get archive folders based on media type
#         archive_folders = settings['tvArchiveFolders'] if item_type == 'tv' else settings['movieArchiveFolders']
#         if not archive_folders:
#             error_msg = f"No archive folders configured for {item_type} content"
#             logging.error(f"Archive failed for '{item_title}': {error_msg}")
#             return jsonify({'status': 'error', 'message': error_msg}), 400
        
#         # Use the selected archive folder from the request
#         selected_archive_folder = data.get('archivePath')
#         if not selected_archive_folder:
#             error_msg = "No archive folder selected in the request"
#             logging.error(f"Archive failed for '{item_title}': {error_msg}")
#             return jsonify({'status': 'error', 'message': error_msg}), 400
            
#         # Validate the selected folder is in the configured folders
#         if selected_archive_folder not in archive_folders:
#             error_msg = f"Selected folder is not in configured {item_type} archive folders"
#             logging.error(f"Archive failed for '{item_title}': {error_msg}")
#             return jsonify({'status': 'error', 'message': error_msg}), 400
            
#         logging.info(f"Using selected archive path: {selected_archive_folder} for {item_title}")
#         if not item_to_action or not item_to_action.get('filePath'):
#             logging.error(f"Archive failed for '{item_title}': Could not find media item file path.")
#             return jsonify({'status': 'error', 'message': 'Could not find media item file path.'}), 404

#         current_folder_path = os.path.dirname(item_to_action['filePath'])

#         if item_type == 'tv':
#             move_success, move_result = file_service.move_sonarr_series(current_folder_path, selected_archive_folder, item_id)  #file_service.move_to_archive(current_folder_path, selected_archive_folder)
#         else: 
#             move_success, move_result = file_service.move_radarr_movie(current_folder_path, selected_archive_folder, item_id)
        
#         if not move_success:
#             return jsonify({'status': 'error', 'message': f"File move failed: {move_result}"}), 500
        
#         new_folder_path = move_result
#         # We removed the assignment of item_type here because we already set it above
#         update_success, update_message = False, "Item type not supported for automated update."

#         if item_type == 'tv':
#             sonarr_id = item_to_action.get('sonarrId')
#             if not sonarr_id:
#                 update_message = f"Files moved, but Sonarr ID was missing. Please update Sonarr manually for show '{item_title}'."
#                 logging.warning(update_message)
#             else:
#                 # Get Sonarr root folders
#                 root_folders = sonarr_service.get_root_folders()
#                 folder_paths = [folder['path'] for folder in root_folders]
                
#                 # Check if new path is in Sonarr's root folders
#                 if new_folder_path not in folder_paths:
#                     if root_folders:
#                         new_root_folder = root_folders[0]['path']
#                         logging.info(f"Selected root folder '{new_root_folder}' for show ID {sonarr_id}")
#                     else:
#                         update_message = "No root folders available in Sonarr"
#                         logging.error(update_message)
#                         return jsonify({'status': 'error', 'message': update_message}), 400
#                 else:
#                     new_root_folder = new_folder_path
                
#                 update_success, update_message = sonarr_service.update_show_root_folder(sonarr_id, new_root_folder)
        
#         elif item_type == 'movie':
#             radarr_id = item_to_action.get('radarrId')
#             if not radarr_id:
#                 update_message = f"Files moved, but Radarr ID was missing. Please update Radarr manually for movie '{item_title}'."
#                 logging.warning(update_message)
#             else:
#                 # Get Radarr root folders
#                 root_folders = radarr_service.radarr_api.get_root_folders()
#                 folder_paths = [folder['path'] for folder in root_folders]
                
#                 # Check if new path is in Radarr's root folders
#                 if new_folder_path not in folder_paths:
#                     if root_folders:
#                         new_root_folder = root_folders[0]['path']
#                         logging.info(f"Selected root folder '{new_root_folder}' for movie ID {radarr_id}")
#                     else:
#                         update_message = "No root folders available in Radarr"
#                         logging.error(update_message)
#                         return jsonify({'status': 'error', 'message': update_message}), 400
#                 else:
#                     new_root_folder = new_folder_path
                
#                 update_success, update_message = radarr_service.update_movie_root_folder(radarr_id, new_root_folder)

#         if not update_success:
#              return jsonify({'status': 'warning', 'message': update_message}), 207
        
#         return jsonify({'status': 'success', 'message': f"Successfully archived '{item_title}'."})
        
#     return jsonify({'status': 'error', 'message': 'Invalid action'}), 400

#if __name__ == '__main__':
#    app.run(debug=True, port=5001)app