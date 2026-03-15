output "vpc_id" {
  value = module.vpc.vpc_id
}

output "ec2_instance_id" {
  value = module.ec2.instance_id
}

output "lambda_function_name" {
  value = module.lambda.lambda_name
}
