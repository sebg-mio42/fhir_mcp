# mcp-terminology MCP server. Needs BuildKit (default since Docker 23). From the repository root:
#   docker build -f packages/mcp-terminology/Dockerfile -t mcp-terminology .
# Behind a TLS-intercepting proxy (e.g. KBV network) add a CA bundle that contains its CAs:
#   --secret id=ca,src=/etc/ssl/certs/ca-certificates.crt
# The image uses https://tx.mio42.de/r4, whose certificate is issued by the KBV CA, so at run time mount a CA bundle
# that contains it ([CA] in the commands below; RHEL hosts: /etc/pki/tls/certs/ca-bundle.crt):
#   [CA] = -v /etc/ssl/certs/ca-certificates.crt:/etc/ssl/host-ca.pem:ro -e SSL_CERT_FILE=/etc/ssl/host-ca.pem
# Run over stdio (Claude Desktop):     docker run -i --rm [CA] mcp-terminology
# Run over HTTP (http://host:8001/mcp): docker run -d -p 8001:8001 -e MCP_TRANSPORT=http [CA] mcp-terminology
# Other settings (TERMINOLOGY_BASE_URL, LOG_FORMAT, LANGFUSE_*): see src/mcp_terminology/settings.py
FROM python:3.14-alpine
WORKDIR /app
# uv checks uv.lock against every workspace member, so all member pyproject.toml files are needed
COPY pyproject.toml uv.lock ./
COPY shared/pyproject.toml shared/
COPY packages/mcp-fhir/pyproject.toml packages/mcp-fhir/
COPY packages/mcp-clinical-reasoner/pyproject.toml packages/mcp-clinical-reasoner/
COPY packages/mcp-terminology/pyproject.toml packages/mcp-terminology/
# uv is mounted for this step only and stays out of the image; --locked fails if uv.lock is out of date
RUN --mount=from=ghcr.io/astral-sh/uv:0.13.8,source=/uv,target=/bin/uv --mount=type=secret,id=ca \
    if [ -f /run/secrets/ca ]; then export SSL_CERT_FILE=/run/secrets/ca; fi; \
    UV_PYTHON_DOWNLOADS=never uv sync --package mcp-terminology --no-install-workspace --no-dev \
      --locked --no-cache --compile-bytecode
# ponytail: workspace code runs from source via PYTHONPATH instead of being built into the venv
# --chmod: the source keeps host modes, and a checkout made with umask 077 is unreadable for nobody
COPY --chmod=755 shared/src shared/src
COPY --chmod=755 packages/mcp-terminology/src packages/mcp-terminology/src
ENV PATH=/app/.venv/bin:$PATH \
    PYTHONPATH=/app/shared/src:/app/packages/mcp-terminology/src \
    TERMINOLOGY_BASE_URL=https://tx.mio42.de/r4
USER nobody
EXPOSE 8001
ENTRYPOINT ["python", "-m", "mcp_terminology.server"]
