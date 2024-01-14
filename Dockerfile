# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Make port 8005 available to the world outside this container
EXPOSE 8005

# Define environment variable
ENV DJANGO_SETTINGS_MODULE=web_budget.settings

# Run app.py when the container launches
ENTRYPOINT ["gunicorn", "web_budget.wsgi:application", "-c", "/app/config/gunicorn/prod.conf.py"]
# ENTRYPOINT ["tail", "-f", "/dev/null"]