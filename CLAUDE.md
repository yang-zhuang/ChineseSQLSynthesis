# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Chinese text-to-SQL data synthesis pipeline that converts CSpider database schemas into high-quality training data. The pipeline follows a modular sequential architecture that transforms raw SQLite databases into validated question-SQL pairs through multiple LLM-powered stages.

## Common Commands

### Database Processing
```bash
# Step 1: Merge CSpider SQLite databases into a single database
cd src/data_synthesis/database_merge/tools
python merge_sqlite_databases.py

# Analyze database schemas and relationships
python analyze_schemas.py
python analyze_sqlite_tables.py
python test_merge_logic.py
```

### Data Enhancement (Steps 2-5)
```bash
# Step 2: Add Chinese comments to database schemas
cd src/data_synthesis/add_database_comments
python generate_ddl_comment_prompts.py
python generate_llm_responses.py.py
python postprocess_llm_responses.py
python finalize_sql_outputs.py

# Step 3: Generate table summaries and business context
cd src/data_synthesis/generate_table_summaries
python generate_ddl_summary_prompts.py
python generate_llm_responses.py.py
python postprocess_llm_responses.py
python finalize_sql_outputs.py

# Step 4: Use vector models to find similar tables
cd src/data_synthesis/vector_table_similarity
cd vector && python huggingface_embeddings.py  # or vllm_embeddings.py
cd retrieve && python vector_search_engine.py
cd .. && python retrieve_similar_tables_by_summary.py

# Step 5: Find appropriate SQLite functions for similar tables
cd src/data_synthesis/match_sqlite_functions
python 构造schema适配的函数名称.py
python generate_sqlite_function_compatibility_prompts.py
python generate_llm_responses.py.py
python postprocess_llm_responses.py
python finalize_sql_outputs.py
python 判断遗漏了哪些函数.py
```

### Pipeline Execution (Steps 6-8)
The pipeline follows this sequential pattern. Each stage has the same processing pattern:

```bash
# Step 6: SQL Synthesis
cd src/data_synthesis/sql_synthesis
python generate_sql_synthesis_prompt.py    # Generate prompts
python generate_llm_responses.py.py        # Call LLM APIs
python postprocess_llm_responses.py        # Clean outputs
python finalize_sql_outputs.py             # Create final structured outputs

# Step 7: Question Synthesis
cd src/data_synthesis/question_synthesis
python generate_question_synthesis_prompts_zh.py
python generate_llm_responses.py.py
python postprocess_llm_responses.py
python finalize_sql_outputs.py

# Step 8: Query Validation (Final Step)
cd src/data_synthesis/sql_query_match_validation
python generate_prompts_zh.py
python generate_llm_responses.py.py
python postprocess_llm_responses.py
python finalize_sql_outputs.py
```

## Architecture Overview

### Pipeline Stages (8 Sequential Steps)
1. **Database Merge**: Merge CSpider SQLite databases → Single `merged_cspider.sqlite`
2. **Add Comments**: Generate Chinese comments for tables and columns
3. **Generate Summaries**: Create business summaries and context for each table
4. **Vector Similarity**: Use embedding models to find 5 most similar tables per table
5. **Match Functions**: Map appropriate SQLite functions based on similar tables
6. **SQL Synthesis**: Generate diverse SQL queries using rich context
7. **Question Synthesis**: Convert SQL queries back to natural Chinese questions
8. **Query Validation**: Validate question-SQL pairs through semantic matching

Each step depends on the output of the previous step, creating a complete pipeline from raw databases to validated training data.

### Data Format Standards
- **Primary Format**: JSONL (JSON Lines) - each line is a complete data record
- **Record Structure**: DDL, sample data, annotations, prompts, LLM responses, metadata
- **Character Encoding**: UTF-8 throughout for Chinese text processing

### Module Processing Pattern
Each synthesis module follows the same 4-step pattern:
1. `generate_*_prompts*.py` - Create structured prompts with templates
2. `generate_llm_responses.py.py` - Call LLM APIs (OpenAI-compatible, local models)
3. `postprocess_llm_responses.py` - Clean and validate LLM outputs
4. `finalize_*_outputs.py` - Produce final structured data files

### Configuration Management
- **LLM Settings**: Model endpoints configured in each generator script (Qwen3-4B-AWQ, Qwen3-32B, etc.)
- **Template System**: Question styles (colloquial, formal, imperative, etc.) and complexity levels
- **Function Dictionary**: Comprehensive SQLite function descriptions with Chinese explanations

## Key Technical Details

### LLM Integration
- Uses OpenAI-compatible API endpoints for local models
- Primary model: Qwen3-30B-A3B via localhost:42434
- Supports concurrent processing with ThreadPoolExecutor
- Includes timeout and error handling for batch processing

### Database Schema Handling
- CSpider dataset compatibility (Chinese version of Spider dataset)
- Automatic table name conflict resolution during merging
- Foreign key constraint handling and schema validation
- Chinese comment generation for better LLM understanding

### Vector Search Integration
- Vector-based table similarity search for better function mapping
- Supports both HuggingFace and vLLM embeddings
- Used for finding semantically similar table structures

### Output Organization
- Each stage creates timestamped output directories
- Intermediate files preserved for debugging and resumption
- Final training data in standardized JSONL format
- Comprehensive logging and progress tracking

## Development Notes

- All processing scripts are designed to be resumable - they check for existing outputs before processing
- Chinese language processing throughout the pipeline
- Extensive error handling and validation at each stage
- Template-driven approach ensures consistency and reproducibility