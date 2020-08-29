#
# IMPORTANT: 
#
# Before you run this you must have a valid
# set of AWS credentials. Run `aws configure --profile airq` 
# and input those keys. Choose `us-west-1` as your region.
#
# This command will create 1 VPC and 2 Subnets. 
# You'll need to open up the `ecs-params.yml` file and paste them in.
#
# TODO: Use Terraform?

cd ..

ecs-cli up \
    --aws-profile airq \
    --ecs-profile airq \
    --cluster-config airq \
    --capability-iam \



# ecs-cli compose --file docker-compose.prod.yml \
#     --project-name app \
#     service down \

# ecs-cli compose --file docker-compose.prod.yml \
#     --project-name app \
#     service up \
#     --target-group-arn arn:aws:elasticloadbalancing:us-east-1:968940811236:targetgroup/servicesTargetGroupNGINX/69299638b8c485d1 \
#     --container-name nginx \
#     --container-port 80