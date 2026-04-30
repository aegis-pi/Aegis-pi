# Edge Agent

이 디렉터리는 `factory-a`에서 센서 및 시스템 상태를 수집해 표준 스키마로 변환하고 Hub로 전송하는 Edge Agent 코드를 둔다.

Dashboard VPC 확장 기준에서는 Edge Agent가 센서값뿐 아니라 `system_status`, `device_status`, `workload_status`, `pipeline_heartbeat`도 IoT Core로 전송한다. 대시보드는 Spoke나 Processing VPC 내부 API를 직접 조회하지 않고 이 데이터가 반영된 latest status store를 읽는다.
