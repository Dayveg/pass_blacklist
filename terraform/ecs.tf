# Grupo de logs en Amazon CloudWatch para los contenedores Fargate
resource "aws_cloudwatch_log_group" "ecs_logs" {
  name              = "/ecs/blacklist-task-def"
  retention_in_days = 7
}

# Cluster Serverless en Amazon ECS (AWS Fargate)
resource "aws_ecs_cluster" "blacklist_cluster" {
  name = "${var.app_name}-cluster"
}

# Definicion de Tarea (Task Definition) para AWS Fargate
resource "aws_ecs_task_definition" "blacklist_task" {
  family                   = "blacklist-task-def"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "256"
  memory                   = "512"
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn

  container_definitions = jsonencode([
    {
      name      = "blacklist-container"
      image     = "${aws_ecr_repository.blacklist.repository_url}:latest"
      essential = true
      portMappings = [
        {
          containerPort = 5000
          hostPort      = 5000
          protocol      = "tcp"
        }
      ]
      environment = [
        {
          name  = "STATIC_BEARER_TOKEN"
          value = "token-estatico-secreto-12345"
        },
        {
          name  = "JWT_SECRET_KEY"
          value = "super-secret-uniandes-key-2026"
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.ecs_logs.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }
    }
  ])
}

# Servicio en Amazon ECS Fargate conectado al Application Load Balancer
resource "aws_ecs_service" "blacklist_service" {
  name            = "${var.app_name}-service"
  cluster         = aws_ecs_cluster.blacklist_cluster.id
  task_definition = aws_ecs_task_definition.blacklist_task.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = data.aws_subnets.default.ids
    security_groups  = [aws_security_group.fargate_sg.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.blacklist_tg.arn
    container_name   = "blacklist-container"
    container_port   = 5000
  }

  depends_on = [aws_lb_listener.http]
}
