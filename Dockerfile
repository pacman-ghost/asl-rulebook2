# NOTE: Use the run-container.sh script to build and launch this container.

FROM centos:8 AS base

# update packages
RUN dnf -y upgrade-minimal

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

FROM base AS build

# install Python
# NOTE: The version of Python we want is newer than what's in Centos 8,
# so we have to install from source :-/
RUN dnf -y groupinstall "Development Tools" && \
    dnf -y install openssl-devel bzip2-devel libffi-devel sqlite-devel
RUN cd /tmp && \
    dnf -y install wget && \
    wget https://www.python.org/ftp/python/3.8.7/Python-3.8.7.tgz && \
    tar xvf Python-3.8.7.tgz && \
    cd Python-3.8.7/ && \
    ./configure --enable-optimizations && \
    make install

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

FROM base

# copy the Python installation from the build image
COPY --from=build /usr/local/bin/python3.8 /usr/local/bin/python3.8
COPY --from=build /usr/local/lib/python3.8 /usr/local/lib/python3.8
COPY --from=build /usr/local/bin/pip3 /usr/local/bin/pip3
RUN ln -s /usr/local/bin/python3.8 /usr/local/bin/python3

# install requirements
RUN dnf -y install ghostscript && \
    dnf clean all

# install the application requirements
COPY requirements.txt requirements-dev.txt ./
RUN pip3 install -r requirements.txt
ARG CONTROL_TESTS_PORT
RUN if [ -n "$CONTROL_TESTS_PORT" ]; then \
    pip3 install -r requirements-dev.txt \
; fi

# install the application
WORKDIR /app
COPY asl_rulebook2/ ./asl_rulebook2/
COPY setup.py requirements.txt requirements-dev.txt LICENSE.txt ./
RUN pip3 install --editable .

# install the config files
COPY docker/config/ ./asl_rulebook2/webapp/config/
COPY asl_rulebook2/webapp/config/logging.yaml.example ./asl_rulebook2/webapp/config/logging.yaml

# create a new user
RUN useradd --create-home app
USER app

EXPOSE 5020
COPY docker/run.sh ./
CMD ./run.sh
