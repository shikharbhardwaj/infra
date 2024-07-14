# Coder-v2

## Installation process

1. Add repo

```
helm repo add coder-v2 https://helm.coder.com/v2
```

2. Install the chart

```
helm upgrade --install coder-v2 coder-v2/coder --version 2.13.0 --namespace coder-v2 --create-namespace -f out/dst.yml
```