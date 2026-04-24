# 🛡️ Aegis-Pi Risk Twin

> **Safe-Edge 기반 단일 공장 엣지를, 멀티 공장 중앙 관제 구조로 확장하는 Risk Twin 플랫폼**

---

## 📌 프로젝트 개요

기존 **Safe-Edge** 프로젝트는 라즈베리파이 3노드 K3s 클러스터로 단일 공장 내 엣지 모니터링을 구현한 프로젝트입니다.  
**Aegis-Pi**는 이 기반 위에서, 여러 공장의 위험 상태를 본사에서 한눈에 보는 **Hub/Spoke 중앙 관제 구조**로 확장합니다.

| 항목 | 내용 |
|------|------|
| 프로젝트명 | Aegis-Pi Risk Twin |
| 현재 단계 | 설계 기준선 완료 / 구현 시작 전 |
| 1차 대상 사용자 | 본사 관제 담당자 |
| 2차 대상 사용자 | 운영·배포 담당 개발자 |

---

## 🏗️ 전체 구조

```
🌐 AWS EKS Hub  ← 중앙 제어 / 관제
    │
    ├── 🏭 factory-a  (Raspberry Pi 5 × 3, K3s)   ← 실제 운영형 Spoke
    ├── 🖥️  factory-b  (Mac mini VM, K3s)           ← 테스트베드형 Spoke
    └── 💻 factory-c  (Windows VM, K3s)             ← 테스트베드형 Spoke
```

Hub와 각 Spoke는 **별도의 독립 Kubernetes 클러스터**로 구성됩니다.  
단일 클러스터 통합 방식이 아닌, **EKS Hub + 공장별 K3s Spoke** 구조를 기준으로 합니다.

### 공장별 역할 비교

| 구분 | factory-a | factory-b / factory-c |
|------|-----------|----------------------|
| 성격 | 실제 운영형 | 테스트베드형 |
| 입력 | 실제 센서·카메라·마이크 | Dummy 시나리오 |
| 스토리지 | Longhorn 유지 | Longhorn 제외 |
| 배포 정책 | 보수적 (수동 복구) | 빠른 반영 / 자동 롤백 허용 |

---

## 🔄 두 개의 핵심 흐름

### ⚙️ 제어 평면 (배포)

```
GitHub Push
    → GitHub Actions
    → ECR (이미지 빌드/푸시)
    → ArgoCD
    → Tailscale (보안 터널)
    → 각 Spoke 롤아웃
```

ArgoCD **ApplicationSet** 기반으로 공장별 `values.yaml` 차등 적용,  
운영형과 테스트베드형의 Sync 정책을 분리합니다.

### 📡 데이터 평면 (관제)

```
센서 / 카메라 / 마이크 / 시스템 상태
    → Edge Agent
    → AWS IoT Core
    → S3 (factory_id / source_type / 날짜 파티셔닝)
    → 정규화 / 판단 서비스
    → Risk Score Engine
```

S3 적재 이후 EKS 내부에서 처리하며, 결과는 **Prometheus 호환 메트릭** 형태로 AMP / Grafana에 노출합니다.

---

## ⚠️ Risk 모델

위험 상태는 **3단계**로 표현하며, 내부적으로 0~100점 스코어를 계산합니다.  
메인 대시보드 카드에는 점수를 직접 노출하지 않고, 상태 레이블만 표시합니다.

| 상태 | 내부 점수 | 의미 |
|------|----------|------|
| 🟢 **안전** | 0 ~ 39 | 정상 운영 범위 |
| 🟡 **주의** | 40 ~ 69 | 이상 징후 감지, 모니터링 강화 |
| 🔴 **위험** | 70 ~ 100 | 즉시 조치 필요 |

### 주요 Risk 입력 항목

- 🌡️ `temperature` / `humidity` (온도·습도)
- 📟 `sensor_status` (센서 정상 여부)
- 🤖 `edge_agent_status` (에이전트 상태)
- 🖧 `node_status` (노드 상태)
- 📷 `camera_status` / `mic_status` (카메라·마이크 상태)
- 🔁 `pipeline_status` (Hub 파이프라인 상태)

### Risk 출력 항목

- 현재 상태 (`안전 / 주의 / 위험`)
- 최근 10분 변화 방향 (▲ 상승 / ▼ 하강)
- 주요 원인 Top 3
- `event_timestamp` / `processed_at`

---

## 🖥️ 관제 대시보드 구조

```
┌──────────────────────────────────────────────────────────┐
│  🏭 factory-a    🏭 factory-b    🏭 factory-c            │  ← 공장별 위험 상태 카드
│  🟢 안전          🟡 주의          🔴 위험                 │
├───────────────────────────┬──────────────────────────────┤
│  🌡️ 온도·습도 센서 현황    │  ⚠️  이상 시스템 목록          │
│                           │                              │
├───────────────────────────┴──────────────────────────────┤
│  📋 최근 상태 변화 / 주요 이벤트 로그                        │
└──────────────────────────────────────────────────────────┘
```

각 공장 카드에는 **공장명 / 현재 상태 / 최근 10분 변화 방향 / 이상 시스템 개수**를 표시합니다.

---

## 🗂️ Hub 내부 구성

AWS EKS 내부는 기능 단위 네임스페이스로 분리합니다.

| 네임스페이스 | 역할 |
|-------------|------|
| `argocd` | 배포 제어 |
| `observability` | 관제·메트릭 (AMP + Grafana) |
| `risk` | Risk 정규화, Risk Score Engine |
| `ops-support` | pipeline_status 집계 보조 |

