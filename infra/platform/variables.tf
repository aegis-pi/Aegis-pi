variable "aws_region" {
  description = "AWS region where the Hub EKS cluster exists."
  type        = string
  default     = "ap-south-1"
}

variable "cluster_name" {
  description = "Existing Hub EKS cluster name."
  type        = string
  default     = "AEGIS-EKS"
}

variable "project_name" {
  description = "Project tag value."
  type        = string
  default     = "AEGIS"
}

variable "environment" {
  description = "Environment tag value."
  type        = string
  default     = "hub-mvp"
}
