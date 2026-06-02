from report_generator.bedrock_client import MockBedrockReportClient
from report_generator.generate_cloud_infra_report import generate_cloud_infra_report


def test_generate_cloud_infra_report_inserts_tables_and_validates_context_only_prompt():
    context = _context()
    client = MockBedrockReportClient(
        "\n".join([
            "# Cloud Infra 일일 운영 리포트 - 2026-01-01",
            "",
            "## 요약",
            "",
            "cloud-infra 2026-01-01 overall_status warning 상태입니다.",
            "",
            "## 데이터 수집 상태",
            "",
            "fast 1430/1440, 0.9931 및 slow 288/288, 1.0 기준입니다.",
            "",
            "## Backend Runtime",
            "",
            "ECS는 running 2와 desired 2를 유지했습니다.",
            "",
            "## Data Pipeline",
            "",
            "Lambda 오류와 throttle을 확인합니다.",
            "",
            "## EKS Management",
            "",
            "EKS node ready 2/2 상태입니다.",
            "",
            "## ArgoCD 및 배포 상태",
            "",
            "ArgoCD synced 3/3 상태입니다.",
            "",
            "## Factory Freshness 및 Storage Freshness",
            "",
            "freshness는 정상 범위입니다.",
            "",
            "## 주요 이벤트",
            "",
            "ALB 5xx 이벤트를 확인합니다.",
            "",
            "## 확인 필요 항목",
            "",
            "ALB trace를 확인합니다.",
            "",
            "## 데이터 한계",
            "",
            "S3 processed 기반 LLM 초안입니다.",
        ])
    )

    result = generate_cloud_infra_report(
        report_context=context,
        output_prefix="reports/daily/yyyy=2026/mm=01/dd=01/cloud-infra",
        bedrock_client=client,
    )

    assert result["status"] == "success"
    assert result["report_key"] == "reports/daily/yyyy=2026/mm=01/dd=01/cloud-infra/report.md"
    assert result["metadata_key"] == "reports/daily/yyyy=2026/mm=01/dd=01/cloud-infra/generation-metadata.json"
    assert "## 핵심 지표 표" in result["markdown"]
    assert "| fast 수집률 | 1430/1440, 99.31% | 양호 |" in result["markdown"]
    assert "| Backend ECS running/desired | 2/2 | running 최소값 기준 |" in result["markdown"]
    assert "| 마지막 관측 hour | 23 | 뒤쪽 empty 0h | partial-day/미수집 구분 |" in result["markdown"]
    assert "| CPU 사용 상위 Pod | argocd/argocd-server | 12.5 |" in result["markdown"]
    assert "target_id=cloud-infra, report_date=2026-01-01, overall_status=warning" in result["markdown"]
    assert "fast 수집 원문: 1430/1440, collection_rate 0.9931" in result["markdown"]
    assert "latest_observed_hour=23, empty_tail_hour_count=0" in result["markdown"]
    assert "report-context.json" in client.prompts[0]
    assert "각 본문 섹션은 표 아래에 2~5개 bullet" in client.prompts[0]
    assert "Backend Runtime 섹션에는 ECS desired/running 차이" in client.prompts[0]
    assert "source_message_id" not in client.prompts[0]
    assert "raw_body" not in client.prompts[0]


def test_generate_cloud_infra_report_rejects_missing_invariants():
    result = generate_cloud_infra_report(
        report_context=_context(),
        output_prefix="reports/daily/yyyy=2026/mm=01/dd=01/cloud-infra",
        bedrock_client=MockBedrockReportClient("# 잘못된 보고서\n"),
    )

    assert result["status"] == "validation_failed"
    assert "missing invariant value: 2026-01-01" in result["validation_errors"]
    assert "report_key" not in result


def _context():
    return {
        "schema_version": "0.1.0",
        "context_type": "daily_cloud_infra_report",
        "target_id": "cloud-infra",
        "report_date": "2026-01-01",
        "timezone": "Asia/Seoul",
        "report_window": {
            "timezone": "Asia/Seoul",
            "start_local": "2026-01-01T00:00:00+09:00",
            "end_local": "2026-01-01T23:59:59+09:00",
            "start_utc": "2025-12-31T15:00:00Z",
            "end_utc": "2026-01-01T14:59:59Z",
            "s3_partition_timezone": "UTC",
        },
        "overall_status": "warning",
        "data_quality": {
            "fast_expected_count": 1440,
            "fast_actual_count": 1430,
            "fast_collection_rate": 0.9931,
            "slow_expected_count": 288,
            "slow_actual_count": 288,
            "slow_collection_rate": 1.0,
            "max_gap_minutes": 3,
            "latest_observed_hour": "23",
            "empty_tail_hour_count": 0,
            "gap_windows": [{"time_range": "03:00~03:03", "duration_seconds": 180}],
            "invalid_record_count": 0,
            "duplicate_record_count": 0,
        },
        "backend_runtime": {
            "ecs_desired_count": 2,
            "ecs_running_count_min": 2,
            "ecs_running_count_max": 2,
            "ecs_pending_count_max": 0,
            "ecs_cpu_avg": 33,
            "ecs_cpu_max": 44,
            "ecs_memory_avg": 55,
            "ecs_memory_max": 61,
            "alb_healthy_host_min": 2,
            "alb_unhealthy_host_max": 0,
            "alb_5xx_total": 1,
        },
        "data_pipeline": {
            "lambda_error_total": 0,
            "lambda_throttle_total": 0,
            "lambda_duration_p95_max": 120,
            "dynamodb_read_throttle_total": 0,
            "dynamodb_write_throttle_total": 0,
            "dynamodb_system_error_total": 0,
            "disabled_scheduler_count": 0,
        },
        "eks_management": {
            "cluster_status": "ACTIVE",
            "nodes_ready_min": 2,
            "nodes_total_max": 2,
            "not_ready_node_minutes": 0,
            "pod_pending_max": 0,
            "pod_failed_max": 0,
            "pod_unknown_max": 0,
            "restart_count_delta": 0,
            "top_cpu_pods": [{"namespace": "argocd", "pod": "argocd-server", "cpu_millicores": 12.5}],
            "top_memory_pods": [{"namespace": "argocd", "pod": "argocd-server", "memory_mib": 128.25}],
        },
        "argocd": {
            "applications_total_max": 3,
            "synced_min": 3,
            "out_of_sync_max": 0,
            "degraded_max": 0,
            "healthy_min": 3,
        },
        "freshness": {
            "factory_pipeline_warning_minutes": 0,
            "factory_pipeline_critical_minutes": 0,
            "stale_factory_count_max": 0,
            "storage_freshness_non_normal_count": 0,
        },
        "events": [],
        "recommended_checks": [],
        "data_limitations": ["Report is based on S3 processed cloud_infra fast/slow snapshots."],
    }
