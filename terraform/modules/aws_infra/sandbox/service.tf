variable "enable_service_demo" {
  type    = bool
  default = false
}

variable "demo_ami_id" {
  description = "Amazon Linux 2023 x86_64 AMI with Python 3 installed."
  type        = string
  default     = null
}

data "aws_availability_zones" "demo" {
  count = var.enable_service_demo ? 1 : 0
  state = "available"
}

resource "aws_subnet" "service_demo" {
  count                   = var.enable_service_demo ? 2 : 0
  vpc_id                  = aws_vpc.sandbox.id
  cidr_block              = cidrsubnet(var.cidr, 8, count.index + 10)
  availability_zone       = data.aws_availability_zones.demo[0].names[count.index]
  map_public_ip_on_launch = false
}

locals {
  demo_groups = var.enable_service_demo ? toset(["alb", "app", "db"]) : toset([])
}

resource "aws_security_group" "service_demo" {
  for_each = local.demo_groups
  name     = "${var.name}-${each.key}"
  vpc_id   = aws_vpc.sandbox.id
}

resource "aws_vpc_security_group_ingress_rule" "alb_http" {
  count             = var.enable_service_demo ? 1 : 0
  security_group_id = aws_security_group.service_demo["alb"].id
  cidr_ipv4         = var.cidr
  ip_protocol       = "tcp"
  from_port         = 80
  to_port           = 80
}

resource "aws_vpc_security_group_egress_rule" "alb_app" {
  count                        = var.enable_service_demo ? 1 : 0
  security_group_id            = aws_security_group.service_demo["alb"].id
  referenced_security_group_id = aws_security_group.service_demo["app"].id
  ip_protocol                  = "tcp"
  from_port                    = 8080
  to_port                      = 8080
}

resource "aws_vpc_security_group_ingress_rule" "app_alb" {
  count                        = var.enable_service_demo ? 1 : 0
  security_group_id            = aws_security_group.service_demo["app"].id
  referenced_security_group_id = aws_security_group.service_demo["alb"].id
  ip_protocol                  = "tcp"
  from_port                    = 8080
  to_port                      = 8080
}

resource "aws_vpc_security_group_egress_rule" "app_db" {
  count                        = var.enable_service_demo ? 1 : 0
  security_group_id            = aws_security_group.service_demo["app"].id
  referenced_security_group_id = aws_security_group.service_demo["db"].id
  ip_protocol                  = "tcp"
  from_port                    = 3306
  to_port                      = 3306
}

resource "aws_vpc_security_group_ingress_rule" "db_app" {
  count                        = var.enable_service_demo ? 1 : 0
  security_group_id            = aws_security_group.service_demo["db"].id
  referenced_security_group_id = aws_security_group.service_demo["app"].id
  ip_protocol                  = "tcp"
  from_port                    = 3306
  to_port                      = 3306
}

resource "aws_lb" "service_demo" {
  count              = var.enable_service_demo ? 1 : 0
  name               = var.name
  internal           = true
  load_balancer_type = "application"
  subnets            = aws_subnet.service_demo[*].id
  security_groups    = [aws_security_group.service_demo["alb"].id]
}

resource "aws_lb_target_group" "service_demo" {
  count       = var.enable_service_demo ? 1 : 0
  name        = var.name
  port        = 8080
  protocol    = "HTTP"
  target_type = "instance"
  vpc_id      = aws_vpc.sandbox.id

  health_check {
    path = "/"
  }
}

resource "aws_lb_listener" "service_demo" {
  count             = var.enable_service_demo ? 1 : 0
  load_balancer_arn = aws_lb.service_demo[0].arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.service_demo[0].arn
  }
}

resource "aws_launch_template" "service_demo" {
  count                  = var.enable_service_demo ? 1 : 0
  name_prefix            = "${var.name}-"
  image_id               = var.demo_ami_id
  instance_type          = "t3.micro"
  vpc_security_group_ids = [aws_security_group.service_demo["app"].id]
  user_data              = base64encode(replace(file("${path.module}/service-demo.sh"), "\r\n", "\n"))

  metadata_options {
    http_tokens = "required"
  }

  credit_specification {
    cpu_credits = "standard"
  }

  lifecycle {
    precondition {
      condition     = var.demo_ami_id != null
      error_message = "Set demo_ami_id when enabling the isolated service demo."
    }
  }
}

resource "aws_autoscaling_group" "service_demo" {
  count               = var.enable_service_demo ? 1 : 0
  name                = var.name
  min_size            = 2
  max_size            = 2
  desired_capacity    = 2
  vpc_zone_identifier = aws_subnet.service_demo[*].id
  target_group_arns   = [aws_lb_target_group.service_demo[0].arn]
  health_check_type   = "ELB"

  depends_on = [aws_lb_listener.service_demo]

  launch_template {
    id      = aws_launch_template.service_demo[0].id
    version = aws_launch_template.service_demo[0].latest_version
  }
}

resource "aws_db_subnet_group" "service_demo" {
  count      = var.enable_service_demo ? 1 : 0
  name       = var.name
  subnet_ids = aws_subnet.service_demo[*].id
}

resource "aws_db_parameter_group" "service_demo" {
  count  = var.enable_service_demo ? 1 : 0
  name   = var.name
  family = "mysql8.4"

  parameter {
    name  = "require_secure_transport"
    value = "ON"
  }
}

resource "aws_db_instance" "service_demo" {
  count                       = var.enable_service_demo ? 1 : 0
  identifier                  = var.name
  engine                      = "mysql"
  engine_version              = "8.4.13"
  instance_class              = "db.t3.micro"
  allocated_storage           = 20
  storage_type                = "gp3"
  storage_encrypted           = true
  db_subnet_group_name        = aws_db_subnet_group.service_demo[0].name
  parameter_group_name        = aws_db_parameter_group.service_demo[0].name
  vpc_security_group_ids      = [aws_security_group.service_demo["db"].id]
  username                    = "ninjasecadmin"
  manage_master_user_password = true
  publicly_accessible         = false
  multi_az                    = false
  backup_retention_period     = 0
  skip_final_snapshot         = true
}

output "service_demo" {
  value = var.enable_service_demo ? {
    asg_name         = aws_autoscaling_group.service_demo[0].name
    target_group_arn = aws_lb_target_group.service_demo[0].arn
    alb_dns          = aws_lb.service_demo[0].dns_name
    rds_arn          = aws_db_instance.service_demo[0].arn
  } : null
}
