# Safe-Edge Ansible Checks

Factory-A Safe-Edge 반복 점검용 Ansible 파일이다.

## start_test 실행

비밀번호는 inventory나 파일에 저장하지 않고 실행 시 입력한다.

```bash
cd scripts/ansible
ansible-playbook playbooks/02_start_test.yml
```

`02_start_test.yml`은 `master`에만 SSH 접속하고, worker 상태는 `master`의 `kubectl` 결과로 확인한다. 따라서 현재 start_test 실행 때는 아래 프롬프트 하나만 입력한다.

```text
master SSH/sudo password:
```

성공하면 `scripts/ansible/evidence/` 아래에 Markdown evidence 파일이 생성된다.

Factory-A IP, LoadBalancer IP, 워크로드 노드명은 `inventory/group_vars/factory_a.yml`에서 관리한다. 다른 현장이나 IP 대역으로 바꿀 때는 이 파일을 먼저 수정한다.

주요 변수:

```yaml
factory_a_nodes:
  master:
    ip: 10.10.10.10
  worker1:
    ip: 10.10.10.11
  worker2:
    ip: 10.10.10.12

factory_a_services:
  longhorn_frontend:
    ip: 10.10.10.201
```

비밀번호 SSH를 쓰는 경우 control host에 `sshpass`가 필요하다.

```bash
sudo apt-get install -y sshpass
```

SSH key 인증을 설정했다면 `-k`는 빼고 실행한다.

node별 비밀번호 매핑은 `inventory/group_vars/factory_a.yml`의 `password_var`로 관리한다. worker에 직접 접속하는 playbook을 추가할 때는 같은 방식으로 `factory_a_worker1_password`, `factory_a_worker2_password`를 `vars_prompt`에 추가한다.

## 범위

이 playbook은 `safe-edge/start_test.md`의 시작 점검 명령을 `master`에서 실행하고 주요 기대값을 검증한다.

자동화 대상:

- Kubernetes node, service, pod 상태 확인
- MetalLB, Longhorn, Argo CD, Monitoring, AI Apps 상태 확인
- failback cron 로그 확인
- 로컬 evidence Markdown 생성

자동화하지 않는 대상:

- worker2 LAN 제거
- worker2 전원 차단
- 장애 주입 후 최종 성공/실패 해석
