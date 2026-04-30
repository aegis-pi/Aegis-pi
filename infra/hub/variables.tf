variable "project_name" {
  description = "Project name used for AWS resource naming and tagging."
  type        = string
  default     = "aegis-pi"
}

variable "environment" {
  description = "Environment name for the Hub MVP."
  type        = string
  default     = "hub-mvp"
}

variable "aws_region" {
  description = "AWS region for the Hub infrastructure."
  type        = string
  default     = "ap-south-1"
}

variable "vpc_cidr" {
  description = "CIDR block for the Hub Processing VPC."
  type        = string
  default     = "10.40.0.0/16"
}

variable "az_count" {
  description = "Number of availability zones to use for the MVP VPC."
  type        = number
  default     = 2

  validation {
    condition     = var.az_count == 2
    error_message = "The MVP baseline intentionally uses exactly 2 AZs."
  }
}

variable "cluster_name" {
  description = "EKS cluster name."
  type        = string
  default     = "aegis-pi-hub-mvp"
}

variable "kubernetes_version" {
  description = "EKS Kubernetes version."
  type        = string
  default     = "1.33"
}

variable "cluster_endpoint_public_access_cidrs" {
  description = "CIDR blocks allowed to access the public EKS API endpoint. MVP bootstrap allows 0.0.0.0/0 for mobility; narrow this before operational use."
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "node_instance_types" {
  description = "Instance types for the EKS managed node group."
  type        = list(string)
  default     = ["t3.medium"]
}

variable "node_min_size" {
  description = "Minimum node count for the MVP managed node group."
  type        = number
  default     = 2
}

variable "node_desired_size" {
  description = "Desired node count for the MVP managed node group."
  type        = number
  default     = 2
}

variable "node_max_size" {
  description = "Maximum node count for the MVP managed node group."
  type        = number
  default     = 2
}
