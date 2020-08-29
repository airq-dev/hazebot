TAG=`git rev-parse --short HEAD`
ECR_ROOT="146486422038.dkr.ecr.us-west-1.amazonaws.com"
APP_REPO="$ECR_ROOT/airq/app"
NGINX_REPO="$ECR_ROOT/airq/nginx"

cd ..
docker-compose -f docker-compose.prod.yml build
docker tag airq_app "$APP_REPO":"$TAG"
docker tag airq_nginx "$NGINX_REPO":"$TAG"
aws ecr get-login-password | docker login --username AWS --password-stdin $ECR_ROOT
docker push $APP_REPO
docker push $NGINX_REPO