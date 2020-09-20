set -eux

export COMPOSE_PROJECT_NAME=airq_test

function usage() {
    echo "Usage:"
    echo "  ./test                  Run all tests."
    echo "  ./test path.to.module   Run tests for the given module."
    echo ""
    echo "Options:"
    echo "  -b --build      Rebuild containers before running tests."
    echo "  -d --down       Stop test containers."
    echo "  -h --help       Display this message."
    exit
}

build=false
down=false
module=''

is_first=true
while [[ $# -gt 0 ]]
do
  key="$1"
  case $key in
      -h|--help)
      usage
      ;;
      -b|--build)
      build=true
      shift
      ;;
      -d|--down)
      down=true
      shift
      ;;
      *)
      if $is_first; then
        module=$key
        shift
      else 
        usage
      fi
      ;;
  esac
  is_first=false
done

if $build && $down; then
    echo "You cannot specify the -b and -d options together."
    exit
fi

containers=`docker ps`
running=false
if echo $containers | grep airq_test; then 
  running=true
fi

if $down; then
    if $running; then
        docker-compose down
    else
        echo "Containers are not running."
    fi

    exit
fi

if ! $running; then
    cmd="docker-compose -f docker-compose.yml -f docker-compose.test.yml up -d"
    if $build; then
        cmd+=" --build"
    fi

    eval $cmd

    printf "Waiting for server"

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

    docker-compose exec -T -e SKIP_FORCE_REBUILD=1 app python3 -m unittest tests.test_sync.SyncTestCase.test_sync
fi

if [ "$module" ]; then
  echo "Running tests for ${module}"
  docker-compose exec -T app python3 -m unittest ${module}
else
  echo "Running all tests"
  docker-compose exec -T app python3 -m unittest discover
fi

exit $?
