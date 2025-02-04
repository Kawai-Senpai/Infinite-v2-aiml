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
