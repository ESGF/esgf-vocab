FROM python:3.12-alpine

RUN apk update && apk upgrade && apk add git

RUN pip install esgvoc pytest

RUN esgvoc install

WORKDIR /test
ADD https://github.com/ESGF/esgf-vocab.git#main esgvoc

WORKDIR /test/esgvoc
RUN pytest tests
