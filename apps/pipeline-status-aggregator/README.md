# Pipeline Status Aggregator

이 디렉터리는 IoT Core 수신과 S3 적재 상태를 기준으로 `pipeline_status`를 계산하는 보조 서비스 코드를 둔다.

계산 결과는 Data / Dashboard VPC가 조회할 latest status store에 반영한다. Data / Dashboard VPC와 Control / Management VPC 사이에는 직접 DB 접근이나 상시 private service 호출을 두지 않는 방향을 기본으로 한다.
