# Use the official lightweight Python image.
# https://hub.docker.com/_/python
FROM python:3.10.9-slim

# Allow statements and log messages to immediately appear in the Knative logs
ENV PYTHONUNBUFFERED True

# Copy local code to the container image.
ENV APP_HOME /app
WORKDIR $APP_HOME
COPY . ./

# Install production dependencies.
RUN apt-get update && apt-get install -y wget unzip curl

# Install Chrome version 114 and its corresponding ChromeDriver
RUN wget https://dl.google.com/linux/direct/google-chrome-stable_114.0.5735.90-1_amd64.deb
RUN dpkg -i google-chrome-stable_114.0.5735.90-1_amd64.deb; apt-get -fy install

# Install ChromeDriver for Chrome 114
RUN CHROMEDRIVER_VERSION=$(curl -sSL https://chromedriver.storage.googleapis.com/LATEST_RELEASE_114) && \
    wget -N https://chromedriver.storage.googleapis.com/$CHROMEDRIVER_VERSION/chromedriver_linux64.zip &&\
    unzip chromedriver_linux64.zip &&\
    mv chromedriver /usr/bin/chromedriver &&\
    chown root:root /usr/bin/chromedriver &&\
    chmod +x /usr/bin/chromedriver

RUN pip install --no-cache-dir -r requirements.txt

# Run the web service on container startup. Here we use the gunicorn
# webserver, with one worker process and 8 threads.
# For environments with multiple CPU cores, increase the number of workers
# to be equal to the cores available.
# Timeout is set to 0 to disable the timeouts of the workers to allow Cloud Run to handle instance scaling.
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 main:app
