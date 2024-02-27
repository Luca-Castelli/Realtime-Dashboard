FROM python:3.10.6-slim

WORKDIR /app

COPY . .

RUN pip install --trusted-host pypi.python.org -r requirements.txt

ENTRYPOINT ["/app/entrypoint.sh"]
