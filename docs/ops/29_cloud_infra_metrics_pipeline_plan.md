# Cloud Infra Metrics Pipeline Plan

상태: 구현/운영 확인 기준
기준일: 2026-06-01

이 문서는 Aegis 프로젝트를 처음 진행하는 사람이 기존 데이터 파이프라인의 구조와 한계를 이해하고, Cloud infra metric을 어떤 방식으로 수집/저장/조회할지 판단할 수 있도록 정리한다.

핵심 방향은 **Dashboard에 필요한 metric만 주기적으로 추출해서 DynamoDB/S3에 read model로 저장하는 것**이다. CloudWatch Container Insights처럼 모든 EKS container metric을 상시 수집하지 않는다.

## 기존 데이터 파이프라인

기존 공장 데이터는 다음 흐름으로 구성되어 있다.

```text
factory-a/b/c 장비 또는 dummy sensor
  -> AWS IoT Core
  -> DataProcessor Lambda
  -> DynamoDB LATEST / HISTORY#STATE
  -> S3 processed
  -> GraphAggregator
  -> S3 processed_agg
  -> Backend / Front
```

각 저장소의 역할은 아래와 같다.

| 저장소 | 역할 |
| --- | --- |
| S3 `raw/` | IoT Core로 들어온 원본 메시지 보존 |
| DynamoDB `LATEST` | 공장별 현재 상태 1개 |
| DynamoDB `HISTORY#STATE` | 시간별 상태 스냅샷, TTL 적용 |
| S3 `processed/` | 정규화된 처리 결과와 상태 스냅샷 |
| S3 `processed_agg/` | 그래프용 시간 bucket 집계 결과 |

기존 파이프라인은 공장 데이터 중심이다. 즉 센서, AI score, edge infra 상태, risk score, pipeline freshness를 다룬다.

## 기존 수정 방향: 데이터 단절도 상태로 저장

초기 구조에서는 새 IoT 메시지가 들어올 때만 `risk`와 `pipeline_status`가 갱신됐다. 이 때문에 `factory-a`가 꺼져서 raw 데이터가 끊겨도 `DynamoDB LATEST.risk.score`가 마지막 정상 값으로 남을 수 있었다.

이를 해결하기 위해 `DataProcessor`에 `refresh_pipeline_status` 흐름을 추가했다.

```text
EventBridge Scheduler
  -> DataProcessor Lambda
  -> action=refresh_pipeline_status
  -> DynamoDB LATEST의 마지막 infra_state 시각 확인
  -> pipeline_status / risk 재계산
  -> LATEST 업데이트
  -> HISTORY#STATE + S3 state_snapshot 저장
```

이 수정 이후에는 새 센서 메시지가 없어도 데이터 단절이 상태로 표현된다.

예시:

```json
{
  "factory_id": "factory-a",
  "pipeline_status": {
    "status": "critical",
    "latest_infra_state_age_seconds": 360
  },
  "risk": {
    "score": 0,
    "level": "danger",
    "top_causes": [
      {
        "field": "data_freshness",
        "reason": "pipeline_status_outage",
        "severity": "danger",
        "source": "gate"
      }
    ]
  }
}
```

## 새 요구사항: Cloud infra 상태도 Dashboard에 보여주기

Dashboard VPC에서는 공장 상태뿐 아니라 Cloud infra 상태도 보여줘야 한다.

확인하고 싶은 영역은 다음과 같다.

```text
Backend/API 상태
Data pipeline Lambda 상태
DynamoDB/S3 저장 상태
Scheduler 상태
Factory freshness/risk
EKS management plane 상태
ArgoCD sync/health
S3 latest object freshness
```

처음에는 CloudWatch Container Insights를 켜서 EKS node/pod/container metric을 전부 수집하는 방법을 검토했다. 실제 적용 후 `metrics-server`와 `amazon-cloudwatch-observability`를 모두 켰고, `kubectl top`과 `ContainerInsights` metric이 동작하는 것까지 확인했다.

하지만 비용이 문제였다.

현재 2-node Hub 기준 CloudWatch Container Insights를 상시 켜면 월 추가 비용이 대략 다음 수준이다.

