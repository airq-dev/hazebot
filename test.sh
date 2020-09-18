# TODO: Build opt
export COMPOSE_PROJECT_NAME=airq_test
export COMPOSE_FILE=docker-compose.test.yml

function usage() {
    echo "Usage:"
    echo "    ./test                      Run tests."
    echo "    ./test -b                   Rebuild docker, then run tests."
    echo "    ./test -d                   Shut down test container."
    echo "    ./test -h                   Display this help message."
    exit
}

build=false;
down=false;
while getopts ":bdh" opt; do
  case ${opt} in
    h ) 
      usage
      ;;
    b ) 
      build=true
      ;;
    d ) 
      down=true
      ;;
    \? ) 
      usage
      ;;
  esac
done

if $build && $down; then
    echo "You cannot specify the -b and -d options together."
    exit
fi

container=`docker ps | grep airq_test_app`

if $down; then
    if [ "$container" ]; then
        docker-compose down
    else
        echo "Containers are not running."
    fi

    exit
fi

if [ -z "$container" ]; then
    cmd="docker-compose up -d"
    if $build; then
        cmd+=" --build"
    fi

    eval $cmd

    printf "Waiting for server"

    # Wait for server to start
    attempt_counter=0
    max_attempts=20

    until $(curl --output /dev/null --silent --head --fail http://localhost:8080); do
        if [ ${attempt_counter} -eq ${max_attempts} ]; then
          echo "Server failed to start in time"
          exit 1
        fi

        printf '.'
        attempt_counter=$(($attempt_counter+1))
        sleep 1
    done

    echo ""

    docker-compose exec app flask sync --only-if-empty
fi

docker-compose exec app python3 -m unittest tests/test_sync.py

# if [ ! $volume ]; then 
#     docker-compose --file docker-compose.test.yml exec app flask sync --geography
# fi