### AWS 관리형 서비스 역할

| 서비스 | 역할 |
|--------|------|
| **IoT Core** | 중앙 수신 진입점 |
| **S3** | 원본 데이터 적재 |
| **AMP** | Prometheus 호환 메트릭 백엔드 |
| **ECR** | 컨테이너 이미지 레지스트리 |

---

## 📅 구현 단계 (M0 ~ M7)

| 단계 | 내용 | 상태 |
|------|------|------|
| **Phase 0** | 문서 기준선 고정 | ✅ 완료 |
| **Phase 1 (M0)** | factory-a Safe-Edge 기준선 재구성 | 🔜 다음 |
| **Phase 2 (M1)** | AWS EKS Hub 기준선 구성 | ⬜ 대기 |
| **Phase 3 (M2)** | Tailscale Mesh 기반 Hub ↔ factory-a 연결 | ⬜ 대기 |
| **Phase 4 (M3~M4)** | factory-a 배포·데이터 파이프라인 구성 | ⬜ 대기 |
| **Phase 5 (M5)** | factory-b / factory-c VM Spoke 확장 | ⬜ 대기 |
| **Phase 6 (M6)** | Risk Twin + 관제 화면 연결 | ⬜ 대기 |
| **Phase 7 (M7)** | 통합 검증 (운영형·테스트베드형·Failover·롤백) | ⬜ 대기 |

---

## ✅ MVP 포함 범위

**포함 ✅**
- factory-a Safe-Edge 기준선 재구성
- factory-b / factory-c K3s 테스트베드형 Spoke
- AWS EKS Hub (배포·관제·Risk 처리)
- Tailscale 기반 Hub-Spoke 보안 연결
- IoT Core → S3 수집 경로
- Risk Score 기반 `안전 / 주의 / 위험` 표현
- 메인 관제 대시보드 (공장 카드, 센서 현황, 이상 목록, 로그)

**제외 ❌**
- LLM 기반 일일 보고서 자동 생성
- event 기반 점수 반영
- 별도 이벤트 전용 파이프라인
- 공장별 상세 커스텀 정책 활성화
- 자동화된 장애·복구 리허설

---

## 🚀 향후 확장 방향

| 확장 축 | 내용 |
|---------|------|
| 🎯 이벤트 기반 | `event` 입력 활성화, Risk Score 직접 반영 |
| 📊 Analysis 계층 | 일일 보고서, LLM 기반 위험도 해석 |
| 🔁 데이터 플레인 | 직접 호출형 → 큐/이벤트 기반 트리거 |
| 🏭 Fleet 확장 | 공장 수 추가, 공장별 override 운영 활성화 |
| 🤖 배포 자동화 | 배포 검증 자동화, 장애·복구 리허설 자동화 |

---

## 📁 문서 구조

```
docs/
├── planning/         # 프로젝트 계획 및 구현 전략
│   ├── 00_project_overview.md     # 프로젝트 개요 (읽기 시작점)
│   ├── 01_safe_edge_transition.md # Safe-Edge → Aegis-Pi 전환
│   ├── 02_implementation_plan.md  # 단계별 구현 계획
│   └── 03_evaluation_plan.md      # 테스트 및 평가 전략
├── architecture/     # 구조 설계
│   ├── current_architecture.md    # 현재 freeze된 설계 기준
│   └── target_architecture.md     # MVP 이후 확장 방향
├── product/          # 제품 정의
│   ├── mvp_scope.md               # MVP 포함/제외 범위
│   └── user_flow.md               # 사용자 흐름
├── specs/            # 기능 스펙
│   └── monitoring_dashboard/      # 관제 대시보드 상세 스펙
│       ├── requirements.md
│       ├── screen_plan.md
│       ├── api_spec.md
│       └── data_model.md
├── ops/              # 운영 가이드
│   ├── quick_start.md
│   ├── safe_edge_bootstrap.md
│   ├── self_check.md
│   └── troubleshooting.md
├── demo/             # 시연 가이드
│   ├── demo_scenario.md
│   └── demo_ops_notes.md
├── presentation/     # 발표·보고 자료
│   ├── advisor_brief.md
│   └── review_summary.md
└── report/           # 보고서
    ├── executive_summary.md
    └── report_draft.md
```

### 📖 추천 읽기 순서

**구조를 이해할 때**
1. `planning/00_project_overview.md`
2. `architecture/current_architecture.md`
3. `planning/02_implementation_plan.md`

**구축을 시작할 때**
1. `ops/quick_start.md`
2. `ops/safe_edge_bootstrap.md`
3. `planning/03_evaluation_plan.md`

**관제 화면을 구현할 때**
1. `specs/monitoring_dashboard/requirements.md`
2. `specs/monitoring_dashboard/screen_plan.md`
3. `specs/monitoring_dashboard/api_spec.md`

---

## ⚡ 주요 리스크

| 리스크 | 내용 |
|--------|------|
| ⏱️ 일정 지연 | factory-a 기준선 복구가 늦어지면 전체 일정에 영향 |
| 🔬 수치 미확정 | 온도·습도 임계값, 지연 기준 등은 실측 후 확정 |
| 🧪 환경 차이 | 운영형(실제 입력)과 테스트베드형(Dummy) 간 차이 검증 필요 |

---

## 📝 문서 상태 기준

| 상태 | 의미 |
|------|------|
| `source of truth` | 현재 구현·설계 기준 문서 |
| `draft` | 방향은 있으나 세부값 미정 |
| `candidate` | 후속 확장 또는 검토용 |

---

*기준일: 2026-04-24*
