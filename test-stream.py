import requests
import json
import logging
from time import sleep

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_streaming():
    """Test streaming response from the API endpoint"""
    url = "https://api.canalavi.com/chat/team/67b36b253988040f53b35f8e"
    headers = {
        "Accept": "text/event-stream",  # Important for SSE
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Authorization": "Bearer eyJhbGciOiJSUzI1NiIsImNhdCI6ImNsX0I3ZDRQRDIyMkFBQSIsImtpZCI6Imluc18ycXFrTXhVQXQwQmJ4NW9EZld0MTd5WTNMQmsiLCJ0eXAiOiJKV1QifQ.eyJleHAiOjE3Mzk4MTczNzMsImlhdCI6MTczOTgxMTM3MywiaXNzIjoiaHR0cHM6Ly9mdW5ueS1wYXJyb3QtNTAuY2xlcmsuYWNjb3VudHMuZGV2IiwianRpIjoiNjM2NjNhMGY3YWM0ZWMxYjYyNzIiLCJuYmYiOjE3Mzk4MTEzNjgsInN1YiI6InVzZXJfMnNMME5Za3NSNDl5NUVKUDFXQjhVY0FCOWUwIn0.19ZJ01iDH-F-BbqbHogYkJftYSsksEgKDLkxT8jTRHr-mXjVqIDCyBS5zBXZaOiSm74SanAwBa0kVinONxWa5nn9R5OSmrK4xy9k6eIJDMVmk2PFmygtphQxoxQ0KM0sUjE3Vo-WznQ3ZFAQ5a-kyqrIanXZtBp4gZMXSyON5rfM2oSZUv7egl8yPuIPcYo19K3awyjCCya5KvDPNzIm2ElhYmd8Vh2I9Nn-QhVc9Mmnb-ivLDt5htapLTZGeN5nqSh-c-kqkTmuXg3qKcQk86IVhT6nKJhqNpZskxELzprGYN3MjvGpD3XHe3AlaznQa4fyEJ4KnqVF5_qnKuXuFg",
        "Content-Type": "application/json",
    }
    params = {
        "stream": True,
        "use_rag": False
    }
    payload = {
        "message": "do you know what is skibidi toilet ?"
    }

    try:
        logger.info("Starting streaming request...")
        with requests.post(url, headers=headers, json=payload, params=params, stream=True) as response:
            response.raise_for_status()
            logger.debug(f"Response headers: {response.headers}")
            
            buffer = ""
            for chunk in response.iter_content(chunk_size=1024, decode_unicode=True):
                if chunk:
                    logger.debug(f"Raw chunk received: {chunk}")
                    buffer += chunk if isinstance(chunk, str) else chunk.decode('utf-8')
                    
                    # Process complete lines from buffer
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        line = line.strip()
                        if line:
                            if line.startswith('data: '):
                                data = line[6:]  # Remove 'data: ' prefix
                                try:
                                    json_data = json.loads(data)
                                    content = json_data.get('content', data)
                                    print(content, end='', flush=True)
                                except json.JSONDecodeError:
                                    print(data, end='', flush=True)
                            else:
                                print(line, end='', flush=True)
                    
                    # Small delay to simulate real-time processing
                    sleep(0.01)
            
            # Process any remaining data in buffer
            if buffer:
                print(buffer, end='', flush=True)

    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {str(e)}")
        if hasattr(e.response, 'text'):
            logger.error(f"Response text: {e.response.text}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")

if __name__ == "__main__":
    print("\nStarting streaming test...\n")
    test_streaming()
    print("\nStreaming test completed.\n")
