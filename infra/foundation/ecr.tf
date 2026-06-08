resource "aws_ecr_repository" "edge_agent" {
  name                 = var.ecr_edge_agent_repository_name
  image_tag_mutability = var.ecr_edge_agent_image_tag_mutability
  force_delete         = var.ecr_repository_force_delete

  image_scanning_configuration {
    scan_on_push = var.ecr_edge_agent_scan_on_push
  }

  encryption_configuration {
    encryption_type = "AES256"
  }
}

resource "aws_ecr_lifecycle_policy" "edge_agent" {
  repository = aws_ecr_repository.edge_agent.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Expire untagged edge-agent images after ${var.ecr_edge_agent_expire_untagged_days} days"
        selection = {
          tagStatus   = "untagged"
          countType   = "sinceImagePushed"
          countUnit   = "days"
          countNumber = var.ecr_edge_agent_expire_untagged_days
        }
        action = {
          type = "expire"
        }
      },
      {
        rulePriority = 2
        description  = "Keep the latest ${var.ecr_edge_agent_keep_sha_images} sha-tagged edge-agent images"
        selection = {
          tagStatus     = "tagged"
          tagPrefixList = ["sha-"]
          countType     = "imageCountMoreThan"
          countNumber   = var.ecr_edge_agent_keep_sha_images
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}

resource "aws_ecr_repository" "factory_a_log_adapter" {
  name                 = var.ecr_factory_a_log_adapter_repository_name
  image_tag_mutability = var.ecr_edge_agent_image_tag_mutability
  force_delete         = var.ecr_repository_force_delete

  image_scanning_configuration {
    scan_on_push = var.ecr_edge_agent_scan_on_push
  }

  encryption_configuration {
    encryption_type = "AES256"
  }
}

resource "aws_ecr_lifecycle_policy" "factory_a_log_adapter" {
  repository = aws_ecr_repository.factory_a_log_adapter.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Expire untagged factory-a-log-adapter images after ${var.ecr_edge_agent_expire_untagged_days} days"
        selection = {
          tagStatus   = "untagged"
          countType   = "sinceImagePushed"
          countUnit   = "days"
          countNumber = var.ecr_edge_agent_expire_untagged_days
        }
        action = {
          type = "expire"
        }
      },
      {
        rulePriority = 2
        description  = "Keep the latest ${var.ecr_edge_agent_keep_sha_images} sha-tagged factory-a-log-adapter images"
        selection = {
          tagStatus     = "tagged"
          tagPrefixList = ["sha-"]
          countType     = "imageCountMoreThan"
          countNumber   = var.ecr_edge_agent_keep_sha_images
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}

resource "aws_ecr_repository" "edge_iot_publisher" {
  name                 = var.ecr_edge_iot_publisher_repository_name
  image_tag_mutability = var.ecr_edge_agent_image_tag_mutability
  force_delete         = var.ecr_repository_force_delete

  image_scanning_configuration {
    scan_on_push = var.ecr_edge_agent_scan_on_push
  }

  encryption_configuration {
    encryption_type = "AES256"
  }
}

resource "aws_ecr_lifecycle_policy" "edge_iot_publisher" {
  repository = aws_ecr_repository.edge_iot_publisher.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Expire untagged edge-iot-publisher images after ${var.ecr_edge_agent_expire_untagged_days} days"
        selection = {
          tagStatus   = "untagged"
          countType   = "sinceImagePushed"
          countUnit   = "days"
          countNumber = var.ecr_edge_agent_expire_untagged_days
        }
        action = {
          type = "expire"
        }
      },
      {
        rulePriority = 2
        description  = "Keep the latest ${var.ecr_edge_agent_keep_sha_images} sha-tagged edge-iot-publisher images"
        selection = {
          tagStatus     = "tagged"
          tagPrefixList = ["sha-"]
          countType     = "imageCountMoreThan"
          countNumber   = var.ecr_edge_agent_keep_sha_images
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}

resource "aws_ecr_repository" "snapshot_uploader" {
  name                 = var.ecr_snapshot_uploader_repository_name
  image_tag_mutability = var.ecr_edge_agent_image_tag_mutability
  force_delete         = var.ecr_repository_force_delete

  image_scanning_configuration {
    scan_on_push = var.ecr_edge_agent_scan_on_push
  }

  encryption_configuration {
    encryption_type = "AES256"
  }
}

resource "aws_ecr_lifecycle_policy" "snapshot_uploader" {
  repository = aws_ecr_repository.snapshot_uploader.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Expire untagged snapshot-uploader images after ${var.ecr_edge_agent_expire_untagged_days} days"
        selection = {
          tagStatus   = "untagged"
          countType   = "sinceImagePushed"
          countUnit   = "days"
          countNumber = var.ecr_edge_agent_expire_untagged_days
        }
        action = {
          type = "expire"
        }
      },
      {
        rulePriority = 2
        description  = "Keep the latest ${var.ecr_edge_agent_keep_sha_images} sha-tagged snapshot-uploader images"
        selection = {
          tagStatus     = "tagged"
          tagPrefixList = ["sha-"]
          countType     = "imageCountMoreThan"
          countNumber   = var.ecr_edge_agent_keep_sha_images
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}
