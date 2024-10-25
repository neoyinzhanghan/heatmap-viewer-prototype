import openslide
import numpy as np
from tqdm import tqdm
from dataset import LowMagRegionDataset
from torch.utils.data import DataLoader
from BMARegionClfManager import load_clf_model, predict_batch
from BMAassumptions import region_clf_ckpt_path, high_mag_region_clf_ckpt_path, high_mag_region_clf_threshold


batch_size =256
num_workers = 16

# Custom collate function to handle PIL images and names
def custom_collate_fn(batch):
    # Batch is a list of tuples (PIL image, image_name)
    pil_images, coordinates = zip(*batch)
    return list(pil_images), list(coordinates)

def dyadic_average_downsample_heatmap(float_matrix):
    """
    Downsample the heatmap by averaging the values in 2x2 blocks.
    
    Parameters:
    - float_matrix (np.ndarray): The heatmap as a float numpy array.
    
    Returns:
    - np.ndarray: The downsampled heatmap.
    """
    # Get the dimensions of the input matrix
    height, width = float_matrix.shape

    # remove the last row and column if the height or width is odd
    if height % 2 != 0:
        float_matrix = float_matrix[:-1]
        height -= 1
    if width % 2 != 0:
        float_matrix = float_matrix[:, :-1]
        width -= 1
    
    # Compute the new dimensions after downsampling
    new_height = height // 2
    new_width = width // 2
    
    # Reshape the input matrix to a 4D tensor
    reshaped_matrix = float_matrix.reshape(new_height, 2, new_width, 2)
    
    # Average the values in each 2x2 block
    downsampled_matrix = reshaped_matrix.mean(axis=(1, 3))
    
    return downsampled_matrix

class HeatMapTileMaker:
    """
    === Attributes ===
    - slide_path: the path to the slide image
    - slide: the openslide object of
    - tile_size: the size of the tiles
    - dataset: the dataset object to extract tiles from
    - dataloader: the dataloader object to load the tiles
    - heatmap: the heatmap of the slide stored at the highest resolution, it is a float tensor where heatmap[x, y] is the confidence score of the region at (x, y)
    - model: the classifier model to predict the heatmap

    """
    def __init__(self, slide_path, tile_size=256):
        self.slide_path = slide_path
        self.tile_size = tile_size
        self.slide = openslide.OpenSlide(self.slide_path)
        self.dataset = LowMagRegionDataset(self.slide, self.tile_size)
        self.dataloader = DataLoader(self.dataset, batch_size=batch_size, num_workers=num_workers, collate_fn=custom_collate_fn)
        # Load the model
        self.model = load_clf_model(region_clf_ckpt_path)

        # shape of the heatmap should be slide_width_level_0 // 256, slide_height_level_0 // 256, we start by initializing it to zeros numpy array
        self.heatmap = np.zeros((self.slide.dimensions[0] // 256, self.slide.dimensions[1] // 256))
        self.dz_heatmap_dict = {}

    def compute_heatmap(self):
        # Iterate through the dataset with a DataLoader and progress bar
        for pil_images, coordinates in tqdm(self.dataloader, desc="Processing Batches"):
            # Predict batch of images
            scores = predict_batch(pil_images, self.model)
            
            for i, (x, y) in enumerate(coordinates):
                # Update the heatmap with the confidence score, as a float
                self.heatmap[x, y] = scores[i]

        self.dz_heatmap_dict[self.slide.level_count - 1] = self.heatmap

        current_heatmap = self.heatmap

        for level in range(self.slide.level_count - 2, -1, -1):
            current_heatmap = dyadic_average_downsample_heatmap(current_heatmap)
            self.dz_heatmap_dict[level] = current_heatmap    
        

    def get_heatmap_values(self, level, x, y):
        """
        Get the heatmap values at a specific level and location.

        Parameters:
        - level (int): The level of the heatmap.
        - x (int): The x-coordinate of the location.
        - y (int): The y-coordinate of the location.

        Returns:
        - float: The heatmap value at the specified location.
        """

        try:
            float(self.dz_heatmap_dict[level][x, y]) # if index out of bounds, return 0
        except IndexError:
            return 0