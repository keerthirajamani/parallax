data "archive_file" "lambda_zip" {

  type        = "zip"
  source_dir  = "${path.root}/../lambda_handlers"
  output_path = "${path.module}/lambda.zip"

}

resource "aws_lambda_function" "webhook" {

  function_name = var.lambda_function_name
  role          = var.role_arn

  runtime = "python3.10"
  handler = "webhook_trigger.lambda_handler"

  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256

  memory_size = var.lambda_memory_size
  timeout     = var.lambda_timeout
  environment {
    variables = {
      ENVIRONMENT = var.environment
    }
  }

}