```text
Container Insights enhanced observations: ~$58/month
CloudWatch Logs ingest/storage: ~$7+/month
합계: ~$65~75/month
```

MVP/개발 단계에서 이 비용은 과하다. 그래서 기본 전략을 바꿨다.

```text
metrics-server: 기본 ON
CloudWatch Observability / Container Insights: 기본 OFF
필요한 metric만 직접 수집
```

## 구현된 수집 전략

Cloud infra metric은 원본 metric 전체를 복제하지 않는다. Dashboard가 바로 읽을 수 있는 summary read model만 만든다.

전체 흐름:

```text
EventBridge Scheduler 1m
  -> CloudInfraFastCollector Lambda
  -> AWS API / CloudWatch / DynamoDB 조회
  -> DynamoDB CLOUD#infra / LATEST.fast 업데이트
  -> DynamoDB HISTORY#FAST#timestamp 저장
  -> S3 processed/cloud_infra/fast snapshot 저장

EventBridge Scheduler 5m
  -> CloudInfraSlowCollector Lambda
  -> EKS API / Kubernetes API / S3 조회
  -> DynamoDB CLOUD#infra / LATEST.slow 업데이트
  -> DynamoDB HISTORY#SLOW#timestamp 저장
  -> S3 processed/cloud_infra/slow snapshot 저장

Backend
  -> DynamoDB CLOUD#infra / LATEST 조회
  -> Front에 Cloud infra 상태 제공
```

2026-06-01 기준 Phase 1~3은 구현, Terraform 적용, Lambda invoke, DynamoDB/S3 snapshot 검증까지 완료했다.

| 구분 | 실제 리소스 |
| --- | --- |
| Fast Lambda | `AEGIS-Lambda-CloudInfraFastCollector` |
| Fast Scheduler | `AEGIS-Schedule-CloudInfraFastCollector1m` |
| Slow Lambda | `AEGIS-Lambda-CloudInfraSlowCollector` |
| Slow Scheduler | `AEGIS-Schedule-CloudInfraSlowCollector5m` |
| DynamoDB table | `AEGIS-DynamoDB-FactoryStatus` |
| Cloud infra latest key | `pk=CLOUD#infra`, `sk=LATEST` |
| Fast S3 snapshot | `processed/cloud_infra/fast/...` |
| Slow S3 snapshot | `processed/cloud_infra/slow/...` |

검증 결과:

- FastCollector invoke: `errors=[]`, `overall_status=normal`
- SlowCollector invoke: `errors=[]`, `overall_status=normal`
- SlowCollector 최적화 후 실행 시간: 약 6초대
- `slow.eks_management.nodes`: 2/2 ready, CPU/memory utilization 저장
- `slow.eks_management.pods`: running 22, pending 0, failed 0, restart_count_total 2, `top_by_cpu`/`top_by_memory` 저장
- `slow.eks_management.argocd`: apps 3, synced 3, healthy 3
- S3 `processed/cloud_infra/{fast,slow}/...` snapshot `head-object` 확인 완료

## 왜 1분과 5분으로 나누는가

모든 metric을 같은 주기로 수집하면 비용과 latency가 맞지 않는다.

1분 metric은 사용자 서비스와 데이터 파이프라인 장애 감지에 필요하다.

```text
ECS desired/running
ECS CPU utilization
ECS memory utilization
ALB healthy host / 5xx / latency
Lambda errors / duration / throttles
DynamoDB throttles
Scheduler enabled
factory freshness/risk
```

5분 metric은 management plane과 상대적으로 느리게 변하는 상태다.

```text
EKS cluster/nodegroup
EKS node CPU utilization
EKS node memory utilization
EKS pod phase/restart
EKS top pods by CPU/memory
ArgoCD sync/health
S3 latest object time
```

## 수집 대상과 출처

### 1분 Fast Collector

