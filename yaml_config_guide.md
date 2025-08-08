# YAML Configuration Guide for Raster Processing Library

This guide explains how to create and structure YAML configuration files for passing into Vectroscopy. The configuration file defines parameters, processing pipelines, and output settings for different workflows.

## Basic Structure

```yaml
# Top-level key: Name of your analysis/mineral type
ProcessName:
  path:                    # Optional: Base path for relative file paths
  parameters:              # Required: Input parameter rasters
  masks:                   # Optional: Mask rasters to constrain analysis
  pipeline:                # Required: Processing steps to apply
  vectorization:           # Required: Output settings
```

## 1. Process Name (Top Level)

The top-level key defines the name of your analysis. This will be the output file:

```yaml
# Examples of analysis names
PolySulfate:           # Polysulfate detection using band combinations
D2300:                 # A single band thresholded
```

## 2. Base Path (Optional) (In Progress)

Define a base path to a directory or spatial cube to directly pull rasters from.:

```yaml
PolySulfate_BC:
  path: /Users/username/SPATIAL_DATA/MC13_demo_parameters/
  # Will search this dir for specified files
```

## 3. Parameters Section

Define input parameter rasters that will be combined to create the final classification. Each parameter includes:

- **name (Key)**: A name that will be appended to the stats if calculated
- **path**: Full or relative path to the raster file
- **median**: Median filtering settings (optional)
- **thresholds**: List of threshold values to test. All parameters must have the same number of thresholds

```yaml
parameters:
  BD1900:                                   # Parameter name (descriptive)
    path: MC13_BAL1_EQU_IMP_BD1900_2.IMG    # Raster file path
    median:                                 # Optional preprocessing
      iterations: 3                         # Number of median filter passes
    thresholds: [0.012, 0.015, 0.017]       # Threshold values to test
  
  SINDEX:
    path: MC13_BAL1_EQU_IMP_SINDEX2.IMG
    median:
      iterations: 3
    thresholds: [0.01, 0.015, 0.02]
  
  # Add more parameters as needed
  BD2100:
    path: MC13_BAL1_EQU_IMP_BD2100.IMG
    thresholds: [0.008, 0.012, 0.02]              
    # No median filtering
```

### Parameter Configuration Options:

```yaml
parameters:
  ParameterName:
    path: /path/to/raster.img               # Required: File path
    thresholds: [0.01, 0.02, 0.03]         # Required: Threshold list
    
    # Optional preprocessing
    median:
      iterations: 1                       # Number of median filter iterations
```

## 4. Masks Section (Optional)

Define mask rasters to remove regions from your analysis. Masks should have only one treshold:
- **keep_shape**: Bool, to indicate whether the mask should be applied before (False) or after (True) the processing pipeline. 

```yaml
masks:
  BD1500:                                   # Mask name
    path: MC13_BAL1_EQU_IMP_BD1500_2.IMG
    thresholds: [0.005]                     # Threshold for mask creation
    median:                                 # Optional preprocessing
      iterations: 1
  
  # Shape-preserving masks (special case)
  BD1900_2_mask:
    path: MC13_NSP_EQU_IMP_BD1900_2_GID.IMG
    thresholds: [1]
    keep_shape: True                        # Preserve original raster geometry
```

### Mask Types:

```yaml
masks:
  # Standard processing masks
  RegularMask:
    path: mask_file.img
    thresholds: [0.01]
    median:
      iterations: 2
  
  # Shape-preserving masks (for geometric constraints)
  GeometryMask:
    path: geometry_mask.img
    thresholds: [1]
    keep_shape: True                        # Don't modify this mask in pipeline
```

## 5. Pipeline Section

Define the sequence of processing steps to apply to your rasters. These processes are exicuted in a sequential order:

