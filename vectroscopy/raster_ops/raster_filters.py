from affine import Affine
import numpy as np
import bottleneck as bn
import numpy as np
from tqdm import tqdm
from scipy.ndimage import iterate_structure
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
import geopandas as gpd
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view
import dask.array as da
from skimage.morphology import dilation, erosion, footprint_rectangle
from scipy.ndimage import convolve
# from osgeo import gdal
import rasterio as rio
from scipy.ndimage import binary_opening
from skimage.morphology import square
from scipy import ndimage
import xarray as xr
from rasterio.features import sieve

"""Median Filter"""
def dask_nanmedian_filter(data, window_size=3, iterations=1):
    """
    Apply nanmedian filter to either numpy array or Xarray DataArray.
    Returns lazy Dask-backed DataArray if input is Xarray, otherwise numpy array.
    """
    # Handle both numpy arrays and Xarray DataArrays
    if isinstance(data, xr.DataArray):
        # Work with the underlying Dask array (or convert to Dask if numpy-backed)
        if data.chunks is None:
            # If not chunked, create chunks
            dask_arr = da.from_array(data.values, chunks=(1024, 1024))
        else:
            # Already chunked
            dask_arr = data.data
        
        # Apply the filter iterations
        for _ in tqdm(range(iterations), desc="Applying Xarray nanmedian filter"):
            dask_arr = dask_arr.map_overlap(
                nanmedian_2d,
                window_size=window_size,
                depth=window_size // 2,
                boundary=np.nan,
                dtype=dask_arr.dtype
            )

        # Return as lazy Xarray DataArray
        return xr.DataArray(
            dask_arr,  # Keep as Dask array (lazy)
            coords=data.coords,
            dims=data.dims,
            attrs=data.attrs
        )
    else:
        # Original behavior for numpy arrays
        # dask_arr = da.from_array(data, chunks=(1024, 1024))
        dask_arr = data

        for _ in tqdm(range(iterations), desc="Applying Dask nanmedian filter"):
            dask_arr = dask_arr.map_overlap(
                nanmedian_2d,
                window_size=window_size,
                depth=window_size // 2,
                boundary=np.nan,
                dtype=data.dtype
            )
        
        return dask_arr.compute()

def nanmedian_2d(x, window_size):
    """Apply 2D nanmedian filter to a NumPy array with given window size."""
    pad = window_size // 2
    padded = np.pad(x, pad, mode='constant', constant_values=np.nan)

    # Create sliding windows
    windows = np.lib.stride_tricks.sliding_window_view(padded, (window_size, window_size))
    windows = windows.reshape(windows.shape[0], windows.shape[1], -1)

    return bn.nanmedian(windows, axis=2)

"""Majority Filter"""
def list_majority_filter(raster_list, iterations=1, size=3):
    return [
        majority_filter_fast(raster, size=size, iterations=iterations)
        #for raster in raster_list
        for raster in tqdm(raster_list, desc="Applying majority filter")
    ]

def majority_filter_fast(binary_array, size=3, iterations=1):
    kernel = np.ones((size, size), dtype=np.uint8)
    array = np.nan_to_num(binary_array, nan=0).astype(np.uint8)
    threshold = (size * size) // 2

    for _ in range(iterations):
        count = convolve(array, kernel, mode='mirror')
        array = (count > threshold).astype(np.uint8)

    return array

def dask_list_majority_filter(raster_list, iterations=1, size=3, chunk_size=(1024, 1024), dask=True):
    """Apply majority filter to a list of rasters using Dask for parallelization."""
    return [
        dask_majority_filter(raster, size=size, iterations=iterations, chunk_size=chunk_size, dask=dask)
        for raster in tqdm(raster_list, desc="Applying Dask majority filter")
    ]

def dask_majority_filter(binary_array, size=3, iterations=1, chunk_size=(1024, 1024), dask=True):
    """Apply majority filter using Dask for memory efficiency and potential speed gains."""
    # Convert to dask array
    dask_arr = da.from_array(binary_array, chunks=chunk_size)
    
    # Apply majority filter iterations
    for _ in range(iterations):
        dask_arr = dask_arr.map_overlap(
            majority_filter_kernel,
            size=size,
            depth=size // 2,
            boundary='reflect',
            dtype=np.uint8
        )
    if dask:
        return dask_arr
    else:
        return dask_arr.compute()

def majority_filter_kernel(x, size):
    """Apply majority filter kernel to a chunk."""
    kernel = np.ones((size, size), dtype=np.uint8)
    array = np.nan_to_num(x, nan=0).astype(np.uint8)
    threshold = (size * size) // 2
    
    count = convolve(array, kernel, mode='mirror')
    return (count > threshold).astype(np.uint8)


