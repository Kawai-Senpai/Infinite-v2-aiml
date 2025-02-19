import requests
import json
import logging
from time import sleep

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_streaming():
    """Test streaming response from the API endpoint"""
    url = "https://api.canalavi.com/chat/team/67b499b13f5dd757352a9b2f"
    headers = {
        "Accept": "text/event-stream",  # Important for SSE
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Authorization": "Bearer eyJhbGciOiJSUzI1NiIsImNhdCI6ImNsX0I3ZDRQRDIyMkFBQSIsImtpZCI6Imluc18ycXFrTXhVQXQwQmJ4NW9EZld0MTd5WTNMQmsiLCJ0eXAiOiJKV1QifQ.eyJleHAiOjE3Mzk4OTYyOTYsImlhdCI6MTczOTg5MDI5NiwiaXNzIjoiaHR0cHM6Ly9mdW5ueS1wYXJyb3QtNTAuY2xlcmsuYWNjb3VudHMuZGV2IiwianRpIjoiYjc2MjEyMzE0MzdhZmQ3MTg1YzUiLCJuYmYiOjE3Mzk4OTAyOTEsInN1YiI6InVzZXJfMnNMME5Za3NSNDl5NUVKUDFXQjhVY0FCOWUwIn0.jQ4xX3hjDqMzVU9Bvkfq1t8VHhXSYIgZJ6wVHLMVsSp5TGKmLJE7LvdOLKErM282DY85yY9wAbI3T6i1PIugMR7X0SLaT7YB-v0Pwkj_8bCLnHUCP9LTx2oYGPdi3DdOoUMn95wtFsqrM2C48qSY74Ai1GGfn1lA1Gt-8m732Zc39kEhXGMKg-IXf8t7gj6stCHl3bXThPVZ1B2sT-m1jQ5JnApTWNNZFr_6dCzRMqiRFGzvDfWDxDeH5obcJyb2r4MwfbgnGqoiBC3AZQECDBmDQ0z2X_aoOeyfB8xa4FBCoJXpHa-hDH4fnSSCG34msc9LGTedzEzRBwHn29O9iA",
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
