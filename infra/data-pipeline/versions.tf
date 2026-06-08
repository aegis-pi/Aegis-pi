terraform {
  required_version = ">= 1.15.0"

  backend "s3" {
    bucket       = "kjw-aegis-terraform-state"
    key          = "aegis-pi/data-pipeline/terraform.tfstate"
    region       = "ap-south-1"
    use_lockfile = true
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }

    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.7"
    }
  }
}
