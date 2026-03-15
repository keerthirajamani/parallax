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

resource "aws_lambda_function" "stop_ec2" {

  function_name = "stop-ec2-instances"
  role          = var.role_arn

  runtime = "python3.10"
  handler = "stop_ec2_instances.lambda_handler"

  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256

  memory_size = 128
  timeout     = 30
}

resource "aws_cloudwatch_event_rule" "every30mins" {
  name                = "EC2Stop30mins"
  schedule_expression = "cron(0/30 * ? * MON-FRI *)"
}

resource "aws_cloudwatch_event_target" "stop_ec2_target" {
  rule = aws_cloudwatch_event_rule.every30mins.name
  arn  = aws_lambda_function.stop_ec2.arn
}

resource "aws_lambda_permission" "allow_eventbridge_stop_ec2" {

  statement_id  = "AllowExecutionFromEventBridgeStopEC2"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.stop_ec2.function_name
  principal     = "events.amazonaws.com"

  source_arn = aws_cloudwatch_event_rule.every30mins.arn
}