# Ansible Group Vars

이 디렉터리는 Ansible inventory group에 적용할 변수 파일을 둔다.

## 파일

| 파일 | 내용 |
| --- | --- |
| `factory_a.yml` | `factory-a` 노드 IP, 서비스 IP, workload 이름, Ansible 접속 변수 |

## 기준

- 비밀번호 값은 이 파일에 직접 적지 않는다.
- `password_var` 이름만 정의하고 실제 값은 playbook prompt로 받는다.
- 운영 주소가 바뀌면 이 파일을 먼저 갱신한다.
