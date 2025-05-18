# SurfSense Backend RAG Architecture

This document outlines the architecture of the Retrieval Augmented Generation (RAG) application within the SurfSense backend. It's designed to help new engineers understand the system components, data flow, and key technologies used.

## 1. Overview

The SurfSense RAG system is designed to answer user queries by retrieving relevant information from a variety of connected data sources and then using a Large Language Model (LLM) to generate a comprehensive answer. It leverages several modern tools and libraries to achieve this, including FastAPI, Langchain, PGVector, and various LLM providers. For queries requiring up-to-the-minute information, it can also leverage real-time web search capabilities.

The system can be broadly divided into the following key areas:

-   **Data Ingestion and Processing:** How data gets into the system and is prepared for retrieval.
-   **Storage:** Where the processed data and vector embeddings are stored.
-   **Retrieval:** How relevant information is found based on a user's query. This includes retrieval from internal knowledge bases and optionally from live web searches.
-   **Augmentation and Generation:** How the retrieved information is used with an LLM to generate an answer.
-   **API and Application Layer:** How the system exposes its functionality to users/clients.
-   **Configuration:** How the system is configured.

## 2. Core Technologies and Libraries

-   **Web Framework:** FastAPI (`app/app.py`, `main.py`)
-   **LLM Orchestration:** Langchain, LangGraph (`app/agents/`, `app/prompts/`)
-   **LLM Interface:** LiteLLM (via `ChatLiteLLM` in `app/config/__init__.py`, also used for STT/TTS)
-   **Embedding & Chunking:** Chonkie (`app/config/__init__.py`, using `RecursiveChunker` and `CodeChunker`)
-   **Re-ranking:** Rerankers library (`app/config/__init__.py`)
-   **Vector Store:** PostgreSQL with PGVector extension (`app/db.py`, `app/config/__init__.py`)
-   **Primary Database:** PostgreSQL
-   **Document Parsing:** Unstructured.io (configured via API key)
-   **Web Crawling (Data Ingestion):** Firecrawl (configured via API key in `app/config/__init__.py`)
-   **Real-time Web Search (Agent Tool):** Tavily API (used via `TavilyClient` in `app/utils/connector_service.py`)
-   **ORM:** SQLAlchemy (`app/db.py`)
-   **Database Migrations:** Alembic (`alembic/`, `alembic.ini`)
-   **ASGI Server:** Uvicorn (`main.py`)
-   **Authentication:** `fastapi-users` (JWT, Google OAuth)
-   **Audio Processing:** FFmpeg (system dependency, managed via `static-ffmpeg`)
-   **Speech-to-Text (STT) / Text-to-Speech (TTS):** Via LiteLLM, configured in `app/config/__init__.py`

## 3. Detailed Architecture

### 3.1. Data Ingestion and Processing

This pipeline is responsible for fetching data from various sources, processing it, generating embeddings, and storing it for retrieval.

-   **Data Sources:**
    -   **Connectors (`app/connectors/`):** Modules for fetching data from external services:
        -   `github_connector.py`: GitHub repositories.
        -   `notion_history.py`: Notion workspaces.
        -   `slack_history.py`: Slack channels.
        -   `linear_connector.py`: Linear projects/issues.
    -   **Document Uploads:** Users can likely upload documents (e.g., PDFs, TXT files) via API endpoints (see `app/routes/documents_routes.py`).
    -   **Podcast Feeds:** Support for ingesting podcast data (see `app/routes/podcasts_routes.py`). This involves audio fetching, transcription via STT services, and potentially other processing by the Podcaster Agent.
    -   **Web Content (Ingestion):** `Firecrawl` (configured via `FIRECRAWL_API_KEY` in `app/config/__init__.py`) is used for scraping and ingesting content from websites into the knowledge base.
-   **Parsing:**
    -   `Unstructured.io` (configured via `UNSTRUCTURED_API_KEY` in `app/config/__init__.py`) is likely used to parse diverse file formats into clean text.
-   **Audio Processing (for Podcasts):**
    -   `FFmpeg` is a core dependency for handling audio files. Its presence is checked and managed by `app/config/__init__.py`.
    -   **Speech-to-Text (STT):** Configured STT services (via LiteLLM, see `STT_SERVICE` in `app/config/__init__.py`) are used to transcribe podcast audio into text for indexing and RAG.
