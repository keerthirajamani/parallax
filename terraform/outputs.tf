# ─────────────────────────────
# Lambda Outputs
# ─────────────────────────────
output "lambda_function_arn" {
  value = aws_lambda_function.webhook_lambda.arn
}

output "lambda_function_name" {
  value = aws_lambda_function.webhook_lambda.function_name
}

# ─────────────────────────────
# EC2 Outputs
# ─────────────────────────────
output "ec2_instance_id" {
  value = aws_instance.signal_engine.id
}

output "ec2_public_ip" {
  value = aws_instance.signal_engine.public_ip
}
