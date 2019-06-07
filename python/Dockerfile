FROM python:3.7-alpine
#FROM python:3.7-slim

RUN pip3 --no-cache-dir install -r /app/requirements.txt \
  kubernetes \
  boto3

#COPY . /app

COPY . /src
RUN python -m compileall -d /app /src
#RUN python -m py_compile -d /app /src/*.py

WORKDIR /app

CMD ["python", "eks-map-iam-groups.pyc"]
