# Mesh VPN Infrastructure

이 디렉터리는 Tailscale 기반 Hub-Spoke 연결 구성과 관련된 인프라 또는 운영 설정 파일을 둔다.

Tailscale은 Hub가 Spoke K3s API에 접근하고 ArgoCD가 배포를 제어하기 위한 운영/제어망이다.

관리자 대시보드는 Tailscale에 의존하지 않고 별도 Dashboard VPC에서 제공한다. Dashboard VPC는 processed S3와 latest status store를 조회하며 Spoke API를 직접 호출하지 않는다.
