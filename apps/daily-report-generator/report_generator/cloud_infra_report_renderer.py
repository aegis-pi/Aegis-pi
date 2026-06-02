from __future__ import annotations

import re


def render_cloud_infra_markdown(generated_text: str, context: dict) -> str:
    markdown = generated_text.rstrip() + "\n"
    markdown = _insert_key_metrics_table(markdown, context)
    for heading, table in (
        ("## 데이터 수집 상태", _data_collection_table(context)),
        ("## Backend Runtime", _backend_runtime_table(context)),
        ("## Data Pipeline", _data_pipeline_table(context)),
        ("## EKS Management", _eks_management_table(context)),
        ("## ArgoCD 및 배포 상태", _argocd_table(context)),
        ("## Factory Freshness 및 Storage Freshness", _freshness_table(context)),
        ("## 주요 이벤트", _events_table(context)),
        ("## 확인 필요 항목", _checks_table(context)),
    ):
        markdown = _insert_table_after_heading(markdown, heading, table)
    return _append_verification_metrics(markdown, context)


def _insert_key_metrics_table(markdown: str, context: dict) -> str:
    if "## 핵심 지표 표" in markdown:
        return markdown
    table = _key_metrics_table(context)
    marker = "\n## 데이터 수집 상태"
    if marker in markdown:
        head, tail = markdown.split(marker, 1)
        return f"{head.rstrip()}\n\n{table}\n{marker}{tail}"
    return markdown.rstrip() + "\n\n" + table + "\n"


def _key_metrics_table(context: dict) -> str:
    dq = context.get("data_quality", {})
    backend = context.get("backend_runtime", {})
    pipeline = context.get("data_pipeline", {})
    eks = context.get("eks_management", {})
    argo = context.get("argocd", {})
    freshness = context.get("freshness", {})
    rows = [
        ("전체 상태", context.get("overall_status"), _overall_judgement(context.get("overall_status"))),
        ("fast 수집률", _collection_value(dq, "fast"), _collection_judgement(dq.get("fast_collection_rate"))),
        ("slow 수집률", _collection_value(dq, "slow"), _collection_judgement(dq.get("slow_collection_rate"))),
        ("Backend ECS running/desired", f"{_fmt(backend.get('ecs_running_count_min'))}/{_fmt(backend.get('ecs_desired_count'))}", "running 최소값 기준"),
        ("ALB healthy/unhealthy host", f"{_fmt(backend.get('alb_healthy_host_min'))}/{_fmt(backend.get('alb_unhealthy_host_max'))}", _count_judgement(backend.get("alb_unhealthy_host_max"), "ALB target 확인")),
        ("ALB 5xx count", _fmt(backend.get("alb_5xx_total")), _count_judgement(backend.get("alb_5xx_total"), "요청 trace 확인")),
        ("Data Pipeline Lambda error/throttle", f"{_fmt(pipeline.get('lambda_error_total'))}/{_fmt(pipeline.get('lambda_throttle_total'))}", _count_judgement((pipeline.get("lambda_error_total") or 0) + (pipeline.get("lambda_throttle_total") or 0), "Lambda 로그 확인")),
        ("DynamoDB throttle/system error", f"{_fmt((pipeline.get('dynamodb_read_throttle_total') or 0) + (pipeline.get('dynamodb_write_throttle_total') or 0))}/{_fmt(pipeline.get('dynamodb_system_error_total'))}", "throttle/error 확인"),
        ("EKS node ready/total", f"{_fmt(eks.get('nodes_ready_min'))}/{_fmt(eks.get('nodes_total_max'))}", _count_judgement(eks.get("not_ready_node_minutes"), "Node 상태 확인", "Node ready 양호")),
        ("Pod pending/failed", f"{_fmt(eks.get('pod_pending_max'))}/{_fmt(eks.get('pod_failed_max'))}", "Pod 상태 확인"),
        ("Pod restart delta", _fmt(eks.get("restart_count_delta")), _count_judgement(eks.get("restart_count_delta"), "재시작 원인 확인")),
        ("ArgoCD synced/healthy", f"{_fmt(argo.get('synced_min'))}/{_fmt(argo.get('healthy_min'))}", "배포 상태 확인"),
        ("Factory freshness stale count", _fmt(freshness.get("stale_factory_count_max")), _count_judgement(freshness.get("stale_factory_count_max"), "Factory freshness 확인")),
        ("Storage freshness stale count", _fmt(freshness.get("storage_freshness_non_normal_count")), _count_judgement(freshness.get("storage_freshness_non_normal_count"), "Storage freshness 확인")),
    ]
    return _table(("구분", "값", "판단"), rows, align=(None, "right", None), heading="## 핵심 지표 표")


