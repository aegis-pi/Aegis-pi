# Troubleshooting Wiki Reports

상태: Git Wiki 변환본
기준일: 2026-05-26
원본: `docs/ops/04_troubleshooting.md` 및 Hub/Cloud 운영 문서

## 목적

`docs/ops/04_troubleshooting.md`와 Hub/Cloud 운영 문서에서 Git Wiki에 포함할 가치가 높은 트러블슈팅을 골라 이슈 템플릿 형식으로 재정리한다.

각 항목은 아래 필드를 가진다.

```text
📌 현상 요약
🖥️ 환경 정보
🔁 재현 순서
✅ 기대 동작
❌ 실제 동작
🔍 시도한 것들
🚨 심각도
🗂️ 영역
💡 해결 방법
```

## 포함 기준

보편적인 Linux/SSH 사용 실수, 일시적인 네트워크 오류, 영향 없는 경고는 제외한다.
K3s, Raspberry Pi OS 설정, 네트워크 아키텍처, Longhorn, MetalLB, 모니터링, AI 하드웨어, 자동화/DR 운영에 재사용 가능한 항목만 포함한다.

## 문서 목록

| 문서 | 포함 항목 |
| --- | --- |
| `os-raspberry-pi.md` | 5, 7 |
| `k3s-kubernetes.md` | 9, 13, 22 |
| `storage-longhorn.md` | 11, 14, 18, 32 |
| `loadbalancer-metallb.md` | 15, 16, 17, 19, 27 |
| `monitoring-db.md` | 28, 29, 35 |
| `ai-hardware.md` | 31, 37 |
| `automation-scripts.md` | 8, 25, 부록1, 부록2, 부록3 |
| `operations-dr.md` | 30, 33, 34 |
| `network.md` | 36, 38, 39, 40 |
| `cloud-aws-hub.md` | AWS Hub, EKS, Terraform, ArgoCD, Tailscale, IoT/S3, VM Spoke cloud 연동, data-pipeline overwrite |

## 우선 검토 대상

운영/회고에서 먼저 읽을 항목은 다음이다.

1. `network.md`의 40번 `eth0`/`wlan0` 역할 고정
2. `storage-longhorn.md`의 32번 Longhorn RWO PVC failover 한계
3. `operations-dr.md`의 30번 Failback 재생성 루프 위험
4. `ai-hardware.md`의 31번 하드웨어 의존 Pod `Recreate` 전략
5. `network.md`의 36번 flannel/default route 문제
6. `cloud-aws-hub.md`의 EKS/Terraform/ArgoCD bootstrap 장애
