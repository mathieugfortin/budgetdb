# Use an official Python runtime as a parent image
FROM python:alpine
ARG BUILD_DATE
ARG VERSION="0.8"
ARG GIT_COMMIT="unknown"
LABEL build_version="version:- ${VERSION} Build-date:- ${BUILD_DATE}"
LABEL maintainer="mathieugfortin"
LABEL git_commit=$GIT_COMMIT

# Set the working directory in the container
WORKDIR /app

# Install build dependencies for mysqlclient
RUN apk add --no-cache \
    gcc \
    musl-dev \
    mariadb-connector-c-dev \
    pkgconfig

# Copy requirements into the container at /app
COPY requirements.txt /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the current directory contents into the container at /app
COPY . /app

# Make port 8005 available to the world outside this container
EXPOSE 8005

# Define environment variable
ENV DJANGO_SETTINGS_MODULE=web_budget.settings

# Run app.py when the container launches
ENTRYPOINT ["gunicorn", "web_budget.wsgi:application", "-c", "/app/config/gunicorn/prod.conf.py"]
# ENTRYPOINT ["tail", "-f", "/dev/null"]