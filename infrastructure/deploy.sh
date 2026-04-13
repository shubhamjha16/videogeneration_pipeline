#!/bin/bash
# ----------------------------------------------------------------------------
# AWS ECS & ALB Deployment Commands for EaseToLearn Factory
# ----------------------------------------------------------------------------
# Note: Replace variables (ACCOUNT_ID, etc.) before running this directly.
# ----------------------------------------------------------------------------

export AWS_REGION="ap-south-1"
export PROJECT_NAME="easetolearn-factory"
export CLUSTER_NAME="${PROJECT_NAME}-cluster"
export STACK_NAME="${PROJECT_NAME}-production-stack"

echo "1. Deploying/Updating AWS Infrastructure Stack (CloudFormation)..."
aws cloudformation deploy \
    --template-file infrastructure/cloudformation-stack.yaml \
    --stack-name $STACK_NAME \
    --capabilities CAPABILITY_NAMED_IAM \
    --parameter-overrides ProjectName=$PROJECT_NAME

# Extract outputs for deployment
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

echo "4. Triggering ECS Task update..."
aws ecs update-service \
    --cluster $CLUSTER_NAME \
    --service factory-service \
    --force-new-deployment

echo "Note: The Application Load Balancer target group must be checking /health"
echo "Deployment triggered. Monitor logs in CloudWatch under /ecs/easetolearn-factory"
