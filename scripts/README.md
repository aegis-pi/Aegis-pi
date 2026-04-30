# Scripts

이 디렉터리는 구축, 검증, 보조 자동화에 사용하는 스크립트를 둔다.

현재 운영 스크립트는 없다.

반복 점검 자동화는 `ansible/` 아래에 둔다.

이전에 사용한 `safe-edge-agent-watchdog.*` fencing 구성은 AI snapshot PVC 제거 후 폐기했다. 현재 AI failover는 Longhorn RWO snapshot PVC에 의존하지 않으므로 worker2 reboot fencing을 사용하지 않는다.
