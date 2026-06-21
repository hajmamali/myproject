# MCP Server Configuration
# Production deployment guide

## Setup

### 1. Install dependencies
```bash
pip install -r mahoun/mcp/requirements.txt
```

### 2. Set environment variables
```bash
# REQUIRED: Set a strong API key
export MCP_API_KEY="your-super-secret-key-change-this"

# OPTIONAL: Neo4j connection (if using GraphTool)
export NEO4J_URI="bolt://localhost:7687"
export NEO4J_USER="neo4j"
export NEO4J_PASSWORD="your-neo4j-password"
```

### 3. Run the server
```bash
# Development
uvicorn mahoun.mcp.server:app --reload --host 0.0.0.0 --port 8000

# Production
uvicorn mahoun.mcp.server:app --host 0.0.0.0 --port 8000 --workers 4
```

## Security

### API Key Authentication
All requests to `/mcp` endpoint require a valid API key in the `X-API-Key` header.

Example request:
```bash
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-super-secret-key-change-this" \
  -d '{
    "jsonrpc": "2.0",
    "method": "System.health",
    "id": 1
  }'
```

### Rate Limiting
- Default: 100 requests/minute per IP address
- Exceeding limit returns HTTP 429

### Production Checklist
- [ ] Change default API key (never use `dev-key-change-in-production`)
- [ ] Use HTTPS in production (configure reverse proxy)
- [ ] Set up firewall rules
- [ ] Enable logging to file/monitoring system
- [ ] Configure rate limiting for your use case
- [ ] Set up SSL certificates
- [ ] Use environment-specific configs

## Testing

Run tests:
```bash
pytest tests/test_mcp_server.py -v
```

## Monitoring

### Health Check
```bash
curl http://localhost:8000/health
```

### List Available Tools
```bash
curl http://localhost:8000/mcp/tools
```

## Error Codes

| Code | Name | Description |
|------|------|-------------|
| -32700 | Parse error | Invalid JSON |
| -32600 | Invalid Request | Invalid method format |
| -32601 | Method not found | Tool/function not found |
| -32602 | Invalid params | Invalid parameters |
| -32603 | Internal error | Server error |
| -32001 | DB unavailable | Database connection failed |
| -32002 | Timeout | Request timeout |
| -32003 | Unauthorized | Invalid/missing API key |
| -32004 | Rate limited | Too many requests |

## Performance Tips

1. **Use connection pooling** for database tools
2. **Enable caching** for frequently accessed data
3. **Monitor slow queries** and optimize
4. **Scale horizontally** with multiple workers
5. **Use async** whenever possible

## Troubleshooting

### "Missing API key" error
- Ensure `X-API-Key` header is set
- Check `MCP_API_KEY` environment variable

### "Tool not found" error
- Check tool registry in `mahoun/mcp/registry.py`
- Verify tool is properly imported

### Slow responses
- Check database connection
- Monitor with logging
- Consider caching

## Production Deployment

### Using Docker
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
ENV MCP_API_KEY=change-this
CMD ["uvicorn", "mahoun.mcp.server:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Using systemd
```ini
[Unit]
Description=MAHOUN MCP Server
After=network.target

[Service]
Type=simple
User=mahoun
WorkingDirectory=/opt/mahoun
Environment="MCP_API_KEY=your-secret-key"
ExecStart=/opt/mahoun/venv/bin/uvicorn mahoun.mcp.server:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```
