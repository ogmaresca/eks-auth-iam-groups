FROM python:3.7-alpine
#FROM python:3.7-slim

COPY requirements.txt /src/requirements.txt

RUN pip3 --no-cache-dir install -r /src/requirements.txt

WORKDIR /app

COPY *.py /app

ENTRYPOINT ["python", "eks-map-iam-groups.py"]
CMD []
