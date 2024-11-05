import os
import time
import boto3
from dotenv import load_dotenv
from dzsave import dzsave
from tqdm import tqdm

# Load environment variables from .env file
load_dotenv()

# Paths and parameters for DZI creation
slide_path = "/media/hdd3/neo/BMA_AML/H23-9432;S14;MSK1 - 2023-12-12 04.55.10.ndpi"
tmp_save_dir = "/media/hdd3/neo/S3_tmp_dir"
folder_name = "bma_test_slide"
s3_bucket_name = os.getenv("S3_BUCKET_NAME")
s3_subfolder = "wsi-and-heatmaps"

# Generate DZI files
dzsave(
    slide_path,
    tmp_save_dir,
    folder_name,
    tile_size=512,
    num_cpus=32,
    region_cropping_batch_size=256,
)

# Set up paths for DZI and tiles folder
dzi_file_path = os.path.join(tmp_save_dir, f"{folder_name}.dzi")
tiles_folder_path = os.path.join(tmp_save_dir, f"{folder_name}_files")

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


# Upload the .dzi file
dzi_s3_key = f"{s3_subfolder}/{folder_name}.dzi"
upload_file_to_s3(dzi_file_path, s3_bucket_name, dzi_s3_key)

# Upload all files in the tiles folder
for root, _, files in os.walk(tiles_folder_path):
    for file in files:
        local_file_path = os.path.join(root, file)
        relative_path = os.path.relpath(local_file_path, tmp_save_dir)
        s3_key = f"{s3_subfolder}/{relative_path.replace('\\', '/')}"
        upload_file_to_s3(local_file_path, s3_bucket_name, s3_key)

print("All files uploaded successfully.")
import os
import boto3
from dotenv import load_dotenv
from dzsave import dzsave

# Load environment variables from .env file
load_dotenv()

# Paths and parameters for DZI creation
slide_path = "/media/hdd3/neo/BMA_AML/H23-9432;S14;MSK1 - 2023-12-12 04.55.10.ndpi"
tmp_save_dir = "/media/hdd3/neo/S3_tmp_dir"
folder_name = "bma_test_slide"
s3_bucket_name = os.getenv("S3_BUCKET_NAME")
s3_subfolder = "wsi-and-heatmaps"

# Generate DZI files
dzsave(
    slide_path,
    tmp_save_dir,
    folder_name,
    tile_size=512,
    num_cpus=32,
    region_cropping_batch_size=256,
)

# Set up paths for DZI and tiles folder
dzi_file_path = os.path.join(tmp_save_dir, f"{folder_name}.dzi")
tiles_folder_path = os.path.join(tmp_save_dir, f"{folder_name}_files")

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


startime = time.time()

# Upload the .dzi file
dzi_s3_key = f"{s3_subfolder}/{folder_name}.dzi"
upload_file_to_s3(dzi_file_path, s3_bucket_name, dzi_s3_key)

# Upload all files in the tiles folder
for root, _, files in tqdm(
    os.walk(tiles_folder_path), desc="Uploading DZI Tiles Files"
):
    for file in files:
        local_file_path = os.path.join(root, file)
        relative_path = os.path.relpath(local_file_path, tmp_save_dir)
        s3_key = f"{s3_subfolder}/{relative_path.replace('\\', '/')}"
        upload_file_to_s3(local_file_path, s3_bucket_name, s3_key)

print("All files uploaded successfully.")

time_taken = time.time() - startime

print(f"Time taken: {time_taken} seconds")
