FROM python:3.7
COPY src/ /app
COPY entrypoint.sh /app
COPY Pipfile /app
COPY Pipfile.lock /app
WORKDIR /app
RUN apt-get update
RUN apt-get install pkg-config libsecp256k1-dev libzmq3-dev -y
RUN pip3 install --upgrade setuptools pip pipenv
RUN pipenv install
RUN chmod +x /app/entrypoint.sh
EXPOSE 8085
CMD ["./entrypoint.sh"]