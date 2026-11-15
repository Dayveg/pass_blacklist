output "alb_url" {
  description = "URL publica del Application Load Balancer en AWS Fargate para consumir en Postman"
  value       = "http://${aws_lb.blacklist_alb.dns_name}"
}

output "ecr_repository_url" {
  description = "URI del repositorio en Amazon ECR"
  value       = aws_ecr_repository.blacklist.repository_url
}

output "ecs_cluster_name" {
  description = "Nombre del Cluster en Amazon ECS Fargate"
  value       = aws_ecs_cluster.blacklist_cluster.name
}

output "ecs_service_name" {
  description = "Nombre del Servicio en Amazon ECS Fargate"
  value       = aws_ecs_service.blacklist_service.name
}
