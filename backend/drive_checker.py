#!/usr/bin/env python3

import shutil
import os
import sys

def load_env_file(env_file_path='.env'):
    """Load environment variables from a .env file"""
    env_vars = {}
    
    if not os.path.exists(env_file_path):
        return env_vars
    
    try:
        with open(env_file_path, 'r') as f:
            for line in f:
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                
                # Parse key=value pairs
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")  # Remove quotes
                    env_vars[key] = value
    
    except Exception as e:
        print(f"Error reading .env file: {e}")
        return {}
    
    return env_vars

def parse_mount_points_from_env(env_vars):
    """Parse mount points from environment variables"""
    mount_points = []
    
    # Look for MOUNT_POINTS variable (comma-separated list)
    if 'MOUNT_POINTS' in env_vars:
        points = env_vars['MOUNT_POINTS'].split(',')
        mount_points.extend([point.strip() for point in points if point.strip()])
    
    # Look for individual MOUNT_POINT_X variables
    for key, value in env_vars.items():
        if key.startswith('MOUNT_POINT_') and value.strip():
            mount_points.append(value.strip())
    
    return mount_points

def bytes_to_human_readable(bytes_value):
    """Convert bytes to human readable format (KB, MB, GB, TB)"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.2f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.2f} PB"

def get_drive_usage(path):
    """Get disk usage statistics for a given path"""
    try:
        usage = shutil.disk_usage(path)
        return {
            'total': usage.total,
            'used': usage.total - usage.free,
            'available': usage.free,
            'total_human': bytes_to_human_readable(usage.total),
            'used_human': bytes_to_human_readable(usage.total - usage.free),
            'available_human': bytes_to_human_readable(usage.free),
            'usage_percent': ((usage.total - usage.free) / usage.total) * 100
        }
    except (OSError, FileNotFoundError) as e:
        return None

def get_mounted_drives():
    """Get list of mounted drives from /proc/mounts"""
    mounted_drives = []
    try:
        with open('/proc/mounts', 'r') as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) >= 2:
                    device = parts[0]
                    mount_point = parts[1]
                    filesystem = parts[2]
                    
                    # Filter out common virtual filesystems
                    if not device.startswith('/dev/') and device not in ['tmpfs', 'devtmpfs']:
                        continue
                    
                    # Skip common virtual mount points
                    virtual_mounts = ['/proc', '/sys', '/dev', '/run', '/tmp']
                    if any(mount_point.startswith(vm) for vm in virtual_mounts):
                        continue
                    
                    mounted_drives.append({
                        'device': device,
                        'mount_point': mount_point,
                        'filesystem': filesystem
                    })
    except FileNotFoundError:
        print("Error: Could not read /proc/mounts")
        return []
    
    return mounted_drives

def create_sample_env_file():
    """Create a sample .env file if one doesn't exist"""
    sample_content = """# Drive Storage Checker Configuration
# Specify mount points to monitor

# Method 1: Comma-separated list
MOUNT_POINTS=/,/home,/var

# Method 2: Individual mount points (these will be added to the list above)
# MOUNT_POINT_1=/
# MOUNT_POINT_2=/home
# MOUNT_POINT_3=/var
# MOUNT_POINT_4=/mnt/external

# Optional: Custom .env file path
# ENV_FILE_PATH=custom_config.env
"""
    
    with open('.env.example', 'w') as f:
        f.write(sample_content)
    
    print("Created .env.example file with sample configuration.")
    print("Copy it to .env and modify as needed:")
    print("cp .env.example .env")

