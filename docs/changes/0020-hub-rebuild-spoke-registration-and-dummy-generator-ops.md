# 0020 Hub-only rebuild spoke registration and dummy generator operations

상태: accepted
결정일: 2026-05-21

## 기존 계획

Hub 재생성 이후 실행 순서가 `build-iot-factory-a.sh`, `register-spoke-factory-a/b/c.sh`, `connect-hub-tailscale-ui.sh`, factory-b/c dummy generator start 사이에서 명확히 분리되어 있지 않았다.

factory-b/c dummy 운영도 초기에는 VM 로컬 generator와 VM 로컬 publisher systemd를 함께 다루는 문서가 남아 있어, 현재 GitOps로 배포되는 `edge-iot-publisher`와 역할이 겹쳐 보였다.

## 변경된 실제 기준

Hub만 삭제/재생성했고 IoT Thing/certificate와 Spoke K3s Secret이 살아있는 경우 표준 순서는 아래다.

```text
build-hub.sh
-> build-admin-ui-after-ns.sh              # ALB/Admin UI HTTPS가 필요할 때
-> connect-hub-tailscale-ui.sh             # Tailnet UI가 필요할 때만 선택 실행
-> register-spoke-factory-a/b/c.sh
-> scripts/ops/manage-dummy-generators.sh start factory-b
-> scripts/ops/manage-dummy-generators.sh start factory-c
```

`build-iot-factory-a.sh`는 IoT Thing/certificate 또는 `factory-a` K3s Secret을 새로 만들거나 갱신해야 할 때만 사용한다. Hub-only rebuild에서는 `register-spoke-factory-a/b/c.sh`를 사용해 기존 IoT Secret을 유지한 채 Hub Tailscale egress, ArgoCD cluster Secret, ApplicationSet, Application sync/wait만 복구한다.

`register-spoke-factory-*`의 ArgoCD core sync/wait는 임시 kubeconfig의 current namespace를 `argocd`로 설정해서 실행한다. 이렇게 해야 `argocd --core`가 `argocd-cm`을 `default` namespace에서 찾는 오류를 피할 수 있다.

factory-b/c의 현재 표준 data-plane은 VM 로컬 dummy generator와 K3s `edge-iot-publisher` 조합이다. VM 로컬 dummy publisher systemd는 현행 표준 운영 경로가 아니며, 과거 smoke/legacy 용도로만 남긴다.

`scripts/ops/manage-dummy-generators.sh`는 `scripts/ops/dummy-generators.env`를 읽어 factory-b/c master IP, worker IP, SSH user, service 이름을 가져온다. SSH는 master를 ProxyJump로 사용해 worker에서 단일 원격 명령을 실행한다.

## 변경 이유

- Hub 비용 절감을 위해 Hub만 내렸다 올리는 흐름과 IoT 재등록 흐름을 분리해야 한다.
- ALB 기반 Admin UI가 준비된 환경에서는 Tailnet UI Service가 필수가 아니다.
- 로컬 dummy publisher와 K3s `edge-iot-publisher`를 동시에 쓰면 같은 MQTT client id 충돌과 중복 publish 위험이 있다.
- nested SSH/here-doc 방식은 password prompt, TTY, quoting 오류를 만들기 쉬워 ProxyJump 단일 명령 방식으로 단순화했다.
- `argocd --core`는 kubeconfig current namespace에 의존하므로, 스크립트가 `argocd` namespace를 명시적으로 보장해야 한다.

## 영향

- Hub-only rebuild 후에는 `register-spoke-factory-a/b/c.sh` 뒤에 factory-b/c dummy generator를 다시 시작한다.
- `connect-hub-tailscale-ui.sh`는 ALB/Admin UI HTTPS를 쓰는 경우 필수가 아니다.
- `manage-dummy-generators.sh status`는 로컬 publisher를 조회하지 않는다.
- `manage-dummy-generators.sh stop`과 `stop-dummy-generators.sh`는 legacy local publisher unit이 설치돼 있으면 함께 정지하지만, 설치돼 있지 않은 것은 정상으로 본다.
- factory-b/c 접속 정보는 `scripts/ops/dummy-generators.env`에서 관리하고, 필요하면 `AEGIS_DUMMY_GENERATORS_ENV`로 다른 파일을 지정한다.

## 업데이트 필요한 문서

- `README.md`
- `scripts/README.md`
- `scripts/build/README.md`
- `scripts/destroy/README.md`
- `docs/ops/00_quick_start.md`
- `docs/ops/04_troubleshooting.md`
- `docs/ops/14_hub_run_commands.md`
- `docs/ops/22_factory_bc_testbed_data_plane.md`
- `apps/dummy-sensor/README.md`
- `apps/dummy-sensor/docs/factory-b-c-dummy-systemd-runbook.md`

## 검증

- `factory-a` master에서 기존 `ai-apps/aws-iot-factory-a-cert` Secret과 `argocd-manager` RBAC/token 존재를 확인했다.
- Hub EKS에는 Hub 재생성 후 `cluster-factory-a/b/c`와 `aegis-spoke-factory-a/b/c`가 없어 register 단계가 필요함을 확인했다.
- 임시 kubeconfig namespace를 `argocd`로 설정한 뒤 `argocd --core app get aegis-spoke-factory-a --app-namespace argocd`가 `Synced/Healthy` 상태를 반환했다.
- `factory-b` worker에서 `aegis-factory-b-dummy-generator.service`가 `active (running)`이고 `/var/lib/aegis/outbox`에 canonical JSON을 쓰는 것을 확인했다.
