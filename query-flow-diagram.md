# RAG Chatbot Query Flow Diagram

## Visual Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                   FRONTEND                                      │
│                              (index.html, script.js)                            │
└─────────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       │ User types query
                                       │ & clicks Send/Enter
                                       ▼
                        ┌──────────────────────────────┐
                        │   sendMessage() triggered    │
                        │   script.js:45-72            │
                        └──────────────────────────────┘
                                       │
                                       │ POST /api/query
                                       │ {query: "...", session_id: "..."}
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              BACKEND API LAYER                                  │
│                                  (app.py)                                       │
│                                                                                 │
│   ┌─────────────────────────────────────────────────────────────────────┐     │
│   │  @app.post("/api/query")                                            │     │
│   │  async def query_documents(request)                                 │     │
│   │      app.py:56-74                                                   │     │
│   │                                                                     │     │
│   │  • Validate session_id or create new                               │     │
│   │  • Call rag_system.query(query, session_id)                        │     │
│   │  • Return {answer, sources, session_id}                            │     │
│   └─────────────────────────────────────────────────────────────────────┘     │
│                                       │                                         │
└───────────────────────────────────────┼─────────────────────────────────────────┘
                                        │
                                        │ Orchestrate RAG
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           RAG SYSTEM ORCHESTRATOR                               │
│                              (rag_system.py)                                    │
│                                                                                 │
│   ┌─────────────────────────────────────────────────────────────────────┐     │
│   │  def query(query, session_id)                                       │     │
│   │      rag_system.py:102-140                                          │     │
│   │                                                                     │     │
│   │  ┌─────────────────────────────────────────────────────────┐      │     │
│   │  │ 1. Get Conversation History                             │      │     │
│   │  │    session_manager.get_conversation_history()           │      │     │
│   │  │    • Retrieves last 2 Q&A pairs                         │      │     │
│   │  │    • Formats for Claude context                         │      │     │
│   │  └─────────────────────────────────────────────────────────┘      │     │
│   │                          ↓                                         │     │
│   │  ┌─────────────────────────────────────────────────────────┐      │     │
│   │  │ 2. Generate AI Response                                 │      │     │
│   │  │    ai_generator.generate_response()                     │      │     │
│   │  │    • Pass conversation history                          │      │     │
│   │  │    • Pass available tools                               │      │     │
│   │  └─────────────────────────────────────────────────────────┘      │     │
│   │                          ↓                                         │     │
│   │  ┌─────────────────────────────────────────────────────────┐      │     │
│   │  │ 3. Extract Sources                                      │      │     │
│   │  │    tool_manager.get_last_sources()                      │      │     │
│   │  └─────────────────────────────────────────────────────────┘      │     │
│   │                          ↓                                         │     │
│   │  ┌─────────────────────────────────────────────────────────┐      │     │
│   │  │ 4. Save Exchange                                        │      │     │
│   │  │    session_manager.add_exchange()                       │      │     │
│   │  └─────────────────────────────────────────────────────────┘      │     │
│   └─────────────────────────────────────────────────────────────────────┘     │
│                                       │                                         │
└───────────────────────────────────────┼─────────────────────────────────────────┘
                                        │
                                        │ Generate response
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                             AI GENERATION LAYER                                 │
│                            (ai_generator.py)                                    │
│                                                                                 │
│   ┌─────────────────────────────────────────────────────────────────────┐     │
│   │  def generate_response(query, history, tools)                       │     │
│   │      ai_generator.py:35-135                                         │     │
│   │                                                                     │     │
│   │  ┌──────────────────────────────────────────────────┐             │     │
│   │  │  INITIAL CLAUDE API CALL                         │             │     │
│   │  │                                                  │             │     │
│   │  │  client.messages.create(                        │             │     │
│   │  │      model="claude-sonnet-4-20250514",         │             │     │
│   │  │      messages=[{"role":"user","content":query}],│             │     │
│   │  │      tools=[search_course_content_tool],       │             │     │
│   │  │      tool_choice={"type": "auto"}              │             │     │
│   │  │  )                                              │             │     │
│   │  └──────────────────────────────────────────────────┘             │     │
│   │                          │                                         │     │
│   │                          │                                         │     │
│   │         ┌────────────────┴────────────────┐                       │     │
│   │         │                                 │                       │     │
│   │         ▼                                 ▼                       │     │
│   │  ┌─────────────┐                  ┌──────────────┐              │     │
│   │  │  General    │                  │ Course-      │              │     │
│   │  │  Question   │                  │ Specific     │              │     │
│   │  │             │                  │ Question     │              │     │
│   │  │  No tool    │                  │              │              │     │
│   │  │  needed     │                  │ Tool use     │              │     │
│   │  └─────────────┘                  │ requested    │              │     │
│   │         │                          └──────────────┘              │     │
│   │         │                                 │                       │     │
│   │         │                                 ▼                       │     │
│   │         │                    ┌──────────────────────────┐        │     │
│   │         │                    │ _handle_tool_execution() │        │     │
│   │         │                    │                          │        │     │
│   │         │                    │ • Execute search tool    │        │     │
│   │         │                    │ • Get results            │        │     │
│   │         │                    │ • Call Claude again      │        │     │
│   │         │                    │   with tool results      │        │     │
│   │         │                    └──────────────────────────┘        │     │
│   │         │                                 │                       │     │
│   │         └─────────────┬───────────────────┘                       │     │
│   │                       ▼                                           │     │
│   │              ┌─────────────────┐                                 │     │
│   │              │ Final Response  │                                 │     │
│   │              │ Text            │                                 │     │
│   │              └─────────────────┘                                 │     │
│   └─────────────────────────────────────────────────────────────────────┘     │
│                                       │                                         │
└───────────────────────────────────────┼─────────────────────────────────────────┘
                                        │
                                        │ Execute tool
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              TOOL EXECUTION LAYER                               │
│                              (search_tools.py)                                  │
│                                                                                 │
│   ┌─────────────────────────────────────────────────────────────────────┐     │
│   │  CourseSearchTool.execute(query, course_name, lesson_number)       │     │
│   │      search_tools.py:60-95                                          │     │
│   │                                                                     │     │
│   │  • Parse tool parameters                                           │     │
│   │  • Call vector_store.search()                                      │     │
│   │  • Format results with metadata                                    │     │
│   │  • Track sources for UI display                                    │     │
│   └─────────────────────────────────────────────────────────────────────┘     │
│                                       │                                         │
└───────────────────────────────────────┼─────────────────────────────────────────┘
                                        │
                                        │ Search content
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            VECTOR STORE LAYER                                   │
│                            (vector_store.py)                                    │
│                                                                                 │
│   ┌─────────────────────────────────────────────────────────────────────┐     │
│   │  def search(query, course_name, lesson_number)                      │     │
│   │      vector_store.py:61-100                                         │     │
│   │                                                                     │     │
│   │  ┌─────────────────────────────────────────────────────────┐      │     │
│   │  │ STEP 1: Resolve Course Name                             │      │     │
│   │  │                                                         │      │     │
│   │  │  course_catalog.query(course_name)                     │      │     │
│   │  │  • Semantic search in course titles                    │      │     │
│   │  │  • "MCP" → "MCP: Build Rich-Context AI Apps..."       │      │     │
│   │  └─────────────────────────────────────────────────────────┘      │     │
│   │                          ↓                                         │     │
│   │  ┌─────────────────────────────────────────────────────────┐      │     │
│   │  │ STEP 2: Build Filters                                   │      │     │
│   │  │                                                         │      │     │
│   │  │  filter_dict = {                                       │      │     │
│   │  │      "course_title": resolved_course,                 │      │     │
│   │  │      "lesson_number": lesson_number                   │      │     │
│   │  │  }                                                     │      │     │
│   │  └─────────────────────────────────────────────────────────┘      │     │
│   │                          ↓                                         │     │
│   │  ┌─────────────────────────────────────────────────────────┐      │     │
│   │  │ STEP 3: Semantic Search                                 │      │     │
│   │  │                                                         │      │     │
│   │  │  course_content.query(                                 │      │     │
│   │  │      query_texts=[query],                             │      │     │
│   │  │      n_results=5,                                      │      │     │
│   │  │      where=filter_dict                                 │      │     │
│   │  │  )                                                     │      │     │
│   │  └─────────────────────────────────────────────────────────┘      │     │
│   └─────────────────────────────────────────────────────────────────────┘     │
│                                       │                                         │
└───────────────────────────────────────┼─────────────────────────────────────────┘
                                        │
                                        │ Vector similarity search
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              CHROMADB LAYER                                     │
│                          (Persistent Vector DB)                                 │
│                                                                                 │
│   ┌───────────────────────────────────────────────────────────────────┐       │
│   │                    COLLECTION: course_catalog                     │       │
│   │                                                                   │       │
│   │  Documents: Course titles                                        │       │
│   │  Metadata:  {instructor, course_link, lessons_json}              │       │
│   │  Purpose:   Resolve partial course names semantically            │       │
│   │                                                                   │       │
│   │  Example:                                                        │       │
│   │  Query: "MCP"                                                    │       │
│   │  Returns: "MCP: Build Rich-Context AI Apps with Anthropic"      │       │
│   └───────────────────────────────────────────────────────────────────┘       │
│                                                                                 │
│   ┌───────────────────────────────────────────────────────────────────┐       │
│   │                    COLLECTION: course_content                     │       │
│   │                                                                   │       │
│   │  Documents: Text chunks (800 chars, 100 overlap)                 │       │
│   │  Metadata:  {course_title, lesson_number, chunk_index}           │       │
│   │  Embeddings: all-MiniLM-L6-v2 (384 dimensions)                  │       │
│   │                                                                   │       │
│   │  Process:                                                        │       │
│   │  1. Query → Embedding (384-dim vector)                          │       │
│   │  2. Cosine similarity with all chunks                           │       │
│   │  3. Apply metadata filters                                       │       │
│   │  4. Return top 5 results with:                                  │       │
│   │     • document text                                             │       │
│   │     • metadata (course, lesson)                                 │       │
│   │     • similarity score                                          │       │
│   └───────────────────────────────────────────────────────────────────┘       │
│                                                                                 │
│   Storage Location: ./chroma_db/                                               │
│   Embedding Model: sentence-transformers/all-MiniLM-L6-v2                      │
└─────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        │ Results bubble back up
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           RESPONSE ASSEMBLY                                     │
│                                                                                 │
│   ChromaDB Results                                                              │
│         ↓                                                                       │
│   Tool Manager (formats & extracts sources)                                     │
│         ↓                                                                       │
│   Claude (synthesizes into natural language)                                    │
│         ↓                                                                       │
│   Session Manager (saves conversation)                                          │
│         ↓                                                                       │
│   API Response: {                                                               │
│       "answer": "Based on the course materials...",                             │
│       "sources": ["MCP Course - Lesson 1", "MCP Course - Lesson 3"],           │
│       "session_id": "session_123"                                               │
│   }                                                                             │
└─────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        │ JSON response
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND DISPLAY                                   │
│                            (script.js:73-110)                                   │
│                                                                                 │
│   ┌─────────────────────────────────────────────────────────────────────┐     │
│   │  1. Remove loading animation                                        │     │
│   │  2. Create message bubble with answer                               │     │
│   │  3. Parse markdown formatting                                       │     │
│   │  4. Add collapsible sources section                                 │     │
│   │  5. Display each source as citation                                 │     │
│   │  6. Scroll to latest message                                        │     │
│   │  7. Store session_id for next query                                 │     │
│   └─────────────────────────────────────────────────────────────────────┘     │
│                                                                                 │
│                           USER SEES RESPONSE                                    │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Summary

