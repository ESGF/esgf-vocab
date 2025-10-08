FROM python:3.12-alpine

RUN apk --no-cache update && apk --no-cache upgrade && apk --no-cache add git

RUN pip --no-cache-dir install esgvoc pytest

RUN esgvoc install

WORKDIR /test
ADD https://github.com/ESGF/esgf-vocab.git#main esgvoc

WORKDIR /test/esgvoc
RUN pytest tests
