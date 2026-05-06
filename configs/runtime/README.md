# Runtime Config

이 디렉터리는 공장별 필드 표시 여부와 Risk 계산 가중치를 제어하는 런타임 설정 파일을 둔다.

## 파일

| 파일 | 역할 |
| --- | --- |
| `runtime-config.yaml` | 전역 Risk field 기준, 공장별 override, VM dummy data profile 초안 |

## 현재 권장 기준

- `factory-a`는 실제 Raspberry Pi 기반 production-edge로 두고 dummy data를 비활성화한다.
- `factory-b`는 Mac mini + UTM 기반 `stable-lab` dummy profile로 둔다.
- `factory-c`는 Windows + VirtualBox 기반 `noisy-vm` dummy profile로 둔다.
- `global.fields`에서 `risk_enabled=true`인 field의 weight 합계는 100 이하로 유지한다. 현재 전역 합계는 100이다.
- SSH 비밀번호, AWS access key, IoT private key, Grafana admin password, kubeconfig token 같은 민감값은 이 파일에 넣지 않는다.
