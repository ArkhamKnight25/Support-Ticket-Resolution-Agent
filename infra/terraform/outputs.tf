output "documents_bucket" {
  description = "S3 bucket for document uploads"
  value       = aws_s3_bucket.documents.id
}

output "ingestion_log_table" {
  description = "DynamoDB table tracking ingestion runs"
  value       = aws_dynamodb_table.ingestion_log.name
}

output "ecs_cluster_arn" {
  description = "ECS Fargate cluster ARN"
  value       = aws_ecs_cluster.main.arn
}

output "opensearch_endpoint" {
  description = "OpenSearch domain endpoint for the vector store"
  value       = aws_opensearch_domain.vectors.endpoint
}

output "opensearch_arn" {
  description = "OpenSearch domain ARN"
  value       = aws_opensearch_domain.vectors.arn
}

output "ecs_task_role_arn" {
  description = "IAM role ARN assumed by ECS tasks"
  value       = aws_iam_role.ecs_task.arn
}

output "cloudwatch_log_group" {
  description = "CloudWatch log group for the API"
  value       = aws_cloudwatch_log_group.api.name
}
