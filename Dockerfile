# Minimal base image
FROM cgr.dev/chainguard/wolfi-base

# specify the python version
ARG version=3.12

WORKDIR /app

COPY requirements.txt .

# Install dependencies
RUN apk upgrade --no-cache
RUN apk add --no-cache python-${version} py${version}-pip && \
    pip install --upgrade pip && \
    pip install -r requirements.txt && \
    apk del py${version}-pip && \
    chown -R nonroot:nonroot /app

COPY . .

USER nonroot

ENTRYPOINT ["python", "main.py"]
