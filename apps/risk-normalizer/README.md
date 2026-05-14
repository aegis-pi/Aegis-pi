# Risk Normalizer

상태: legacy placeholder

이 디렉터리는 이전 설계에서 S3 원본 데이터를 읽어 정규화하고 Risk Score Engine 입력 형식으로 변환하는 서비스 코드를 두기 위한 자리였다.

## 2026-05-14 수정 방향

최신 기준에서는 별도 `risk-normalizer` 컨테이너 서비스/파드를 구현하지 않는다.

IoT Core 이후 처리는 아래 흐름을 따른다.

```text
IoT Core
  -> IoT Rule -> S3 raw
  -> Lambda data processor
      -> DynamoDB LATEST
      -> DynamoDB HISTORY
      -> S3 processed
```

정규화 로직은 Lambda data processor 내부 단계로 구현한다.