| 영역 | 값 | 출처 |
| --- | --- | --- |
| ECS | desired/running/pending count | `ecs:DescribeServices` |
| ECS | CPU/Memory utilization | CloudWatch `AWS/ECS` |
| ALB | healthy/unhealthy host count | `elbv2:DescribeTargetHealth`, CloudWatch `AWS/ApplicationELB` |
| ALB | Target 5xx, latency | CloudWatch `AWS/ApplicationELB` |
| Lambda | invocations/errors/duration/throttles | CloudWatch `AWS/Lambda` |
| DynamoDB | read/write throttles, errors, latency | CloudWatch `AWS/DynamoDB` |
| Scheduler | enabled/disabled state | EventBridge Scheduler `GetSchedule` |
| Factory | pipeline_status, risk, top_causes | DynamoDB `FACTORY#{factory_id} / LATEST` |

### 5분 Slow Collector

| 영역 | 값 | 출처 |
| --- | --- | --- |
| EKS | cluster status/version | `eks:DescribeCluster` |
| EKS | nodegroup status/desired/health issues | `eks:DescribeNodegroup` |
| EKS | ASG healthy instances | `autoscaling:DescribeAutoScalingGroups` |
| Kubernetes | node ready count | Kubernetes API |
| Kubernetes | node CPU/memory | Kubernetes Metrics API, metrics-server |
| Kubernetes | pod phase/restart | Kubernetes API |
| Kubernetes | top pods by CPU/memory | Kubernetes Metrics API, metrics-server |
| ArgoCD | sync/health | `applications.argoproj.io` CRD |
| S3 | latest raw/processed/processed_agg object time | `s3:ListBucket` |

## 권한 모델

Fast collector Lambda role:

```text
AEGIS-IAMRole-Lambda-CloudInfraFastCollector
```

주요 권한:

- CloudWatch `GetMetricData`
- ECS `DescribeServices`
- ELBv2 `DescribeTargetGroups`, `DescribeTargetHealth`
- EventBridge Scheduler `GetSchedule`
- DynamoDB `GetItem`, `PutItem`
- S3 `PutObject` to `processed/cloud_infra/fast/*`

Slow collector Lambda role:

```text
arn:aws:iam::611058323802:role/AEGIS-IAMRole-Lambda-CloudInfraSlowCollector
```

주요 권한:

- EKS `DescribeCluster`, `ListNodegroups`, `DescribeNodegroup`
- Auto Scaling `DescribeAutoScalingGroups`
- S3 `ListBucket`
- DynamoDB `GetItem`, `PutItem`
- S3 `PutObject` to `processed/cloud_infra/slow/*`

Kubernetes API 접근은 EKS access entry로 부여한다.

```text
cluster: AEGIS-EKS
principal: arn:aws:iam::611058323802:role/AEGIS-IAMRole-Lambda-CloudInfraSlowCollector
policy: AmazonEKSAdminViewPolicy
scope: cluster
```

처음 `AmazonEKSViewPolicy`로는 Kubernetes API 조회가 `403 Forbidden`이었다. 사용자 승인 후 `AmazonEKSAdminViewPolicy`로 교체해 node/pod/ArgoCD read가 성공했다. 이 권한은 쓰기 권한은 아니지만 cluster-wide read visibility를 갖기 때문에 보안 영향으로 관리한다.

CloudWatch Container Insights는 이 권한 모델과 별개이며, 기본값은 계속 OFF다.

## DynamoDB 저장 구조

기존 `AEGIS-DynamoDB-FactoryStatus` 테이블을 재사용한다.

현재 상태:

```text
pk = CLOUD#infra
sk = LATEST
```

최근 이력:

```text
pk = CLOUD#infra
sk = HISTORY#FAST#2026-06-01T15:30:00Z
ttl = now + 6h

pk = CLOUD#infra
sk = HISTORY#SLOW#2026-06-01T15:30:00Z
ttl = now + 24h
```

`LATEST`는 하나만 유지하고, fast/slow collector가 서로 다른 필드만 업데이트한다.

```text
FastCollector -> LATEST.fast 갱신
SlowCollector -> LATEST.slow 갱신
```

이 방식이면 1분 collector가 5분 데이터를 덮어쓰지 않고, 5분 collector도 1분 데이터를 덮어쓰지 않는다.

## LATEST 예시

