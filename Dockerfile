FROM python:3.12-slim

RUN pip install --no-cache-dir estat-mcp

ENTRYPOINT ["estat-mcp"]
CMD ["serve"]
