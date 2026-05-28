# Runtime Config

이 디렉터리는 공장별 필드 표시 여부와 Risk 계산 가중치를 제어하는 런타임 설정 파일을 둔다.

2026-05-28 기준 이 설정 파일은 source of truth 후보이지만, `apps/data-processor/processor/risk.py`는 아직 하드코딩 상수를 사용한다. 다음 M6 작업에서 Lambda data processor가 이 파일의 weight/threshold/risk_enabled/factory override를 읽도록 연결한다.

## 파일

| 파일 | 역할 |
| --- | --- |
| `runtime-config.yaml` | 전역 Risk field 기준, 공장별 override, VM dummy data profile 초안 |

## 현재 권장 기준

- `factory-a`는 실제 Raspberry Pi 기반 production-edge로 두고 dummy data를 비활성화한다.
- `factory-b`는 Mac mini + UTM 기반 2-node K3s testbed이며, `worker1`에서 `stable-lab` dummy profile을 실행한다.
- `factory-c`는 Windows + VirtualBox 기반 2-node K3s testbed이며, `factory-c-worker`에서 `noisy-vm` dummy profile을 실행한다.
- `factory-c`는 VirtualBox NAT IP 중복을 피하기 위해 host-only `enp0s8` 대역을 K3s node-ip/flannel 인터페이스 기준으로 사용한다.
- `global.fields`에서 `risk_enabled=true`인 field의 weight 합계는 100 이하로 유지한다. 현재 전역 합계는 100이다.
- SSH 비밀번호, AWS access key, IoT private key, Grafana admin password, kubeconfig token 같은 민감값은 이 파일에 넣지 않는다.