```json
{
  "pk": "CLOUD#infra",
  "sk": "LATEST",
  "schema_version": "cloud-infra-status-v1",
  "updated_at": "2026-06-01T15:30:00Z",
  "fast_updated_at": "2026-06-01T15:30:00Z",
  "slow_updated_at": "2026-06-01T15:25:00Z",
  "overall_status": "warning",
  "fast": {
    "backend_runtime": {
      "status": "warning",
      "ecs": {
        "cluster_name": "KJW-AEGIS-Data-ECSCluster",
        "service_name": "KJW-AEGIS-Data-Service-Backend",
        "desired_count": 1,
        "running_count": 1,
        "pending_count": 0,
        "cpu_utilization_avg": 18.2,
        "cpu_utilization_max": 94.4,
        "memory_utilization_avg": 34.1,
        "memory_utilization_max": 35.0
      },
      "alb": {
        "target_group_name": "kjw-aegis-data-tg-backend",
        "healthy_host_count": 1,
        "unhealthy_host_count": 0,
        "target_5xx_count_5m": 7,
        "target_response_time_avg": 0.8,
        "target_response_time_p95": 1.9
      }
    },
    "data_pipeline": {
      "status": "normal",
      "lambdas": [
        {
          "name": "AEGIS-Lambda-DataProcessor",
          "invocations_5m": 10,
          "errors_5m": 0,
          "throttles_5m": 0,
          "duration_p95_ms": 320
        },
        {
          "name": "AEGIS-Lambda-GraphAggregator5m",
          "invocations_5m": 1,
          "errors_5m": 0,
          "throttles_5m": 0,
          "duration_p95_ms": 450
        }
      ],
      "dynamodb": {
        "table_name": "AEGIS-DynamoDB-FactoryStatus",
        "read_throttle_events_5m": 0,
        "write_throttle_events_5m": 0,
        "system_errors_5m": 0
      },
      "schedulers": [
        {
          "name": "AEGIS-Schedule-DataProcessorRefresh1m",
          "state": "ENABLED"
        },
        {
          "name": "AEGIS-Schedule-GraphAggregator5m",
          "state": "ENABLED"
        }
      ]
    },
    "factory_freshness": {
      "status": "normal",
      "factories": [
        {
          "factory_id": "factory-a",
          "pipeline_status": "normal",
          "latest_infra_state_age_seconds": 12,
          "risk_score": 100,
          "risk_level": "safe",
          "top_causes": []
        }
      ]
    }
  },
  "slow": {
    "eks_management": {
      "status": "normal",
      "cluster": {
        "name": "AEGIS-EKS",
        "status": "ACTIVE",
        "version": "1.34"
      },
      "nodegroup": {
        "name": "AEGIS-EKS-node",
        "status": "ACTIVE",
        "desired_size": 2,
        "min_size": 2,
        "max_size": 2,
        "health_issues": []
      },
      "nodes": {
        "ready": 2,
        "total": 2,
        "items": [
          {
            "name": "ip-10-0-10-16.ap-south-1.compute.internal",
            "cpu_utilization_percent": 2,
            "memory_utilization_percent": 29
          },
          {
            "name": "ip-10-0-11-232.ap-south-1.compute.internal",
            "cpu_utilization_percent": 2,
            "memory_utilization_percent": 43
          }
        ]
      },
      "pods": {
        "running": 27,
        "pending": 0,
        "failed": 0,
        "unknown": 0,
        "restart_count_total": 2,
        "top_by_cpu": [
          {
            "namespace": "argocd",
            "pod": "argocd-application-controller-0",
            "cpu_millicores": 19,
            "memory_mib": 202
          }
        ]
      },
      "argocd": {
        "applications_total": 3,
        "synced": 3,
        "out_of_sync": 0,
        "healthy": 3,
        "degraded": 0,
        "apps": [
          {
            "name": "aegis-spoke-factory-a",
            "sync_status": "Synced",
            "health_status": "Healthy"
          }
        ]
      }
    },
    "storage_freshness": {
      "factories": [
        {
          "factory_id": "factory-a",
          "latest_raw_at": "2026-06-01T15:29:50Z",
          "latest_processed_at": "2026-06-01T15:29:52Z",
          "latest_processed_agg_at": "2026-06-01T15:25:00Z"
        }
      ]
    }
  }
}
```

