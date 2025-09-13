#!/usr/bin/env python3

import os
import subprocess
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mount.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

class CIFSMounter:
    def __init__(self, env_file='.env'):
        """Initialize the CIFS mounter with environment file."""
        self.env_file = env_file
        self.load_environment()
        
    def load_environment(self):
        """Load environment variables from .env file."""
        if not os.path.exists(self.env_file):
            logging.error(f"Environment file {self.env_file} not found!")
            sys.exit(1)
            
        load_dotenv(self.env_file)
        logging.info(f"Loaded environment from {self.env_file}")
        
    def get_mount_configs(self):
        """Parse environment variables to get mount configurations."""
        configs = []
        
        # Look for numbered mount configurations (MOUNT_1, MOUNT_2, etc.)
        i = 1
        while True:
            share_key = f"MOUNT_{i}_SHARE"
            dest_key = f"MOUNT_{i}_DEST"
            
            share = os.getenv(share_key)
            dest = os.getenv(dest_key)
            
            if not share or not dest:
                break
                
            # Optional per-mount credentials
            username = os.getenv(f"MOUNT_{i}_USERNAME") or os.getenv("DEFAULT_USERNAME")
            password = os.getenv(f"MOUNT_{i}_PASSWORD") or os.getenv("DEFAULT_PASSWORD")
            domain = os.getenv(f"MOUNT_{i}_DOMAIN") or os.getenv("DEFAULT_DOMAIN")
            options = os.getenv(f"MOUNT_{i}_OPTIONS") or os.getenv("DEFAULT_OPTIONS", "")
            
            configs.append({
                'share': share,
                'destination': dest,
                'username': username,
                'password': password,
                'domain': domain,
                'options': options,
                'index': i
            })
            
            i += 1
            
        if not configs:
            logging.error("No mount configurations found in environment file!")
            sys.exit(1)
            
        return configs
    
    def create_mount_point(self, path):
        """Create mount point directory if it doesn't exist."""
        try:
            Path(path).mkdir(parents=True, exist_ok=True)
            logging.info(f"Created/verified mount point: {path}")
            return True
        except Exception as e:
            logging.error(f"Failed to create mount point {path}: {e}")
            return False
    
    def build_mount_command(self, config):
        """Build the mount command from configuration."""
        cmd = ["mount", "-t", "cifs", config['share'], config['destination']]
        
        # Build options string
        options = []
        
        if config['username']:
            options.append(f"username={config['username']}")
        if config['password']:
            options.append(f"password={config['password']}")
        if config['domain']:
            options.append(f"domain={config['domain']}")
            
        # Add default options
        default_opts = ["uid=0", "gid=0", "iocharset=utf8", "file_mode=0777", "dir_mode=0777"]
        options.extend(default_opts)
        
        # Add custom options from env
        if config['options']:
            custom_opts = [opt.strip() for opt in config['options'].split(',') if opt.strip()]
            options.extend(custom_opts)
        
        if options:
            cmd.extend(["-o", ",".join(options)])
            
        return cmd
    
    def mount_share(self, config):
        """Mount a single CIFS share."""
        logging.info(f"Mounting {config['share']} to {config['destination']}")
        
        # Create mount point
        if not self.create_mount_point(config['destination']):
            return False
        
        # Check if already mounted
        if self.is_mounted(config['destination']):
            logging.warning(f"{config['destination']} is already mounted")
            return True
        
        # Build and execute mount command
        cmd = self.build_mount_command(config)
        
        try:
            # Log the command (without password for security)
            safe_cmd = [part if 'password=' not in part else 'password=***' for part in cmd]
            logging.info(f"Executing: {' '.join(safe_cmd)}")
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                logging.info(f"Successfully mounted {config['share']} to {config['destination']}")
                return True
            else:
                logging.error(f"Mount failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logging.error(f"Mount command timed out for {config['share']}")
            return False
        except Exception as e:
            logging.error(f"Error executing mount command: {e}")
            return False
    
    def is_mounted(self, path):
        """Check if a path is already mounted."""
        try:
            result = subprocess.run(['mountpoint', '-q', path], capture_output=True)
            return result.returncode == 0
        except Exception:
            return False
    
    def unmount_share(self, path):
        """Unmount a CIFS share."""
        logging.info(f"Unmounting {path}")
        
        try:
            result = subprocess.run(['umount', path], capture_output=True, text=True)
            if result.returncode == 0:
                logging.info(f"Successfully unmounted {path}")
                return True
            else:
                logging.error(f"Unmount failed: {result.stderr}")
                return False
        except Exception as e:
            logging.error(f"Error unmounting {path}: {e}")
            return False
    
    def show_mount_status(self, configs):
        """Show current mount status."""
        print("\n=== Mount Status ===")
        for config in configs:
            mounted = "✓" if self.is_mounted(config['destination']) else "✗"
            print(f"{mounted} {config['share']} -> {config['destination']}")
        print()
    
    def mount_all(self):
        """Mount all configured shares."""
        configs = self.get_mount_configs()
        logging.info(f"Found {len(configs)} mount configurations")
        
        success_count = 0
        
        for config in configs:
            if self.mount_share(config):
                success_count += 1
            else:
                logging.error(f"Failed to mount share {config['index']}")
        
        logging.info(f"Successfully mounted {success_count}/{len(configs)} shares")
        
        # Show final status
        self.show_mount_status(configs)
        
        return success_count == len(configs)
    
    def unmount_all(self):
        """Unmount all configured shares."""
        configs = self.get_mount_configs()
        
        for config in configs:
            if self.is_mounted(config['destination']):
                self.unmount_share(config['destination'])
    
    def verify_requirements(self):
        """Verify system requirements."""
        # Check if running as root
        if os.geteuid() != 0:
            logging.error("This script must be run as root to mount CIFS shares")
            return False
        
        # Check if cifs-utils is installed
        try:
            subprocess.run(['mount.cifs', '--help'], capture_output=True, timeout=5)
        except (subprocess.TimeoutExpired, FileNotFoundError):
            logging.error("cifs-utils not found. Please install: apt-get install cifs-utils")
            return False
        
        return True

def main():
    """Main function."""
    if len(sys.argv) > 1:
        env_file = sys.argv[1]
    else:
        env_file = '.env'
    
    mounter = CIFSMounter(env_file)
    
    # Verify requirements
    if not mounter.verify_requirements():
        sys.exit(1)
    
    # Handle command line arguments
    if len(sys.argv) > 2:
        command = sys.argv[2]
        if command == 'unmount':
            mounter.unmount_all()
            return
        elif command == 'status':
            configs = mounter.get_mount_configs()
            mounter.show_mount_status(configs)
            return
    
    # Default action: mount all
    success = mounter.mount_all()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
