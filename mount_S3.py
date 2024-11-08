import os
import subprocess
from dotenv import load_dotenv
import boto3
from botocore.exceptions import NoCredentialsError, PartialCredentialsError

# Load environment variables from .env file
load_dotenv()

def mount_s3_bucket():
    # Load environment variables
    bucket_name = os.getenv("BUCKET_NAME")
    mount_point = os.getenv("MOUNT_POINT")
    aws_region = os.getenv("AWS_REGION")
    aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")

    # Ensure required variables are set
    if not all([bucket_name, mount_point, aws_region, aws_access_key, aws_secret_key]):
        print("Missing required environment variables. Check your .env file.")
        return

    try:
        # Ensure the mount point directory exists
        os.makedirs(mount_point, exist_ok=True)

        # Mount the S3 bucket using s3fs
        cmd = [
            "s3fs", bucket_name, mount_point,
            "-o", f"endpoint={aws_region}",
            "-o", f"allow_other",
            "-o", f"passwd_file=/etc/passwd-s3fs"
        ]
        subprocess.run(cmd, check=True)
        print(f"S3 bucket '{bucket_name}' mounted at '{mount_point}'")

    except (NoCredentialsError, PartialCredentialsError):
        print("AWS credentials are incomplete or missing.")
    except subprocess.CalledProcessError as e:
        print(f"Error mounting S3 bucket: {e}")

if __name__ == "__main__":
    mount_s3_bucket()
