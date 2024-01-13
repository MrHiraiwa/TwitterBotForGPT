# Use the official lightweight Python image.
# https://hub.docker.com/_/python
FROM python:3.10.13-slim

# Allow statements and log messages to immediately appear in the Knative logs
ENV PYTHONUNBUFFERED True

# Copy local code to the container image.
ENV APP_HOME /app
WORKDIR $APP_HOME
COPY . ./

# Install production dependencies.
RUN apt-get update && apt-get install -y wget curl unzip gnupg 

# Download and install Chrome
RUN wget https://dl.google.com/linux/chrome/deb/pool/main/g/google-chrome-stable/google-chrome-stable_120.0.6099.71-1_amd64.deb &&\
    dpkg -i google-chrome-stable_120.0.6099.71-1_amd64.deb || apt-get install -fy

# TODO: You will also need to install the matching ChromeDriver version. 
# However, finding the exact ChromeDriver version for older Chrome versions can be challenging. 
# Make sure to replace the ChromeDriver download URL with the correct version.
RUN wget https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/120.0.6099.71/linux64/chromedriver-linux64.zip &&\
    unzip chromedriver-linux64.zip &&\
    mv chromedriver-linux64/chromedriver /usr/bin/chromedriver &&\
    chown root:root /usr/bin/chromedriver &&\
    chmod +x /usr/bin/chromedriver

RUN pip install --no-cache-dir -r requirements.txt

# Run the web service on container startup. Here we use the gunicorn
# webserver, with one worker process and 8 threads.
# For environments with multiple CPU cores, increase the number of workers
# to be equal to the cores available.
# Timeout is set to 0 to disable the timeouts of the workers to allow Cloud Run to handle instance scaling.
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 main:app
