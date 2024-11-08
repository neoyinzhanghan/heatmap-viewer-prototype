import os
import subprocess
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def mount_s3_bucket():
    # Load variables from .env
    bucket_name = os.getenv("S3_BUCKET_NAME")
    mount_point = (
        "/home/ubuntu/cp-lab-wsi-upload"  # Change this to your desired mount point path
    )
    aws_region = os.getenv("AWS_REGION")

    if not all([bucket_name, mount_point, aws_region]):
        print("Missing required environment variables.")
        return

    # Ensure the mount point directory exists
    os.makedirs(mount_point, exist_ok=True)

    # Mount the S3 bucket using s3fs
    try:
        cmd = [
            "s3fs",
            bucket_name,
            mount_point,
            "-o",
            f"endpoint={aws_region}",
            "-o",
            "allow_other",
            "-o",
            "use_path_request_style",
            "-o",
            "dbglevel=info",
            "-o",
            "curldbg",
        ]

        subprocess.run(cmd, check=True)
        print(f"S3 bucket '{bucket_name}' mounted at '{mount_point}'")
    except subprocess.CalledProcessError as e:
        print(f"Error mounting S3 bucket: {e}")


if __name__ == "__main__":
    mount_s3_bucket()
