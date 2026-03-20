import geopandas as gpd
import pandas as pd
import rasterio
from exactextract import exact_extract
import time
from .. import file_handler as fh

def list_zonal_stats(polygons, param_list, stats_list, simplification_level):
    """
    Calculate zonal statistics for a list of polygons and parameters.
    
    Parameters:
    - polygons (list): List of polygon geometries.
    - param_list (list): List of parameters for each polygon.
    - crs: Coordinate reference system.
    - transform: Affine transform for the raster.
    
    Returns:
    - list: Zonal statistics for each polygon.
    """
    results = []
    area = False
    results = gpd.GeoDataFrame()
    for param in param_list:
        if "area" in stats_list:
            stats_list.remove("area")
            area = True
        stats_config = config_stats(stats_list, param.name)  # Get the configured stats for the parameter
        temp = zonal_stats(polygons, param, stats_config)

        if results.empty:
            results = temp
        else:
            results = results.join(temp.set_index(results.index), rsuffix=f"_{param.name}")
            if f"geometry_{param.name}" in results.columns:
                results = results.drop(columns=[f"geometry_{param.name}"])
                # results = results.drop(columns=[f"value_{param.name}"])
            if f"Threshold_{param.name}" in results.columns:
                results = results.drop(columns=[f"Threshold_{param.name}"])
    if simplification_level:
        results.geometry = results.geometry.simplify_coverage(simplification_level)
    if area:
        results['AREA_SQK'] = results.geometry.area * 0.000001
    return results

def zonal_stats(gdf, param, stats_config):
    """ Calculate zonal statistics for a raster and vector layers."""
    if len(stats_config) != 0:
        empty_gdf = gpd.GeoDataFrame()
        param_name = param.name
        da = param.preprocessed_path
        processed_raster_path = fh.FileHandler().create_file(f"{param_name}_processed", "tif", temp=True)
        start = time.time()
        da.rio.to_raster(processed_raster_path)
        end = time.time()
        print(f"Raster saved in {end - start:.2f} seconds")
        try:
            with rasterio.open(processed_raster_path) as src:
                temp = exact_extract(
                    src,
                    gdf,
                    stats_config,
                    include_geom=True,
                    include_cols="Threshold",
                    # strategy="raster-sequential",
                    output='pandas',
                    progress=True,
                    max_cells_in_memory=1000000000  # Adjust as needed for large datasets
                )
            # temp = percintile_rename(temp)
            gdf = pd.concat([empty_gdf, temp], ignore_index=True)

            # gdf[f'{param_name}_DIF'] = gdf[f"Threshold"] - gdf[f"{param_name}_MIN"]

            float_cols = gdf.select_dtypes(include=['float']).columns
            gdf[float_cols] = gdf[float_cols].round(5) 
        except Exception as e:
            print(f"Error calculating zonal stats for {param_name}: {e}")
    return gdf

def config_stats(stats_list, param_name):
    """configure statistics for a list of stats to fit exact_extracts specifications."""
    stat_config = []
    stats_map = {
            'mean': f"{param_name}_MEN=mean",
            'median': f"{param_name}_MDN=median",
            'count': f"{param_name}_CNT=count",
            'min': f"{param_name}_MIN=min",
            'max': f"{param_name}_MAX=max",
            'std': f"{param_name}_STD=stdev",
        }
    # stats_map = {
    #         'mean': "MEN=mean",
    #         'median': "MDN=median",
    #         'area': "SQK=count",
    #         'count': "CNT=count",
    #         'min': "MIN=min",
    #         'max': "MAX=max",
    #         'std': "STD=stdev",
    #     }
    for stat in stats_list:
        if isinstance(stat, str) and stat.endswith('p'):
            if len(stat) < 2 or not stat[:-1].isdigit():
                raise ValueError(f"Invalid percentile format: {stat}. Must be a number followed by 'p'.")
            p = float(stat[:-1])
            stat_config.append(f"{param_name}=quantile(q={p/100})")
        elif stat in stats_map:
            stat_config.append(stats_map[stat])
        else:
            raise ValueError(f"Statistic '{stat}' is not supported. Supported statistics are: {list(stats_map.keys())}")
    return stat_config

def percintile_rename(gdf):
    """ Rename percentile columns in a GeoDataFrame."""
    for col in gdf.columns:
        if isinstance(col, str) and col and col[-1].isdigit():
            if not col[-2] == '_':
                number = f"0{col[-1]}"
                gdf = gdf.rename(columns={col: f"{col[:-1]}P{number}"})
            gdf = gdf.rename(columns={col: f"{col}P"})
    return gdf