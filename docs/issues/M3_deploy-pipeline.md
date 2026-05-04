# M3. 배포 파이프라인

> **마일스톤 목표**: GitHub Actions → ECR → ArgoCD → Spoke 롤아웃 흐름을 자동화한다.  
> M2(Hub-Spoke 연결) 완료 후 진행하며, M4(데이터 플레인)와 병렬 진행 가능하다.  
> 이 마일스톤이 완료되면 push 한 번으로 `factory-a`에 배포가 자동으로 흐른다.

---

## 수정 이력

| 날짜 | 버전 | 내용 |
| --- | --- | --- |
| 2026-05-04 | rev-20260504-01 | GitHub Actions는 CI, GitHub+ArgoCD는 CD로 사용하는 책임 경계 기준을 반영 |

---

## 책임 경계

이 마일스톤은 `docs/planning/11_delivery_ownership_flow.md`를 따른다.

```text
GitHub Actions:
  CI, image build, test, ECR push, manifest/value update

GitHub + ArgoCD:
  CD, Application/ApplicationSet sync, deployment drift control
```

GitHub Actions는 운영 클러스터에 직접 `kubectl apply`하지 않는다. 실제 배포는 GitHub repository에 남은 desired state를 ArgoCD가 sync하는 방식으로 수행한다.

---

## Issue 1 - [배포/Helm] GitHub 저장소 구조 설계 (베이스 + 공장별 values)

### 🎯 목표 (What & Why)

공통 베이스 Helm 차트와 공장별 values 파일을 분리하는 저장소 구조를 확정한다.  
이 구조가 ArgoCD ApplicationSet 자동화와 공장별 독립 배포 관리의 기반이 된다.

### ✅ 완료 조건 (Definition of Done)

- [ ] 저장소 구조 확정 및 초기화
  ```
  charts/
    aegis-spoke/          # 공통 베이스 Helm 차트
      Chart.yaml
      values.yaml         # 기본값
      templates/
  envs/
    factory-a/
      values.yaml         # factory-a 전용 override
    factory-b/
      values.yaml
    factory-c/
      values.yaml
  .github/
    workflows/
  ```
- [ ] 공장별 values 범위 확정 및 초기값 작성
  - `factory_id`
  - `environment_type` (`physical-rpi` / `vm-mac` / `vm-windows`)
  - `input_module_type` (`sensor` / `dummy`)
  - 사용 필드 여부 (display, risk_enabled)
- [ ] M3 배포 검증용 기준 앱 1개 선정
  - 실제 서비스 또는 `sample-app`
  - 이후 GitHub Actions / ArgoCD / end-to-end 검증의 공통 대상
- [ ] `input_module_type` 기본 매핑 적용
  - `factory-a` = `sensor`
  - `factory-b` = `dummy`
  - `factory-c` = `dummy`
- [ ] 베이스 차트와 values 경계 역할 분리 문서화

### 🔍 Acceptance Criteria

- `helm template charts/aegis-spoke -f envs/factory-a/values.yaml` 정상 렌더링
- 기준 앱이 차트/values 구조 안에서 일관되게 표현됨
- 공장별 values 파일이 서로 독립적으로 동작
- 저장소 구조가 배포 파이프라인 관련 문서에 반영됨

---

## Issue 2 - [배포/ECR] 저장소 구성 및 이미지 태그 전략

### 🎯 목표 (What & Why)

컨테이너 이미지를 저장하고 ArgoCD가 참조할 ECR 저장소를 구성한다.  
`git sha` 기반 태그로 배포 이력을 추적하고, 보조 태그로 운영 편의를 확보한다.

### ✅ 완료 조건 (Definition of Done)

- [ ] 서비스별 ECR 저장소 생성
  - Edge Agent
  - Dummy Sensor
  - Risk Score Engine
  - 정규화/판단 서비스
- [ ] 이미지 태그 전략 확정
  - 기본 태그: `git sha` (`sha-<7자리>`)
  - 보조 태그: `latest` 또는 브랜치명 (선택 적용)
- [ ] ECR 저장소 접근 IAM 정책 설정
  - GitHub Actions → ECR 푸시 권한
  - EKS 노드그룹 → ECR 풀 권한
- [ ] 이미지 스캔 설정 (선택)

### 🔍 Acceptance Criteria

