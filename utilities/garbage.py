import functools
import gc

def garbage_collector(func):
    """Decorator to handle garbage collection after function execution"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        finally:
            gc.collect()
    return wrapper