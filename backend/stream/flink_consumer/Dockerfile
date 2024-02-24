FROM python:3.10.6-slim

WORKDIR /app

COPY . .

RUN pip install --trusted-host pypi.python.org -r requirements.txt

# JRE is needed for Apache Flink
RUN apt-get update && apt-get install -y openjdk-17-jre-headless && apt-get clean;

# Install NetCat to check when specific dependencies are up and running
RUN apt-get update && apt-get install -y netcat-openbsd

ENTRYPOINT ["/app/entrypoint.sh"]