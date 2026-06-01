# Data Pipeline Refresh Flow Explained

이 문서는 Aegis 데이터 파이프라인을 처음 읽는 사람이 `refresh_pipeline_status`가 왜 필요한지 이해할 수 있도록 설명한다.

핵심은 **들어온 데이터뿐 아니라 데이터가 안 들어오고 있다는 사실도 상태로 저장하고 보여주는 구조**다.

## 전체 흐름

공장 데이터는 대략 다음 순서로 흐른다.

```text
factory-a 장비/센서
  -> IoT Core
  -> DataProcessor Lambda
  -> DynamoDB LATEST / HISTORY
  -> S3 processed
  -> GraphAggregator
  -> S3 processed_agg
  -> Backend / Front
```

각 저장소의 역할은 다르다.

| 저장소 | 역할 |
| --- | --- |
| `raw` | 실제로 들어온 원본 메시지 |
| `DynamoDB LATEST` | 공장별 현재 상태 1개 |
| `DynamoDB HISTORY` | 시간별 상태 스냅샷 |
| `S3 processed` | 정규화된 처리 결과 |
| `S3 processed_agg` | 그래프용 시간 bucket 집계 결과 |

## 기존에 헷갈렸던 상황

예를 들어 `factory-a`가 5월 28일 10:00에 꺼졌다고 가정한다.

그러면 실제 원본 데이터는 다음처럼 된다.

```text
raw/factory-a/.../10:00 있음
raw/factory-a/.../10:01 없음
raw/factory-a/.../10:02 없음
raw/factory-a/.../10:03 없음
```

`raw`는 이 상태가 맞다. 공장이 꺼졌으므로 새 원본 데이터가 없는 것이 정상이다.

문제는 `LATEST`였다.

기존 구조에서는 새 메시지가 들어올 때만 Risk를 다시 계산했다. 공장이 꺼진 뒤에는 새 메시지가 없으므로 `LATEST`가 마지막 정상 상태에 머물 수 있었다.

예시는 다음과 같다.

```json
{
  "factory_id": "factory-a",
  "sk": "LATEST",
  "last_factory_state_at": "2026-05-28T10:00:00Z",
  "risk": {
    "score": 100,
    "level": "safe",
    "top_causes": []
  }
}
```

실제로는 10:05, 10:10이 되어도 데이터가 들어오지 않는다. 그런데 `LATEST.risk.score`가 계속 100이면 Front에서는 정상처럼 보일 수 있다.

## 추가한 것

이번 수정의 핵심은 `refresh_pipeline_status`다.

이 흐름은 새 센서 메시지가 없어도 1분마다 실행된다.

```text
EventBridge Scheduler
  -> DataProcessor Lambda
  -> "factory-a 지금 데이터 신선한가?"
  -> 아니면 Risk 다시 계산
  -> LATEST / HISTORY / S3 state_snapshot 업데이트
```

즉 기존의 "새 데이터가 들어왔을 때만 계산"하던 구조에, "시간이 지나 데이터가 안 들어오는 것도 주기적으로 계산"하는 구조를 추가했다.

새 Lambda를 추가한 것은 아니다. 기존 `AEGIS-Lambda-DataProcessor`에 action 분기를 추가했고, EventBridge Scheduler가 다음 이벤트를 전달한다.

```json
{
  "action": "refresh_pipeline_status",
  "factories": ["factory-a", "factory-b", "factory-c"]
}
```

## 예시: factory-a가 꺼진 경우

처음에는 정상 상태다.

```json
{
  "factory_id": "factory-a",
  "last_infra_state_at": "2026-05-28T10:00:00Z",
  "pipeline_status": {
    "status": "normal",
    "latest_infra_state_age_seconds": 10
  },
  "risk": {
    "score": 100,
    "level": "safe",
    "top_causes": []
  }
}
```

5분 이상 데이터가 안 들어오면 refresh가 다음처럼 상태를 바꾼다.

```json
{
  "factory_id": "factory-a",
  "last_infra_state_at": "2026-05-28T10:00:00Z",
  "updated_at": "2026-05-28T10:06:00Z",
  "pipeline_status": {
    "status": "critical",
    "latest_infra_state_age_seconds": 360
  },
  "risk": {
    "score": 0,
    "base_score": 90,
    "level": "danger",
    "base_level": "safe",
    "top_causes": [
      {
        "field": "data_freshness",
        "reason": "pipeline_status_outage",
        "value": 360,
        "contribution": 90,
        "severity": "danger",
        "source": "gate"
      }
    ],
    "calculation_version": "risk-v0.2.0"
  }
}
```

