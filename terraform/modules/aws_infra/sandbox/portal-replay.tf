variable "portal_replay" {
  description = "Settings for running the actual portal in the isolated service topology."
  type = object({
    instance_profile  = string
    instance_role_arn = string
    certificate_arn   = string
    archive_path      = string
  })
  default = null
}

variable "start_portal_instances" {
  description = "Start the application nodes after the isolated database and runtime secret are initialized."
  type        = bool
  default     = false
}

locals {
  portal_enabled = var.enable_service_demo && var.portal_replay != null
  backend_port   = var.portal_replay == null ? 8080 : 80
  portal_user_data = local.portal_enabled ? base64gzip(templatefile("${path.module}/portal-replay.sh.tftpl", {
    archive_b64 = filebase64(var.portal_replay.archive_path)
    bootstrap   = base64encode(replace(replace(replace(file("${path.module}/../../../../scripts/bootstrap-aws-app.sh"), "\r\n", "\n"), "/ninjasec/", "/ninjasec-iac-service-demo/"), "NINJA-SEC/Host", "NINJA-SEC/IaCReplay"))
    secret_arn  = aws_secretsmanager_secret.portal[0].arn
    database    = aws_db_instance.service_demo[0].address
    region      = data.aws_region.portal[0].name
  })) : null
}

data "aws_region" "portal" {
  count = local.portal_enabled ? 1 : 0
}

resource "aws_internet_gateway" "portal" {
  count  = local.portal_enabled ? 1 : 0
  vpc_id = aws_vpc.sandbox.id
}

resource "aws_subnet" "portal_egress" {
  count             = local.portal_enabled ? 1 : 0
  vpc_id            = aws_vpc.sandbox.id
  cidr_block        = cidrsubnet(var.cidr, 8, 16)
  availability_zone = data.aws_availability_zones.demo[0].names[0]
}

resource "aws_eip" "portal_egress" {
  count  = local.portal_enabled ? 1 : 0
  domain = "vpc"
}

resource "aws_nat_gateway" "portal" {
  count         = local.portal_enabled ? 1 : 0
  subnet_id     = aws_subnet.portal_egress[0].id
  allocation_id = aws_eip.portal_egress[0].id
  depends_on    = [aws_internet_gateway.portal, aws_route.portal_internet, aws_route_table_association.portal_egress]
}

resource "aws_route_table" "portal_egress" {
  count  = local.portal_enabled ? 1 : 0
  vpc_id = aws_vpc.sandbox.id
}

resource "aws_route" "portal_internet" {
  count                  = local.portal_enabled ? 1 : 0
  route_table_id         = aws_route_table.portal_egress[0].id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.portal[0].id
}

resource "aws_route_table_association" "portal_egress" {
  count          = local.portal_enabled ? 1 : 0
  subnet_id      = aws_subnet.portal_egress[0].id
  route_table_id = aws_route_table.portal_egress[0].id
}

resource "aws_route_table" "portal_app" {
  count  = local.portal_enabled ? 1 : 0
  vpc_id = aws_vpc.sandbox.id
}

resource "aws_route" "portal_nat" {
  count                  = local.portal_enabled ? 1 : 0
  route_table_id         = aws_route_table.portal_app[0].id
  destination_cidr_block = "0.0.0.0/0"
  nat_gateway_id         = aws_nat_gateway.portal[0].id
}

resource "aws_route_table_association" "portal_app" {
  for_each       = local.portal_enabled ? toset(["app_a", "app_b"]) : toset([])
  subnet_id      = aws_subnet.service_demo_tier[each.key].id
  route_table_id = aws_route_table.portal_app[0].id
}

resource "aws_vpc_security_group_egress_rule" "portal_https" {
  count             = local.portal_enabled ? 1 : 0
  security_group_id = aws_security_group.service_demo["app"].id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "tcp"
  from_port         = 443
  to_port           = 443
}

resource "aws_vpc_security_group_ingress_rule" "portal_https" {
  count             = local.portal_enabled ? 1 : 0
  security_group_id = aws_security_group.service_demo["alb"].id
  cidr_ipv4         = var.cidr
  ip_protocol       = "tcp"
  from_port         = 443
  to_port           = 443
}

resource "aws_lb_listener" "portal" {
  count             = local.portal_enabled ? 1 : 0
  load_balancer_arn = aws_lb.service_demo[0].arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = var.portal_replay.certificate_arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.service_demo[0].arn
  }
}

resource "aws_security_group" "portal_endpoint" {
  count  = local.portal_enabled ? 1 : 0
  name   = "${var.name}-secrets-endpoint"
  vpc_id = aws_vpc.sandbox.id
}

resource "aws_vpc_security_group_ingress_rule" "portal_endpoint" {
  count                        = local.portal_enabled ? 1 : 0
  security_group_id            = aws_security_group.portal_endpoint[0].id
  referenced_security_group_id = aws_security_group.service_demo["app"].id
  ip_protocol                  = "tcp"
  from_port                    = 443
  to_port                      = 443
}

resource "aws_vpc_endpoint" "portal_secrets" {
  count               = local.portal_enabled ? 1 : 0
  vpc_id              = aws_vpc.sandbox.id
  vpc_endpoint_type   = "Interface"
  service_name        = "com.amazonaws.${data.aws_region.portal[0].name}.secretsmanager"
  subnet_ids          = [aws_subnet.service_demo_tier["app_a"].id]
  security_group_ids  = [aws_security_group.portal_endpoint[0].id]
  private_dns_enabled = true
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { AWS = var.portal_replay.instance_role_arn }
      Action    = ["secretsmanager:GetSecretValue"]
      Resource  = aws_secretsmanager_secret.portal[0].arn
    }]
  })
}

resource "aws_secretsmanager_secret" "portal" {
  count                   = local.portal_enabled ? 1 : 0
  name                    = "${var.name}/portal-runtime"
  recovery_window_in_days = 0
}

resource "aws_cloudwatch_log_group" "portal" {
  for_each          = local.portal_enabled ? toset(["waf/blocked", "nginx/access", "app"]) : toset([])
  name              = "/ninjasec-iac-service-demo/${each.key}"
  retention_in_days = 7
}

resource "aws_secretsmanager_secret_policy" "portal" {
  count               = local.portal_enabled ? 1 : 0
  secret_arn          = aws_secretsmanager_secret.portal[0].arn
  block_public_policy = true
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Deny"
      Principal = { AWS = var.portal_replay.instance_role_arn }
      Action    = "secretsmanager:GetSecretValue"
      Resource  = aws_secretsmanager_secret.portal[0].arn
      Condition = {
        StringNotEquals = { "aws:SourceVpce" = aws_vpc_endpoint.portal_secrets[0].id }
      }
    }]
  })
}

output "portal_replay" {
  value = local.portal_enabled ? {
    vpc_id             = aws_vpc.sandbox.id
    app_subnet_ids     = [aws_subnet.service_demo_tier["app_a"].id, aws_subnet.service_demo_tier["app_b"].id]
    app_security_group = aws_security_group.service_demo["app"].id
    portal_secret_arn  = aws_secretsmanager_secret.portal[0].arn
    database_host      = aws_db_instance.service_demo[0].address
  } : null
}
