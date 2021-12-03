# NOTE: Use the run-container.sh script to build and launch this container.

# NOTE: Multi-stage builds require Docker >= 17.05.
FROM centos:8 AS base

# update packages and install requirements
RUN dnf -y upgrade-minimal && \
    dnf install -y python38 && \
    dnf install -y ghostscript && \
    dnf clean all

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

FROM base AS build

# set up a virtualenv
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --upgrade pip

# install the application requirements
COPY requirements.txt requirements-dev.txt /tmp/
RUN pip3 install -r /tmp/requirements.txt
ARG CONTROL_TESTS_PORT
RUN if [ -n "$CONTROL_TESTS_PORT" ]; then \
    pip3 install -r /tmp/requirements-dev.txt \
; fi

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

FROM base

# copy the virtualenv from the build image
COPY --from=build /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# install the application
WORKDIR /app
COPY asl_rulebook2/ ./asl_rulebook2/
COPY doc/ ./doc/
COPY setup.py requirements.txt requirements-dev.txt LICENSE.txt ./
RUN pip3 install --editable .

# install the config files
COPY asl_rulebook2/webapp/config/logging.yaml.example ./asl_rulebook2/webapp/config/logging.yaml
COPY docker/config/ ./asl_rulebook2/webapp/config/

# create a new user
RUN useradd --create-home app
USER app

EXPOSE 5020
COPY docker/run.sh ./
CMD ./run.sh
