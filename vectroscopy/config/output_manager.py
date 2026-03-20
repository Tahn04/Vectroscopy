"""
Output and vectorization configuration management.
"""
import os
from pyproj import CRS
from .process_manager import ProcessManager

class OutputManager:
    """
    Handles output paths, drivers, and vectorization settings.
    """
    
    def __init__(self, config_instance):
        self.config = config_instance
        self.output_path = None
        self.driver = None
        self.stats = None
        self.output_filename = None
        self.process_manager = ProcessManager(self.config)
        self.default_output_config = {}
        self.mem_safe = None  

    def get_mem_safe(self):
        """Get the memory safety setting for the current process."""
        if hasattr(self, 'mem_safe') and self.mem_safe is not None: # attributes are then setting from array
            return self.mem_safe

        process = self.process_manager.get_current_process()
        if process['vectorization'].get('mem_safe', None):
            return process['vectorization']['mem_safe']
        else:
            return self.default_output_config.get('mem_safe', False)

    def set_mem_safe(self, mem_safe):
        """Set the memory safety setting for the current process."""
        if not isinstance(mem_safe, bool):
            raise ValueError("mem_safe must be a boolean value")
        self.mem_safe = mem_safe
        # Also update the current process in the config
        process = self.process_manager.get_current_process()
        process['vectorization']['mem_safe'] = mem_safe

    def get_output_path(self):
        """Get the output path for the current process."""
        if hasattr(self, 'output_path') and self.output_path:
            return self.output_path
    
        process = self.process_manager.get_current_process()
        if process['vectorization'].get('output_dict', False):
            return process['vectorization']['output_dict']
        elif self.default_output_config:
            return self.default_output_config.get('output_dict', os.getcwd())
        return os.getcwd()

    def get_driver(self):
        """Get the driver for the current process."""
        if hasattr(self, 'driver') and self.driver:
            return self.driver
        try:
            process = self.process_manager.get_current_process()

            return process['vectorization'].get('driver', 'pandas')
        except (ValueError, KeyError):
            # If current process is not set, return default driver
            return 'pandas'
    
    def create_output_filename(self):
        """Get the output filename for the current process."""
        driver = self.get_driver()
        if driver == 'pandas':
            return None
            
        extension_map = {
            'GeoJSON': 'geojson',
            'ESRI Shapefile': 'shp',
            'GPKG': 'gpkg'
        }
        file_extension = extension_map.get(driver)
        if not file_extension:
            raise ValueError(f"Unknown driver: {driver}")
        name = self.process_manager.get_current_process()["name"]
        
        # Simple sanitization: replace spaces with underscores
        safe_name = name.replace(" ", "_")
        return f"{safe_name}_final.{file_extension}"
    
    def get_output_filename(self):
        """Get the output filename for the current process."""
        return self.output_filename

    def get_intermediates(self):
        """Check if intermediate files should be saved."""
        process = self.process_manager.get_current_process()
        
        return process['vectorization'].get('intermediates', False)

    def get_cs(self, crs):
        """Get the coordinate reference system for the current process."""
        process = self.process_manager.get_current_process()
        
        cs = process['vectorization'].get('cs', None)

        crs_obj = CRS.from_string(crs) if isinstance(crs, str) else crs
        if cs is None or cs == "GCS":
            if crs_obj.is_projected:
                geogcs = crs_obj.geodetic_crs
                return geogcs.to_wkt()
            else:
                return crs_obj.to_wkt()
        elif cs == "PCS":
            if crs_obj.is_geographic:
                print("CRS is geographic, converting to projected CRS.")
                return crs_obj.to_wkt()
            else:
                return crs_obj.to_wkt()
        else:
            return cs

    def get_color(self):
        """Get the color for the current process."""
        process = self.process_manager.get_current_process()
        if process['vectorization'].get('color', None):
            return process['vectorization']['color']
        else:
            return self.default_output_config.get('color', None)

    def get_stats(self):
        """Get the statistics configuration for the current process."""
        if hasattr(self, 'stats') and self.stats:
            return self.stats
            
        try:
            process = self.process_manager.get_current_process()
            vector_stats = process['vectorization'].get('stats', None)
            if vector_stats is not None:
                return vector_stats
            default_stats = self.default_output_config.get('stats', None)
            if default_stats is not None:
                return default_stats
            return []
        except (ValueError, KeyError):
            return []
    
    def get_base_check(self):
        """Check if the current process is set to run in base mode."""
        process = self.process_manager.get_current_process()
        
        base_config = process['vectorization'].get('base', None)
        if isinstance(base_config, dict):
            return base_config.get('show', False)

    def get_base_stats(self):
        """Get the base statistics for the current process."""
        process = self.process_manager.get_current_process()
        
        if self.get_base_check():
            base_config = process['vectorization'].get('base', None)
            if isinstance(base_config, dict):
                return base_config.get('stats', [])
        return []
    
    def get_simplification_level(self):
        """Get the simplification level for vectorization."""
        process = self.process_manager.get_current_process()
        
        simplify = process['vectorization'].get('simplify', 0)
        return simplify
    
    def get_stack(self):
        """Check if the current process is set to stack results."""
        process = self.process_manager.get_current_process()
        
        return process['vectorization'].get('stack', True)
