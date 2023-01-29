FROM python:3.10

COPY requirements.txt /tmp/requirements.txt

RUN pip install -r /tmp/requirements.txt

COPY src /usr/src

CMD ["python", "/usr/src/py/main.py"]