def _data_collection_table(context: dict) -> str:
    dq = context.get("data_quality", {})
    rows = [
        ("fast", f"{dq.get('fast_actual_count')}/{dq.get('fast_expected_count')}", _percent(dq.get("fast_collection_rate")), _collection_judgement(dq.get("fast_collection_rate"))),
        ("slow", f"{dq.get('slow_actual_count')}/{dq.get('slow_expected_count')}", _percent(dq.get("slow_collection_rate")), _collection_judgement(dq.get("slow_collection_rate"))),
        ("최대 결측 구간", _gap_range(dq), f"{_fmt(dq.get('max_gap_minutes'))}분", _count_judgement(dq.get("max_gap_minutes"), "결측 확인 필요", "긴 결측 없음")),
        ("마지막 관측 hour", dq.get("latest_observed_hour") or "-", f"뒤쪽 empty {dq.get('empty_tail_hour_count', 0)}h", "partial-day/미수집 구분"),
        ("invalid/duplicate", f"{dq.get('invalid_record_count')}/{dq.get('duplicate_record_count')}", "-", "입력 품질 확인"),
    ]
    return _table(("데이터", "수집량/구간", "수집률/시간", "판단"), rows, align=(None, "right", "right", None))


def _backend_runtime_table(context: dict) -> str:
    item = context.get("backend_runtime", {})
    rows = [
        ("ECS desired", _fmt(item.get("ecs_desired_count")), "목표 task 수"),
        ("ECS running min/max", f"{_fmt(item.get('ecs_running_count_min'))}/{_fmt(item.get('ecs_running_count_max'))}", "실행 task 범위"),
        ("ECS pending max", _fmt(item.get("ecs_pending_count_max")), "배치 지연 확인"),
        ("ECS CPU avg/max", f"{_fmt(item.get('ecs_cpu_avg'))}/{_fmt(item.get('ecs_cpu_max'))}", "runtime 부하"),
        ("ECS memory avg/max", f"{_fmt(item.get('ecs_memory_avg'))}/{_fmt(item.get('ecs_memory_max'))}", "memory 부하"),
        ("ALB healthy/unhealthy", f"{_fmt(item.get('alb_healthy_host_min'))}/{_fmt(item.get('alb_unhealthy_host_max'))}", "target 상태"),
        ("ALB 5xx total", _fmt(item.get("alb_5xx_total")), "서버 오류"),
    ]
    return _table(("항목", "값", "판단"), rows, align=(None, "right", None))


def _data_pipeline_table(context: dict) -> str:
    item = context.get("data_pipeline", {})
    rows = [
        ("Lambda error/throttle", f"{_fmt(item.get('lambda_error_total'))}/{_fmt(item.get('lambda_throttle_total'))}", "Lambda 실행 품질"),
        ("Lambda duration p95 max", _fmt(item.get("lambda_duration_p95_max")), "지연 확인"),
        ("DynamoDB read/write throttle", f"{_fmt(item.get('dynamodb_read_throttle_total'))}/{_fmt(item.get('dynamodb_write_throttle_total'))}", "처리량 제한"),
        ("DynamoDB system error", _fmt(item.get("dynamodb_system_error_total")), "DynamoDB 오류"),
        ("Disabled scheduler", _fmt(item.get("disabled_scheduler_count")), "스케줄 상태"),
    ]
    return _table(("항목", "값", "판단"), rows, align=(None, "right", None))


def _eks_management_table(context: dict) -> str:
    item = context.get("eks_management", {})
    rows = [
        ("Cluster status", item.get("cluster_status") or "-", "ACTIVE 여부"),
        ("Nodes ready/total", f"{_fmt(item.get('nodes_ready_min'))}/{_fmt(item.get('nodes_total_max'))}", "노드 상태"),
        ("Not-ready node minutes", _fmt(item.get("not_ready_node_minutes")), "누적 영향"),
        ("Pod pending/failed/unknown", f"{_fmt(item.get('pod_pending_max'))}/{_fmt(item.get('pod_failed_max'))}/{_fmt(item.get('pod_unknown_max'))}", "Pod 상태"),
        ("Restart delta", _fmt(item.get("restart_count_delta")), "재시작 증가"),
    ]
    tables = [_table(("항목", "값", "판단"), rows, align=(None, "right", None))]
    if item.get("top_cpu_pods"):
        tables.append(_pods_table("CPU 사용 상위 Pod", item.get("top_cpu_pods", []), "cpu_millicores"))
    if item.get("top_memory_pods"):
        tables.append(_pods_table("Memory 사용 상위 Pod", item.get("top_memory_pods", []), "memory_mib"))
    return "\n\n".join(tables)


