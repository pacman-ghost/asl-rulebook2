# NOTE: Use the run-container.sh script to build and launch this container.

FROM centos:8

# update packages
RUN dnf -y upgrade-minimal

# install Python
RUN dnf install -y python38 python3-pip && \
    pip3 install -U pip setuptools

# install the application requirements
COPY requirements.txt requirements-dev.txt ./
RUN pip3 install -r requirements.txt
ARG CONTROL_TESTS_PORT
RUN if [ -n "$CONTROL_TESTS_PORT" ]; then \
    pip3 install -r requirements-dev.txt \
; fi

# clean up
RUN dnf clean all

# install the application
WORKDIR /app
COPY asl_rulebook2/ ./asl_rulebook2/
COPY setup.py requirements.txt requirements-dev.txt LICENSE.txt ./
RUN pip3 install --editable .

# install the config files
COPY docker/config/ ./asl_rulebook2/webapp/config/

# create a new user
RUN useradd --create-home app
USER app

EXPOSE 5020
COPY docker/run.sh ./
CMD ./run.sh