- AWS 콘솔에서 ECR 저장소 목록 확인
- 로컬에서 `docker push` 후 ECR 저장소에 이미지 확인
- EKS 파드에서 ECR 이미지 풀 성공

---

## Issue 3 - [배포/GitHub Actions] 빌드/푸시 워크플로우 구성

### 🎯 목표 (What & Why)

코드 변경 시 컨테이너 이미지를 자동으로 빌드하고 ECR에 푸시하는 워크플로우를 구성한다.  
서비스별 변경 감지나 세부 분기는 후속 단계에서 추가할 수 있게 구조만 열어둔다.

### ✅ 완료 조건 (Definition of Done)

- [ ] M3 배포 검증용 기준 앱 Dockerfile 및 빌드 대상 확정
- [ ] `.github/workflows/build-push.yaml` 생성
- [ ] 워크플로우 트리거 설정 (main 브랜치 push)
- [ ] AWS 인증 설정 (OIDC 기반 역할 연동, 시크릿 없이)
- [ ] Docker 빌드 및 ECR 푸시 스텝 구성
  - `git sha` 태그 자동 적용
- [ ] ARM64 빌드 지원 확인 (Raspberry Pi 대상 이미지)
- [ ] 빌드 성공/실패 알림 설정 (선택)

### 🔍 Acceptance Criteria

- main 브랜치 push 후 GitHub Actions 워크플로우 `Success`
- ECR 저장소에 `sha-<커밋해시>` 태그 이미지 확인
- 기준 앱 이미지가 실제로 빌드/푸시됨 확인
- 빌드 로그에서 빌드/푸시 단계 정상 완료 확인

---

## Issue 4 - [배포/ArgoCD] ApplicationSet 구성 (`factory-a` 기준)

### 🎯 목표 (What & Why)

공장별 values 목록을 기준으로 ApplicationSet을 생성하여 공장 추가 시 자동으로 Application이 생기는 구조를 만든다.  
`factory-a`를 기준으로 먼저 검증하고, M5(VM Spoke 확장) 시 `factory-b`, `factory-c`를 추가한다.

### ✅ 완료 조건 (Definition of Done)

- [ ] ArgoCD ApplicationSet 매니페스트 작성
  - Generator: `Git` 또는 `List` 기반 (공장별 values 경로 기준)
  - Template: 공통 베이스 차트 참조 + 공장별 values 경로 주입
- [ ] `factory-a` ApplicationSet 적용 및 Application 자동 생성 확인
- [ ] Application 이름 규칙 확정 (예: `aegis-spoke-factory-a`)
- [ ] 기준 앱이 `factory-a` values 경로를 통해 실제 배포 대상으로 연결됨 확인
- [ ] Sync 정책 설정 (운영형: 보수적 수동 Sync 또는 자동 Sync with Prune)

### 🔍 Acceptance Criteria

- ArgoCD UI에서 `aegis-spoke-factory-a` Application 자동 생성 확인
- Application이 `factory-a` Spoke 클러스터를 대상으로 설정되어 있음
- Sync 정책에 따라 자동/수동 Sync 동작 확인

---

## Issue 5 - [배포/ArgoCD] 운영형 동기화 정책 및 롤백 정책 적용

### 🎯 목표 (What & Why)

`factory-a` 운영형 Spoke에 맞는 보수적 동기화 정책과 배포 실패 시 수동 확인 원칙을 적용한다.  
테스트베드형 Spoke(M5에서 추가)와 차별화된 정책을 명확히 한다.

### ✅ 완료 조건 (Definition of Done)

- [ ] 운영형 Spoke 동기화 정책 확정 및 적용
  - 자동 Sync with Prune 또는 수동 Sync 방식 결정
  - Self-heal 설정 여부 결정
- [ ] 배포 실패 시 처리 원칙 적용
  - 운영형(`factory-a`): 실패 시 수동 확인 후 조치
- [ ] RollingUpdate 전략 설정 (파드 교체 방식)
- [ ] 정책 내용을 배포 파이프라인 관련 문서에 반영

### 🔍 Acceptance Criteria

- 의도적으로 잘못된 이미지 태그 배포 시 기존 파드 유지 확인
- ArgoCD에서 배포 실패 상태 명확히 표시
- 수동으로 이전 values로 Sync 시 이전 버전 복구 확인

---

## Issue 6 - [배포/GitHub Actions] manifest 갱신 워크플로우 구성

### 🎯 목표 (What & Why)