중요한 점은 `factory_state` 자체를 새로 만든 것이 아니라는 점이다. 마지막으로 들어온 데이터는 그대로 둔다. 대신 `pipeline_status`와 `risk`만 지금 시점 기준으로 다시 계산한다.

## HISTORY는 어떻게 되는가

refresh가 실행될 때마다 `HISTORY#STATE`에도 스냅샷이 남는다.

```text
FACTORY#factory-a / HISTORY#STATE#2026-05-28T10:00:00Z -> score 100
FACTORY#factory-a / HISTORY#STATE#2026-05-28T10:03:00Z -> score 65
FACTORY#factory-a / HISTORY#STATE#2026-05-28T10:06:00Z -> score 0
FACTORY#factory-a / HISTORY#STATE#2026-05-28T10:07:00Z -> score 0
```

따라서 나중에 보면 언제부터 데이터가 끊겼고, 언제 위험 상태가 되었는지 확인할 수 있다.

## processed_agg는 왜 계속 생기는가

`processed_agg`는 그래프용 시간 bucket이다. 예를 들어 1분 단위로 계속 파일을 만들 수 있다.

```text
processed_agg/factory-a/10:00.json
processed_agg/factory-a/10:01.json
processed_agg/factory-a/10:02.json
processed_agg/factory-a/10:03.json
```

이 자체는 문제가 아니다. 그래프는 시간이 흘러가므로 bucket이 계속 생길 수 있다.

문제는 새 센서값이 없는데 예전 센서값을 최신 bucket에 넣으면 안 된다는 점이다. 그래서 수정 후에는 bucket 안에 실제 새 관측값이 없으면 센서와 infra 값은 비운다.

예시는 다음과 같다.

```json
{
  "factory_id": "factory-a",
  "bucket_start": "2026-05-28T10:06:00Z",
  "source_count": 0,
  "sensor": {},
  "infra": {},
  "risk": {
    "score": 0,
    "level": "danger",
    "top_causes": [
      {
        "field": "data_freshness",
        "reason": "pipeline_status_outage"
      }
    ]
  }
}
```

즉 `processed_agg`가 계속 생성되는 것은 괜찮다. 대신 그 안의 의미가 바뀌었다.

기존 의미:

```text
새 데이터가 없어도 마지막 센서값이 계속 보일 수 있음
```

수정 후 의미:

```text
새 데이터가 없으면 sensor/infra는 비어 있음
하지만 risk는 "현재 데이터가 끊긴 상태"를 반영함
```

## Front에서 해석하는 방법

Front는 다음 조합을 데이터 단절 상태로 해석하면 된다.

```text
source_count = 0
sensor = {}
infra = {}
risk.score = 0
top_causes에 data_freshness / pipeline_status_outage 있음
```

이 조합의 의미는 다음과 같다.

```text
공장 데이터가 실제로 안 들어오고 있고,
그 때문에 현재 Risk가 위험으로 판단됐다.
```

반대로 정상 상태는 다음과 비슷하다.

```json
{
  "source_count": 2,
  "sensor": {
    "temperature_celsius_avg": 28.4,
    "humidity_percent_avg": 41.2
  },
  "infra": {
    "nodes_ready": 2,
    "nodes_total": 2
  },
  "risk": {
    "score": 100,
    "level": "safe",
    "top_causes": []
  }
}
```

## 정리

이번 수정의 방향은 다음과 같다.

1. 원본 데이터가 없으면 `raw`는 비어 있는 것이 맞다.
2. 하지만 `LATEST`가 과거 정상 상태에 멈춰 있으면 안 된다.
3. 그래서 1분마다 현재 기준으로 `pipeline_status`와 `risk`를 다시 계산한다.
4. 데이터가 계속 안 들어오면 `risk.score`는 0으로 떨어진다.
5. 그 이유는 `top_causes`에 `data_freshness` / `pipeline_status_outage`로 남긴다.
6. `processed_agg`는 계속 만들되, 없는 센서값을 있는 것처럼 채우지 않는다.

이 시스템은 이제 들어온 데이터뿐 아니라 데이터가 안 들어오고 있다는 사실도 상태로 저장하고 보여준다.