def main():
    """Main function to display drive usage information"""
    
    # Check for custom env file path from command line
    env_file_path = '.env'
    if '--env' in sys.argv:
        try:
            env_index = sys.argv.index('--env')
            if env_index + 1 < len(sys.argv):
                env_file_path = sys.argv[env_index + 1]
        except (ValueError, IndexError):
            print("Error: --env flag requires a file path")
            return
    
    # Load environment variables
    env_vars = load_env_file(env_file_path)
    
    # Parse mount points from env
    env_mount_points = parse_mount_points_from_env(env_vars)
    
    # Check for command line arguments (excluding --env and its value)
    cmd_args = [arg for arg in sys.argv[1:] if arg != '--env' and not arg.endswith('.env')]
    if '--env' in sys.argv:
        # Remove the env file path from args too
        try:
            env_index = sys.argv.index('--env')
            if env_index + 1 < len(sys.argv):
                env_file_arg = sys.argv[env_index + 1]
                cmd_args = [arg for arg in cmd_args if arg != env_file_arg]
        except ValueError:
            pass
    
    # Variables to track totals
    total_drives = 0
    total_space = 0
    total_used = 0
    total_available = 0
    successful_checks = []
    
    # Determine which paths to check
    if cmd_args:
        # Command line arguments take precedence
        paths = cmd_args
        print(f"Checking paths from command line arguments:")
    elif env_mount_points:
        # Use paths from .env file
        paths = env_mount_points
        print(f"Checking mount points from {env_file_path}:")
    else:
        # No specific paths provided, show all mounted drives
        if not os.path.exists('.env'):
            print("No .env file found and no command line arguments provided.")
            create_sample_env_file()
            print("\nShowing all mounted drives:")
        
        print("Mounted Drive Storage Information")
        print("=" * 80)
        
        mounted_drives = get_mounted_drives()
        
        if not mounted_drives:
            print("No mounted drives found or error reading mount information.")
            return
        
        for drive in mounted_drives:
            usage = get_drive_usage(drive['mount_point'])
            
            if usage:
                total_drives += 1
                total_space += usage['total']
                total_used += usage['used']
                total_available += usage['available']
                successful_checks.append(drive['mount_point'])
                
                print(f"\nDevice: {drive['device']}")
                print(f"Mount Point: {drive['mount_point']}")
                print(f"Filesystem: {drive['filesystem']}")
                print(f"Total:     {usage['total_human']} ({usage['total']:,} bytes)")
                print(f"Used:      {usage['used_human']} ({usage['used']:,} bytes)")
                print(f"Available: {usage['available_human']} ({usage['available']:,} bytes)")
                print(f"Usage:     {usage['usage_percent']:.1f}%")
                print("-" * 60)
            else:
                print(f"Could not get usage information for {drive['mount_point']}")
        
        # Print totals for all mounted drives
        if total_drives > 0:
            print(f"\n{'='*20} TOTALS FOR ALL MOUNTED DRIVES {'='*20}")
            print(f"Total Drives Checked: {total_drives}")
            print(f"Combined Total Space:     {bytes_to_human_readable(total_space)} ({total_space:,} bytes)")
            print(f"Combined Used Space:      {bytes_to_human_readable(total_used)} ({total_used:,} bytes)")
            print(f"Combined Available Space: {bytes_to_human_readable(total_available)} ({total_available:,} bytes)")
            print(f"Overall Usage:            {(total_used / total_space * 100):.1f}%")
            print("=" * 80)
        return
    
    # Check specified paths
    print("=" * 80)
    
    for path in paths:
        if not os.path.exists(path):
            print(f"Path '{path}' does not exist!")
            continue
            
        usage = get_drive_usage(path)
        if usage:
            total_drives += 1
            total_space += usage['total']
            total_used += usage['used']
            total_available += usage['available']
            successful_checks.append(path)
            
            print(f"\nPath: {path}")
            print(f"Total:     {usage['total_human']} ({usage['total']:,} bytes)")
            print(f"Used:      {usage['used_human']} ({usage['used']:,} bytes)")
            print(f"Available: {usage['available_human']} ({usage['available']:,} bytes)")
            print(f"Usage:     {usage['usage_percent']:.1f}%")
            print("-" * 60)
        else:
            print(f"Could not get usage information for '{path}'")
    
    # Print totals for specified paths
    if total_drives > 0:
        print(f"\n{'='*25} TOTALS SUMMARY {'='*25}")
        print(f"Drives/Paths Checked: {total_drives}")
        if len(successful_checks) > 1:
            print(f"Paths: {', '.join(successful_checks)}")
        print(f"Combined Total Space:     {bytes_to_human_readable(total_space)} ({total_space:,} bytes)")
        print(f"Combined Used Space:      {bytes_to_human_readable(total_used)} ({total_used:,} bytes)")
        print(f"Combined Available Space: {bytes_to_human_readable(total_available)} ({total_available:,} bytes)")
        print(f"Overall Usage:            {(total_used / total_space * 100):.1f}%")
        print("=" * 80)

if __name__ == "__main__":
    main()