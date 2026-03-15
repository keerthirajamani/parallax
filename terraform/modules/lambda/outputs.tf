output "lambda_name" {
  value = aws_lambda_function.webhook.function_name
}

output "lambda_arn" {
  value = aws_lambda_function.webhook.arn
}