"""Boundary Clean Filter"""
# def list_boundary_clean(raster_list, iterations=1, radius=1):
#     return [
#         boundary_clean(raster, iterations=iterations, radius=radius)
#         #for raster in raster_list
#         for raster in tqdm(raster_list, desc="Boundary cleaning")
#     ]

# def boundary_clean(raster_array, iterations=2, radius=3):
#     """
#     Smooth binary raster boundaries similar to ArcGIS Boundary Clean tool.
    
#     Parameters:
#     - raster_array (np.ndarray): Binary array (1 = feature, 0 = background)
#     - iterations (int): How many expand-shrink cycles to perform
#     - radius (int): Structuring element size (larger = more aggressive smoothing)
    
#     Returns:
#     - np.ndarray: Smoothed binary raster
#     """
#     result = np.copy(raster_array).astype(np.uint8)
#     selem = footprint_rectangle((radius, radius))
    
#     for _ in range(iterations):
#         expanded = dilation(result, selem)
#         result = erosion(expanded, selem)

#     return result
def boundary_clean(raster_array, iterations=2, radius=3):
    """
    Smooth binary raster boundaries similar to ArcGIS Boundary Clean tool.
    """
    result = np.copy(raster_array).astype(np.uint8)
    selem = footprint_rectangle((radius, radius))
    for _ in range(iterations):
        result = erosion(dilation(result, selem), selem)
    return result

def dask_boundary_clean(array, iterations=2, radius=3):
    """
    Dask-compatible version of boundary_clean using map_overlap.
    """
    depth = radius  # symmetric depth for erosion/dilation

    def _clean_block(block):
        return boundary_clean(block, iterations=iterations, radius=radius)

    return array.map_overlap(
        _clean_block,
        depth=depth,
        boundary='reflect',
        dtype=np.uint8
    )

def list_boundary_clean(raster_list, iterations=2, radius=3, chunk_size=(1024, 1024), dask=True):
    """
    Apply boundary clean to a list of rasters. Optionally use Dask.
    
    Parameters:
    - raster_list: list of np.ndarray or existing dask arrays
    - iterations: how many expand-shrink cycles
    - radius: size of smoothing window
    - chunk_size: if converting np.ndarray to Dask
    - use_dask: return dask arrays (True) or compute results (False)
    
    Returns:
    - list of Dask or NumPy arrays
    """
    results = []

    for raster in tqdm(raster_list, desc="Boundary cleaning"):
        if isinstance(raster, da.Array):
            dask_arr = raster
        else:
            dask_arr = da.from_array(raster, chunks=chunk_size)

        cleaned = dask_boundary_clean(dask_arr, iterations=iterations, radius=radius)

        if dask:
            results.append(cleaned)
        else:
            results.append(cleaned.compute())

    return results

"""Sieve Filter"""
def dask_sieve_filter_optimized(array_list, iterations=1, threshold=9, connectedness=4, 
                               chunk_size=(1024, 1024), batch_compute=True):
    """
    Optimized version that can compute arrays in batches to control memory usage.
    
    Additional Parameters:
    - batch_compute: If False and dask=False, compute arrays one at a time to save memory
    """
    
    def sieve_kernel_optimized(chunk, threshold, connectedness, iterations):
        """Optimized sieve kernel with better memory handling."""
        # Handle edge case of empty or uniform chunks
        if chunk.size == 0:
            return chunk
        
        # Quick check if chunk is uniform (all same value)
        if len(np.unique(chunk)) <= 1:
            return chunk.astype(np.uint8)
        
        # Convert to uint8 and handle NaN values
        chunk_uint8 = np.nan_to_num(chunk, nan=0).astype("uint8")
        
        # Apply sieve filter iterations
        filtered = chunk_uint8
        for iteration in range(iterations):
            try:
                filtered = sieve(
                    source=filtered,
                    size=threshold,
                    connectivity=connectedness
                )
            except Exception as e:
                # If sieve fails, return original chunk
                print(f"Sieve filter failed on iteration {iteration + 1} with error: {e}")
                return chunk_uint8
        
        return filtered
    
    # Validate inputs (same as before)
    if threshold < 1:
        print("Threshold must be >= 1")
        threshold = 9
    if connectedness not in [4, 8]:
        print("Connectedness must be 4 or 8")
        connectedness = 4
    if iterations < 1:
        return array_list  # No filtering needed
    
    # Calculate overlap - be more conservative for sieve operations
    depth = max(threshold, 20)  # Ensure sufficient overlap
    
    filtered_arrays = []
    
    # Process arrays
    for i, array in enumerate(tqdm(array_list, desc="Processing arrays with Dask sieve filter")):
        # Convert to dask array
        if isinstance(array, da.Array):
            dask_arr = array.rechunk(chunk_size)
        else:
            dask_arr = da.from_array(array, chunks=chunk_size)
        
        # Apply optimized sieve filter
        filtered_dask = dask_arr.map_overlap(
            sieve_kernel_optimized,
            threshold=threshold,
            connectedness=connectedness,
            iterations=iterations,
            depth=depth,
            boundary='reflect',
            dtype=np.uint8,
            meta=np.array([], dtype=np.uint8)  # Provide metadata for better performance
        )
        filtered_arrays.append(filtered_dask)
    
    return filtered_arrays

