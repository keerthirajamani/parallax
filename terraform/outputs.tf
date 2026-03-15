output "vpc_id" {
  value = module.vpc.vpc_id
}

output "ec2_instance_id" {
  value = module.ec2.instance_id
}

output "lambda_function_name" {
  value = module.lambda.lambda_name
}

output "lambda_function_arn" {
  value = module.lambda.lambda_arn
}

output "ec2_public_ip" {
  value = module.ec2.public_ip
}