# Task 3 Plan: The System Agent

## New tool: query_api
- Parameters: method, path, body (optional)
- Authenticates with LMS_API_KEY from environment
- Base URL from AGENT_API_BASE_URL (default: http://localhost:42002)
- Returns JSON with status_code and body

## Environment variables
- LMS_API_KEY — from .env.docker.secret
- AGENT_API_BASE_URL — optional, defaults to http://localhost:42002

## System prompt update
- Use list_files/read_file for wiki and source code questions
- Use query_api for live data questions (counts, scores, status)

## Benchmark strategy
- Run run_eval.py, fix failures one by one
