cd ..

ecs-cli compose \
    --file docker-compose.prod.yml \
    --project-name app \
    service up \
    --aws-profile airq \
    --cluster-config airq \
    --ecs-profile airq \
    --target-group-arn arn:aws:elasticloadbalancing:us-west-1:146486422038:targetgroup/airq-tg/a56258a9bd7c3ec6 \
    --container-name nginx \
    --container-port 80