def _argocd_table(context: dict) -> str:
    item = context.get("argocd", {})
    rows = [
        ("Applications total", _fmt(item.get("applications_total_max")), "대상 앱 수"),
        ("Synced min", _fmt(item.get("synced_min")), "동기화 앱 최솟값"),
        ("OutOfSync max", _fmt(item.get("out_of_sync_max")), "불일치 앱"),
        ("Degraded max", _fmt(item.get("degraded_max")), "저하 앱"),
        ("Healthy min", _fmt(item.get("healthy_min")), "정상 앱 최솟값"),
    ]
    return _table(("항목", "값", "판단"), rows, align=(None, "right", None))


def _freshness_table(context: dict) -> str:
    item = context.get("freshness", {})
    rows = [
        ("Factory warning/critical minutes", f"{_fmt(item.get('factory_pipeline_warning_minutes'))}/{_fmt(item.get('factory_pipeline_critical_minutes'))}", "factory freshness"),
        ("Stale factory count max", _fmt(item.get("stale_factory_count_max")), "factory stale"),
        ("Storage non-normal count", _fmt(item.get("storage_freshness_non_normal_count")), "storage freshness"),
    ]
    return _table(("항목", "값", "판단"), rows, align=(None, "right", None))


def _events_table(context: dict) -> str:
    events = context.get("events", [])[:10]
    if not events:
        return _table(("시간", "유형", "심각도", "지속", "근거"), [("-", "주요 이벤트 없음", "-", "-", "-")])
    rows = [
        (
            event.get("time_range") or "-",
            _event_type_label(event.get("type")),
            _fmt(event.get("severity_score")),
            _duration(event.get("duration_seconds")),
            _event_evidence(event),
        )
        for event in events
    ]
    return _table(("시간", "유형", "심각도", "지속", "근거"), rows, align=(None, None, "right", "right", None))


def _checks_table(context: dict) -> str:
    checks = context.get("recommended_checks", [])[:10]
    if not checks:
        return _table(("우선순위", "항목", "이유", "구간"), [("-", "권장 확인 항목 없음", "-", "-")])
    rows = [(_priority_label(check.get("priority")), _check_item_label(check.get("item")), check.get("reason") or "-", check.get("time_range") or "-") for check in checks]
    return _table(("우선순위", "항목", "이유", "구간"), rows)


def _pods_table(title: str, pods: list[dict], value_key: str) -> str:
    rows = []
    for pod in pods[:5]:
        rows.append((
            title,
            f"{pod.get('namespace', '-')}/{pod.get('pod', '-')}",
            _fmt(pod.get(value_key)),
        ))
    return _table(("구분", "Pod", "값"), rows, align=(None, None, "right"))


def _insert_table_after_heading(markdown: str, heading: str, table: str) -> str:
    if not table or table in markdown:
        return markdown
    pattern = re.compile(rf"(?m)^({re.escape(heading.strip())})[ \t]*\r?\n")
    match = pattern.search(markdown)
    if not match:
        return markdown
    return f"{markdown[:match.start()]}{match.group(1)}\n\n{table}\n\n{markdown[match.end():]}"


def _append_verification_metrics(markdown: str, context: dict) -> str:
    dq = context.get("data_quality", {})
    backend = context.get("backend_runtime", {})
    eks = context.get("eks_management", {})
    argo = context.get("argocd", {})
    lines = [
        "",
        "## 검증 기준 수치",
        "",
        "- 이 섹션은 보고서 검증을 위해 context 원문 수치를 그대로 남긴다.",
        f"- target_id={context.get('target_id')}, report_date={context.get('report_date')}, overall_status={context.get('overall_status')}",
        f"- fast 수집 원문: {dq.get('fast_actual_count')}/{dq.get('fast_expected_count')}, collection_rate {dq.get('fast_collection_rate')}",
        f"- slow 수집 원문: {dq.get('slow_actual_count')}/{dq.get('slow_expected_count')}, collection_rate {dq.get('slow_collection_rate')}",
        f"- cloud_infra 관측 원문: latest_observed_hour={dq.get('latest_observed_hour')}, empty_tail_hour_count={dq.get('empty_tail_hour_count')}",
        f"- ECS 원문: running_min={backend.get('ecs_running_count_min')}, desired={backend.get('ecs_desired_count')}",
        f"- EKS node 원문: ready_min={eks.get('nodes_ready_min')}, total_max={eks.get('nodes_total_max')}",
        f"- ArgoCD 원문: synced_min={argo.get('synced_min')}, total_max={argo.get('applications_total_max')}",
    ]
    return markdown.rstrip() + "\n" + "\n".join(lines) + "\n"


def _table(headers: tuple[str, ...], rows: list[tuple], align: tuple[str | None, ...] | None = None, heading: str | None = None) -> str:
    align = align or tuple(None for _ in headers)
    lines = []
    if heading:
        lines.extend([heading, ""])
    lines.extend([
        "| " + " | ".join(_esc(header) for header in headers) + " |",
        "| " + " | ".join("---:" if item == "right" else "---" for item in align) + " |",
    ])
    lines.extend("| " + " | ".join(_esc(value) for value in row) + " |" for row in rows)
    return "\n".join(lines)