## HISTORY 예시

Fast collector가 실행되면 `LATEST`를 업데이트한 뒤 snapshot을 복사해서 TTL이 있는 history item으로 저장한다.

```json
{
  "pk": "CLOUD#infra",
  "sk": "HISTORY#FAST#2026-06-01T15:30:00Z",
  "schema_version": "cloud-infra-status-v1",
  "snapshot_type": "fast",
  "updated_at": "2026-06-01T15:30:00Z",
  "ttl": 1780327800,
  "fast_updated_at": "2026-06-01T15:30:00Z",
  "slow_updated_at": "2026-06-01T15:25:00Z",
  "overall_status": "warning",
  "fast": {
    "backend_runtime": {},
    "data_pipeline": {},
    "factory_freshness": {}
  },
  "slow": {
    "eks_management": {},
    "storage_freshness": {}
  }
}
```

Slow collector도 같은 방식으로 저장한다.

```json
{
  "pk": "CLOUD#infra",
  "sk": "HISTORY#SLOW#2026-06-01T15:30:00Z",
  "schema_version": "cloud-infra-status-v1",
  "snapshot_type": "slow",
  "updated_at": "2026-06-01T15:30:00Z",
  "ttl": 1780392600,
  "fast_updated_at": "2026-06-01T15:30:00Z",
  "slow_updated_at": "2026-06-01T15:30:00Z",
  "overall_status": "normal",
  "fast": {
    "backend_runtime": {},
    "data_pipeline": {},
    "factory_freshness": {}
  },
  "slow": {
    "eks_management": {},
    "storage_freshness": {}
  }
}
```

권장 TTL:

| history type | 주기 | TTL |
| --- | ---: | ---: |
| `HISTORY#FAST` | 1분 | 6시간 |
| `HISTORY#SLOW` | 5분 | 24시간 |

## S3 저장 구조

S3는 장기 보관과 디버깅용이다.

```text
processed/cloud_infra/fast/yyyy=2026/mm=06/dd=01/hh=15/2026-06-01T15-30-00Z.json
processed/cloud_infra/slow/yyyy=2026/mm=06/dd=01/hh=15/2026-06-01T15-30-00Z.json
```

S3에는 DynamoDB보다 더 자세한 full snapshot을 저장해도 된다. DynamoDB는 Dashboard read model 중심으로 유지한다.

## Backend 조회 방식

Backend는 CloudWatch, EKS, Kubernetes API, S3를 직접 여러 번 조회하지 않는다.

기본 화면:

```text
GetItem
pk = CLOUD#infra
sk = LATEST
```

최근 추이:

```text
Query pk=CLOUD#infra begins_with(sk, HISTORY#FAST#)
Query pk=CLOUD#infra begins_with(sk, HISTORY#SLOW#)
```

상세 디버깅:

```text
S3 processed/cloud_infra/... snapshot 조회
```

## Status 계산

각 section은 자체 `status`를 가진다.

```text
normal
warning
critical
unknown
```

예시 기준:

| section | warning | critical |
| --- | --- | --- |
| Backend ECS | running < desired | running = 0 |
| ALB | target 5xx > 0 또는 latency 증가 | healthy host = 0 |
| Lambda | errors > 0 또는 throttles > 0 | 반복 errors 또는 throttles 지속 |
| DynamoDB | throttle > 0 | throttle 지속 또는 system error |
| Scheduler | 일부 disabled | refresh scheduler disabled |
| Factory freshness | warning factory 존재 | critical factory 존재 |
| EKS | node/pod warning | cluster/nodegroup degraded |
| ArgoCD | OutOfSync 존재 | Degraded 존재 |

`overall_status`는 가장 나쁜 section 상태를 따른다.

```text
critical > warning > unknown > normal
```

## 비용 추정

Fast/Slow collector 방식은 비용이 낮다.

월 실행 횟수:

