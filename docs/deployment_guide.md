# Deployment Guide

This guide covers deploying the Enterprise AI Ops Copilot, from local Docker to a full AWS production deployment.

---

## 1. Local Docker

The fastest way to run the full app in a container.

```bash
cp .env.example .env
# Fill in AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION, BEDROCK_CHAT_MODEL_ID

docker build -t enterprise-ai-ops-copilot .
docker run -p 8000:8000 --env-file .env enterprise-ai-ops-copilot
```

Verify:
```bash
curl http://localhost:8000/health
```

For the production-style stack with OpenSearch:
```bash
docker compose --profile prod up --build
```

---

## 2. Docker Hub (via CI/CD)

The GitHub Actions workflow [docker-build.yml](../.github/workflows/docker-build.yml) automatically builds and pushes the image on every push to `main`.

**Required GitHub secrets** (Settings → Secrets and variables → Actions):

| Secret | Value |
|---|---|
| `DOCKERHUB_USERNAME` | Your Docker Hub username |
| `DOCKERHUB_TOKEN` | A Docker Hub access token (not your password) |

Pull the published image:
```bash
docker pull supun0806/enterprise-ai-ops-copilot:latest
```

---

## 3. AWS Production Deployment

The full AWS architecture is defined in [infra/](../infra/). See [infra/architecture.md](../infra/architecture.md) for the design.

### Prerequisites

- AWS CLI configured (`aws configure`)
- Terraform CLI installed (`terraform >= 1.5`)
- Docker image pushed to ECR or Docker Hub
- Bedrock model access enabled in your region

### Step 1 — Provision infrastructure with Terraform

```bash
cd infra/terraform

terraform init
terraform plan      # review what will be created
terraform apply     # creates S3, DynamoDB, ECS cluster, OpenSearch, IAM
```

> **Cost warning:** `terraform apply` creates an always-on OpenSearch domain (~$25/mo) and may add NAT Gateway costs. For a portfolio, reviewing the plan with `terraform plan` demonstrates the competency without incurring cost. Run `terraform destroy` to tear everything down.

Capture the outputs:
```bash
terraform output
# documents_bucket, opensearch_endpoint, ecs_cluster_arn, ecs_task_role_arn, ...
```

### Step 2 — Store secrets

Put integration credentials in AWS Secrets Manager and config in SSM Parameter Store:

```bash
aws ssm put-parameter --name "/copilot/opensearch-endpoint" \
  --value "$(terraform output -raw opensearch_endpoint)" --type String

aws ssm put-parameter --name "/copilot/bedrock-chat-model" \
  --value "arn:aws:bedrock:eu-north-1:ACCOUNT:inference-profile/eu.anthropic.claude-haiku-4-5-20251001-v1:0" \
  --type String

aws secretsmanager create-secret --name "/copilot/servicenow-password" \
  --secret-string "your-servicenow-password"
```

### Step 3 — Register the ECS task definition

The task definition template is at [infra/ecs/task_definition.json](../infra/ecs/task_definition.json). Substitute the `${...}` placeholders with the Terraform outputs and SSM/Secrets ARNs, then register it:

```bash
aws ecs register-task-definition --cli-input-json file://infra/ecs/task_definition.json
```

### Step 4 — Create the ECS service behind an ALB

```bash
aws ecs create-service \
  --cluster enterprise-ai-ops-copilot-dev \
  --service-name api \
  --task-definition enterprise-ai-ops-copilot \
  --desired-count 2 \
  --launch-type FARGATE \
  --load-balancers targetGroupArn=<alb-target-group>,containerName=api,containerPort=8000 \
  --network-configuration "awsvpcConfiguration={subnets=[...],securityGroups=[...]}"
```

### Step 5 — Deploy the ingestion pipeline

1. Package and deploy the Lambda functions in [infra/lambda/](../infra/lambda/).
2. Create the Step Functions state machine from [infra/aws_stepfunctions_definition.json](../infra/aws_stepfunctions_definition.json), substituting the `${...}` ARN placeholders.
3. Create an EventBridge rule that starts the state machine on `s3:ObjectCreated` events for the documents bucket.

### Step 6 — Verify

```bash
# Upload a document to trigger ingestion
aws s3 cp data/raw/runbooks/payment_api_runbook.md \
  s3://$(terraform output -raw documents_bucket)/runbooks/

# Watch the Step Functions execution in the AWS Console

# Hit the API via the ALB DNS name
curl https://<alb-dns-name>/health
```

---

## 4. Teardown

```bash
cd infra/terraform
terraform destroy
```

This removes all provisioned AWS resources. Always run this after a demo to avoid ongoing charges.

---

## Deployment Checklist

- [ ] Bedrock model access enabled in target region
- [ ] Docker image built and pushed
- [ ] `terraform apply` succeeded
- [ ] Secrets stored in Secrets Manager / SSM
- [ ] ECS task definition registered
- [ ] ECS service running behind ALB with healthy targets
- [ ] Step Functions + EventBridge ingestion wired up
- [ ] `/health` returns 200 via the ALB
- [ ] A test document upload triggers a successful ingestion run
- [ ] `terraform destroy` run after the demo (if cost-sensitive)
