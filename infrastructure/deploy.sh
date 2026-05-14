#!/bin/bash
# ----------------------------------------------------------------------------
# AWS ECS & ALB Deployment Commands for EaseToLearn Factory
# Now supports dual-image deployment (Factory API + SearXNG Sidecar)
# ----------------------------------------------------------------------------

export AWS_REGION="${AWS_REGION:-ap-south-1}"
export PROJECT_NAME="${PROJECT_NAME:-easetolearn-factory}"
export SEARXNG_NAME="easetolearn-searxng"
export CLUSTER_NAME="${CLUSTER_NAME:-${PROJECT_NAME}-cluster}"
export STACK_NAME="${STACK_NAME:-${PROJECT_NAME}-production-stack}"

echo "1. Deploying/Updating AWS Infrastructure Stack (CloudFormation)..."
aws cloudformation deploy \
    --template-file infrastructure/cloudformation-stack.yaml \
    --stack-name $STACK_NAME \
    --capabilities CAPABILITY_NAMED_IAM \
    --parameter-overrides ProjectName=$PROJECT_NAME

# Extract outputs for deployment and task definition
export ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export ECR_BASE="${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
export IMAGE_TAG=$(git rev-parse --short HEAD || echo "latest")

echo "2. Ensuring ECR repositories exist..."
for repo in $PROJECT_NAME $SEARXNG_NAME; do
    aws ecr describe-repositories --repository-names $repo || \
        aws ecr create-repository --repository-name $repo
done

echo "3. Logging in to ECR..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_BASE

echo "4. Building and pushing Factory API..."
docker build -t $PROJECT_NAME .
docker tag $PROJECT_NAME:latest $ECR_BASE/$PROJECT_NAME:latest
docker tag $PROJECT_NAME:latest $ECR_BASE/$PROJECT_NAME:$IMAGE_TAG
docker push $ECR_BASE/$PROJECT_NAME:latest
docker push $ECR_BASE/$PROJECT_NAME:$IMAGE_TAG

echo "5. Building and pushing SearXNG Sidecar..."
docker build -t $SEARXNG_NAME ./searxng_standalone
docker tag $SEARXNG_NAME:latest $ECR_BASE/$SEARXNG_NAME:latest
docker tag $SEARXNG_NAME:latest $ECR_BASE/$SEARXNG_NAME:$IMAGE_TAG
docker push $ECR_BASE/$SEARXNG_NAME:latest
docker push $ECR_BASE/$SEARXNG_NAME:$IMAGE_TAG

echo "6. Retrieving Infrastructure Outputs (EFS, Roles, Redis, Service)..."
export EFS_FS_ID=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --query "Stacks[0].Outputs[?OutputKey=='EFSFileSystemId'].OutputValue" --output text)
export TASK_EXEC_ROLE=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --query "Stacks[0].Outputs[?OutputKey=='ECSTaskExecutionRoleArn'].OutputValue" --output text)
export TASK_ROLE=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --query "Stacks[0].Outputs[?OutputKey=='ECSTaskRoleArn'].OutputValue" --output text)
export S3_BUCKET=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --query "Stacks[0].Outputs[?OutputKey=='VideoBucketName'].OutputValue" --output text)
export REDIS_ENDPOINT=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --query "Stacks[0].Outputs[?OutputKey=='RedisEndpoint'].OutputValue" --output text)
export ECS_SERVICE_NAME=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --query "Stacks[0].Outputs[?OutputKey=='ECSServiceName'].OutputValue" --output text)

echo "6a. Wiring Redis endpoint into Secrets Manager..."
CURRENT_SECRET=$(aws secretsmanager get-secret-value --secret-id factory-keys --query SecretString --output text)
UPDATED_SECRET=$(echo "$CURRENT_SECRET" | python3 -c "
import sys, json
d = json.load(sys.stdin)
d['REDIS_URL'] = 'rediss://$REDIS_ENDPOINT:6379/0'
print(json.dumps(d))
")
aws secretsmanager update-secret --secret-id factory-keys --secret-string "$UPDATED_SECRET"
echo "   Redis URL set to: rediss://$REDIS_ENDPOINT:6379/0"

echo "7. Preparing Task Definition (Token Injection)..."
cat infrastructure/ecs-task-def.json | \
    sed "s|arn:aws:iam::<ACCOUNT_ID>:role/ecsTaskExecutionRole|$TASK_EXEC_ROLE|g" | \
    sed "s|arn:aws:iam::<ACCOUNT_ID>:role/ecsTaskRole|$TASK_ROLE|g" | \
    sed "s|<ACCOUNT_ID>|$ACCOUNT_ID|g" | \
    sed "s|<AWS_REGION>|$AWS_REGION|g" | \
    sed "s|<EFS_FS_ID>|$EFS_FS_ID|g" | \
    sed "s|<S3_BUCKET>|$S3_BUCKET|g" \
    > infrastructure/task-def-temp.json

echo "8. Registering Task Definition..."
TASK_REVISION=$(aws ecs register-task-definition \
    --cli-input-json file://infrastructure/task-def-temp.json \
    --query "taskDefinition.taskDefinitionArn" --output text)

echo "9. Triggering ECS Service update with revision: $TASK_REVISION"
aws ecs update-service \
    --cluster $CLUSTER_NAME \
    --service $ECS_SERVICE_NAME \
    --task-definition $TASK_REVISION \
    --force-new-deployment

echo "Note: Both images (Factory & SearXNG) are now live."
echo "Deployment successful. Monitor logs in CloudWatch under /ecs/${PROJECT_NAME}"
rm infrastructure/task-def-temp.json
