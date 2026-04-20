#!/bin/bash
# ----------------------------------------------------------------------------
# AWS ECS & ALB Deployment Commands for EaseToLearn Factory
# ----------------------------------------------------------------------------
# ----------------------------------------------------------------------------
# Note: Variables can be overridden by environment vars (useful for Jenkins/CI).
# ----------------------------------------------------------------------------

export AWS_REGION="${AWS_REGION:-ap-south-1}"
export PROJECT_NAME="${PROJECT_NAME:-easetolearn-factory}"
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
export ECR_URL="${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${PROJECT_NAME}"
export IMAGE_TAG=$(git rev-parse --short HEAD || echo "latest")

echo "2. Ensuring ECR repository exists..."
aws ecr describe-repositories --repository-names $PROJECT_NAME || \
    aws ecr create-repository --repository-name $PROJECT_NAME

echo "3. Building and pushing Docker container..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_URL
docker build -t $PROJECT_NAME .
docker tag $PROJECT_NAME:latest $ECR_URL:latest
docker tag $PROJECT_NAME:latest $ECR_URL:$IMAGE_TAG
docker push $ECR_URL:latest
docker push $ECR_URL:$IMAGE_TAG

echo "4. Retrieving Infrastructure Outputs (EFS, Roles)..."
export EFS_FS_ID=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --query "Stacks[0].Outputs[?OutputKey=='EFSFileSystemId'].OutputValue" --output text)
export TASK_EXEC_ROLE=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --query "Stacks[0].Outputs[?OutputKey=='ECSTaskExecutionRoleArn'].OutputValue" --output text)
export TASK_ROLE=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --query "Stacks[0].Outputs[?OutputKey=='ECSTaskRoleArn'].OutputValue" --output text)
export S3_BUCKET=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --query "Stacks[0].Outputs[?OutputKey=='VideoBucketName'].OutputValue" --output text)

echo "5. Preparing Task Definition (Token Injection)..."
cat infrastructure/ecs-task-def.json | \
    sed "s|arn:aws:iam::<ACCOUNT_ID>:role/ecsTaskExecutionRole|$TASK_EXEC_ROLE|g" | \
    sed "s|arn:aws:iam::<ACCOUNT_ID>:role/ecsTaskRole|$TASK_ROLE|g" | \
    sed "s|<ACCOUNT_ID>|$ACCOUNT_ID|g" | \
    sed "s|<AWS_REGION>|$AWS_REGION|g" | \
    sed "s|<EFS_FS_ID>|$EFS_FS_ID|g" | \
    sed "s|<S3_BUCKET>|$S3_BUCKET|g" \
    > infrastructure/task-def-temp.json


echo "6. Registering Task Definition..."
TASK_REVISION=$(aws ecs register-task-definition \
    --cli-input-json file://infrastructure/task-def-temp.json \
    --query "taskDefinition.taskDefinitionArn" --output text)

echo "7. Triggering ECS Service update with revision: $TASK_REVISION"
aws ecs update-service \
    --cluster $CLUSTER_NAME \
    --service factory-service \
    --task-definition $TASK_REVISION \
    --force-new-deployment

echo "Note: The Application Load Balancer target group must be checking /health"
echo "Deployment successful. Monitor logs in CloudWatch under /ecs/${PROJECT_NAME}"
rm infrastructure/task-def-temp.json

