FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    openssh-client \
    git \
    ansible \
    unzip \
    lsb-release \
    software-properties-common \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Install Terraform
RUN curl -fsSL https://releases.hashicorp.com/terraform/1.6.0/terraform_1.6.0_linux_amd64.zip -o terraform.zip \
    && unzip terraform.zip \
    && mv terraform /usr/local/bin/ \
    && rm terraform.zip \
    && terraform --version

# Install uv for fast package management
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Copy project files
COPY pyproject.toml uv.lock ./

# Install Python dependencies
RUN uv sync --frozen --no-dev

# Copy application source
COPY . .

# Expose both MCP server (3000) and chat server (3001) ports
EXPOSE 3000 3001

# Set Docker mode environment variable
ENV DOCKER_MODE=true

# Health check for chat server (has health endpoint)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3001/health || exit 1

# Default command - run both servers
CMD ["uv", "run", "python", "-c", "import asyncio; from src.server.mcp_server import HomelabMCPServer; server = HomelabMCPServer(host='0.0.0.0'); asyncio.run(server.run_both_servers())"]