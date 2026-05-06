variable "project_name" {
  description = "Project name used for AWS resource naming and tagging."
  type        = string
  default     = "AEGIS"
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
  default     = "10.0.0.0/16"
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

variable "availability_zone_suffixes" {
  description = "Availability Zone suffixes used for Hub Processing VPC subnets."
  type        = list(string)
  default     = ["a", "c"]

  validation {
    condition     = length(var.availability_zone_suffixes) == 2
    error_message = "availability_zone_suffixes must contain exactly 2 suffixes."
  }
}

variable "cluster_name" {
  description = "EKS cluster name."
  type        = string
  default     = "AEGIS-EKS"
}

variable "kubernetes_version" {
  description = "EKS Kubernetes version."
  type        = string
  default     = "1.34"
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

variable "data_bucket_name" {
  description = "S3 bucket name used by Hub workloads."
  type        = string
  default     = "aegis-bucket-data"
}

variable "risk_factory_id" {
  description = "Factory ID whose raw/latest prefixes are accessible to the risk normalizer."
  type        = string
  default     = "factory-a"
}

variable "risk_normalizer_namespace" {
  description = "Kubernetes namespace for the risk normalizer service account."
  type        = string
  default     = "risk"
}

variable "risk_normalizer_service_account" {
  description = "Kubernetes service account name used by the risk normalizer workload."
  type        = string
  default     = "risk-normalizer"
}

variable "foundation_state_path" {
  description = "Local Terraform state path for infra/foundation outputs consumed by Hub IAM policies."
  type        = string
  default     = "../foundation/terraform.tfstate"
}

variable "grafana_namespace" {
  description = "Kubernetes namespace for the internal Grafana service account."
  type        = string
  default     = "observability"
}

variable "grafana_service_account" {
  description = "Kubernetes service account name used by internal Grafana for AMP query access."
  type        = string
  default     = "grafana"
}

variable "prometheus_remote_write_namespace" {
  description = "Kubernetes namespace for the Prometheus remote_write service account."
  type        = string
  default     = "observability"
}

variable "prometheus_remote_write_service_account" {
  description = "Kubernetes service account name used by Prometheus or Prometheus Agent for AMP remote_write."
  type        = string
  default     = "prometheus-agent"
}
