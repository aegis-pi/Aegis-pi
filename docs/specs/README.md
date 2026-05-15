# Specs

이 디렉터리는 기능별 상세 요구사항과 인터페이스 설계를 둔다.

## 하위 폴더

| 경로 | 역할 |
| --- | --- |
| `iot_data_format.md` | Edge data-plane components -> IoT Core 전송 데이터 포맷, topic, S3 raw path, 전송 주기 명세 |
| `data_storage_pipeline.md` | IoT Core 이후 S3 raw/processed, DynamoDB LATEST/HISTORY 저장 경로와 포맷 |
| `monitoring_dashboard/` | 관제 화면 요구사항, 화면 구성, API, 데이터 모델 명세 |

## 기준

- 구현 전 합의가 필요한 화면, API, 데이터 구조를 이곳에서 관리한다.
- 실제 운영 절차나 장애 대응은 `docs/ops/`로 분리한다.
