from enum import unique
from kafka import KafkaConsumer, KafkaProducer
import json
import time
from db.powerpostgre import PowerPost
import configargparse
import numpy as np
import faiss as fs
import sys
from logbook import Logger, NestedSetup, NullHandler, FileHandler, MailHandler, Processor, StreamHandler
import logbook
import os
import base64
import cv2
from datetime import datetime
import requests
import threading

class clientThread(threading.Thread):
    def __init__(self, func, args):
        threading.Thread.__init__(self)
        self.func = func
        self.args = args

    def run(self):
        self.func(*self.args)


def get_logger(camera, debug=True):
    logbook.set_datetime_format('local')
    handler = StreamHandler(sys.stdout) if debug else FileHandler('/app/insert_to_db/logs/'+camera+'.log', level='WARNING')
    handler.push_application()
    return Logger(os.path.basename(camera))


def preprocessing(metadatas):
    original_image_id = metadatas['unique_id']
    embeddings_list = metadatas['embeddings']
    faces_list = metadatas['num_faces']
    camera_id = metadatas['camera_id']

    return original_image_id, embeddings_list, faces_list, camera_id


def defaultconverter(dtstr):
    if isinstance(dtstr, datetime):
        return dtstr.__str__()


def send_to_front(producer_data):
    headers = {'User-Agent': 'Mozilla/5.0'}
    to_azat = requests.post('http://10.150.34.13:10100/api/detect-faces-live-ready', headers=headers, data={'data': json.dumps(producer_data, default = defaultconverter)})
    from_azat = json.loads(to_azat.text)
    print(from_azat)


def insertion():
    FLAGS = None
    parser = configargparse.ArgParser() #(default_config_files=[conf_file])
    parser.add('-c', '--my-config', required=False, is_config_file=True, help='config file path')
    #parser = configargparse.ArgParser(default_config_files=[conf_file])
    parser.add('--psql_server', type=str, required=False, help='Postgres server URL.')
    parser.add('--psql_server_port', type=int, required=False, help='Postgres server port.')
    parser.add('--psql_db', type=str, required=False, help='Postgres database.')
    parser.add('--psql_user', type=str, required=False, help='Postgres user.')
    parser.add('--psql_user_pass', type=str, required=False, help='Postgres password.')

    parser.add('--kafka_topic', type=str, required=False, help='Kafka topic.')
    parser.add('--kafka_server', type=str, required=False, help='Kafka server URL.')
    parser.add('--auto_offset_reset', type=str, required=False, help='Auto offset reset.')
    parser.add('--enable_auto_commit', type=bool, required=False, help='Enable auto commit.')
    parser.add('--group_id', type=str, required=False, help='Grup id.')

    parser.add('--threshold', type=int, required=False, help='Threshold.')
    parser.add('--crops_folder', type=str, required=False, help='Path to crops folder.')

    FLAGS = parser.parse_args()

    pgconnectionString = [FLAGS.psql_server, FLAGS.psql_server_port, FLAGS.psql_db, FLAGS.psql_user, FLAGS.psql_user_pass]
    powerPostgre = PowerPost(pgconnectionString[0], pgconnectionString[1], pgconnectionString[2], pgconnectionString[3], pgconnectionString[4])

    faiss_index = fs.read_index('/final_index/populated.index', fs.IO_FLAG_ONDISK_SAME_DIR)

    threshold = FLAGS.threshold

    log = get_logger('cameras')    

    while True:
        try:
            consumer = KafkaConsumer(
                FLAGS.kafka_topic,
                bootstrap_servers=[FLAGS.kafka_server],
                auto_offset_reset=FLAGS.auto_offset_reset,
                enable_auto_commit=FLAGS.enable_auto_commit,
                group_id=FLAGS.group_id,
                value_deserializer=lambda x: json.loads(x.decode('utf-8'))
            )
            break
        except Exception as e:
            log_message = {'status':'error', 'message': 'Could not connect to kafka Consumer', 'name': FLAGS.kafka_topic}
            log.debug(log_message)
            print (e)    

    for event in consumer:
        start = time.time()
        original_image_id, embeddings_list, faces_list, camera_id = preprocessing(event.value)
        # red_id, similarity = powerPostgre.search_from_blacklist(vector, 60)
        face_cnt = 0
        for embedding in embeddings_list:
            distances, indexes = powerPostgre.search_from_gbdfl_faiss(faiss_index, embedding, 1, threshold)
            # print('Distances, indexes:', distances, indexes)
            if indexes is not None and distances[0][0] > float(threshold)/100:
                # print("FIRST PRINT FROM insert to db:", distances, indexes)
                ids = tuple(list(map(str,indexes[0])))
                similarity = float(distances[0])
                with_zeros = []
                str_ids = list(map(str, indexes[0]))
                for i in str_ids:
                    while len(i) < 9:
                        i = "0" + i
                    with_zeros.append(i)
                from_gbdfl = powerPostgre.get_info_from_unique_ud_gr(tuple(with_zeros))
                # from_gbdfl = powerPostgre.get_blob_from_ud_gr(ud_code)
                result_dict = {}

                if len(from_gbdfl) > 0:                    
                    image_path = os.path.join(FLAGS.crops_folder, original_image_id + '_' + str(face_cnt) + '.jpg')
                    img = cv2.imread(image_path)

                    result_dict['similarity'] = int(round(similarity*100, 2))  # format(from_gbdfl['lst'][1], '.2f')
                    result_dict['iin'] = from_gbdfl[0]
                    result_dict['surname'] = from_gbdfl[1]
                    result_dict['firstname'] = from_gbdfl[2]
                    if from_gbdfl[3] is None:
                        result_dict['secondname'] = ''
                    else:
                        result_dict['secondname'] = from_gbdfl[3]
                    
                    result_dict['ud_number'] = from_gbdfl[4]
                    crop_time = datetime.now()
                    result_dict['timestamp'] = crop_time
                    print(result_dict)
                    strimg = base64.b64encode(cv2.imencode('.jpg', img)[1]).decode()
                    producer_data = {'app': 'detection',
                                    'command': 'new_face_detected',
                                    'crop': strimg,
                                    'meta': result_dict,
                                    'source': camera_id,
                                    'timestamp_sent': datetime.now().strftime("%d-%m-%Y, %H:%M:%S")
                                    }
                    # headers = {'User-Agent': 'Mozilla/5.0'}
                    # to_azat = requests.post('http://10.150.34.13:10100/api/detect-faces-live-ready', headers=headers, data={'data': json.dumps(producer_data, default = defaultconverter)})
                    # from_azat = json.loads(to_azat.text)
                    # print(from_azat)
                    thread = clientThread(send_to_front, [producer_data])
                    thread.start()
                    thread.join()
                else:
                    print('Not in database')
                    continue
                log_message = {'rtsp': camera_id, 'message': 'Successfully sent', 'table_name': 'fr.unique_ud_gr', 'ud_code': with_zeros, 'time_spent': time.time() - start}
                log.debug(log_message)
            else:
                print('Not PASSED THRESHOLD', distances, indexes, 'TIME SPENT:', time.time() - start)
                log_message = {'rtsp': camera_id, 'message': 'Person Not in Database', 'table_name': 'fr.unique_ud_gr', 'ud_code': None}
                log.debug(log_message)


if __name__ == "__main__":
    insertion()