```
USER INPUT
    ↓
JavaScript (script.js)
    ↓
HTTP POST /api/query
    ↓
FastAPI Endpoint (app.py)
    ↓
RAG Orchestrator (rag_system.py)
    ├─→ Session Manager (get history)
    ├─→ AI Generator (generate response)
    │       ├─→ Claude API (analyze query)
    │       │       ├─→ Direct answer (general knowledge)
    │       │       └─→ Tool call (course-specific)
    │       │               ↓
    │       └─→ Tool Manager (execute search)
    │               ↓
    │           Search Tool (search_tools.py)
    │               ↓
    │           Vector Store (vector_store.py)
    │               ├─→ Resolve course name (course_catalog)
    │               └─→ Search content (course_content)
    │                       ↓
    │                   ChromaDB (semantic search)
    │                       ↓
    │                   Top 5 relevant chunks
    │                       ↓
    │           [Results flow back through chain]
    │                       ↓
    │           Claude (synthesize results)
    │                       ↓
    └─→ Session Manager (save exchange)
    ↓
Extract sources
    ↓
Return {answer, sources, session_id}
    ↓
HTTP Response
    ↓
JavaScript renders UI
    ↓
USER SEES ANSWER + SOURCES
```

---

## Component Interaction Map

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Frontend   │────▶│   FastAPI    │────▶│ RAG System   │
│  (Browser)   │◀────│   (app.py)   │◀────│ Orchestrator │
└──────────────┘     └──────────────┘     └──────────────┘
                                                   │
                    ┌──────────────────────────────┼──────────────────────────────┐
                    │                              │                              │
                    ▼                              ▼                              ▼
           ┌─────────────────┐         ┌──────────────────┐          ┌──────────────────┐
           │ Session Manager │         │  AI Generator    │          │   Tool Manager   │
           │                 │         │  (Claude API)    │          │                  │
           │ • History       │         │                  │          │ • Tool registry  │
           │ • Context       │         │ • Tool use       │          │ • Execution      │
           └─────────────────┘         │ • Synthesis      │          │ • Source track   │
                                       └──────────────────┘          └──────────────────┘
                                                                              │
                                                                              ▼
                                                                    ┌──────────────────┐
                                                                    │  Search Tool     │
                                                                    │                  │
                                                                    │ • Parameter      │
                                                                    │   extraction     │
                                                                    │ • Result format  │
                                                                    └──────────────────┘
                                                                              │
                                                                              ▼
                                                                    ┌──────────────────┐
                                                                    │  Vector Store    │
                                                                    │                  │
                                                                    │ • Course match   │
                                                                    │ • Filtering      │
                                                                    │ • Search         │
                                                                    └──────────────────┘
                                                                              │
                                                                              ▼
                                                                    ┌──────────────────┐
                                                                    │    ChromaDB      │
                                                                    │                  │
                                                                    │ • Embeddings     │
                                                                    │ • Similarity     │
                                                                    │ • Persistence    │
                                                                    └──────────────────┘
