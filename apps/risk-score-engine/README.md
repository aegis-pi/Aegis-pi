# Risk Score Engine

상태: legacy placeholder

이 디렉터리는 이전 설계에서 공장별 Risk Score와 상태를 계산하고 관제 화면용 출력을 만드는 장기 실행 서비스 코드를 두기 위한 자리였다.

## 2026-05-14 수정 방향

최신 기준에서는 별도 `risk-score-engine` 컨테이너 서비스/파드를 구현하지 않는다.

Risk 계산은 Lambda data processor 내부 로직으로 구현하고, 결과는 Dashboard VPC의 Web/API가 조회할 수 있도록 DynamoDB와 S3 processed에 저장한다.

```text
Lambda data processor
  -> Risk score calculation
  -> DynamoDB LATEST
  -> DynamoDB HISTORY
  -> S3 processed
```
