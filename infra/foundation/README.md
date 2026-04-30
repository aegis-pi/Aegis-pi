# Foundation Layer

이 디렉터리는 Hub EKS 생명주기와 분리해야 하는 영속 리소스를 둘 자리다.

후보 리소스:

- S3 원본 데이터 버킷
- ECR 이미지 저장소
- AMP workspace
- IoT Core Thing, 인증서, Rule

아직 Terraform 리소스는 만들지 않았다. `infra/hub`를 destroy해도 데이터가 유지되어야 하는 리소스부터 이 root로 옮긴다.
