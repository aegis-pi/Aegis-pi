# Scripts

이 디렉터리는 구축, 검증, 보조 자동화에 사용하는 스크립트를 둔다.

## Safe-Edge watchdog fencing

`safe-edge-agent-watchdog.*` 파일은 `factory-a` worker2에서 `k3s-agent` 상태와 master API 도달성을 감시하는 systemd watchdog 구성이다.

설치 대상:

```text
worker2
```

설치 위치:

```text
/usr/local/sbin/safe-edge-agent-watchdog.sh
/etc/systemd/system/safe-edge-agent-watchdog.service
/etc/systemd/system/safe-edge-agent-watchdog.timer
```

활성화:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now safe-edge-agent-watchdog.timer
```

확인:

```bash
systemctl is-active safe-edge-agent-watchdog.timer
sudo journalctl -u safe-edge-agent-watchdog.service -n 50 --no-pager
```
