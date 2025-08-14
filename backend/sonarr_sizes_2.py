#!/usr/bin/env python3
"""
Sonarr Series Size Calculator
Fetches all series from Sonarr API and calculates total storage usage
"""

import requests
import json
import os
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import argparse
from datetime import datetime
from dotenv import load_dotenv

@dataclass
class SonarrSeries:
    id: int
    title: str
    monitored: bool
    season_count: int
    episode_count: int
    size_bytes: int
    path: str
    status: str
    
    @property
    def size_gb(self) -> float:
        """Convert bytes to gigabytes"""
        return round(self.size_bytes / (1024**3), 2)
    
    @property 
    def size_mb(self) -> float:
        """Convert bytes to megabytes"""
        return round(self.size_bytes / (1024**2), 2)

class SonarrAPI:
    def __init__(self, base_url: str, api_key: str):
        """
        Initialize Sonarr API client
        
        Args:
            base_url: Sonarr server URL (e.g., 'http://192.168.1.100:8989')
            api_key: Sonarr API key
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            'X-Api-Key': api_key,
            'Content-Type': 'application/json'
        })
    
    def test_connection(self) -> bool:
        """Test if the API connection is working"""
        try:
            response = self.session.get(f'{self.base_url}/api/v3/system/status')
            return response.status_code == 200
        except Exception as e:
            print(f"Connection test failed: {e}")
            return False
    
    def get_all_series(self) -> List[Dict]:
        """Get all series from Sonarr"""
        try:
            response = self.session.get(f'{self.base_url}/api/v3/series')
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching series: {e}")
            return []
    
    def get_episode_files(self, series_list: Optional[List[Dict]] = None) -> List[Dict]:
        """
        Get all episode files from Sonarr
        
        Args:
            series_list: Optional list of series to get episodes for. If None, gets all episodes.
        
        Returns:
            List of all episode file information
        """
        try:
            all_episodes = []
            
            if series_list is None:
                # Fallback to original method if no series list provided
                response = self.session.get(f'{self.base_url}/api/v3/episodefile')
                response.raise_for_status()
                return response.json()
            
            print(f"Fetching episodes for {len(series_list)} series...")
            
            for i, series in enumerate(series_list):
                series_id = series['id']
                series_title = series.get('title', f'Series {series_id}')
                
                try:
                    # Use the episode endpoint to get episode information for this series
                    response = self.session.get(f'{self.base_url}/api/v3/episodeFile', 
                                              params={'seriesId': series_id})
                    response.raise_for_status()
                    episodes = response.json()
                    
                    # Filter episodes that have episode files and extract file info
                    for episode in episodes:
                       # if episode.get('hasFile', False) and 'path' in episode:
                            episode_file = episode #episode['path']
                            # Add series ID to the episode file for consistency
                            episode_file['seriesId'] = series_id
                            all_episodes.append(episode_file)
                    
                    # Progress indicator
                    if (i + 1) % 10 == 0:
                        print(f"  Processed {i + 1}/{len(series_list)} series...")
                        
                except requests.exceptions.RequestException as e:
                    print(f"Warning: Error fetching episodes for series '{series_title}' (ID: {series_id}): {e}")
                    continue
            
            print(f"Found {len(all_episodes)} episode files across all series")
            return all_episodes
            
        except Exception as e:
            print(f"Error fetching episode files: {e}")
            return []
    
    def get_episode_files_by_series(self, series_id: int) -> List[Dict]:
        """Get episode files for a specific series"""
        try:
            response = self.session.get(f'{self.base_url}/api/v3/episodefile', 
                                      params={'seriesId': series_id})
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching episode files for series {series_id}: {e}")
            return []
    
    def get_series_statistics(self) -> Dict[int, Dict]:
        """
        Get detailed statistics for all series including file sizes
        This is more efficient than calling individual series endpoints
        """
        try:
            # Get all episode files at once
            all_files = self.get_episode_files()
            
            # Group files by series ID
            series_stats = {}
            
            for episode_file in all_files:
                series_id = episode_file.get('seriesId')
                if not series_id:
                    continue
                    
                if series_id not in series_stats:
                    series_stats[series_id] = {
                        'total_size': 0,
                        'episode_count': 0,
                        'files': []
                    }
                
                file_size = episode_file.get('size', 0)
                series_stats[series_id]['total_size'] += file_size
                series_stats[series_id]['episode_count'] += 1
                series_stats[series_id]['files'].append({
                    'id': episode_file.get('id'),
                    'relativePath': episode_file.get('relativePath'),
                    'size': file_size,
                    'quality': episode_file.get('quality', {}).get('quality', {}).get('name', 'Unknown'),
                    'mediaInfo': episode_file.get('mediaInfo', {})
                })
            
            return series_stats
            
        except Exception as e:
            print(f"Error calculating series statistics: {e}")
            return {}

    def get_series_statistics_optimized(self, series_list: Optional[List[Dict]] = None) -> Dict[int, Dict]:
        """
        Get detailed statistics for all series including file sizes
        Optimized version that can reuse existing series data
        
        Args:
            series_list: Optional pre-fetched series list to avoid duplicate API calls
        
        Returns:
            Dictionary mapping series_id to statistics
        """
        try:
            # Use provided series list or fetch it if not provided
            if series_list is None:
                series_list = self.get_all_series()
            
            # Create a mapping of series ID to basic series info for faster lookups
            series_lookup = {series['id']: series for series in series_list}
            
            # Get all episode files using the series-specific approach
            print("Fetching episode files using series-specific API calls...")
            all_files = self.get_episode_files(series_list)
            
            # Group files by series ID
            series_stats = {}
            
            # Initialize stats for all series (including those with no files)
            for series in series_list:
                series_id = series['id']
                series_stats[series_id] = {
                    'total_size': 0,
                    'episode_count': 0,
                    'files': [],
                    'series_info': series  # Include series metadata
                }
            
            print(f"Processing {len(all_files)} episode files...")
            
            # Process episode files
            for episode_file in all_files:
                series_id = episode_file.get('seriesId')
                if not series_id or series_id not in series_stats:
                    continue
                
                file_size = episode_file.get('size', 0)
                series_stats[series_id]['total_size'] += file_size
                series_stats[series_id]['episode_count'] += 1
                series_stats[series_id]['files'].append({
                    'id': episode_file.get('id'),
                    'relativePath': episode_file.get('relativePath'),
                    'size': file_size,
                    'quality': episode_file.get('quality', {}).get('quality', {}).get('name', 'Unknown'),
                    'mediaInfo': episode_file.get('mediaInfo', {})
                })
            
            return series_stats
            
        except Exception as e:
            print(f"Error calculating series statistics: {e}")
            return {}

    def get_series_statistics_batch(self, series_ids: List[int] = None, 
                                   include_files: bool = True) -> Dict[int, Dict]:
        """
        Get statistics for specific series or all series with better control
        
        Args:
            series_ids: List of specific series IDs to get stats for (None = all)
            include_files: Whether to include detailed file information
        
        Returns:
            Dictionary mapping series_id to statistics
        """
        try:
            # If specific series IDs provided, we can be more targeted
            if series_ids:
                print(f"Fetching statistics for {len(series_ids)} specific series...")
                
                # Get series info for the requested IDs
                all_series = self.get_all_series()
                target_series = [s for s in all_series if s['id'] in series_ids]
                
                # Initialize stats for requested series
                series_stats = {}
                for series in target_series:
                    series_id = series['id']
                    series_stats[series_id] = {
                        'total_size': 0,
                        'episode_count': 0,
                        'files': [] if include_files else None,
                        'series_info': series
                    }
                
                # Get episode files for these specific series
                all_files = self.get_episode_files(target_series)
                
                # Process files for requested series
                for episode_file in all_files:
                    series_id = episode_file.get('seriesId')
                    if series_id not in series_stats:
                        continue
                        
                    file_size = episode_file.get('size', 0)
                    series_stats[series_id]['total_size'] += file_size
                    series_stats[series_id]['episode_count'] += 1
                    
                    if include_files:
                        series_stats[series_id]['files'].append({
                            'id': episode_file.get('id'),
                            'relativePath': episode_file.get('relativePath'),
                            'size': file_size,
                            'quality': episode_file.get('quality', {}).get('quality', {}).get('name', 'Unknown'),
                            'mediaInfo': episode_file.get('mediaInfo', {})
                        })
                
                return series_stats
            else:
                # Fall back to getting all series statistics
                return self.get_series_statistics_optimized()
                
        except Exception as e:
            print(f"Error calculating batch series statistics: {e}")
            return {}

    def get_series_with_builtin_stats(self) -> List[Dict]:
        """
        Alternative approach: Use Sonarr's built-in statistics from the series endpoint
        This might be less accurate but much faster for basic size estimates
        
        Note: Sonarr's built-in statistics might not always be up-to-date
        """
        try:
            response = self.session.get(f'{self.base_url}/api/v3/series')
            response.raise_for_status()
            series_list = response.json()
            
            # Sonarr series objects include some statistics
            enhanced_series = []
            for series in series_list:
                # Extract built-in statistics if available
                stats = series.get('statistics', {})
                
                enhanced_series.append({
                    **series,
                    'calculated_size': stats.get('sizeOnDisk', 0),
                    'episode_file_count': stats.get('episodeFileCount', 0),
                    'episode_count': stats.get('episodeCount', 0),
                    'total_episode_count': stats.get('totalEpisodeCount', 0)
                })
            
            return enhanced_series
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching series with built-in stats: {e}")
            return []

def calculate_series_sizes_enhanced(sonarr: SonarrAPI) -> Tuple[List[SonarrSeries], Dict]:
    """
    Enhanced series size calculation with better accuracy
    
    Returns:
        Tuple of (series_list, summary_stats)
    """
    print("Fetching series data...")
    all_series = sonarr.get_all_series()
    
    print("Calculating series statistics...")
    series_stats = sonarr.get_series_statistics()
    
    # Process series data with enhanced statistics
    series_objects = []
    total_size = 0
    monitored_size = 0
    monitored_count = 0
    total_episodes = 0
    
    print(f"Processing {len(all_series)} series...")
    
    for series_data in all_series:
        series_id = series_data['id']
        series_title = series_data.get('title', 'Unknown')
        
        # Get statistics for this series
        stats = series_stats.get(series_id, {
            'total_size': 0,
            'episode_count': 0,
            'files': []
        })
        
        size_bytes = stats['total_size']
        episode_count = stats['episode_count']
        
        # Get additional series information
        seasons = series_data.get('seasons', [])
        season_count = len([s for s in seasons if s.get('seasonNumber', 0) > 0])  # Exclude specials
        
        series = SonarrSeries(
            id=series_id,
            title=series_title,
            monitored=series_data.get('monitored', False),
            season_count=season_count,
            episode_count=episode_count,
            size_bytes=size_bytes,
            path=series_data.get('path', ''),
            status=series_data.get('status', 'unknown')
        )
        
        series_objects.append(series)
        total_size += size_bytes
        total_episodes += episode_count
        
        if series.monitored:
            monitored_size += size_bytes
            monitored_count += 1
            
        # Progress indicator
        if len(series_objects) % 10 == 0:
            print(f"  Processed {len(series_objects)}/{len(all_series)} series...")
    
    # Calculate summary statistics
    summary = {
        'total_series': len(series_objects),
        'monitored_series': monitored_count,
        'unmonitored_series': len(series_objects) - monitored_count,
        'total_size_bytes': total_size,
        'total_size_gb': round(total_size / (1024**3), 2),
        'total_size_tb': round(total_size / (1024**4), 2),
        'monitored_size_bytes': monitored_size,
        'monitored_size_gb': round(monitored_size / (1024**3), 2),
        'unmonitored_size_gb': round((total_size - monitored_size) / (1024**3), 2),
        'total_episodes': total_episodes,
        'average_episode_size_mb': round((total_size / total_episodes) / (1024**2), 2) if total_episodes > 0 else 0,
        'average_series_size_gb': round(total_size / len(series_objects) / (1024**3), 2) if len(series_objects) > 0 else 0
    }
    
    return series_objects, summary

def calculate_series_sizes_optimized(sonarr: SonarrAPI) -> Tuple[List[SonarrSeries], Dict]:
    """
    Enhanced series size calculation with better performance
    Optimized to avoid duplicate API calls
    """
    print("Fetching series data...")
    all_series = sonarr.get_all_series()
    
    print("Calculating series statistics (optimized)...")
    # Pass the already-fetched series list to avoid duplicate API call
    series_stats = sonarr.get_series_statistics_optimized(all_series)
    
    # Process series data with enhanced statistics
    series_objects = []
    total_size = 0
    monitored_size = 0
    monitored_count = 0
    total_episodes = 0
    
    print(f"Processing {len(all_series)} series...")
    
    for series_data in all_series:
        series_id = series_data['id']
        series_title = series_data.get('title', 'Unknown')
        
        # Get statistics for this series
        stats = series_stats.get(series_id, {
            'total_size': 0,
            'episode_count': 0,
            'files': []
        })
        
        size_bytes = stats['total_size']
        episode_count = stats['episode_count']
        
        # Get additional series information
        seasons = series_data.get('seasons', [])
        season_count = len([s for s in seasons if s.get('seasonNumber', 0) > 0])
        
        series = SonarrSeries(
            id=series_id,
            title=series_title,
            monitored=series_data.get('monitored', False),
            season_count=season_count,
            episode_count=episode_count,
            size_bytes=size_bytes,
            path=series_data.get('path', ''),
            status=series_data.get('status', 'unknown')
        )
        
        series_objects.append(series)
        total_size += size_bytes
        total_episodes += episode_count
        
        if series.monitored:
            monitored_size += size_bytes
            monitored_count += 1
    
    # Calculate summary statistics
    summary = {
        'total_series': len(series_objects),
        'monitored_series': monitored_count,
        'unmonitored_series': len(series_objects) - monitored_count,
        'total_size_bytes': total_size,
        'total_size_gb': round(total_size / (1024**3), 2),
        'total_size_tb': round(total_size / (1024**4), 2),
        'monitored_size_bytes': monitored_size,
        'monitored_size_gb': round(monitored_size / (1024**3), 2),
        'unmonitored_size_gb': round((total_size - monitored_size) / (1024**3), 2),
        'total_episodes': total_episodes,
        'average_episode_size_mb': round((total_size / total_episodes) / (1024**2), 2) if total_episodes > 0 else 0,
        'average_series_size_gb': round(total_size / len(series_objects) / (1024**3), 2) if len(series_objects) > 0 else 0,
        'method': 'optimized'
    }
    
    return series_objects, summary

def calculate_series_sizes_fast(sonarr: SonarrAPI) -> Tuple[List[SonarrSeries], Dict]:
    """
    Fast series size calculation using Sonarr's built-in statistics
    Less accurate but much faster for large libraries
    """
    print("Fetching series data with built-in statistics...")
    all_series = sonarr.get_series_with_builtin_stats()
    
    series_objects = []
    total_size = 0
    monitored_size = 0
    monitored_count = 0
    total_episodes = 0
    
    print(f"Processing {len(all_series)} series...")
    
    for series_data in all_series:
        series_id = series_data['id']
        series_title = series_data.get('title', 'Unknown')
        
        # Use built-in statistics
        size_bytes = series_data.get('calculated_size', 0)
        episode_count = series_data.get('episode_file_count', 0)
        
        # Get additional series information
        seasons = series_data.get('seasons', [])
        season_count = len([s for s in seasons if s.get('seasonNumber', 0) > 0])
        
        series = SonarrSeries(
            id=series_id,
            title=series_title,
            monitored=series_data.get('monitored', False),
            season_count=season_count,
            episode_count=episode_count,
            size_bytes=size_bytes,
            path=series_data.get('path', ''),
            status=series_data.get('status', 'unknown')
        )
        
        series_objects.append(series)
        total_size += size_bytes
        total_episodes += episode_count
        
        if series.monitored:
            monitored_size += size_bytes
            monitored_count += 1
    
    # Calculate summary statistics
    summary = {
        'total_series': len(series_objects),
        'monitored_series': monitored_count,
        'unmonitored_series': len(series_objects) - monitored_count,
        'total_size_bytes': total_size,
        'total_size_gb': round(total_size / (1024**3), 2),
        'total_size_tb': round(total_size / (1024**4), 2),
        'monitored_size_bytes': monitored_size,
        'monitored_size_gb': round(monitored_size / (1024**3), 2),
        'unmonitored_size_gb': round((total_size - monitored_size) / (1024**3), 2),
        'total_episodes': total_episodes,
        'average_episode_size_mb': round((total_size / total_episodes) / (1024**2), 2) if total_episodes > 0 else 0,
        'average_series_size_gb': round(total_size / len(series_objects) / (1024**3), 2) if len(series_objects) > 0 else 0,
        'method': 'fast (built-in statistics)'
    }
    
    return series_objects, summary

def get_detailed_series_info(sonarr: SonarrAPI, series_id: int) -> Optional[Dict]:
    """Get detailed information for a specific series including file breakdown"""
    try:
        series_stats = sonarr.get_series_statistics()
        if series_id not in series_stats:
            return None
            
        stats = series_stats[series_id]
        
        # Group files by quality
        quality_breakdown = {}
        for file_info in stats['files']:
            quality = file_info['quality']
            if quality not in quality_breakdown:
                quality_breakdown[quality] = {
                    'count': 0,
                    'total_size': 0,
                    'files': []
                }
            quality_breakdown[quality]['count'] += 1
            quality_breakdown[quality]['total_size'] += file_info['size']
            quality_breakdown[quality]['files'].append(file_info)
        
        return {
            'series_id': series_id,
            'total_size': stats['total_size'],
            'total_size_gb': round(stats['total_size'] / (1024**3), 2),
            'episode_count': stats['episode_count'],
            'quality_breakdown': quality_breakdown,
            'files': stats['files']
        }
        
    except Exception as e:
        print(f"Error getting detailed info for series {series_id}: {e}")
        return None

def calculate_series_sizes(sonarr: SonarrAPI) -> Tuple[List[SonarrSeries], Dict]:
    """
    Calculate sizes for all series (kept for backwards compatibility)
    
    Returns:
        Tuple of (series_list, summary_stats)
    """
    return calculate_series_sizes_enhanced(sonarr)

def print_series_report(series_list: List[SonarrSeries], summary: Dict, 
                       show_all: bool = False, min_size_gb: float = 0):
    """Print a formatted report of series sizes"""
    
    print("\n" + "="*80)
    print("SONARR LIBRARY SIZE REPORT")
    print("="*80)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if 'method' in summary:
        print(f"Method: {summary['method']}")
    print()
    
    # Summary statistics
    print("SUMMARY:")
    print(f"  Total Series: {summary['total_series']}")
    print(f"  Monitored Series: {summary['monitored_series']}")
    print(f"  Unmonitored Series: {summary.get('unmonitored_series', 0)}")
    print(f"  Total Episodes: {summary['total_episodes']}")
    print(f"  Total Size: {summary['total_size_gb']} GB ({summary.get('total_size_tb', 0)} TB)")
    print(f"  Monitored Size: {summary['monitored_size_gb']} GB")
    print(f"  Unmonitored Size: {summary.get('unmonitored_size_gb', 0)} GB")
    print(f"  Average Episode Size: {summary.get('average_episode_size_mb', 0)} MB")
    print(f"  Average Series Size: {summary.get('average_series_size_gb', 0)} GB")
    print()
    
    # Filter and sort series
    if not show_all:
        series_list = [s for s in series_list if s.monitored]
        print("MONITORED SERIES (sorted by size):")
    else:
        print("ALL SERIES (sorted by size):")
    
    # Filter by minimum size
    series_list = [s for s in series_list if s.size_gb >= min_size_gb]
    series_list.sort(key=lambda x: x.size_bytes, reverse=True)
    
    print("-" * 100)
    print(f"{'Title':<45} {'Status':<8} {'Size (GB)':<10} {'Episodes':<10} {'Seasons':<8} {'Avg MB/Ep':<10}")
    print("-" * 100)
    
    for series in series_list:
        status = "📺" if series.monitored else "⏸️ "
        avg_mb_per_ep = round(series.size_mb / series.episode_count, 1) if series.episode_count > 0 else 0
        print(f"{series.title[:43]:<45} {status:<8} {series.size_gb:<10} "
              f"{series.episode_count:<10} {series.season_count:<8} {avg_mb_per_ep:<10}")
    
    if min_size_gb > 0:
        print(f"\n(Filtered: showing series >= {min_size_gb} GB)")
    
    print(f"\nShowing {len(series_list)} series")

def save_to_json(series_list: List[SonarrSeries], summary: Dict, filename: str):
    """Save results to JSON file"""
    data = {
        'summary': summary,
        'generated': datetime.now().isoformat(),
        'series': [
            {
                'id': s.id,
                'title': s.title,
                'monitored': s.monitored,
                'season_count': s.season_count,
                'episode_count': s.episode_count,
                'size_bytes': s.size_bytes,
                'size_gb': s.size_gb,
                'path': s.path,
                'status': s.status
            } for s in series_list
        ]
    }
    
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"\nData saved to {filename}")

def load_config() -> Tuple[str, str]:
    """
    Load configuration from .env file
    
    Returns:
        Tuple of (sonarr_url, sonarr_api_key)
    """
    # Load environment variables from .env file
    load_dotenv()
    
    sonarr_url = os.getenv('SONARR_URL')
    sonarr_api_key = os.getenv('SONARR_API_KEY')
    
    if not sonarr_url or not sonarr_api_key:
        print("❌ Missing required environment variables!")
        print("Please create a .env file with:")
        print("SONARR_URL=http://your-sonarr-server:8989")
        print("SONARR_API_KEY=your_api_key_here")
        exit(1)
    
    return sonarr_url, sonarr_api_key

def main():
    parser = argparse.ArgumentParser(description='Calculate Sonarr series sizes')
    parser.add_argument('--url', 
                       help='Sonarr base URL (overrides .env file)')
    parser.add_argument('--api-key',
                       help='Sonarr API key (overrides .env file)')
    parser.add_argument('--all', action='store_true',
                       help='Show all series (not just monitored)')
    parser.add_argument('--min-size', type=float, default=0,
                       help='Minimum size in GB to display')
    parser.add_argument('--json', type=str,
                       help='Save results to JSON file')
    parser.add_argument('--test', action='store_true',
                       help='Test connection only')
    parser.add_argument('--detailed', type=int,
                       help='Show detailed breakdown for specific series ID')
    parser.add_argument('--fast', action='store_true',
                       help='Use fast method with built-in Sonarr statistics (less accurate but faster)')
    parser.add_argument('--optimized', action='store_true',
                       help='Use optimized method (default for better performance)')
    
    args = parser.parse_args()
    
    # Load configuration from .env file or command line arguments
    if args.url and args.api_key:
        sonarr_url, sonarr_api_key = args.url, args.api_key
        print("Using configuration from command line arguments")
    else:
        sonarr_url, sonarr_api_key = load_config()
        print("Using configuration from .env file")
        
        # Allow command line to override individual values
        if args.url:
            sonarr_url = args.url
            print(f"Overriding URL with command line argument: {sonarr_url}")
        if args.api_key:
            sonarr_api_key = args.api_key
            print("Overriding API key with command line argument")
    
    # Initialize API client
    sonarr = SonarrAPI(sonarr_url, sonarr_api_key)
    
    # Test connection
    print(f"Testing connection to {sonarr_url}...")
    if not sonarr.test_connection():
        print("❌ Connection failed! Check URL and API key.")
        return 1
    
    print("✅ Connection successful!")
    
    if args.test:
        return 0
    
    # Show detailed info for specific series
    if args.detailed:
        detailed_info = get_detailed_series_info(sonarr, args.detailed)
        if detailed_info:
            print(f"\n{'='*60}")
            print(f"DETAILED SERIES BREAKDOWN - ID: {args.detailed}")
            print(f"{'='*60}")
            print(f"Total Size: {detailed_info['total_size_gb']} GB")
            print(f"Episode Count: {detailed_info['episode_count']}")
            print()
            print("Quality Breakdown:")
            for quality, info in detailed_info['quality_breakdown'].items():
                avg_size = round(info['total_size'] / info['count'] / (1024**2), 1)
                total_gb = round(info['total_size'] / (1024**3), 2)
                print(f"  {quality}: {info['count']} files, {total_gb} GB (avg: {avg_size} MB/file)")
        else:
            print(f"❌ Series ID {args.detailed} not found or has no files")
        return 0
    
    # Get series data using selected method
    try:
        if args.fast:
            print("Using fast method (built-in Sonarr statistics)...")
            series_list, summary = calculate_series_sizes_fast(sonarr)
        elif args.optimized:
            print("Using optimized method...")
            series_list, summary = calculate_series_sizes_optimized(sonarr)
        else:
            # Default to optimized method for better performance
            print("Using optimized method (default)...")
            series_list, summary = calculate_series_sizes_optimized(sonarr)
        
        # Print report
        print_series_report(series_list, summary, args.all, args.min_size)
        
        # Save to JSON if requested
        if args.json:
            save_to_json(series_list, summary, args.json)
            
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0

if __name__ == '__main__':
    exit(main())

# Example usage:
"""
# Requirements installation:
pip install requests python-dotenv

# Create .env file in the same directory:
SONARR_URL=http://192.168.1.100:8989
SONARR_API_KEY=your_actual_api_key_here

# Basic usage (uses optimized method by default)
python sonarr_sizes.py

# Use fast method with built-in Sonarr statistics (faster but less accurate)
python sonarr_sizes.py --fast

# Use original method (slower but most accurate)
python sonarr_sizes.py --optimized

# Show all series (not just monitored)
python sonarr_sizes.py --all

# Filter series larger than 10GB
python sonarr_sizes.py --min-size 10

# Save results to JSON
python sonarr_sizes.py --json results.json

# Test connection only
python sonarr_sizes.py --test

# Show detailed breakdown for a specific series (use series ID)
python sonarr_sizes.py --detailed 123

# Override .env values with command line (useful for multiple servers)
python sonarr_sizes.py --url http://other-server:8989 --api-key other_key

# Override just the URL (keeping API key from .env)
python sonarr_sizes.py --url http://other-server:8989

# Combine options - fast method, all series, minimum 5GB, save to JSON
python sonarr_sizes.py --fast --all --min-size 5 --json fast_results.json
"""