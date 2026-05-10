output "elastic_ip" {
  value       = aws_eip.parallax.public_ip
  description = "Static public IP — use this as EC2_HOST in GitHub secrets"
}

output "instance_id" {
  value = aws_instance.parallax.id
}

output "instance_name" {
  value = aws_instance.parallax.tags["Name"]
}
