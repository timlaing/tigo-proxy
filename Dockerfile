ARG BUILD_FROM
ARG BUILD_ARCH
ARG BUILD_VERSION
FROM ghcr.io/home-assistant/$BUILD_ARCH-base-python

COPY app /app
COPY run.sh /

RUN \
  apk update \
  && apk add --no-cache \
    py3-paho-mqtt \
    openssl \
  py3-pip \
  && pip install --root-user-action=ignore -r /app/requirements.txt \
  && chmod a+x /run.sh

CMD [ "/run.sh" ]