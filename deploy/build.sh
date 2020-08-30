ECR_ROOT="146486422038.dkr.ecr.us-west-1.amazonaws.com"

cd ..
docker-compose -f docker-compose.prod.yml build
aws ecr get-login-password | docker login --username AWS --password-stdin $ECR_ROOT
docker-compose -f docker-compose.prod.yml push