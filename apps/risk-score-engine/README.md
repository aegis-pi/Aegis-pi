# Risk Score Engine

이 디렉터리는 공장별 Risk Score와 상태를 계산하고 관제 화면용 출력을 만드는 서비스 코드를 둔다.

Risk 결과는 Dashboard VPC의 Web/API가 조회할 수 있도록 latest status store에 반영한다. 필요하면 AMP/Grafana용 Prometheus-compatible metric도 함께 노출한다.