```

---

## Timing Breakdown (Typical Query)

```
Total Time: ~2-4 seconds

┌─────────────────────────────────────────────────────────────┐
│ Phase                              │ Time       │ %         │
├─────────────────────────────────────────────────────────────┤
│ Frontend → Backend (HTTP)          │ ~50ms      │ 2%        │
│ Session retrieval                  │ ~10ms      │ <1%       │
│ First Claude API call              │ ~800ms     │ 30%       │
│ Tool execution (if needed):        │            │           │
│   ├─ Vector search                 │ ~100ms     │ 4%        │
│   └─ Second Claude call            │ ~1200ms    │ 46%       │
│ Session save                       │ ~10ms      │ <1%       │
│ Backend → Frontend (HTTP)          │ ~50ms      │ 2%        │
│ Frontend rendering                 │ ~100ms     │ 4%        │
└─────────────────────────────────────────────────────────────┘

Note: Tool-less queries skip search steps (~1.5s total)
      Tool-based queries include search (~2.5-4s total)
```

---

## Key Files Reference

- **Frontend**: [frontend/script.js](frontend/script.js), [frontend/index.html](frontend/index.html)
- **API Entry**: [backend/app.py](backend/app.py)
- **RAG Core**: [backend/rag_system.py](backend/rag_system.py)
- **AI Layer**: [backend/ai_generator.py](backend/ai_generator.py)
- **Tools**: [backend/search_tools.py](backend/search_tools.py)
- **Vector DB**: [backend/vector_store.py](backend/vector_store.py)
- **Sessions**: [backend/session_manager.py](backend/session_manager.py)
- **Models**: [backend/models.py](backend/models.py)
- **Config**: [backend/config.py](backend/config.py)
