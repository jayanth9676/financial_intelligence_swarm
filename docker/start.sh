#!/bin/bash
# FIS - Docker Infrastructure Startup Script
# This script starts all required services and verifies they are healthy

set -e

echo "=================================================="
echo "Financial Intelligence Swarm - Infrastructure Setup"
echo "=================================================="

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "Starting Docker services..."
docker-compose up -d

echo ""
echo "Waiting for services to start..."
sleep 5

# Check Neo4j
echo ""
echo -n "Checking Neo4j... "
for i in {1..30}; do
    if curl -s http://localhost:7474 > /dev/null 2>&1; then
        echo -e "${GREEN}OK${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}FAILED${NC}"
        echo "Neo4j did not start in time. Check docker logs neo4j"
        exit 1
    fi
    sleep 2
done

# Check Qdrant
echo -n "Checking Qdrant... "
for i in {1..30}; do
    if curl -s http://localhost:6333/health > /dev/null 2>&1; then
        echo -e "${GREEN}OK${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}FAILED${NC}"
        echo "Qdrant did not start in time. Check docker logs qdrant"
        exit 1
    fi
    sleep 2
done

echo ""
echo -e "${GREEN}All services are running!${NC}"
echo ""
echo "Service URLs:"
echo "  - Neo4j Browser: http://localhost:7474"
echo "  - Neo4j Bolt:    bolt://localhost:7687"
echo "  - Qdrant:        http://localhost:6333"
echo ""
echo "Next steps:"
echo "  1. Update .env with your API keys"
echo "  2. Run: uv run python -m backend.loaders.main"
echo "  3. Run: uv run uvicorn backend.main:app --reload"
echo "  4. Run: cd frontend && npm run dev"
echo ""
