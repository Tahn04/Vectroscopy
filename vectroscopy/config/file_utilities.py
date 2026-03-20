"""
File operations and utilities for configuration management.
"""
import os
import re
import shutil
import yaml
try:
    # Python 3.9+
    from importlib.resources import files, as_file
except ImportError:
    # Python 3.8 fallback
    from importlib_resources import files, as_file

class FileUtilities:
    """
    Utilities for file operations in configuration management.
    """
    
    def __init__(self, config_instance):
        self.config = config_instance
    
    def get_file_paths(self, names, dir_path):
        """
        Returns the file path of the parameter raster or paths for indicators.
        
        Args:
            names: List of parameter names to find files for
            
        Returns:
            Dictionary mapping parameter names to file paths
        """
        files = os.listdir(dir_path)
        files_dict = {}

        for param in names:
            file_path = self._find_file(files, param, dir_path)
            if file_path:
                files_dict[param] = file_path
            else:
                print(f"File for parameter {param} not found in {dir_path}")

        return files_dict

    def _find_file(self, files, param, dir_path):
        """
        Helper function to find the file for a given parameter in the directory.
        
        Args:
            files: List of files in the directory
            param: Parameter name to search for
            dir_path: Directory path
            
        Returns:
            Full file path if found, None otherwise
        """
        pattern = re.compile(rf".*{re.escape(param)}$")
        for f in files:
            match = pattern.match(f)
            if match:
                return os.path.join(dir_path, f)
        return None

    def config_path(self, file_path, param_file_dicts, mask_file_dicts):
        """
        Returns the path of the configuration file or directory.

        Args:
            file_path: Path to check
            param_file_dicts: Dictionary of parameter file paths
            mask_file_dicts: Dictionary of mask file paths

        Returns:
            str: Path to the configuration file or directory
        """
        param_names = list(param_file_dicts.keys())
        mask_names = list(mask_file_dicts.keys())

        if os.path.isdir(file_path):
            param_dict = self.get_file_paths(param_names, file_path)
            mask_dict = self.get_file_paths(mask_names, file_path)
            for key in param_dict:
                param_file_dicts[key]["path"] = param_dict[key]
            for key in mask_dict:
                mask_file_dicts[key]["path"] = mask_dict[key]
        else:
            print(f"{file_path} is a file.")
        return file_path
    
    @staticmethod
    def find_default_config(temp_dir) -> str:
        """
        Find the default configuration file using proper resource management.
        
        Returns:
            str: Path to the default configuration file
            
        Raises:
            FileNotFoundError: If no default config file can be found
        """
        # First, try to find config files in the package resources
        try:
            config_files = files("vectroscopy.config_files")
            
            # Try to find config.yaml first
            for config_name in ["config.yaml", "default.yaml"]:
                try:
                    config_file = config_files / config_name
                    if config_file.is_file():
                        # Extract to a temporary location so it can be read
                        with as_file(config_file) as config_path:
                            # Copy to a more permanent location in user's temp directory
                            permanent_config = os.path.join(temp_dir, f"vectroscopy_{config_name}")
                            shutil.copy2(str(config_path), permanent_config)
                            return permanent_config
                except (FileNotFoundError, AttributeError):
                    continue
        except Exception:
            pass
        
        # Fallback: try to find config in various common locations
        search_paths = [
            # Current working directory
            os.path.join(os.getcwd(), "config.yaml"),
            os.path.join(os.getcwd(), "config", "config.yaml"),
            # User's home directory
            os.path.expanduser("~/.vectroscopy/config.yaml"),
            # System-wide config (Unix-like systems)
            "/etc/vectroscopy/config.yaml",
            # Development fallback (relative to package)
            os.path.abspath(os.path.join(os.path.dirname(__file__), "../../config/config.yaml")),
        ]
        
        for path in search_paths:
            if os.path.exists(path):
                return path
        
        # If no config found, create a minimal default one
        temp_config = os.path.join(temp_dir, "vectroscopy_default_config.yaml")
        FileUtilities.create_default_config_file(temp_config)
        return temp_config
    
    @staticmethod
    def create_default_config_file(config_path: str):
        """
        Create a minimal default configuration file.
        
        Args:
            config_path: Path where to create the config file
        """
        default_config = {
            "processes": {
                "default": {
                    "name": "default",
                    "description": "Default processing configuration",
                    "parameters": {},
                    "masks": {},
                    "pipeline": [
                        {"task": "raster_ops", "parameters": {}}
                    ],
                    "output": {
                        "path": "./output",
                        "driver": "GeoJSON",
                        "statistics": True,
                        "base_mode": False,
                        "simplification_level": 0.0,
                        "stack_results": False
                    }
                }
            },
            "median": {
                "iterations": 1,
                "size": 3
            }
        }
        
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, 'w') as f:
            yaml.dump(default_config, f, default_flow_style=False, indent=2)
