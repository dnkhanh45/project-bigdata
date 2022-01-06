FROM bde2020/spark-master:3.1.1-hadoop3.2

ENV SPARK_HOME=/spark
# ENV HADOOP_HOME=/hadoop
# ENV LD_LIBRARY_PATH=:/usr/lib64:/usr/lib:/${HADOOP_HOME}/lib/native
ENV PYTHONUNBUFFERED=1

RUN apk add build-base \
      && apk add --update --no-cache python3 && ln -sf python3 /usr/bin/python \
      && apk add python3-dev \
      && apk add libffi-dev \
      && python3 -m ensurepip \
      && pip3 install --no-cache --upgrade pip setuptools \
      && pip3 install notebook \
      && pip3 install jupyter_http_over_ws \
      && jupyter serverextension enable --py jupyter_http_over_ws \
      && pip3 install findspark \
      && pip3 install requests \
      && pip3 install hdfs \
      && pip3 install elasticsearch \
      && pip3 install numpy \
      # && apk add openjdk11 \
      # && wget https://archive.apache.org/dist/hadoop/common/hadoop-3.2.2/hadoop-3.2.2.tar.gz \
      # && tar -xvzf hadoop-3.2.2.tar.gz \
      # && mv hadoop-3.2.2 hadoop \
      # && rm hadoop-3.2.2.tar.gz \
      && cp ${SPARK_HOME}/conf/log4j.properties.template ${SPARK_HOME}/conf/log4j.properties \
      && mkdir /content \
      && cd /

# COPY ./log4j.properties ${SPARK_HOME}/conf
