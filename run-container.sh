#!/usr/bin/env bash
# Helper script that builds and launches the Docker container.

# ---------------------------------------------------------------------

function main
{
    # initialize
    cd $( dirname "$0" )
    PORT=5020
    IMAGE_TAG=latest
    CONTAINER_NAME=asl-rulebook2
    DETACH=
    NO_BUILD=
    CONTROL_TESTS_PORT=

    # parse the command-line arguments
    if [ $# -eq 0 ]; then
        print_help
        exit 0
    fi
    params="$(getopt -o p:t:d -l port:,tag:,name:,detach,no-build,control-tests-port:,help --name "$0" -- "$@")"
    if [ $? -ne 0 ]; then exit 1; fi
    eval set -- "$params"
    while true; do
        case "$1" in
            -p | --port )
                PORT=$2
                shift 2 ;;
            -t | --tag )
                IMAGE_TAG=$2
                shift 2 ;;
            --name )
                CONTAINER_NAME=$2
                shift 2 ;;
            -d | --detach )
                DETACH=--detach
                shift 1 ;;
            --no-build )
                NO_BUILD=1
                shift 1 ;;
            --control-tests-port )
                CONTROL_TESTS_PORT=$2
                shift 2 ;;
            --help )
                print_help
                exit 0 ;;
            -- ) shift ; break ;;
            * )
                echo "Unknown option: $1" >&2
                exit 1 ;;
        esac
    done

    # check if testing has been enabled
    if [ -n "$CONTROL_TESTS_PORT" ]; then
        CONTROL_TESTS_PORT_BUILD="--build-arg CONTROL_TESTS_PORT=$CONTROL_TESTS_PORT"
        CONTROL_TESTS_PORT_RUN="--env CONTROL_TESTS_PORT=$CONTROL_TESTS_PORT --publish $CONTROL_TESTS_PORT:$CONTROL_TESTS_PORT"
    fi

    # build the image
    if [ -z "$NO_BUILD" ]; then
        echo Building the \"$IMAGE_TAG\" image...
        docker build \
            --tag asl-rulebook2:$IMAGE_TAG \
            $CONTROL_TESTS_PORT_BUILD \
            . 2>&1 \
          | sed -e 's/^/  /'
        if [ ${PIPESTATUS[0]} -ne 0 ]; then exit 10 ; fi
        echo
    fi

    # launch the container
    echo Launching the \"$IMAGE_TAG\" image as \"$CONTAINER_NAME\"...
    docker run \
        --name $CONTAINER_NAME \
        --publish $PORT:5020 \
        -it --rm \
        $CONTROL_TESTS_PORT_RUN \
        asl-rulebook2:$IMAGE_TAG \
        2>&1 \
      | sed -e 's/^/  /'
    exit ${PIPESTATUS[0]}
}

# ---------------------------------------------------------------------

function print_help {
    echo "`basename "$0"` {options}"
    cat <<EOM
  Build and launch the "asl-rulebook2" container.

    -p  --port             Web server port number.

    -t  --tag              Docker image tag.
        --name             Docker container name.
    -d  --detach           Detach from the container and let it run in the background.
        --no-build         Launch the container as-is (i.e. without rebuilding the image first).
EOM
}

# ---------------------------------------------------------------------

main "$@"
