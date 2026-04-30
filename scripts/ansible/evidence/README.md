# Ansible Evidence

이 디렉터리는 Ansible 테스트 자동화 실행 결과를 Markdown evidence로 저장하는 로컬 산출물 공간이다.

## 파일

| 파일 | 내용 |
| --- | --- |
| `.gitignore` | evidence 산출물이 Git에 올라가지 않도록 관리 |
| `start_test_*.md` | `02_start_test.yml` 실행 시 생성되는 상태 점검 결과 |

## 기준

- 이 디렉터리의 실행 산출물은 로컬 보관용이다.
- SSH 비밀번호, sudo 비밀번호, token, credential은 evidence에 기록하지 않는다.
- 필요한 경우 결과 요약만 운영 문서나 보고서에 옮긴다.
