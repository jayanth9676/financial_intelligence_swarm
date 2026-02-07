# Docker Infrastructure for Financial Intelligence Swarm

## Services

| Service | Port | Description |
|---------|------|-------------|
| Neo4j HTTP | 7474 | Browser UI |
| Neo4j Bolt | 7687 | Driver connections |
| Qdrant REST | 6333 | REST API |
| Qdrant gRPC | 6334 | gRPC API |

## Startup

```bash
cd docker
docker-compose up -d
```

## Access

- **Neo4j Browser:** http://localhost:7474 (user: `neo4j`, password: `password123`)
- **Qdrant Dashboard:** http://localhost:6333/dashboard

## Stop

```bash
docker-compose down
```

## Reset Data

```bash
docker-compose down -v
```
