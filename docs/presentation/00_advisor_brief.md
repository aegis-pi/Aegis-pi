# 지도/검토용 브리프

상태: source of truth
기준일: 2026-05-08

## 현재 진행 상태

`factory-a` Safe-Edge 기준선 구축과 장애 검증이 완료됐다.

완료된 핵심:

```text
3-node K3s
Longhorn
ArgoCD GitOps
Grafana / InfluxDB / Prometheus
BME280 / AI / Audio workload
Failover / Failback
Data retention
AI snapshot retention
```

## 검증 결과

```text
LAN 제거: failover/failback 성공, AI/audio/BME worker1 Running
k3s-agent 중지: failover/failback 성공
AI snapshot PVC 제거 후 Multi-Attach 재발 없음
LAN 제거 InfluxDB 공백: 10초 bucket 기준 AI/audio 80초, BME 70초
```

## 현재 판단

- M0는 핵심 기준선 완료로 볼 수 있다.
- NFS Cold Storage와 Ansible tiering은 보류했다.
- AWS Hub EKS/VPC/namespace/ArgoCD bootstrap, Hub Prometheus Agent, Grafana/AMP datasource, AWS Load Balancer Controller, Admin UI HTTPS Ingress, foundation S3/AMP/IoT Rule, `factory-a` IoT Thing/Policy/K3s Secret, IRSA S3/AMP 권한은 2026-05-06~2026-05-07 기준 `build-all --admin-ui`와 `build-hub`로 재생성/검증했고, 2026-05-08 비용 정리를 위해 destroy 완료 상태다.
- 후속 구현 책임 경계는 Terraform = 인프라, Ansible = bootstrap/설정/소프트웨어, GitHub Actions = CI, GitHub+ArgoCD = CD로 고정한다.

## 다음 검토 주제

1. failover 데이터 공백 허용 범위
2. failback 중복 write 처리 필요성
3. active writer guard 필요 여부
4. `runtime-config.yaml`과 Risk 가중치 기준
5. Dashboard VPC와 Risk Twin dashboard 범위
