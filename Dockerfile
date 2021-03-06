FROM python:3.7
USER root
COPY src/ /app
COPY entrypoint.web.sh /app
COPY entrypoint.beat.sh /app
COPY entrypoint.worker.sh /app
COPY Pipfile /app
COPY Pipfile.lock /app
WORKDIR /app
RUN apt-get update
RUN apt-get install pkg-config libsecp256k1-dev libzmq3-dev -y
# Required to install/run Orca/Electron:
RUN apt-get install curl libnss3-dev libgtk-3-0 libgconf-2-4 libx11-xcb1 libasound2 xvfb -y
RUN curl -sL https://deb.nodesource.com/setup_14.x  | bash -
RUN apt-get install nodejs -y
RUN npm install --global --unsafe-perm --save-dev electron@6.1.4 orca
RUN pip3 install --upgrade setuptools pip pipenv
RUN pipenv sync
RUN chmod +x /app/entrypoint.web.sh
RUN chmod +x /app/entrypoint.beat.sh
RUN chmod +x /app/entrypoint.worker.sh
EXPOSE 8085
CMD ["./entrypoint.web.sh"]
