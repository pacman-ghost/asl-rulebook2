#!/usr/bin/env bash
# Helper script that builds and launches the Docker container.

# ---------------------------------------------------------------------

function main
{
    # initialize
    cd "$( dirname "$0" )"
    PORT=5020
    DATA_DIR=
    QA_DIR=
    ERRATA_DIR=
    USER_ANNO_FILE=
    ASOP_DIR=
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
    params="$(getopt -o p:d:t: -l port:,data:,qa:,errata:,annotations:,asop:,tag:,name:,detach,no-build,control-tests-port:,help --name "$0" -- "$@")"
    if [ $? -ne 0 ]; then exit 1; fi
    eval set -- "$params"
    while true; do
        case "$1" in
            -p | --port )
                PORT=$2
                shift 2 ;;
            -d | --data )
                DATA_DIR=$2
                shift 2 ;;
            --qa )
                QA_DIR=$2
                shift 2 ;;
            --errata )
                ERRATA_DIR=$2
                shift 2 ;;
            --annotations )
                USER_ANNO_FILE=$2
                shift 2 ;;
            --asop )
                ASOP_DIR=$2
                shift 2 ;;
            -t | --tag )
                IMAGE_TAG=$2
                shift 2 ;;
            --name )
                CONTAINER_NAME=$2
                shift 2 ;;
            --detach )
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

    # check the data directory
    if [ -n "$DATA_DIR" ]; then
        target=$( get_target DIR "$DATA_DIR" )
        if [ -z "$target" ]; then
            echo "Can't find the data directory: $DATA_DIR"
            exit 2
        fi
        mpoint=/data/
        DATA_DIR_VOLUME="--volume $target:$mpoint"
        DATA_DIR_ENV="--env DOCKER_DATA_DIR=$mpoint"
    fi

    # check the Q+A directory
    if [ -n "$QA_DIR" ]; then
        target=$( get_target DIR "$QA_DIR" )
        if [ -z "$target" ]; then
            echo "Can't find the Q+A directory: $QA_DIR"
            exit 2
        fi
        mpoint=/data/q+a/
        QA_DIR_VOLUME="--volume $target:$mpoint"
    fi

    # check the errata directory
    if [ -n "$ERRATA_DIR" ]; then
        target=$( get_target DIR "$ERRATA_DIR" )
        if [ -z "$target" ]; then
            echo "Can't find the errata directory: $ERRATA_DIR"
            exit 2
        fi
        mpoint=/data/errata/
        ERRATA_DIR_VOLUME="--volume $target:$mpoint"
    fi

    # check the user annotations file
    if [ -n "$USER_ANNO_FILE" ]; then
        target=$( get_target FILE "$USER_ANNO_FILE" )
        if [ -z "$target" ]; then
            echo "Can't find the user annotations: $USER_ANNO_FILE"
            exit 2
        fi
        mpoint=/data/annotations.json
        USER_ANNO_VOLUME="--volume $target:$mpoint"
    fi

    # check the ASOP directory
    if [ -n "$ASOP_DIR" ]; then
        target=$( get_target DIR "$ASOP_DIR" )
        if [ -z "$target" ]; then
            echo "Can't find the ASOP directory: $ASOP_DIR"
            exit 2
        fi
        mpoint=/data/asop/
        ASOP_DIR_VOLUME="--volume $target:$mpoint"
    fi

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
        $DATA_DIR_VOLUME $DATA_DIR_ENV \
        $QA_DIR_VOLUME \
        $ERRATA_DIR_VOLUME \
        $ASOP_DIR_VOLUME \
        $USER_ANNO_VOLUME \
        $DETACH \
        asl-rulebook2:$IMAGE_TAG \
        2>&1 \
      | sed -e 's/^/  /'
    exit ${PIPESTATUS[0]}
}

# ---------------------------------------------------------------------

function get_target {
    local type=$1
    local target=$2

    # check that the target exists
    if [ "$type" == "FILE" ]; then
        test -f "$target" || return
    elif [ "$type" == "DIR" ]; then
        test -d "$target" || return
    elif [ "$type" == "FILE-OR-DIR" ]; then
        ls "$target" >/dev/null 2>&1 || return
    fi

    # convert the target to a full path
    # FUDGE! I couldn't get the "docker run" command to work with spaces in the volume targets (although
    # copying the generated command into the terminal worked fine) (and no, using ${var@Q} didn't help).
    # So, the next best thing is to allow users to create symlinks to the targets :-/
    echo $( realpath --no-symlinks "$target" )
}

# ---------------------------------------------------------------------

function print_help {
    echo "`basename "$0"` {options}"
    cat <<EOM
  Build and launch the "asl-rulebook2" container.

    -p  --port          Web server port number.
    -d  --data          Data directory.
        --qa            Q+A+ directory (default = \$DATA/q+a/)
        --errata        Errata directory (default = \$DATA/errata/)
        --annotations   User-defined annotations (default = \$DATA/annotations.json)
        --asop          ASOP directory (default = \$DATA/asop/)

    -t  --tag           Docker image tag.
        --name          Docker container name.
    -d  --detach        Detach from the container and let it run in the background.
        --no-build      Launch the container as-is (i.e. without rebuilding the image first).
EOM
}

# ---------------------------------------------------------------------

main "$@"
