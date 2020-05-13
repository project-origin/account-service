FROM python:3.7
COPY src/ /app
COPY entrypoint.web.sh /app
COPY entrypoint.beat.sh /app
COPY entrypoint.worker.sh /app
COPY Pipfile /app
COPY Pipfile.lock /app
WORKDIR /app
RUN apt-get update
RUN apt-get install pkg-config libsecp256k1-dev libzmq3-dev -y
RUN pip3 install --upgrade setuptools pip pipenv
RUN pipenv install
RUN chmod +x /app/entrypoint.web.sh
RUN chmod +x /app/entrypoint.beat.sh
RUN chmod +x /app/entrypoint.worker.sh
EXPOSE 8085
CMD ["./entrypoint.web.sh"]
