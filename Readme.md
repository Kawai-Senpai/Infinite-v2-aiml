# Infinite v2 AI/ML

An advanced conversational AI system with multi-model support, RAG capabilities, dynamic tool usage, and persistent memory.

## Project Structure

```
│   .env
│   .env.development
│   .env.production
│   .gitignore
│   .gitmessage
│   config.json
│   Readme.md
│   requirements.txt
│
├───cache
│       Readme.md
│
├───database
│       chroma.py
│       mongo.py
│
├───debug
│       Readme.md
│
├───keys
│       keys.py
│
├───llm
│       agents.py
│       chat.py
│       decision.py
│       prompts.py
│       schemas.py
│       sessions.py
│       tools.py
│
├───rag
│       file_handler.py
│       file_management.py
│       file_processor.py
│
└───utilities
        garbage.py
        s3_loader.py
        save_json.py
        scraping.py
```

## Core Features

### Multi-Model Support
- OpenAI models (GPT-4 and variants)
- Cohere models (Command-R series)
- Model-agnostic architecture for easy expansion
- Automatic model routing and response handling

### RAG (Retrieval Augmented Generation)
- Multiple collection support per agent
- Automatic context retrieval and integration
- Vector database integration (ChromaDB)
- Support for various document types
- Smart chunking strategies:
  - Sentence-based chunking with overlap
  - Character-based chunking for complex documents
  - Automatic chunk size optimization

### Dynamic Tool System
- Automatic tool selection using AI
- Multiple tools per request
- Parallel tool execution
- Current tools:
  - Web search (DuckDuckGo)
  - More tools can be easily added
- Tool response integration into context

### Memory System
- Long-term information storage
- Automatic importance analysis
- Smart memory management
- Size-limited memory with configurable limits
- Persistent across sessions
- Automatic memory integration in responses

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

### Streaming Support
- Real-time response generation
- Progress accumulation
- Automatic history updates
- Support for both OpenAI and Cohere streaming

### Agent System
- Custom agent creation
- Role-based behavior
- Configurable capabilities
- Rule enforcement
- Multiple collections per agent
- Memory management
- Tool access control

### Session Management
- Persistent chat sessions
- History management
- Context preservation
- Configurable history limits
- Multi-user support

## Advanced Features

### Context Management
- Smart context retrieval
- Relevance-based sorting
- Multiple collection search
- Automatic context integration
- Memory-context fusion

### AWS Integration
- S3 storage support
- Document caching
- Efficient file handling
- Automatic cleanup

### Logging and Monitoring
- Detailed logging system
- Development/Production modes
- Performance monitoring
- Error tracking
- Debug capabilities

### Configuration System
- JSON-based configuration
- Environment-specific settings
- Model configurations
- System constraints
- Easy customization

### Security Features
- API key management
- Role-based access
- System agent protection
- Secure file handling

## Technical Specifications

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
1. Request analysis
2. Tool selection
3. Parallel execution
4. Response formatting
5. Context integration

### Memory Processing Pipeline
1. Content analysis
2. Importance evaluation
3. Memory storage
4. Size management
5. Context integration

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
