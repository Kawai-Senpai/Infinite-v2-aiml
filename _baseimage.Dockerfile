FROM python:3.12.8-bookworm

WORKDIR /app

ENV DEBIAN_FRONTEND=noninteractive

# Set timezone to UTC
RUN ln -fs /usr/share/zoneinfo/Etc/UTC /etc/localtime && \
    dpkg-reconfigure -f noninteractive tzdata

# Copy and install requirements
COPY ./requirements.txt /app/
RUN pip install --no-cache-dir -r /app/requirements.txt