import os
from pathlib import Path

#os.environ['WEB_SRC_ROOT']

psql_server = os.environ['ITD_PGSERVER_IP']           #Postgres server
psql_server_port = os.environ['ITD_PGSERVER_PORT']    #Postgres server port
psql_db = os.environ['ITD_PG_DB']                     #Postgres database
psql_user = os.environ['ITD_PG_DB_USER']              #Postgres user
psql_user_pass = os.environ['ITD_PG_DB_PASS']         #Postgres password

#kafka settings
kafka_topic = os.environ['ITD_KAFKA_TOPIC']                                  #Kafka topic
kafka_server = os.environ['ITD_KAFKA_SERVER']                                #Kafka server
kafka_server_port = os.environ['ITD_KAFKA_SERVER_PORT']                      #Kafka server port
auto_offset_reset = os.environ['ITD_KAFKA_OFFSET']                           #Kafka offset policy. Consumption starts either at the earliest offset or the latest offset
enable_auto_commit = os.environ['ITD_KAFKA_AUTOCOMMIT']                      #As the consumer reads messages from Kafka, it will periodically commit its current offset
group_id = os.environ['ITD_KAFKA_GROUP']                                     #Kafka group
front_kafka_server = os.environ['ITD_KAFKA_FRONT_SERVER']                    #Frontend kafka server
front_kafka_server_port = os.environ['ITD_KAFKA_FRONT_SERVER_PORT']          #Frontend kafka server port
kafka_producer_front_topic = os.environ['ITD_KAFKA_FRONT_SERVER_TOPIC']      #Frontend kafka producer topic to send info to

faiss_index = os.environ['ITD_FAISS_INDEX_FILE']


PSQL_SERVER_SETTINGS = [psql_server, psql_server_port, psql_db, psql_user, psql_user_pass]
KAFKA_SETTINGS = [kafka_topic, kafka_server + ':' + kafka_server_port, auto_offset_reset, enable_auto_commit, group_id]
FRONT_KAFKA_SETTINGS = [front_kafka_server + ':' + front_kafka_server_port, kafka_producer_front_topic]


