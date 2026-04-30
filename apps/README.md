# Apps

이 디렉터리는 Aegis-Pi에서 직접 구현할 애플리케이션 코드를 서비스별로 나누어 두는 공간이다.

현재는 대부분 구현 전 placeholder이며, M4 이후 Edge Agent와 Risk 관련 서비스가 채워질 예정이다.

## 하위 폴더

| 경로 | 역할 |
| --- | --- |
| `edge-agent/` | `factory-a` 로컬 데이터와 상태를 수집해 AWS IoT Core로 송신하는 Edge Agent |
| `dummy-sensor/` | `factory-b`, `factory-c` 테스트베드용 더미 입력 생성 모듈 |
| `risk-normalizer/` | S3 raw 데이터를 Risk Score Engine 입력 형식으로 정규화하는 서비스 |
| `risk-score-engine/` | 공장별 위험 상태와 Risk Twin 출력을 계산하는 서비스 |
| `pipeline-status-aggregator/` | IoT Core 수신과 S3 적재 상태를 기준으로 pipeline status를 계산하는 보조 서비스 |
