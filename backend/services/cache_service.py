# backend/services/cache_service.py
from cachelib.simple import SimpleCache

# Initialize a simple in-memory cache.
# For production, you might consider a file-based or Redis cache.
# The default timeout is 300 seconds (5 minutes).
cache = SimpleCache()

# You can adjust the cache timeout (in seconds) globally here
CACHE_TIMEOUT = 21600 # 6 hours