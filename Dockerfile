FROM ghcr.io/open-webui/open-webui:v0.11.4

USER root

ENV PYTHONUNBUFFERED=1
ENV GARMIN_TRAINER_VENV=/opt/garmin-trainer/.venv
ENV PYTHONPATH=/opt/garmin-trainer/app:/opt/garmin-trainer/.venv/lib/python3.11/site-packages

RUN python -m venv "$GARMIN_TRAINER_VENV" \
    && "$GARMIN_TRAINER_VENV/bin/pip" install --no-cache-dir \
    garmindb==3.7.0 \
    garmin-fit-sdk==21.214.0

RUN mkdir -p \
    /opt/garmin-trainer/app \
    /opt/garmin-trainer/config \
    /data/garmindb \
    /data/training_diary \
    /data/generated \
    /data/knowledge

COPY app/ /opt/garmin-trainer/app/
COPY config/ /opt/garmin-trainer/config/
COPY bootstrap_openwebui.py docker-entrypoint.sh /opt/garmin-trainer/

CMD ["bash", "/opt/garmin-trainer/docker-entrypoint.sh"]
