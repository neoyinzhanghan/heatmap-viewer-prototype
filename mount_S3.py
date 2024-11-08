import os
import subprocess
import sys

def is_mounted(mount_point):
    """Check if a directory is already mounted."""
    result = subprocess.run(['mountpoint', '-q', mount_point], capture_output=True)
    return result.returncode == 0

def mount_s3(bucket_name, mount_point, cache_dir="/tmp", credentials_file="/home/ubuntu/.aws/credentials"):
    """Mount an S3 bucket using s3fs if it's not already mounted."""
    if is_mounted(mount_point):
        print(f"{mount_point} is already mounted.")
        return

    # Ensure the mount directory exists
    os.makedirs(mount_point, exist_ok=True)

    # Construct the s3fs mount command
    cmd = [
        "/usr/bin/s3fs", bucket_name, mount_point,
        "-o", f"use_cache={cache_dir}",
        "-o", f"passwd_file={credentials_file}",
        "-o", "allow_other",
        "-o", "umask=0000"
    ]

    # Run the mount command
    try:
        print(f"Mounting {bucket_name} to {mount_point}...")
        subprocess.run(cmd, check=True)
        print(f"Mounted {bucket_name} to {mount_point}")
    except subprocess.CalledProcessError as e:
        print(f"Failed to mount {bucket_name} to {mount_point}: {e}")
        sys.exit(1)

if __name__ == "__main__":
    BUCKET_NAME = "cp-lab-wsi-upload"
    MOUNT_POINT = "/home/ubuntu/cp-lab-wsi-upload"

    mount_s3(BUCKET_NAME, MOUNT_POINT)
