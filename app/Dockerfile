FROM python:3.7.2-stretch

ADD . /app/

WORKDIR /app/

RUN pip3 install -r requirements.txt

EXPOSE 5000

ENTRYPOINT ["python3", "./server/app.py"]