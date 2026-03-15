# 1. Zip the source folder
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = var.source_dir
  output_path = "${path.module}/../../webhook_lambda.zip"
}

# 2. Create the Lambda Function using the zip archive
resource "aws_lambda_function" "lambda" {
  function_name    = var.function_name
  role             = var.role_arn
  handler          = "webhook_trigger.lambda_handler"
  runtime          = "python3.10"
  
  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256

  memory_size      = var.memory_size
  timeout          = var.timeout
}