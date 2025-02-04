# 🤖 Infinite v2 AI/ML

## Table of Contents
- [Core Features ⚙️](#core-features)
- [Advanced Features ✨](#advanced-features)
- [Technical Specifications 📊](#technical-specifications)
- [Environment Configuration 🛠️](#environment-configuration)
- [Project Structure 🗂️](#project-structure)

---

# 🤖 Infinite v2 AI/ML

An advanced conversational AI system with multi-model support, RAG capabilities, dynamic tool usage, and persistent memory.

## Core Features ⚙️

### Multi-Model Support
- OpenAI models (GPT-4 and variants)
- Cohere models (Command-R series)
- Easy extensibility for new models
- Model-agnostic architecture for easy expansion
- Automatic model routing and response handling
- Dynamic integration of both synchronous and streaming approaches

### RAG (Retrieval Augmented Generation)
- Multiple collection support per agent
- Automatic context retrieval and integration
- Vector database integration (ChromaDB)
- Support for various document types
- Smart chunking strategies:
  - Sentence-based chunking with overlap
  - Character-based chunking for complex documents
  - Automatic chunk size optimization
- Enhanced context aggregation: Merges recent session history and long-term memory for richer responses

### Dynamic Tool System
- Automatic tool selection using AI with decision naming that dynamically identifies required tools.
- Dynamic tool loading: Tools are discovered on the fly from a dedicated tools directory, enabling plug-and-play integration.
- Parallel tool execution: Multiple tools are executed concurrently using ThreadPoolExecutor with robust error handling.
- Tool response integration into context.
- Multiple tools per request.
- Current tools:
  - Web search (DuckDuckGo)
  - More tools can be easily added.
- Dynamic tool discovery: Validates and retrieves tool descriptions from a dedicated tools directory.
- Parallel execution with error handling using ThreadPoolExecutor.
- Parallel execution of tool and memory analysis to optimize response generation.
- Extensible API Integration: Tools can now include API calls and even incorporate internal LLMs for advanced functionalities.

New tools can be integrated by simply adding a new folder or module within the tools directory following the established naming conventions. No changes in the central dispatch logic are required, making it very easy to extend the system. This modular architecture enables each tool to perform complex operations—including external API integrations and embedded LLM calls—thereby encouraging rapid experimentation and seamless enhancements.

### Memory System
- Long-term information storage
- Automatic importance analysis
- Smart memory management
- Size-limited memory with configurable limits
- Persistent across sessions
- Automatic memory integration in responses
- Integrated memory analysis: Parallel processing to detect important user details and update agent memory

### Document Processing
Supported file types:
- PDF (with OCR support)
- Microsoft Word (DOCX)
- Excel spreadsheets
- Web pages (with scraping)
- Support for:
  - Tables and structured data
  - Images and diagrams (via OCR)
  - Complex formatting
- File caching via AWS S3 and robust error handling for file operations

### Streaming Support
- Real-time response generation
- Progress accumulation
- Automatic history updates
- Support for both OpenAI and Cohere streaming
- Improved handling of incremental responses and session history updates as responses stream in

### Agent System
- Custom agent creation and dynamic configuration.
- Dynamic ownership checks: Validates agent and session access on the fly based on user ownership, ensuring that operations like creation, update, or deletion are secured.
- Tool access control integrated with dynamic tool discovery and validation.
- Role-based behavior
- Configurable capabilities
- Rule enforcement
- Multiple collections per agent
- Memory management
- Tool access control
- Enhanced agent security: Dynamic agent type validation and access control based on ownership
- Automatic generation and validation of collection IDs and tool modules
- Dynamic retrieval of available tool metadata to enrich agent capabilities

### Session Management
- Persistent chat sessions
- History management
- Context preservation
- Configurable history limits
- Multi-user support
- Granular access control: Enhanced security checks for session creation, update, and deletion
- Paginated session history retrieval and sorted session listings
- Enhanced session security validations through multiple ownership checks

## Advanced Features ✨

### Context Management
- Smart context retrieval
- Relevance-based sorting
- Multiple collection search
- Automatic context integration
- Memory-context fusion
- Automated merging of session history with long-term memory to optimize prompt generation

### AWS Integration
- S3 storage support
- Document caching
- Efficient file handling
- Automatic cleanup
- Robust file transfer operations with directory listing and pre-signed URL generation

### Logging and Monitoring
- Detailed logging system
- Development/Production modes
- Performance monitoring
- Error tracking
- Debug capabilities
- Configurable logging: Separate logs per module with extra info when needed
- Improved logging configurations allowing better tuning based on deployment mode

### Configuration System
- JSON-based configuration
- Environment-specific settings
- Model configurations
- System constraints
- Easy customization
- Dynamic constraints for model providers and tool validations driven by configuration

### Security Features
- API key management and role-based dynamic validation.
- Dynamic ownership checks: In-depth security validations ensure users have proper rights to view or modify agents and sessions.
- System agent protection
- Secure file handling
- Additional access controls for session history and agent operations

## Technical Specifications 📊

### Database Architecture
- MongoDB for structured data
- ChromaDB for vector storage
- Efficient data retrieval
- Automatic indexing

### Model Support
- OpenAI API integration
- Cohere API integration
- Custom model routing
- Response formatting

### File Processing Pipeline
1. File upload/URL processing
2. Content extraction
3. Text chunking
4. Vector embedding
5. Database storage

### Tool Execution Pipeline
- Request analysis with dynamic decision naming to choose the tool.
- Parallel execution: Tools run concurrently to reduce latency.
- Response formatting and context integration.
- Tool selection
- Parallel execution
- Response formatting
- Context integration

### Memory Processing Pipeline
- Content analysis
- Importance evaluation
- Memory storage
- Size management
- Context integration

### Data Management

#### JSON Processing
- Advanced JSON handling
- Key conversion for compatibility
- NumPy data type support
- Float quantization
- Datetime serialization
- Pydantic model support

#### File Management
- S3 integration with AWS
  - File upload/download
  - Directory listing
  - Pre-signed URL generation
  - Bucket management
- Robust file operations
  - Unique filename generation
  - Automatic retries
  - File handle management
  - Cache cleanup
- Error handling and recovery
  - Permission error handling 
  - Process management
  - File handle force closure

#### Memory Management
- Automated garbage collection
- Resource optimization
- Memory leak prevention
- Decorator-based cleanup

#### Document Processing
- Text chunking strategies:
  - Sentence-based chunking
    - Configurable chunk size
    - Overlap control
    - Deduplication
  - Character-based chunking
    - Fixed size chunks
    - Customizable overlap
    - White space handling
- File type support:
  - PDF extraction
  - DOCX processing
  - Excel parsing
  - Web page scraping
- Document management:
  - Hash-based tracking
  - Chunk management
  - Metadata storage
  - Vector storage integration

## Environment Configuration 🛠️

The project uses multiple environment files for different deployment scenarios:

### Environment Files
- `.env` - Controls which environment settings to use
- `.env.development` - Development environment settings
- `.env.production` - Production environment settings

### Why Multiple Environment Files?

1. **Security**: Separate credentials for development and production
2. **Configuration Management**: Different settings for local development vs production deployment
3. **Debug Settings**: Development environment can have verbose logging and smaller limits
4. **Testing**: Allows testing with different configurations without modifying production settings

## Project Structure 🗂️

```
│   .dockerignore
│   .env
│   .env.development
│   .env.production
│   .gitignore
│   .gitmessage
│   config.json
│   Readme.md
│   requirements.txt
│   test.py
│   _init.py
│   _server.py
│
├───.testdata
│   │   chroma.log
│   │   rundbs.bat
│   │
│   ├───chroma
│   │
│   └───mongo
│
├───cache
│       Readme.md
│
├───database
│   │   chroma.py
│   │   mongo.py
│   │
│   └───__pycache__
│           chroma.cpython-311.pyc
│           mongo.cpython-311.pyc
│
├───debug
│       error_log.csv
│       Readme.md
│
├───errors
│   │   error_logger.py
│   │
│   └───__pycache__
│           error_logger.cpython-311.pyc
│
├───keys
│   │   keys.py
│   │
│   └───__pycache__
│           keys.cpython-311.pyc
│           keys.cpython-312.pyc
│
├───llm
│   │   agents.py
│   │   chat.py
│   │   decision.py
│   │   prompts.py
│   │   schemas.py
│   │   sessions.py
│   │   tools.py
│   │
│   └───__pycache__
│           agents.cpython-311.pyc
│           chat.cpython-311.pyc
│           decision.cpython-311.pyc
│           prompts.cpython-311.pyc
│           schemas.cpython-311.pyc
│           sessions.cpython-311.pyc
│           tools.cpython-311.pyc
│
├───rag
│       file_handler.py
│       file_management.py
│       file_processor.py
│
├───routes
│   │   agent_route.py
│   │   chat_route.py
│   │   session_route.py
│   │
│   └───__pycache__
│           agent_route.cpython-311.pyc
│           chat_route.cpython-311.pyc
│           session_route.cpython-311.pyc
│
├───tools
│   ├───web-search
│   │   │   config.json
│   │   │   core.py
│   │   │   decision.py
│   │   │   main.py
│   │   │   prompts.py
│   │   │   schemas.py
│   │   │
│   │   └───__pycache__
│   │           core.cpython-311.pyc
│   │           decision.cpython-311.pyc
│   │           main.cpython-311.pyc
│   │           prompts.cpython-311.pyc
│   │           schemas.cpython-311.pyc
│   │
│   └───web-search-fast
│       │   config.json
│       │   core.py
│       │   main.py
│       │
│       └───__pycache__
│               core.cpython-311.pyc
│               main.cpython-311.pyc
│
├───utilities
│   │   garbage.py
│   │   s3_loader.py
│   │   save_json.py
│   │   scraping.py
│   │
│   └───__pycache__
│           save_json.cpython-311.pyc
│
└───__pycache__
        _server.cpython-311.pyc
```

## Tool Development Guidelines

When creating a new tool, please follow these guidelines:

1. Folder Naming:
   - Name the folder without special characters or spaces (e.g., "mytool", "websearchfast").
   - The folder can include additional files and submodules if needed.

2. Main File Requirements:
   - Create a main file (typically "main.py") that must contain only:
     a. An _info variable describing the tool.
     b. An _execute function with the signature:
        def _execute(agent, message, history):
            # ...execution code...
            return result
   - Do not include any additional top-level code in this file.

   For example, a valid main.py:
   ```python
   # Example main.py for a new tool
   _info = "This tool performs a sample operation."

   def _execute(agent, message, history):
       # Process the input and perform the tool's function
       return "sample result"
   ```

3. Additional Files:
   - You may include helper modules, configuration files, or additional code in your tool folder.
   - These extra files should support the main functionality defined in main.py.
   - The system will automatically discover your tool based on the main file's _info and _execute.

4. Integration:
   - When a tool is added to the tools directory, no changes are required in the central dispatch logic.
   - Ensure that your tool folder meets the naming and main file guidelines for seamless integration.

## API Documentation

Most endpoints accept an optional `user_id` parameter for authorization. When required, it can be passed as:
- Query parameter for GET/DELETE requests
- JSON body field for POST requests

### Agent Endpoints (Prefix: /agents)

#### Create Agent
- **Method**: POST
- **URL**: /agents/create
- **Required Parameters**:
  - `user_id` (string): Owner's user ID
  - `agent_type` (string): Type of agent ("public", "private", "system")
  - `name` (string): Agent name
- **Optional Parameters**:
  - `role` (string): Agent's role description
  - `capabilities` (array): List of agent capabilities
  - `rules` (array): List of agent rules
  - `model_provider` (string, default: "openai"): LLM provider
  - `model` (string, default: "gpt-4"): Model name
  - `max_history` (integer, default: 20): Maximum conversation history
  - `tools` (array): List of enabled tools
  - `num_collections` (integer, default: 1): Number of memory collections
  - `max_memory_size` (integer, default: 5): Maximum memory size
- **Response**: 
  - Success: `{"agent_id": "string"}`
  - Error: `{"detail": "error message"}`
- **Example**:
```bash
curl -X POST "http://localhost:8000/agents/create" \
     -H "Content-Type: application/json" \
     -d '{
       "user_id": "1234",
       "agent_type": "public",
       "name": "ResearchAssistant",
       "role": "Research and analysis expert",
       "capabilities": ["research", "analysis"],
       "rules": ["Be concise", "Cite sources"],
       "model": "gpt-4",
       "tools": ["web_search", "calculator"]
     }'
```

#### Delete Agent
- Method: DELETE
- URL: /agents/delete/{agent_id}
- Query Parameter: Optional `user_id`
- Example:
```
curl -X DELETE "http://localhost:8000/agents/delete/agent123?user_id=1234"
```

#### List Public Agents
- Method: GET
- URL: /agents/get_public
- Example:
```
curl "http://localhost:8000/agents/get_public?limit=20&skip=0"
```

#### List Approved Agents
- Method: GET
- URL: /agents/get_approved
- Example:
```
curl "http://localhost:8000/agents/get_approved?limit=20&skip=0"
```

#### List System Agents
- Method: GET
- URL: /agents/get_system
- Example:
```
curl "http://localhost:8000/agents/get_system?limit=20&skip=0"
```

#### List User Agents
- Method: GET
- URL: /agents/get_user/{user_id}
- Example:
```
curl "http://localhost:8000/agents/get_user/1234?limit=20&skip=0"
```

#### Get Agent Details
- Method: GET
- URL: /agents/get/{agent_id}
- Query Parameter: Optional `user_id`
- Example:
```
curl "http://localhost:8000/agents/get/agent123?user_id=1234"
```

#### List Available Tools
- Method: GET
- URL: /agents/tools
- Example:
```
curl "http://localhost:8000/agents/tools"
```

### Session Endpoints (Prefix: /sessions)

#### Create Session
- **Method**: POST
- **URL**: /sessions/create
- **Required Parameters**:
  - `agent_id` (string): ID of the agent to chat with
  - `max_context_results` (integer): Maximum context results to return
- **Optional Parameters**:
  - `user_id` (string): User identifier for private sessions
- **Response**:
  - Success: `{"session_id": "string"}`
  - Error: `{"detail": "error message"}`
- **Example**:
```bash
curl -X POST "http://localhost:8000/sessions/create" \
     -H "Content-Type: application/json" \
     -d '{
       "agent_id": "agent123",
       "max_context_results": 1,
       "user_id": "1234"
     }'
```

#### Delete Session
- Method: DELETE
- URL: /sessions/delete/{session_id}
- Query Parameter: Optional `user_id`
- Example:
```
curl -X DELETE "http://localhost:8000/sessions/delete/session123?user_id=1234"
```

#### Get Session History
- Method: GET
- URL: /sessions/history/{session_id}
- Query Parameters: `user_id`, `limit`, `skip`
- Example:
```
curl "http://localhost:8000/sessions/history/session123?user_id=1234&limit=20&skip=0"
```

#### Update Session History
- Method: POST
- URL: /sessions/history/update/{session_id}
- Body (JSON): `role`, `content`, and optional `user_id`
- Example:
```
curl -X POST "http://localhost:8000/sessions/history/update/session123" \
     -H "Content-Type: application/json" \
     -d '{"role": "user", "content": "Hello", "user_id": "1234"}'
```

#### Get Recent Session History
- Method: GET
- URL: /sessions/history/recent/{session_id}
- Query Parameters: Optional `user_id`, `limit`, `skip`
- Example:
```
curl "http://localhost:8000/sessions/history/recent/session123?user_id=1234&limit=20&skip=0"
```

#### List All Sessions for a User
- Method: GET
- URL: /sessions/get_all/{user_id}
- Example:
```
curl "http://localhost:8000/sessions/get_all/1234?limit=20&skip=0"
```

#### List Agent Sessions for a User
- Method: GET
- URL: /sessions/get_by_agent/{agent_id}
- Query Parameter: Optional `user_id`
- Example:
```
curl "http://localhost:8000/sessions/get_by_agent/agent123?user_id=1234&limit=20&skip=0"
```

#### Get Session Details
- Method: GET
- URL: /sessions/get/{session_id}
- Query Parameter: Optional `user_id`
- Example:
```
curl "http://localhost:8000/sessions/get/session123?user_id=1234&limit=20&skip=0"
```

### Chat Endpoint (Prefix: /chat)

#### Chat with Agent
- **Method**: POST
- **URL**: /chat/agent/{session_id}
- **Path Parameters**:
  - `session_id` (string): Active session identifier
- **Query Parameters**:
  - `agent_id` (string, required): Agent identifier
  - `stream` (boolean, optional, default: false): Enable streaming response
  - `use_rag` (boolean, optional, default: true): Use RAG for context
- **Body Parameters**:
  - `message` (string, required): User message
  - `user_id` (string, optional): User identifier
- **Response Formats**:
  - Non-streaming: `{"response": "string"}`
  - Streaming: Server-Sent Events (text/event-stream)
- **Examples**:

1. Regular Chat:
```bash
curl -X POST "http://localhost:8000/chat/agent/session123?agent_id=agent123" \
     -H "Content-Type: application/json" \
     -d '{
       "message": "What is artificial intelligence?",
       "user_id": "1234"
     }'
```

2. Streaming Chat:
```bash
curl -X POST "http://localhost:8000/chat/agent/session123?agent_id=agent123&stream=true" \
     -H "Content-Type: application/json" \
     -d '{
       "message": "What is artificial intelligence?",
       "user_id": "1234"
     }'
```

### Server Status Endpoints

#### Get Server Status
- **Method**: GET
- **URLs**: /status or /
- **Response**:
```json
{
    "server": "AIML",
    "time": "2024-01-01T12:00:00.000Z",
    "mongodb": "up|down",
    "chromadb": "up|down"
}
```
- **Example**:
```bash
curl "http://localhost:8000/status"
```

### Error Handling

#### HTTP Status Codes
- **400 Bad Request**: Missing or invalid parameters
  ```json
  {"detail": "Message is required"}
  ```
- **403 Forbidden**: Unauthorized access
  ```json
  {"detail": "Not authorized to access this resource"}
  ```
- **404 Not Found**: Resource not found
  ```json
  {"detail": "Agent not found"}
  ```
- **500 Internal Server Error**: Server error
  ```json
  {"detail": "Internal Server Error"}
  ```

### Pagination
Many endpoints support pagination using:
- `limit` (integer, default: 20): Number of items per page
- `skip` (integer, default: 0): Number of items to skip
- `sort_by` (string, default: "created_at"): Field to sort by
- `sort_order` (integer, default: -1): Sort direction (1: ascending, -1: descending)

### Rate Limiting
The API implements rate limiting to ensure fair usage. Limits are:
- 100 requests per minute per IP address
- 1000 requests per hour per user

### Best Practices
1. Always handle streaming responses appropriately
2. Include user_id when available for better authorization
3. Use appropriate error handling for all requests
4. Implement proper retry logic for 5xx errors
5. Cache frequently accessed data when possible