def list_sieve_filter_rio(array_list, iterations=1, threshold=9, connectedness=4):
    """
    Apply sieve filter to a list of arrays using rasterio.
    
    Parameters:
    - array_list: List of 2D numpy arrays to filter
    - crs: Coordinate reference system (not used by rasterio sieve but kept for compatibility)
    - transform: Affine transform (not used by rasterio sieve but kept for compatibility) 
    - iterations: Number of sieve iterations to apply
    - threshold: Minimum number of connected pixels to keep
    - connectedness: Pixel connectivity (4 or 8)
    
    Returns:
    - List of filtered arrays
    """
    filtered_array = []

    for array in tqdm(array_list, desc="Applying Sieve Filter"):
        # Convert to uint8 and handle NaN values
        array_uint8 = np.nan_to_num(array, nan=0).astype("uint8")
        
        # Apply sieve filter for specified iterations
        filtered = array_uint8.copy()
        for _ in range(iterations):
            filtered = sieve(
                source=filtered,
                size=threshold,
                connectivity=connectedness
            )
            filtered_array.append(filtered)

    return filtered_array

"""Binary Opening"""
def list_binary_opening(raster_list, iterations=1, size=3, chunk_size=(1024, 1024), dask=True):
    """
    Apply binary opening to a list of rasters using Dask for optional parallel processing.

    Args:
        raster_list (list of np.ndarray): List of binary raster arrays.
        iterations (int): Number of opening iterations.
        size (int): Size of the structuring element (square).
        chunk_size (tuple): Chunk size for Dask arrays.
        dask (bool): If True, return Dask arrays; if False, compute and return NumPy arrays.

    Returns:
        list: List of processed rasters (Dask or NumPy arrays).
    """
    if dask:
        return [
            dask_binary_opening(raster, iterations=iterations, size=size, chunk_size=chunk_size)
            for raster in tqdm(raster_list, desc="Applying Dask binary opening")
        ]
    else:
        return [
            _binary_opening(raster, iterations=iterations, size=size)
            for raster in tqdm(raster_list, desc="Applying Dask binary opening")
        ]


def dask_binary_opening(raster, iterations=1, size=3, chunk_size=(1024, 1024)):
    """
    Apply binary opening to a single raster using Dask for memory efficiency.

    Args:
        raster (np.ndarray): Binary raster (0/1 values).
        iterations (int): Number of morphological opening iterations.
        size (int): Structuring element size.
        chunk_size (tuple): Chunk size for Dask processing.
        dask (bool): Whether to return a Dask array or compute to NumPy.

    Returns:
        dask.array.Array or np.ndarray: Result after binary opening.
    """
    if not isinstance(raster, (np.ndarray, da.Array)):
        raise ValueError("Input raster must be a NumPy or Dask array.")

    # Convert to Dask array if needed
    dask_arr = da.from_array(raster, chunks=chunk_size) if isinstance(raster, np.ndarray) else raster

    # Structuring element depth
    depth = size // 2

    # Apply opening using map_overlap
    for _ in range(iterations):
        dask_arr = dask_arr.map_overlap(
            _binary_opening_kernel,
            size=size,
            depth=depth,
            boundary='reflect',
            dtype=np.uint8
        )

    return dask_arr


def _binary_opening_kernel(block, size):
    """Kernel for applying binary opening to a single chunk."""
    structure = footprint_rectangle((size, size))
    return binary_opening(block, structure=structure).astype(np.uint8)


def footprint_rectangle(shape):
    """Generate a rectangular structuring element."""
    return np.ones(shape, dtype=bool)

def _binary_opening(raster, iterations, size):
    """
    Apply binary opening to a single raster.
    
    Args:
        raster (np.ndarray): Input binary raster.
        structure (np.ndarray): Structuring element for the opening operation.
        
    Returns:
        np.ndarray: Raster after applying binary opening.
    """
    if not isinstance(raster, np.ndarray):
        raise ValueError("Input raster must be a NumPy array.")
    
    structure=footprint_rectangle((size, size))
    
    return binary_opening(raster, structure=structure, iterations=iterations)