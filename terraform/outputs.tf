# ─────────────────────────────
# Lambda Outputs
# ─────────────────────────────
output "lambda_function_arn" {
  value = module.lambda.function_arn
}

output "lambda_function_name" {
  value = module.lambda.function_name
}

# ─────────────────────────────
# EC2 Outputs
# ─────────────────────────────
output "ec2_instance_id" {
  value = module.ec2.instance_id
}

output "ec2_public_ip" {
  value = module.ec2.public_ip
}
