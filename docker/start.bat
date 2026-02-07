@echo off
REM FIS - Docker Infrastructure Startup Script for Windows
REM This script starts all required services and verifies they are healthy

echo ==================================================
echo Financial Intelligence Swarm - Infrastructure Setup
echo ==================================================

cd /d "%~dp0"

echo.
echo Starting Docker services...
docker-compose up -d

echo.
echo Waiting for services to start...
timeout /t 5 /nobreak > nul

echo.
echo Checking Neo4j...
:check_neo4j
curl -s http://localhost:7474 > nul 2>&1
if %errorlevel% neq 0 (
    echo Neo4j not ready, waiting...
    timeout /t 2 /nobreak > nul
    goto check_neo4j
)
echo Neo4j is running!

echo.
echo Checking Qdrant...
:check_qdrant
curl -s http://localhost:6333/health > nul 2>&1
if %errorlevel% neq 0 (
    echo Qdrant not ready, waiting...
    timeout /t 2 /nobreak > nul
    goto check_qdrant
)
echo Qdrant is running!

echo.
echo All services are running!
echo.
echo Service URLs:
echo   - Neo4j Browser: http://localhost:7474
echo   - Neo4j Bolt:    bolt://localhost:7687
echo   - Qdrant:        http://localhost:6333
echo.
echo Next steps:
echo   1. Update .env with your API keys
echo   2. Run: uv run python -m backend.loaders.main
echo   3. Run: uv run uvicorn backend.main:app --reload
echo   4. Run: cd frontend ^&^& npm run dev
echo.
