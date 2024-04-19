ARG BUILD_FROM
FROM $BUILD_FROM

COPY app /app
COPY run.sh /

RUN \
  apk update \
  && apk add --no-cache \
    python3 \
    openssl \
  py3-pip \
  # && pip install /app/requirements.txt \
  && chmod a+x /run.sh

CMD [ "/run.sh" ]