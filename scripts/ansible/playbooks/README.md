# Ansible Playbooks

이 디렉터리는 `factory-a` 운영 점검과 테스트 자동화를 위한 Ansible playbook을 둔다.

## 파일

| 파일 | 내용 |
| --- | --- |
| `02_start_test.yml` | master에 접속해 K3s, MetalLB, Longhorn, ArgoCD, monitoring, ai-apps 상태를 검증하고 evidence를 생성 |

## 기준

- 초기 자동화는 상태 수집과 검증 중심으로 유지한다.
- 물리 LAN 제거, 전원 차단 같은 장애 유발은 수동 절차로 둔다.
- playbook 결과는 `scripts/ansible/evidence/`에 저장한다.
