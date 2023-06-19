FROM ghcr.io/mlflow/mlflow:v2.4.1

RUN groupadd -g 1000 kubeuser && useradd -r -u 1000 -g kubeuser --home '/home/kubeuser' kubeuser 
RUN mkdir /home/kubeuser && chmod 755 /home/kubeuser && chown kubeuser:kubeuser /home/kubeuser/

RUN apt-get update && apt-get install -y build-essential
RUN pip install psycopg2-binary boto3

USER 1000