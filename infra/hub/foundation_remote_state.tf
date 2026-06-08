data "terraform_remote_state" "foundation" {
  backend = "s3"

  config = {
    bucket = "kjw-aegis-terraform-state"
    key    = "aegis-pi/foundation/terraform.tfstate"
    region = "ap-south-1"
  }
}
