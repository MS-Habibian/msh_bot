# ---- Stage 1: The "Builder" ----
FROM python:3.12-slim as builder
WORKDIR /opt/venv

# # Install build dependencies
# RUN apt-get update && apt-get install -y --no-install-recommends \
#     build-essential libpq-dev

RUN python -m venv .
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


# ---- Stage 2: The "Final" Image ----
FROM python:3.12-slim
WORKDIR /app

# RUN apt-get update && apt-get install -y --no-install-recommends \
#     libpq5 \
#     && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY . .

CMD ["bash", "start.sh"]