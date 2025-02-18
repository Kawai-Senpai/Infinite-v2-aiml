FROM infinite-base:latest

WORKDIR /app

# Use .dockerignore to exclude specific folders instead of copying everything
COPY . /app

# Debug: list file tree for verification
RUN ls -la /app

#delete contents of cache and debug folders
RUN rm -rf /app/debug/* /app/cache/* /app/.testdata/*

RUN mkdir -p /app/debug
VOLUME ["/app/debug"]

EXPOSE 8000

CMD ["sh", "-c", "python _init.py && uvicorn _server:app --host 0.0.0.0 --port 8000 --workers 8"]
