# Pipeline Status Aggregator

이 디렉터리는 IoT Core 수신과 S3 적재 상태를 기준으로 `pipeline_status`를 계산하는 보조 서비스 코드를 둔다.

계산 결과는 Dashboard VPC가 read-only로 조회할 latest status store에 반영한다. Dashboard VPC와 Processing VPC 사이에는 VPC Peering을 두지 않는 방향을 기본으로 한다.