def _collection_value(dq: dict, stream: str) -> str:
    return f"{dq.get(f'{stream}_actual_count')}/{dq.get(f'{stream}_expected_count')}, {_percent(dq.get(f'{stream}_collection_rate'))}"


def _collection_judgement(rate) -> str:
    if rate is None:
        return "확인 필요"
    if rate >= 0.99:
        return "양호"
    if rate >= 0.95:
        return "일부 결측"
    return "결측 영향 확인 필요"


def _overall_judgement(status) -> str:
    if str(status).lower() == "danger":
        return "즉시 확인 필요"
    if str(status).lower() == "warning":
        return "주의 항목 확인 필요"
    return "특이 이벤트 없음"


def _event_type_label(value) -> str:
    labels = {
        "cloud_overall_status_non_normal": "Cloud 전체 상태 비정상",
        "cloud_fast_collection_gap": "fast 수집 공백",
        "cloud_slow_collection_gap": "slow 수집 공백",
        "backend_ecs_capacity_mismatch": "ECS desired/running 불일치",
        "backend_alb_unhealthy": "ALB 비정상 target",
        "backend_alb_5xx": "ALB 5xx",
        "pipeline_lambda_error": "Lambda 오류",
        "pipeline_lambda_throttle": "Lambda throttle",
        "dynamodb_throttle_or_error": "DynamoDB throttle/error",
        "scheduler_disabled": "Scheduler 비활성",
        "eks_cluster_non_active": "EKS cluster 비정상",
        "eks_node_not_ready": "EKS node 준비 안됨",
        "eks_pod_unhealthy": "EKS pod 비정상",
        "eks_pod_restart_increase": "Pod 재시작 증가",
        "argocd_out_of_sync": "ArgoCD 동기화 불일치",
        "argocd_degraded": "ArgoCD degraded",
        "factory_freshness_stale": "Factory freshness stale",
        "storage_freshness_stale": "Storage freshness stale",
    }
    return labels.get(value, str(value or "-"))


def _check_item_label(value) -> str:
    labels = {
        "Cloud infra fast collection gap review": "fast 수집 공백 확인",
        "Cloud infra slow collection gap review": "slow 수집 공백 확인",
        "Backend ECS desired/running capacity review": "ECS desired/running 확인",
        "Backend ALB target health review": "ALB target health 확인",
        "Backend ALB 5xx request trace review": "ALB 5xx 요청 추적",
        "Data Pipeline Lambda error log review": "Lambda 오류 로그 확인",
        "Data Pipeline Lambda throttle review": "Lambda throttle 확인",
        "DynamoDB throttle and system error review": "DynamoDB throttle/error 확인",
        "EventBridge Scheduler state review": "Scheduler 상태 확인",
        "EKS cluster status review": "EKS cluster 상태 확인",
        "EKS node readiness review": "EKS node readiness 확인",
        "EKS pod health review": "EKS pod health 확인",
        "EKS pod restart review": "EKS pod 재시작 확인",
        "ArgoCD sync status review": "ArgoCD sync 상태 확인",
        "ArgoCD degraded application review": "ArgoCD degraded 앱 확인",
        "Factory freshness stale pipeline review": "Factory freshness 지연 확인",
        "Storage freshness stale data review": "Storage freshness 지연 확인",
    }
    return labels.get(value, str(value or "-"))


def _priority_label(value) -> str:
    labels = {"high": "높음", "medium": "중간", "low": "낮음"}
    return labels.get(value, str(value or "-"))


def _event_evidence(event: dict) -> str:
    evidence = event.get("evidence") or {}
    if evidence.get("stream"):
        return f"stream={evidence.get('stream')}"
    if evidence.get("hour"):
        hour = evidence.get("hour", {})
        return hour.get("start_utc") or hour.get("start_kst") or "-"
    return "-"


def _count_judgement(count, positive_text: str, zero_text: str = "발생 없음") -> str:
    return positive_text if count is not None and count > 0 else zero_text


def _gap_range(dq: dict) -> str:
    return ((dq.get("gap_windows") or [{}])[0]).get("time_range") or "-"


def _duration(value) -> str:
    if value is None:
        return "-"
    return f"{_fmt(value / 60)}분" if value >= 60 else f"{_fmt(value)}초"


def _percent(value) -> str:
    return "-" if value is None else f"{value * 100:.2f}%"


def _fmt(value) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return str(int(value)) if value.is_integer() else f"{value:.2f}".rstrip("0").rstrip(".")
    return str(value)


def _esc(value) -> str:
    if value is None:
        return "-"
    return str(value).replace("\n", " ").replace("|", "\\|")
