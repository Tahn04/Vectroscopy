import geopandas as gpd
import numpy as np
import pandas as pd
from tqdm import tqdm
from affine import Affine
from rasterio.features import shapes
from shapely.geometry import shape

def list_vectorize(raster_list, thresholds, crs, transform):
    """
    Vectorizes a list of rasters using corresponding threshold values.

    Parameters:
    - raster_list (list of np.ndarray): List of binary rasters.
    - thresholds (list of float or int): Threshold values associated with each raster.
    - crs: Coordinate Reference System (e.g., from rasterio).
    - transform: Affine transform (e.g., from rasterio).

    Returns:
    - List of GeoDataFrames
    """
    gdf = gpd.GeoDataFrame()
    for raster, threshold in tqdm(zip(raster_list, thresholds), desc="Vectorizing", total=len(raster_list)):
        gdf = pd.concat([gdf, vectorize_raster(raster, transform=transform, crs=crs, threshold=threshold)], ignore_index=True)
    # if simplify_tol:
    #     gdf = safe_simplify_coverage(gdf, simplify_tol)
    return gdf

def vectorize_raster(raster, crs=None, transform=None, threshold=None):
    """
    Convert a binary raster (numpy array or xarray.DataArray) to a GeoDataFrame with geometries.
    """
    import sys
    if hasattr(raster, "values"):
        raster = raster.astype("uint8")
        arr = raster.values
    else:
        arr = raster.astype("uint8")
    print(sys.getsizeof(arr), "bytes in raster array")
    # arr = arr.astype("uint8")
    # Ensure transform is an Affine object
    if transform is not None and not isinstance(transform, Affine):
        transform = Affine(transform[1], transform[2], transform[0],
                         transform[4], transform[5], transform[3])
    elif transform is None:
        raise ValueError("Transform must be provided.")

    results = shapes(arr, mask=arr, transform=transform)

    del arr, raster

    geoms = []
    vals = []
    for geom, val in results:
        if val != 0:
            poly = shape(geom)
            # if simplify_tol:
            #     poly = poly.simplify(simplify_tol, preserve_topology=True)
            geoms.append(poly)
            # vals.append(val)
    gdf = gpd.GeoDataFrame(         
        {
            # "value": vals, 
            "Threshold": threshold, 
            "geometry": geoms},
        crs=crs
    )
    # if simplify_tol:
    #     # gdf.geometry = gdf.geometry.simplify(simplify_tol, preserve_topology=True)
    #     gdf.geometry = gdf.geometry.simplify_coverage(simplify_tol)
    return gdf

def safe_simplify_coverage(gdf, simplify_tol):
    """Safely simplify geometries with validation"""
    if simplify_tol <= 0:
        return gdf
    
    original_count = len(gdf)
    
    # Apply simplification
    gdf.geometry = gdf.geometry.simplify_coverage(simplify_tol)
    # gdf.geometry = gdf.geometry.simplify(simplify_tol, preserve_topology=False)
    
    # Validate geometries
    invalid_mask = ~gdf.geometry.is_valid
    if invalid_mask.any():
        print(f"Warning: {invalid_mask.sum()} invalid geometries after simplification")
        # Try to fix invalid geometries
        gdf.loc[invalid_mask, 'geometry'] = gdf.loc[invalid_mask, 'geometry'].buffer(0)
        
        # Check again
        still_invalid = ~gdf.geometry.is_valid
        if still_invalid.any():
            print(f"Removing {still_invalid.sum()} unfixable geometries")
            gdf = gdf[gdf.geometry.is_valid].copy()
    
    # Remove empty geometries
    empty_mask = gdf.geometry.is_empty
    if empty_mask.any():
        print(f"Removing {empty_mask.sum()} empty geometries")
        gdf = gdf[~empty_mask].copy()
    
    # Remove zero-area geometries (collapsed to lines/points)
    if len(gdf) > 0:
        area_mask = gdf.geometry.area > 1e-10  # Very small threshold
        if (~area_mask).any():
            print(f"Removing {(~area_mask).sum()} zero-area geometries")
            gdf = gdf[area_mask].copy()
    
    print(f"Simplification: {original_count} → {len(gdf)} geometries")
    return gdf