```yaml
pipeline:
  - task: majority                          # Majority filter
    iterations: 1                          # Number of iterations
    size: 3                                # Kernel size

  - task: boundary                         # Boundary cleaning
    iterations: 1                          # Number of iterations
    size: 3                                # Kernel size
    
  - task: sieve                            # Sieve filter (remove small objects)
    iterations: 1                          # Number of iterations
    threshold: 9                         # Minimum object size (optional)
    connectedness:
    4                         # 4 for rook or 8 for queen contiguity
  - task: open                             # Morphological opening
    iterations: 1                          # Number of iterations
    size: 3                                # Kernel size (optional)
```

### Available Pipeline Tasks:

```yaml
pipeline:
  # Majority filter - smooths noisy classifications
  - task: majority
    iterations: 1-5                        # Number of filter passes
    size: 3                                # Kernel size (default: 3)
  
  # Boundary cleaning - smooths object boundaries
  - task: boundary
    iterations: 1-3                        # Number of expand-shrink cycles
    size: 3                                # Structuring element size
  
  # Sieve filter - removes small objects
  - task: sieve
    iterations: 1-2                        # Number of sieve passes
    threshold: 1-any                      # Minimum object size in pixels
    connectedness: 4                       # 4 or 8 connectivity (default: 4)
  
  # SciPy's Binary Open filter
  - task: open
    iterations: 1-3                        # Number of opening operations
    size: 3                                # Structuring element size
```

## 6. Vectorization Section

Configure output settings and vector creation:

```yaml
vectorization:
  driver: ESRI Shapefile                    # Output format
  cs: GCS                                   # Coordinate system type
  simplify: 0                              # Geometry simplification
  intermediates: False                      # Save intermediate steps
  stats: ["area", "mean", "std"]           # Zonal statistics to calculate
  color: cyan                              # Display color
  output_dict: /path/to/output             # Output directory
  stack: True                              # Stack all results
  base:                                    # Base layer settings
    show: True
    stats: []
```

### Vectorization Options:

```yaml
vectorization:
  # Output format options
  driver: ESRI Shapefile                   # "ESRI Shapefile", "GeoJSON", "GPKG"
  
  # Coordinate system
  cs: GCS                                  # "GCS" (Geographic) or "PCS" (Projected)
  
  # Geometry processing
  simplify: 0.0                           # Simplification tolerance (0 = no simplification)
  min_area: 0                             # Minimum polygon area to keep
  
  # Intermediate outputs
  intermediates: False                     # Save intermediate processing steps
  save_rasters: False                     # Save processed rasters
  
  # Statistics calculation
  stats:                                  # Zonal statistics to calculate
    - area                                # Polygon area
    - mean                                # Mean parameter value
    - std                                 # Standard deviation
    - median                              # Median value
    - min                                 # Minimum value
    - max                                 # Maximum value
    - 5p                                  # 5th percentile
    - 25p                                 # 25th percentile
    - 75p                                 # 75th percentile
    - 95p                                 # 95th percentile
    - count                               # Pixel count
  
  # Output settings
  output_dict: /path/to/output            # Output directory
  output_prefix: analysis_                # Prefix for output files
  
  # Visualization
  color: cyan                             # Display color for results
  
  # Stacking options
  stack: True                             # Combine all threshold results
  
  # Base layer (background/context)
  base:
    show: True                            # Display base layer
    stats: []                             # Stats to calculate for base
    color: gray                           # Base layer color
```

## Complete Example Templates

### Template 1: Mineral Detection

```yaml
Olivine_Detection:
  path: /data/spectral_parameters/
  
  parameters:
    BD1000:
      path: BD1000_olivine.img
      median:
        iterations: 2
      thresholds: [0.01, 0.015, 0.02]
    
    BD2000:
      path: BD2000_olivine.img
      thresholds: [0.008, 0.012]
  
  masks:
    dust_mask:
      path: dust_coverage.img
      thresholds: [0.1]
      median:
        iterations: 1
  
  pipeline:
    - task: majority
      iterations: 2
    - task: sieve
      iterations: 1
      threshold: 100
    - task: boundary
      iterations: 1
      size: 3
  
  vectorization:
    driver: GPKG
    cs: PCS
    simplify: 10.0
    stats: ["area", "mean", "median", "std"]
    color: green
    output_dict: /output/olivine_results/
    stack: True
    intermediates: True
```

