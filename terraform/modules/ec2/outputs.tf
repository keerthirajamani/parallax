output "instance_id" {
  value = aws_instance.signal_engine.id
}

output "public_ip" {
  value = aws_instance.signal_engine.public_ip
}
