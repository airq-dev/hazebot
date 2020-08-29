ACCESS_KEY=`cat .env.prod | grep AWS_ACCESS_KEY_ID= | sed s/AWS_ACCESS_KEY_ID=//`
SECRET_KEY=`cat .env.prod | grep AWS_SECRET_ACCESS_KEY= | sed s/AWS_SECRET_ACCESS_KEY=//`

ecs-cli configure profile \
    --profile-name airq \
    --access-key $ACCESS_KEY \
    --secret-key $SECRET_KEY

ecs-cli configure \
    --region us-west-1 \
    --cluster airq \
    --config-name airq \
    --default-launch-type FARGATE
