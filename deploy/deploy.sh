TAG=`git rev-parse --short HEAD`
ECR_ROOT="146486422038.dkr.ecr.us-west-1.amazonaws.com"
REPO="$ECR_ROOT/airq/app"

cd ..
docker-compose -f docker-compose.prod.yml build
docker tag airq_app "$REPO":"$TAG"
aws ecr get-login-password | docker login --username AWS --password-stdin $ECR_ROOT
docker push $REPO