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

locals {
  demo_subnets = var.enable_service_demo ? tomap({
    alb_a = { az_index = 0, network = 10 }
    alb_b = { az_index = 1, network = 11 }
    app_a = { az_index = 0, network = 12 }
    app_b = { az_index = 1, network = 13 }
    db_a  = { az_index = 0, network = 14 }
    db_b  = { az_index = 1, network = 15 }
  }) : tomap({})
}

resource "aws_subnet" "service_demo_tier" {
  for_each                = local.demo_subnets
  vpc_id                  = aws_vpc.sandbox.id
  cidr_block              = cidrsubnet(var.cidr, 8, each.value.network)
  availability_zone       = data.aws_availability_zones.demo[0].names[each.value.az_index]
  map_public_ip_on_launch = false

  tags = { Name = "${var.name}-${each.key}" }
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
  count             = var.enable_service_demo && var.portal_replay == null ? 1 : 0
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
  from_port                    = local.backend_port
  to_port                      = local.backend_port
}

resource "aws_vpc_security_group_ingress_rule" "app_alb" {
  count                        = var.enable_service_demo ? 1 : 0
  security_group_id            = aws_security_group.service_demo["app"].id
  referenced_security_group_id = aws_security_group.service_demo["alb"].id
  ip_protocol                  = "tcp"
  from_port                    = local.backend_port
  to_port                      = local.backend_port
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
  subnets            = [aws_subnet.service_demo_tier["alb_a"].id, aws_subnet.service_demo_tier["alb_b"].id]
  security_groups    = [aws_security_group.service_demo["alb"].id]
}

resource "aws_lb_target_group" "service_demo" {
  count       = var.enable_service_demo ? 1 : 0
  name        = var.name
  port        = local.backend_port
  protocol    = "HTTP"
  target_type = "instance"
  vpc_id      = aws_vpc.sandbox.id

  health_check {
    path = var.portal_replay != null ? "/health" : "/"
  }
}

resource "aws_lb_listener" "service_demo" {
  count             = var.enable_service_demo && var.portal_replay == null ? 1 : 0
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
  user_data              = var.portal_replay == null ? base64encode(replace(file("${path.module}/service-demo.sh"), "\r\n", "\n")) : local.portal_user_data

  dynamic "iam_instance_profile" {
    for_each = var.portal_replay == null ? [] : [var.portal_replay.instance_profile]
    content {
      name = iam_instance_profile.value
    }
  }

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
    precondition {
      condition     = var.portal_replay == null ? true : length(local.portal_user_data) <= 21844
      error_message = "Portal user data exceeds the EC2 16 KiB limit."
    }
  }
}

resource "aws_autoscaling_group" "service_demo" {
  count                     = var.enable_service_demo ? 1 : 0
  name                      = var.name
  min_size                  = local.portal_enabled && !var.start_portal_instances ? 0 : 2
  max_size                  = 2
  desired_capacity          = local.portal_enabled && !var.start_portal_instances ? 0 : 2
  vpc_zone_identifier       = [aws_subnet.service_demo_tier["app_a"].id, aws_subnet.service_demo_tier["app_b"].id]
  target_group_arns         = [aws_lb_target_group.service_demo[0].arn]
  health_check_type         = "ELB"
  health_check_grace_period = var.portal_replay == null ? null : 900

  depends_on = [
    aws_lb_listener.service_demo,
    aws_lb_listener.portal,
    aws_route.portal_nat,
    aws_route_table_association.portal_app,
    aws_secretsmanager_secret_policy.portal,
    aws_vpc_security_group_egress_rule.portal_https,
    aws_cloudwatch_log_group.portal,
  ]

  launch_template {
    id      = aws_launch_template.service_demo[0].id
    version = aws_launch_template.service_demo[0].latest_version
  }
}

resource "aws_db_subnet_group" "service_demo" {
  count      = var.enable_service_demo ? 1 : 0
  name       = var.name
  subnet_ids = [aws_subnet.service_demo_tier["db_a"].id, aws_subnet.service_demo_tier["db_b"].id]
}

resource "aws_db_parameter_group" "service_demo" {
  count  = var.enable_service_demo ? 1 : 0
  name   = var.name
  family = "mysql8.4"

  parameter {
    name  = "require_secure_transport"
    value = "1"
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
