from database.mongo import client as db
import csv
import os
from datetime import datetime, timezone
import traceback
from keys.keys import environment
from ultraprint.logging import logger
from ultraconfiguration import UltraConfig

#! Initialize ---------------------------------------------------------------
config = UltraConfig('config.json')
log = logger('error_log', 
            filename='debug/error.log', 
            include_extra_info=config.get("logging.include_extra_info", False), 
            write_to_file=config.get("logging.write_to_file", False), 
            log_level=config.get("logging.development_level", "DEBUG") if environment == 'development' else config.get("logging.production_level", "INFO"))

# Collection for error logs
collection = db.logs.error

def log_exception(exception, function):

    try:
        log.error(exception)
        function_name = function.__name__
        # Get the traceback
        tb = traceback.format_exc()
        
        # Log to MongoDB
        error_entry = {
            "api": "AIML",
            "function": function_name,
            "exception": str(exception),
            "traceback": tb,
            "timestamp": datetime.now(timezone.utc)
        }
        collection.insert_one(error_entry)
        # Log to CSV
        csv_file_path = "debug/error_log.csv"
        file_exists = os.path.isfile(csv_file_path)
        with open(csv_file_path, mode='a', newline='') as file:
            writer = csv.writer(file)
            if not file_exists:
                writer.writerow(["timestamp", "function", "exception", "traceback"])
            writer.writerow([datetime.now(timezone.utc), function_name, str(exception), tb])
    except Exception as e:
        log.error(e)

def log_exception_with_request(exception, function, request):
    try:
        log.error(exception)
        function_name = function.__name__
        tb = traceback.format_exc()
        
        # SafeFastAPI request handling
        request_info = {
            "url": str(request.url) if request and hasattr(request, 'url') else "N/A",
            "method": request.method if request and hasattr(request, 'method') else "N/A",
            "headers": dict(request.headers) if request and hasattr(request, 'headers') else {}
        }

        # Log to MongoDB
        error_entry = {
            "api": "AIML",
            "function": function_name,
            "exception": str(exception),
            "traceback": tb,
            "timestamp": datetime.now(timezone.utc),
            "request": request_info
        }
        collection.insert_one(error_entry)
        
        # Log to CSV
        csv_file_path = "debug/error_log.csv"
        file_exists = os.path.isfile(csv_file_path)
        with open(csv_file_path, mode='a', newline='') as file:
            writer = csv.writer(file)
            if not file_exists:
                writer.writerow(["timestamp", "function", "exception", "traceback", "url", "method", "headers"])
            writer.writerow([
                datetime.now(timezone.utc), 
                function_name, 
                str(exception), 
                tb, 
                str(request.url), 
                request.method, 
                str(dict(request.headers))
            ])
    except Exception as e:
        log.error(e)