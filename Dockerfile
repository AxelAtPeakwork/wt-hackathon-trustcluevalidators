FROM python:3.6-slim


RUN mkdir /app

WORKDIR /app

RUN apt-get update; \
    apt-get install -y build-essential

RUN pip install flask; \
    pip install flask-restful; \
    pip install python-box; \
    pip install dnspython; \
    pip install web3==4.9.2; \
    pip install flask-cors

COPY . /app

WORKDIR /app/trust-clue-validator

CMD ["python3", "app.py"]