### Template 2: Simple Classification

```yaml
Simple_Classification:
  parameters:
    main_parameter:
      path: /data/main_param.tif
      thresholds: [0.5, 0.7, 0.9]
  
  pipeline:
    - task: majority
      iterations: 1
  
  vectorization:
    driver: GeoJSON
    cs: GCS
    simplify: 0
    stats: ["area", "mean"]
    color: red
    output_dict: ./output/
    stack: False
```

### Template 3: Complex Multi-Parameter Analysis

```yaml
Complex_Mineral_Suite:
  path: /project/spectral_data/
  
  parameters:
    BD1900:
      path: BD1900_param.img
      median:
        iterations: 3
      thresholds: [0.010, 0.015, 0.020, 0.025]
    
    BD2100:
      path: BD2100_param.img
      median:
        iterations: 2
      thresholds: [0.005, 0.010, 0.015]
    
    SINDEX:
      path: SINDEX_param.img
      thresholds: [0.01, 0.02, 0.03]
  
  masks:
    elevation_mask:
      path: elevation_constraint.img
      thresholds: [1000]
    
    quality_mask:
      path: data_quality.img
      thresholds: [0.8]
      keep_shape: True
  
  pipeline:
    - task: majority
      iterations: 2
      size: 5
    - task: sieve
      iterations: 1
      threshold: 200
      connectedness: 8
    - task: boundary
      iterations: 2
      size: 3
    - task: open
      iterations: 1
      size: 3
  
  vectorization:
    driver: GPKG
    cs: PCS
    simplify: 5.0
    min_area: 1000
    intermediates: True
    save_rasters: True
    stats: 
      - area
      - mean
      - std
      - median
      - min
      - max
      - 25p
      - 75p
    color: purple
    output_dict: /results/complex_analysis/
    output_prefix: mineral_suite_
    stack: True
    base:
      show: True
      stats: ["mean"]
      color: lightgray
```

## Best Practices

### 1. File Organization
```yaml
# Use consistent directory structure
Project_Name:
  path: /project/base/path/
  # All subsequent paths relative to base
```

### 2. Parameter Naming
```yaml
# Use descriptive, consistent names
parameters:
  BD1900_sulfates:        # Good: descriptive
    path: bd1900.img
  
  param1:                 # Avoid: not descriptive
    path: p1.img
```

### 3. Threshold Selection
```yaml
# Start with broad ranges, then refine
thresholds: [0.005, 0.01, 0.015, 0.02, 0.025]  # Initial exploration
thresholds: [0.012, 0.015, 0.017]              # Refined range
```

### 4. Pipeline Optimization
```yaml
# Order matters - start with noise reduction
pipeline:
  - task: majority      # First: reduce noise
    iterations: 1
  - task: sieve        # Second: remove small objects
    threshold: 100
  - task: boundary     # Last: smooth boundaries
    iterations: 1
```

### 5. Comments and Documentation
```yaml
# Use comments to explain complex configurations
Carbonate_Detection:
  # Using CRISM-derived parameters for carbonate detection
  parameters:
    BD2300:             # 2.3 μm absorption band
      path: BD2300_carbonate.img
      thresholds: [0.01, 0.02]  # Conservative thresholds for high confidence
```

## Validation and Testing

### Check Configuration Validity
```python
# Example validation function
def validate_config(config_path):
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Check required sections
    required = ['parameters', 'pipeline', 'vectorization']
    for section in required:
        if section not in config:
            raise ValueError(f"Missing required section: {section}")
    
    # Validate file paths exist
    for param_name, param_config in config['parameters'].items():
        if not os.path.exists(param_config['path']):
            raise FileNotFoundError(f"Parameter file not found: {param_config['path']}")
```

This guide provides a comprehensive framework for creating YAML configuration files that are both powerful and maintainable for your raster processing library.