빌드된 이미지 태그를 Helm values 파일에 자동으로 반영하는 워크플로우를 구성한다.  
이 단계가 없으면 ArgoCD는 새 이미지를 자동으로 감지하지 못한다.

> 주의:
> 이 워크플로우는 자동 커밋 후 자기 자신을 다시 트리거하지 않도록 loop 방지 규칙을 포함해야 한다.

### ✅ 완료 조건 (Definition of Done)

- [ ] `.github/workflows/update-manifest.yaml` 생성
- [ ] 빌드 워크플로우 완료 후 연계 트리거 설정
- [ ] 신규 이미지 태그를 `envs/{factory}/values.yaml`의 이미지 태그 필드에 자동 반영
- [ ] 변경된 values 파일을 저장소에 자동 커밋 및 push
  - 커밋 메시지 형식 정의 (예: `chore: update image tag to sha-xxxxxxx`)
- [ ] 특정 공장 values만 선택적으로 갱신하는 구조 확인
- [ ] workflow loop 방지 규칙 적용
  - 봇 커밋 메시지 필터 또는 경로 필터
  - 자기 자신이 만든 커밋에 재반응하지 않도록 설정

### 🔍 Acceptance Criteria

- 빌드 워크플로우 완료 후 `envs/factory-a/values.yaml` 이미지 태그 자동 갱신
- 갱신된 커밋이 저장소 히스토리에 기록
- 자동 커밋 후 동일 워크플로우가 무한 반복되지 않음
- ArgoCD가 변경된 values 파일 감지 후 `OutOfSync` 상태 전환

---

## Issue 7 - [배포/GitHub Actions] 배포 검증 워크플로우 구성

### 🎯 목표 (What & Why)

ArgoCD Sync 완료 후 배포 성공 여부를 자동으로 확인하는 워크플로우를 구성한다.  
성공 기준(`Sync` + `Healthy` + 대상 파드 `Running`)을 코드로 정의한다.

### ✅ 완료 조건 (Definition of Done)

- [ ] `.github/workflows/verify-deploy.yaml` 생성
- [ ] 검증 경로 확정
  - ArgoCD API/CLI 상태 확인
  - `factory-a.kubeconfig` 기반 `kubectl` 상태 확인
- [ ] ArgoCD CLI를 사용한 Sync 상태 폴링 로직 구성
- [ ] 배포 성공 판정 기준 적용
  - `Sync` 상태: `Synced`
  - `Health` 상태: `Healthy`
  - 대상 파드: `Running`
- [ ] 타임아웃 설정 (배포 대기 최대 시간)
- [ ] 검증 실패 시 Slack/이메일 알림 설정 (선택)

### 🔍 Acceptance Criteria

- 배포 성공 시 워크플로우 `Success` 종료
- 기준 앱 Deployment/Pod 상태를 `kubectl`로 검증 가능
- 배포 실패(파드 CrashLoopBackOff 등) 시 워크플로우 `Failure` 종료
- 타임아웃 초과 시 워크플로우 `Failure` 종료

---

## Issue 8 - [검증/ArgoCD] `factory-a` end-to-end 배포 검증

### 🎯 목표 (What & Why)

GitHub push부터 `factory-a` Spoke 파드 롤아웃까지 전체 파이프라인이 자동으로 흐르는지 검증한다.  
이 검증이 완료되어야 M3 마일스톤이 완료된다.

### ✅ 완료 조건 (Definition of Done)

- [ ] 기준 앱 코드 또는 이미지 태그에 실제 변경을 만들어 main 브랜치 push
- [ ] 빌드 → ECR 푸시 → manifest 갱신 → ArgoCD Sync → Spoke 롤아웃 전체 흐름 자동 완료 확인
- [ ] `factory-a` K3s에서 새 이미지 파드 `Running` 확인
- [ ] 배포 지연 시간 측정 (참고 지표, 강제 기준 아님)
  - push 시각 → `factory-a` 파드 Running 시각
- [ ] 측정 결과를 배포 파이프라인 관련 문서에 기록

### 🔍 Acceptance Criteria

- GitHub Actions 3개 워크플로우 전부 `Success`
- ArgoCD `aegis-spoke-factory-a` Application `Synced` + `Healthy`
- `kubectl --kubeconfig=factory-a.kubeconfig get pods`에서 새 이미지 파드 `Running`
- 배포 지연 시간 실측값 기록 완료
