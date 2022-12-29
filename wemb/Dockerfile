# One-layer image since compilation is not necessary
FROM python:3.10.9-alpine3.17 as final

# Add container user and drop privileges
RUN addgroup -S python && \
    adduser -SG python python

USER python

# Copy source files and install requirements
WORKDIR /app

# Only copy requirements first and install before proceeding
# This way, changes in the main script
COPY --chown=python:python ./src/requirements.txt /app/
RUN python -m pip install --no-cache-dir -r requirements.txt

COPY --chown=python:python ./src/main.py /app/

# A config.yaml mount point is expected, as well as env vars for PRAW
ENTRYPOINT [ "python", "./main.py" ]


