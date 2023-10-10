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

# Download and install Chrome version 117.0.5938.149 and its ChromeDriver
RUN wget https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/117.0.5938.149/linux64/chrome-linux64.zip &&\
    unzip chrome-linux64.zip &&\
    mv chrome-linux64/chrome /usr/bin/google-chrome &&\
    chmod +x /usr/bin/google-chrome &&\
    wget https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/117.0.5938.149/linux64/chromedriver-linux64.zip &&\
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
