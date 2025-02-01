
import json
import numpy as np
import re
from datetime import datetime
from pydantic import BaseModel

def convert_keys_to_str(obj):
    """Recursively convert keys in a dictionary to strings."""
    if isinstance(obj, dict):
        return {str(key): convert_keys_to_str(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_keys_to_str(element) for element in obj]
    elif isinstance(obj, (np.float32, np.float64)):  # Handle NumPy float types
        return float(obj)
    elif isinstance(obj, (np.int32, np.int64)):  # Handle NumPy int types
        return int(obj)
    return obj

def quantize_floats(obj, decimal_places=2):
    """Recursively round all float values in the data structure to the specified decimal places."""
    if isinstance(obj, dict):
        return {key: quantize_floats(value, decimal_places) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [quantize_floats(element, decimal_places) for element in obj]
    elif isinstance(obj, float):
        return round(obj, decimal_places)
    elif isinstance(obj, (np.float32, np.float64)):
        return round(float(obj), decimal_places)
    return obj

def save_results_to_json(results, output_file, quantize=True):
    # Convert keys to strings for JSON compatibility
    results_str = convert_keys_to_str(results)
    if quantize:
        # Quantize all float values to 2 decimal places
        results_str = quantize_floats(results_str, 2)
    with open(output_file, 'w') as f:
        json.dump(results_str, f, indent=2)

def extract_json_content(video_project):

    if isinstance(video_project, BaseModel):
        return video_project.model_dump(by_alias=True)

    if isinstance(video_project, dict):
        return video_project
    
    try:
        pattern = r'```json(.*?)```'
        match = re.search(pattern, video_project, re.DOTALL)
        if match:
            return json.loads(match.group(1).strip())
        else:
            return json.loads(video_project)
    except Exception as e:
        return video_project

def datetime_handler(obj):
    """Handle datetime serialization for MongoDB"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    return str(obj)