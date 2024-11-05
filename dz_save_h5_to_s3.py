import os
import time
import boto3
from dotenv import load_dotenv
from dzsave_h5 import dzsave_h5
from tqdm import tqdm

# Load environment variables from .env file
load_dotenv()

# Paths and parameters for DZI creation
slide_path = "/media/hdd3/neo/BMA_AML/H23-9432;S14;MSK1 - 2023-12-12 04.55.10.ndpi"
tmp_save_path = "/media/hdd3/neo/S3_tmp_dir/bma_test_slide.h5"
s3_bucket_name = os.getenv("S3_BUCKET_NAME")
s3_subfolder = "wsi-and-heatmaps"

# Generate DZI files
dzsave_h5(
    slide_path,
    tmp_save_path,
    tile_size=512,
    num_cpus=32,
    region_cropping_batch_size=256,
)

# Initialize S3 client using credentials from environment variables
s3 = boto3.client(
    "s3",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_REGION"),
)


# Function to upload file to S3
def upload_file_to_s3(local_path, s3_bucket, s3_key):
    s3.upload_file(local_path, s3_bucket, s3_key)
    print(f"Uploaded {local_path} to s3://{s3_bucket}/{s3_key}")


# Upload the .h5 file to S3 under the specified subfolder
h5_s3_key = f"{s3_subfolder}/{os.path.basename(tmp_save_path)}"
upload_file_to_s3(tmp_save_path, s3_bucket_name, h5_s3_key)

print("H5 file uploaded successfully.")
