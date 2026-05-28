moved {
  from = aws_eip.nat["Azone"]
  to   = aws_eip.nat
}

moved {
  from = aws_nat_gateway.public["Azone"]
  to   = aws_nat_gateway.public
}