```text
FastCollector 1분 = 43,200회/month
SlowCollector 5분 = 8,640회/month
합계 = 51,840회/month
```

각 실행에서 최소 다음 작업을 수행한다.

```text
DynamoDB LATEST UpdateItem 1회
DynamoDB HISTORY PutItem 1회
S3 PutObject 1회
```

대략 비용:

| 항목 | 월 추정 |
| --- | ---: |
| Lambda | `~$0.3~0.8` |
| DynamoDB writes/reads | `~$0.3~0.6` |
| S3 PUT | `~$0.26` |
| S3 storage | `~$0.01~0.05` |
| EventBridge Scheduler | `~$0~0.05` |
| CloudWatch metric API / Lambda logs | `~$0.1~0.4` |
| **합계** | **`~$1~3/month`** |

비교:

```text
CloudWatch Container Insights 전체 수집: ~$65~75/month
필요 metric만 collector로 수집: ~$1~3/month
```

## 구현 순서와 현재 상태

### Phase 1: Fast Collector - 완료

사용자 서비스와 데이터 파이프라인 장애 감지를 구현했다.

수집:

```text
ECS desired/running
ECS CPU/memory
ALB healthy host / 5xx / latency
Lambda errors / duration / throttles
DynamoDB throttles
Scheduler enabled
factory freshness/risk
```

저장:

```text
DynamoDB CLOUD#infra / LATEST.fast
DynamoDB HISTORY#FAST#timestamp
S3 processed/cloud_infra/fast
```

### Phase 2: Slow Collector 1차 - 완료

EKS와 S3 freshness를 추가했다.

수집:

```text
EKS cluster/nodegroup
ASG healthy instances
S3 latest raw/processed/processed_agg object time
```

### Phase 3: Slow Collector 2차 - 완료

Kubernetes 내부 상태를 추가했다.

수집:

```text
node ready count
node CPU/memory via metrics-server
pod phase/restart
top pods by CPU/memory
ArgoCD sync/health
```

### Phase 4: Backend 연결 - 남음

Backend는 `CLOUD#infra / LATEST`를 읽어서 Cloud infra dashboard API를 만든다.

권장 API shape:

```text
GET /api/cloud-infra/status
  -> DynamoDB GetItem pk=CLOUD#infra sk=LATEST
  -> LATEST 구조를 기본적으로 그대로 반환
```

초기 구현에서는 backend가 CloudWatch, EKS, Kubernetes API, S3를 직접 조회하지 않는다. Dashboard에 필요한 필드명이 안정화될 때까지는 `LATEST`를 그대로 노출하고, UI가 실제로 쓰는 compact summary가 확정되면 backend에서 변환 응답을 추가한다.

권장 응답:

```json
{
  "schema_version": "cloud-infra-status-v1",
  "updated_at": "2026-06-01T15:30:00Z",
  "fast_updated_at": "2026-06-01T15:30:00Z",
  "slow_updated_at": "2026-06-01T15:25:00Z",
  "overall_status": "normal",
  "fast": {},
  "slow": {}
}
```

## 설계 원칙

- CloudWatch Container Insights는 기본 disabled로 유지한다.
- Dashboard가 필요한 metric만 read model로 저장한다.
- 원본 metric history는 CloudWatch 또는 각 서비스 API의 책임으로 둔다.
- DynamoDB는 최신 상태와 짧은 TTL history만 담당한다.
- S3는 장기 snapshot과 디버깅 근거를 담당한다.
- Backend는 CloudWatch/EKS/S3를 직접 반복 조회하지 않는다.
- Fast와 Slow collector는 서로 다른 필드만 업데이트한다.
- metric 수집 실패 자체도 `status=unknown`과 `errors[]`로 저장한다.

## 남은 결정 사항

1. S3 `processed/cloud_infra` snapshot lifecycle을 30일 삭제로 둘지 Glacier 전환으로 둘지
2. Cloud infra dashboard API를 `LATEST` pass-through로 시작한 뒤 compact response를 추가할지
3. `HISTORY#FAST`/`HISTORY#SLOW`를 Dashboard trend API에서 실제로 조회할지, 운영 디버깅 전용으로 둘지
