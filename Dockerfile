# Use an official Python runtime as a parent image
FROM python:alpine
ARG BUILD_DATE
ARG VERSION="0.8.5"
ARG GIT_COMMIT="unknown"

# pass to eng variable
ENV APP_BUILD_DATE=$BUILD_DATE
ENV APP_VERSION=$VERSION
ENV APP_GIT_SHA=$GIT_COMMIT

LABEL build_version="version:- ${VERSION} Build-date:- ${BUILD_DATE}"
LABEL maintainer="mathieugfortin"
LABEL git_commit=$GIT_COMMIT

# Set the working directory in the container
WORKDIR /app



# Copy requirements into the container at /app
COPY requirements.txt /app

# Install build dependencies for mysqlclient
# Install any needed packages specified in requirements.txt
RUN apk add --no-cache mariadb-connector-c-dev \
    && apk add --no-cache --virtual .build-deps \
        gcc \
        musl-dev \
        pkgconfig \
    && pip install --no-cache-dir -r requirements.txt \
    && apk del .build-deps

# Copy the current directory contents into the container at /app
COPY . /app

RUN SECRET_KEY=dummy \
    DB_NAME=dummy \
    DB_USER=dummy \
    DB_PASSWORD=dummy \
    DB_HOST=localhost \
    DB_PORT=3306 \
    python manage.py collectstatic --noinput

# Make port 8005 available to the world outside this container
EXPOSE 8005

# Define environment variable
ENV DJANGO_SETTINGS_MODULE=web_budget.settings

# Run app.py when the container launches
ENTRYPOINT ["gunicorn", "web_budget.wsgi:application", "-c", "/app/config/gunicorn/prod.conf.py"]
# ENTRYPOINT ["tail", "-f", "/dev/null"]