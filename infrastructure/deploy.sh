#!/bin/bash
# ----------------------------------------------------------------------------
# AWS ECS & ALB Deployment Commands for EaseToLearn Factory
# ----------------------------------------------------------------------------
# Note: Replace variables (ACCOUNT_ID, etc.) before running this directly.
# ----------------------------------------------------------------------------

export AWS_REGION="ap-south-1"
export ACCOUNT_ID="123456789012" # REPLACE WITH AWS ACCOUNT ID
export CLUSTER_NAME="easetolearn-production"
export ECR_REPO="easetolearn-factory"

echo "1. Building and pushing Docker container to ECR..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com
docker build -t $ECR_REPO .
docker tag $ECR_REPO:latest $ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO:latest
docker push $ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO:latest

echo "2. Registering new ECS Task Definition..."
# Requires replacing <ACCOUNT_ID> and <EFS_FS_ID> inside ecs-task-def.json
aws ecs register-task-definition --cli-input-json file://infrastructure/ecs-task-def.json

echo "3. Updating ECS Service..."
# Assuming service already exists. If not, use 'aws ecs create-service'
aws ecs update-service \
    --cluster $CLUSTER_NAME \
    --service factory-service \
    --task-definition easetolearn-factory \
    --force-new-deployment

echo "Note: The Application Load Balancer target group must be checking /health"
echo "Deployment triggered. Monitor logs in CloudWatch under /ecs/easetolearn-factory"
