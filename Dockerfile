FROM python:3.11-slim-bookworm

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy project definition
COPY pyproject.toml uv.lock ./

# Install dependencies
# We use --system to install into the system python, avoiding the need for activation
# However, uv sync defaults to .venv. 
# Let's use uv sync and use 'uv run' in the CMD to use the environment.
RUN uv sync --frozen --no-cache

# Copy the rest of the application
COPY . .

# Expose the port (Railway typically sets PORT env var, defaulting to 8080 usually)
ENV PORT=8080
EXPOSE 8080

# Run the application
# We use 'uv run' to ensure we run within the environment created by 'uv sync'
CMD ["uv", "run", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8080"]
