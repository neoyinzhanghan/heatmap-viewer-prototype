import os
import shutil
from LLRunner.slide_processing.dzsave_h5 import dzsave_h5
from compute_heatmap import create_heatmap_to_h5
from tqdm import tqdm

tmp_save_dir_path = "/media/hdd3/neo/tmp_heatmap_dir"
tmp_heatmap_save_dir_path = "/media/hdd3/neo/tmp_heatmap_dir/heatmaps"
S3_mount_point_path = "/home/greg/Documents/neo/cp-lab-wsi-upload/wsi-and-heatmaps"
S3_mount_point_heatmap_path = (
    "/home/greg/Documents/neo/cp-lab-wsi-upload/wsi-and-heatmaps/heatmaps"
)


def dzsave_h5_with_heatmap(slide_path):
    slide_name = os.path.basename(slide_path)

    # Replace .ndpi in slide_path with .h5
    tmp_save_name = slide_name.replace(".ndpi", ".h5")
    heatmap_h5_save_name = slide_name.replace(".ndpi", "_heatmap.h5")

    tmp_save_path = os.path.join(tmp_save_dir_path, tmp_save_name)
    heatmap_h5_save_path = os.path.join(tmp_heatmap_save_dir_path, heatmap_h5_save_name)

    S3_save_path = os.path.join(S3_mount_point_path, tmp_save_name)
    heatmap_S3_save_path = os.path.join(
        S3_mount_point_heatmap_path, heatmap_h5_save_name
    )

    # Generate DZI files with a spinner
    print("Generating DZI files...")
    dzsave_h5(
        slide_path,
        tmp_save_path,
        tile_size=512,
        num_cpus=32,
        region_cropping_batch_size=256,
    )

    print("Creating heatmap...")
    create_heatmap_to_h5(slide_path, heatmap_h5_save_path)

    print(
        f"H5 file and heatmap created successfully to {tmp_save_path} and {heatmap_h5_save_path}"
    )

    try:
        print("Uploading H5 files to S3...")
        # Move files to the S3 mount point
        shutil.move(tmp_save_path, S3_save_path)
        shutil.move(heatmap_h5_save_path, heatmap_S3_save_path)
    except Exception as e:
        print(
            f"Error uploading H5 files to S3: {e}. Cleaning up files before shutdown to prevent corruption ..."
        )
        # Clean up files if an error occurs to prevent corruption
        if os.path.exists(tmp_save_path):
            os.remove(tmp_save_path)
        if os.path.exists(heatmap_h5_save_path):
            os.remove(heatmap_h5_save_path)
        if os.path.exists(S3_save_path):
            os.remove(S3_save_path)
        if os.path.exists(heatmap_S3_save_path):
            os.remove(heatmap_S3_save_path)
        print("Files cleaned up successfully.")
        raise e


if __name__ == "__main__":
    slide_path = "/media/hdd3/neo/test_slide_3.ndpi"
    dzsave_h5_with_heatmap(slide_path)
