moved {
  from = aws_eip.nat["Azone"]
  to   = aws_eip.nat
}

moved {
  from = aws_nat_gateway.public["Azone"]
  to   = aws_nat_gateway.public
}

moved {
  from = aws_eks_addon.metrics_server
  to   = aws_eks_addon.metrics_server[0]
}
