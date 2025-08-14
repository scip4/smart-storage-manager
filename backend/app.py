# backend/app.py
import os
import json
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv
from services import plex_service, sonarr_service, radarr_service, analysis_service, file_service, storage_service


load_dotenv()

# --- LOGGING SETUP ---
def setup_logging():
    log_file = 'smart_storage.log'
    # 5 MB per file, keep last 5 files
    file_handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=5)
    file_handler.setLevel(logging.INFO)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    if not logger.handlers:
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
    logging.info("Application starting up...")

# Initialize Flask App
app = Flask(__name__)
setup_logging() # Call the logging setup

CORS(app, resources={r"/api/*": {"origins": "*"}})

from models import StorageInfo
from services import plex_service, sonarr_service, radarr_service, analysis_service, file_service

SETTINGS_FILE = 'settings.json'

def get_default_settings():
    return {
        "autoDeleteAfterDays": 30, "archiveAfterMonths": 6, "keepFreeSpace": 500,
        "enableAutoActions": False, "checkStreamingAvailability": True,
        "preferredStreamingServices": [], "archiveFolderPath": ""
    }

def load_settings():
    try:
        with open(SETTINGS_FILE, 'r') as f:
            defaults = get_default_settings()
            user_settings = json.load(f)
            defaults.update(user_settings)
            return defaults
    except (FileNotFoundError, json.JSONDecodeError):
        return get_default_settings()

def save_settings(settings):
    with open(SETTINGS_FILE, 'w') as f: json.dump(settings, f, indent=2)

@app.route('/api/status')
def status():
    logging.debug("Connection status requested.")
    return jsonify({
        'plex': 'Connected' if plex_service.get_plex_connection() else 'Error',
        'sonarr': 'Connected' if os.getenv('SONARR_API_KEY') else 'Not Configured',
        'radarr': 'Connected' if os.getenv('RADARR_API_KEY') else 'Not Configured',
    })

@app.route('/api/logs')
def get_logs():
    logging.debug("Log data requested from UI.")
    try:
        with open('smart_storage.log', 'r') as f:
            lines = f.readlines()
            last_lines = lines[-200:]
            return jsonify("".join(last_lines))
    except FileNotFoundError:
        logging.warning("Log file not found when requesting /api/logs")
        return jsonify("Log file not found.")
    except Exception as e:
        logging.error(f"Error reading log file: {e}", exc_info=True)
        return jsonify(f"An error occurred while reading logs: {e}"), 500







@app.route('/api/dashboard')
def get_dashboard_data():
    logging.info("Dashboard data requested.")
    settings = load_settings()
    all_media = plex_service.get_plex_library()
    analyzed_media = analysis_service.apply_rules_to_media(all_media, settings)
    
    candidates = [item.__dict__ for item in analyzed_media if 'candidate' in item.status]
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
    
    return jsonify({
        'storageData': storage_data.__dict__, # This now contains REAL data
        'potentialSavings': round(potential_savings, 2),
        'candidates': candidates,
        'upcomingReleases': upcoming,
        'libraryStats': {
            'tv': tv_shows, #len([m for m in all_media if m.type == 'tv']),
            'tv_size': round(tv_shows_size_gb, 1),
            'tv_episodes': tv_shows_episodes,
            'movies': movies, #len([m for m in all_media if m.type == 'movie']),
            'movies_size': round(movies_size_gb, 1),
            'onStreaming': len([m for m in all_media if m.streamingAvailability]),
        }
    })


@app.route('/api/content')
def get_content_data():
    logging.info("Full content list requested.")
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
        return jsonify(new_settings)
    logging.debug("Settings data requested.")
    return jsonify(load_settings())

@app.route('/api/content/<media_id>/action', methods=['POST'])
def handle_action(media_id):
    data = request.json
    action = data.get('action')
    item_to_action = data.get('item', {})
    item_title = item_to_action.get('title', f"ID {media_id}")
    logging.info(f"Action '{action}' requested for item '{item_title}'")
    
    if action == 'delete':
        success, message = plex_service.delete_media_from_plex(media_id)
        if success: return jsonify({'status': 'success', 'message': message})
        return jsonify({'status': 'error', 'message': message}), 500
            
    elif action == 'archive':
        settings = load_settings()
        archive_path = settings.get('archiveFolderPath')
        if not archive_path:
            logging.error(f"Archive failed for '{item_title}': Archive folder path is not configured.")
            return jsonify({'status': 'error', 'message': 'Archive folder path is not configured.'}), 400
        if not item_to_action or not item_to_action.get('filePath'):
            logging.error(f"Archive failed for '{item_title}': Could not find media item file path.")
            return jsonify({'status': 'error', 'message': 'Could not find media item file path.'}), 404

        current_folder_path = os.path.dirname(item_to_action['filePath'])
        move_success, move_result = file_service.move_to_archive(current_folder_path, archive_path)
        if not move_success:
            return jsonify({'status': 'error', 'message': f"File move failed: {move_result}"}), 500
        
        new_folder_path = move_result
        item_type = item_to_action.get('type')
        update_success, update_message = False, "Item type not supported for automated update."

        if item_type == 'tv':
            sonarr_id = item_to_action.get('sonarrId')
            if not sonarr_id:
                update_message = f"Files moved, but Sonarr ID was missing. Please update Sonarr manually for show '{item_title}'."
                logging.warning(update_message)
            else:
                update_success, update_message = sonarr_service.update_show_root_folder(sonarr_id, new_folder_path)
        
        # Add Radarr logic here...

        if not update_success:
             return jsonify({'status': 'warning', 'message': update_message}), 207
        
        return jsonify({'status': 'success', 'message': f"Successfully archived '{item_title}'."})
        
    return jsonify({'status': 'error', 'message': 'Invalid action'}), 400

if __name__ == '__main__':
    app.run(debug=True, port=5001)