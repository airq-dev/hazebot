aws ecs update-service \
    --service app \
    --cluster airq \
    --region us-west-1 \
    --force-new-deployment \
    --desired-count 2 \
    --deployment-configuration minimumHealthyPercent=50,maximumPercent=100 \
    --profile airq