-   **Chunking:**
    -   The `chonkie.RecursiveChunker` (configured in `app/config/__init__.py`) is the default for splitting processed text into smaller, manageable chunks.
    -   A specialized `chonkie.CodeChunker` is available for handling source code, ensuring syntax-aware chunking.
-   **Embedding Generation:**
    -   `chonkie.AutoEmbeddings` (configured in `app/config/__init__.py`) uses a specified embedding model (e.g., from HuggingFace, SentenceTransformers) to convert text chunks into vector embeddings.
-   **Indexing Tasks (`app/tasks/`):**
    -   `connectors_indexing_tasks.py`: Contains background tasks (likely using Celery or FastAPI's `BackgroundTasks`) to manage the asynchronous indexing of data from the connectors.
    -   `podcast_tasks.py`: Dedicated background tasks for podcast processing, including fetching new episodes, triggering transcription (STT), and indexing the transcribed content. This likely works in conjunction with the `Podcaster Agent`.
    -   These tasks orchestrate the fetching, parsing, chunking, embedding, and storage of data.

### 3.2. Storage

-   **Primary Data Store (PostgreSQL):**
    -   Managed by `app/db.py` using SQLAlchemy.
    -   Stores original text content, metadata associated with the data (e.g., source, document ID, user information), user accounts, and other relational data.
    -   Database schema migrations are handled by Alembic.
-   **Vector Store (PostgreSQL with PGVector):**
    -   The `PGVector` extension is used within the PostgreSQL database to store and query vector embeddings.
    -   The `app/config/__init__.py` includes a validation check for embedding dimensions against PGVector's limits.

### 3.3. Retrieval

This is the "R" in RAG. When a user query is received, the system retrieves the most relevant information chunks from its internal knowledge base and can also perform real-time web searches if needed.

-   **Internal Knowledge Base Retrieval (`app/retriver/`):**
    -   `chunks_hybrid_search.py`: Implements hybrid search for individual text chunks from indexed sources.
    -   `documents_hybrid_search.py`: Implements hybrid search at a document level, potentially aggregating chunk scores or searching document-level embeddings.
    -   **Hybrid Search:** This typically combines:
        -   **Dense Retrieval (Vector Search):** Similarity search on vector embeddings stored in PGVector.
        -   **Sparse Retrieval (Keyword Search):** Techniques like BM25/TF-IDF, possibly implemented using PostgreSQL's full-text search capabilities or an external search engine.
-   **Re-ranking:**
    -   The `rerankers` library (configured in `app/config/__init__.py` with a specific model like Cohere Rerank or Cross-Encoders) is used to re-order the initial set of retrieved chunks (from internal sources or web search). Re-ranking improves relevance by applying a more computationally intensive model to a smaller set of candidates.
-   **Real-time Web Search (Tavily):**
    -   The system can augment its knowledge with real-time information from the web using the Tavily API.
    -   As seen in `app/utils/connector_service.py`, the `TavilyClient` is used to perform web searches based on the user's query.
    -   The `TAVILY_API_KEY` is managed through specific connector configurations (e.g., `tavily_connector.config.get("TAVILY_API_KEY")`), indicating a potentially more granular configuration approach for such external tools than the global `app/config/__init__.py`.
    -   This capability is crucial for answering questions about current events or topics not yet ingested into the primary knowledge base.

### 3.4. Augmentation and Generation (The "AG" in RAG)

Once relevant chunks are retrieved (from internal storage and/or live web search) and re-ranked, they are used to augment the user's query and generate a response using an LLM.

-   **Prompt Engineering (`app/prompts/`, `app/agents/researcher/sub_section_writer/prompts.py`, `app/agents/podcaster/prompts.py`):**
    -   `Langchain PromptTemplate`s are used to structure the input for the LLM.
    -   The prompt typically includes:
        -   The original user query.
        -   The retrieved context (the re-ranked chunks from internal and/or web sources).
        -   Instructions for the LLM on how to use the context to answer the query, desired output format, tone, etc. (e.g., `SUMMARY_PROMPT_TEMPLATE` in `app/prompts/__init__.py`).
-   **LLM Interaction:**
    -   `ChatLiteLLM` from `langchain_community.chat_models` (configured in `app/config/__init__.py`) provides a unified interface to various LLMs (OpenAI, Anthropic, etc., specified via environment variables like `LONG_CONTEXT_LLM`, `FAST_LLM`, `STRATEGIC_LLM`). Each LLM configuration now supports an optional `API_BASE` for custom endpoints.
-   **Agentic Behavior (LangGraph - `app/agents/`):**
    -   The system employs sophisticated agents built using LangGraph for complex task execution. LangGraph enables stateful, multi-step workflows with dynamic routing. These agents can decide whether to query internal data, perform a web search via Tavily, or use other tools.
    -   **Researcher Agent (`app/agents/researcher/`):**
        -   Indicated by `graph.py`, `nodes.py`, and `state.py` within `app/agents/researcher/` and its `sub_section_writer/` subdirectory.
        -   Likely responsible for decomposing complex user queries, orchestrating retrieval (from internal sources or triggering Tavily web searches), and synthesizing comprehensive answers.
    -   **Podcaster Agent (`app/agents/podcaster/`):**
        -   A new agent also built with LangGraph (contains `graph.py`, `nodes.py`, `state.py`, `prompts.py`).
        -   Likely handles tasks specific to podcasts, such as processing transcripts, generating summaries, and answering questions about podcast content. It could also potentially leverage Tavily for related web searches.
        -   Potentially utilizing Text-to-Speech (TTS) services (configured via `TTS_SERVICE` in `app/config/__init__.py`) for generating audio outputs related to podcasts.
    -   **LangGraph Workflow (General Principles):**
        -   **State Management:** Each agent maintains its current state (e.g., query, retrieved data, intermediate results) in a defined state object (`state.py`).
        -   **Nodes & Edges:** Operations are performed by nodes (`nodes.py`), and the flow is controlled by edges defined in the graph (`graph.py`), allowing for conditional logic and loops.
        -   This allows for complex reasoning, multi-step information gathering (including deciding when to use tools like Tavily), and structured output generation.
    -   **Visualization:** The `draw.py` script in the project root can be used to generate Mermaid diagrams of the LangGraph structures for the `researcher_graph` and `sub_section_writer_graph`, aiding in understanding their flow.

### 3.5. API and Application Layer

The RAG system's functionalities are exposed through a FastAPI web application.

-   **Application Setup (`app/app.py`, `main.py`):**
    -   `main.py` runs the Uvicorn ASGI server.
    -   `app/app.py` initializes the FastAPI application, including:
        -   CORS middleware.
        -   Database initialization (`create_db_and_tables`).
        -   Authentication routers using `fastapi-users` for JWT and Google OAuth.
-   **API Endpoints (`app/routes/`):**
    -   Routers define specific API endpoints prefixed with `/api/v1` (and `/auth` for authentication).
    -   `chats_routes.py`: Handles chat interactions, which form the primary interface to the RAG pipeline. Users send queries, and the system returns LLM-generated responses based on retrieved context.
    -   `documents_routes.py`: Endpoints for managing documents (e.g., uploading, listing, deleting, possibly triggering summarization or Q&A on specific documents).
    -   `podcasts_routes.py`: Endpoints specific to handling podcast data.
    -   `search_source_connectors_routes.py`: Endpoints for managing data source connectors (e.g., initiating indexing for GitHub, Notion, Slack, Linear).
    -   `search_spaces_routes.py`: Potentially for managing different search contexts or "spaces" (e.g., restricting search to a specific project or data source).

### 3.6. Configuration (`app/config/__init__.py` and connector-specific configs)

-   Centralized global configuration is primarily managed by the `Config` class in `app/config/__init__.py`.
-   Loads settings from a `.env` file at the project root.
-   Defines:
    -   Database URL.
    -   LLM models to use (e.g., `LONG_CONTEXT_LLM`, `FAST_LLM`, `STRATEGIC_LLM`). Each LLM now supports an optional `API_BASE` for flexibility.
    -   Embedding model (`EMBEDDING_MODEL`).
    -   Chunker configuration: `RecursiveChunker` as default, with `CodeChunker` available.
    -   Reranker model (`RERANKERS_MODEL_NAME`).
    -   Global API keys for external services (Google OAuth, Unstructured, Firecrawl).
    -   JWT secret key.
    -   STT (`STT_SERVICE`, `STT_SERVICE_API_BASE`) and TTS (`TTS_SERVICE`, `TTS_SERVICE_API_BASE`) service configurations, often managed via LiteLLM.
    -   Automatic `ffmpeg` path management for audio processing.
-   Initializes global instances of `ChatLiteLLM`, `AutoEmbeddings`, `RecursiveChunker`, `CodeChunker`, and `Reranker`.
-   **Connector-Specific Configuration:** Some external tools or services, like the Tavily API client (used in `app/utils/connector_service.py`), may have their API keys or other settings managed through their respective connector configurations (e.g., `tavily_connector.config.get("TAVILY_API_KEY")`). This allows for more modular or granular control over specific tool integrations. These configurations might still draw values from environment variables but are accessed differently.

## 4. Data Flow (Example: Chat Query)

1.  **User Query:** A user sends a query via an API endpoint (e.g., defined in `chats_routes.py`).
2.  **Authentication:** The request is authenticated.
3.  **Retrieval & Augmentation Planning (by Agent/Service):**
    a.  The system (often an Agent) decides on a strategy: query internal knowledge, perform a live web search, or both.
    b.  **Internal Retrieval:** If querying internal knowledge, the query is passed to the retrieval system (`app/retriver/`). Hybrid search (vector + keyword) is performed against the PGVector database.
    c.  **Real-time Web Search (Optional):** If current information is needed, the system (e.g., via `app/utils/connector_service.py` or an agent tool) uses Tavily to search the web using the user query.
    d.  **Re-ranking:** The retrieved chunks/results (from internal sources and/or Tavily) are re-ranked by the `rerankers` module.
4.  **Contextual Augmentation:**
    a.  The top-k re-ranked chunks (context) are selected.
    b.  A prompt is constructed using a `PromptTemplate`, combining the user's query, the comprehensive retrieved context, and specific instructions.
5.  **Generation:**
    a.  The augmented prompt is sent to an LLM (e.g., a configured `FAST_LLM` or `STRATEGIC_LLM`) via `ChatLiteLLM`.
    b.  If a complex agent like the "Researcher Agent" (`app/agents/researcher/`) is invoked, this step might involve multiple LLM calls orchestrated by its LangGraph to break down the problem, gather more information (from internal or web sources), and synthesize an answer. Similar agent-based processing would apply for podcast-specific queries handled by the "Podcaster Agent".
6.  **Response:** The LLM's generated response is sent back to the user via the API.

## 5. Key Directories Recap

-   `surfsense_backend/app/`: Core application logic.
    -   `agents/`: Langchain agents, including LangGraph implementations for `researcher/` and `podcaster/`.
    -   `config/`: Global application configuration.
    -   `connectors/`: Data source connectors (includes `github_connector.py`, `notion_history.py`, `slack_history.py`, `linear_connector.py`). Also, connector-specific configurations might reside here or be managed by services using these connectors.
    -   `prompts/`: Prompt templates.
    -   `retriver/`: Retrieval logic for internal knowledge base (hybrid search). The directory name `retriver` is a typo in the codebase.
    -   `routes/`: API endpoint definitions.
    -   `schemas/`: Pydantic data models.
    -   `tasks/`: Background indexing and processing tasks (includes `connectors_indexing_tasks.py`, `podcast_tasks.py`).
    -   `utils/`: Utility functions, including services like `connector_service.py` that might integrate tools like Tavily.
    -   `app.py`: FastAPI application setup.
    -   `db.py`: Database setup and ORM models.
-   `surfsense_backend/alembic/`: Database migration scripts.
-   `surfsense_backend/main.py`: Application entry point (Uvicorn runner).
-   `surfsense_backend/.env`: (Not in repo, but crucial) Environment variables for configuration.
-   `surfsense_backend/draw.py`: Utility script to visualize LangGraph agent structures.

This architecture provides a robust foundation for building and extending RAG capabilities. Understanding these components and their interactions will be key to contributing effectively. 
