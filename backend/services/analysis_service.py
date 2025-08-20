# backend/services/analysis_service.py
from datetime import datetime, timedelta

def apply_rules_to_media(media_list, settings):
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

        # Rule: Archive ended shows
        if item.type == 'tv' and (item.status == 'ended' or item.status == 'Ended') and item.rule in ['archive-ended', 'auto-manage']:
            item.status = 'candidate-archive'
            continue
            
        # Rule: Delete if on a preferred streaming service
        if item.rule == 'delete-if-streaming' and item.streamingServices:
            # A more robust check would see if it's on a *preferred* service
            item.status = 'candidate-delete'
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