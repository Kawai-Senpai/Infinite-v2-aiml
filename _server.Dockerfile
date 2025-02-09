FROM infinite-base:latest

WORKDIR /app

# Use .dockerignore to exclude specific folders instead of copying everything
COPY . /app
COPY .env /app/.env
RUN sed -i 's/ENVIRONMENT = development/ENVIRONMENT = production/' .env

# Debug: list file tree for verification
RUN ls -la /app

#delete contents of cache and debug folders
RUN rm -rf /app/debug/* /app/cache/* /app/.testdata/*

RUN mkdir -p /app/debug
VOLUME ["/app/debug"]

#run _init.py to create folders and structures
RUN python _init.py

EXPOSE 8000

CMD ["uvicorn", "_server:app", "--host", "0.0.0.0", "--port", "8000"]
