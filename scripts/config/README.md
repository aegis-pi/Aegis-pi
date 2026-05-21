# scripts/config

상태: source of truth
기준일: 2026-05-21

## 목적

빌드/운영 스크립트의 공통 기본값을 관리하는 설정 파일 디렉터리다.

## 파일

| 파일 | 역할 |
| --- | --- |
| `defaults.sh` | 스크립트 공통 기본값. `AEGIS_REGION`, `AEGIS_CLUSTER_NAME`, 네이밍 접두사 등 정적 파라미터를 정의한다 |

## 사용법

`scripts/lib/config.sh`에서 자동으로 source한다. 직접 수정하면 모든 build/destroy 스크립트에 영향을 준다.

민감 정보(AWS 계정 ID, 비밀번호, 토큰)는 이 파일에 저장하지 않는다.
