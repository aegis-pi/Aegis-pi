# Dummy Data Generator Placeholder

이 디렉터리는 legacy 이름을 유지하는 placeholder다.

2026-05-15 기준 M5에서는 `factory-b`, `factory-c` 테스트베드 Spoke가 `dummy-data-generator`로 canonical JSON을 만들고, IoT Core 전송은 M4에서 만든 공통 `edge-iot-publisher`를 재사용한다.

```text
dummy-data-generator
  -> local spool/outbox canonical JSON
  -> edge-iot-publisher
  -> AWS IoT Core
```
