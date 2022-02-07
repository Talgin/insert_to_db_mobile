from kafka import KafkaConsumer, KafkaProducer
import json
from time import sleep
from db.powerpostgre import PowerPost
import configargparse
import numpy as np
import faiss as fs
import sys
from logbook import Logger, NestedSetup, NullHandler, FileHandler, MailHandler, Processor, StreamHandler
import logbook
import os


def get_logger(camera, debug=True):
    logbook.set_datetime_format('local')
    handler = StreamHandler(sys.stdout) if debug else FileHandler('logs/'+camera+'.log', level='WARNING')
    handler.push_application()
    return Logger(os.path.basename(camera))


def preprocessing(metadatas):
    # original_id = metadatas['original_id']
    face_id = metadatas['face_id']
    rect_x = metadatas['rect_x']
    rect_y = metadatas['rect_y']
    width_x = metadatas['width_x']
    height_y = metadatas['height_y']
    camera_id = metadatas['camera_id']
    server_id = metadatas['server_id']
    crop_id = metadatas['crop_id']
    crop_time = metadatas['timestamp']
    vector = np.array(metadatas['vector'])
    vector_json = metadatas['vector']
    date_folder = metadatas['date_folder']
    proj_code = metadatas['proj_code']
    # crop_path = metadatas['crop_path']
    # original_path = metadatas['original_path']

    # In case red_id is found in blacklist index, then we have to add this line also
    # red_id = metadatas['red_id']

    return face_id, rect_x, rect_y, width_x, height_y, camera_id, server_id, crop_id, crop_time, vector, vector_json, date_folder, proj_code


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

    parser.add('--front_kafka_server', type=str, required=False, help='Kafka server URL.')
    parser.add('--kafka_producer_front_topic', type=str, required=False, help='Name of kafka topic')

    parser.add('--threshold', type=int, required=False, help='threshold.')

    # NEW OBJECTS
    # parser.add('--crops_folder_path', type=str, required=True, help='Path to folder where crops are saved' )
    # parser.add('--frames_folder_path', type=str, required=True, help='Path to folder where original frames are saved' )

    FLAGS = parser.parse_args()

    # setup = NestedSetup([
    # # make sure we never bubble up to the stderr handler
    # # if we run out of setup handling
    # NullHandler(),
    # # then write messages that are at least warnings to a logfile
    # FileHandler('logs/cameras.log', level='WARNING'),
    # StreamHandler(sys.stdout).push_application()
    # # errors should then be delivered by mail and also be kept
    # # in the application log, so we let them bubble up.
    # #MailHandler('servererrors@example.com',
    # #               ['admin@example.com'],
    # #               level='ERROR', bubble=True),
    # # while we're at it we can push a processor on its own stack to
    # # record additional information.  Because processors and handlers
    # # go to different stacks it does not matter if the processor is
    # # added here at the bottom or at the very beginning.  Same would
    # # be true for flags.
    # # Processor(inject_information)
    # ])

    pgconnectionString = [FLAGS.psql_server, FLAGS.psql_server_port, FLAGS.psql_db, FLAGS.psql_user, FLAGS.psql_user_pass]
    powerPostgre = PowerPost(pgconnectionString[0], pgconnectionString[1], pgconnectionString[2], pgconnectionString[3], pgconnectionString[4])
    # l = logbook.Logger()
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
            log_message = {'status':'error', 'rtsp': camera_id, 'message': 'Could not connect to kafka Consumer', 'name': 'crops_queue'}
            log.debug(log_message)
            print (e)
    print('Consumer can be accessed')
    # Create a producer in here
    while True:
        try:
            producer = KafkaProducer(
                bootstrap_servers=[FLAGS.front_kafka_server],
                #value_serializer=lambda x: json.dumps(x).encode('utf-8')
            )
            break
        except Exception as e:
            log_message = {'status':'error', 'rtsp': camera_id, 'message': 'Could not connect to kafka Producer', 'name': 'stream_faces'}
            log.debug(log_message)
            print(e)

    for event in consumer:
        #  unique_id, rect_x, rect_y, width_x, height_y, camera_id, server_id, face_id, crop_time, vector
        # print(event.value)
        # print('FINAL_INDEX:', os.listdir('/final_index'))
        print('Number of people in faiss:', faiss_index.ntotal)
        face_id, rect_x, rect_y, width_x, height_y, camera_id, server_id, crop_id, crop_time, vector, vector_json, date_folder, proj_code = preprocessing(event.value)
        # red_id, similarity = powerPostgre.search_from_blacklist(vector, 60)
        distances, indexes = powerPostgre.search_from_gbdfl_faiss(faiss_index, vector, 1, threshold)
        # print('Distances, indexes:', distances, indexes)
        if indexes is not None:
            # print("FIRST PRINT FROM insert to db:", distances, indexes)
            ud_code = str(indexes[0])
            similarity = distances[0]
            while len(ud_code) < 9:
                ud_code = '0' + ud_code
            # try:
            # iin = powerPostgre.get_iin_from_unique_ud_gr(ud_code)
            # print('UD_CODE:', ud_code)
            info = powerPostgre.get_info_from_unique_ud_gr(ud_code)
            # print('INFO from DB:', info)
            to_kpp_kafka = None
            if len(info) > 0:
                iin = info[0]
                last_name = info[1]
                first_name = info[2]
                second_name = info[3]
                # cv2.imwrite(path_to_crop +'_'+ unique_id +'_'+str(face_id)+'.jpg', crop, [cv2.IMWRITE_JPEG_QUALITY, 80])
                # cv2.imwrite(path_to_frames +'_'+ unique_id + '.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 50])
                # TEST VALS
                # to_kpp_kafka = {'iin': str(iin), 'title': 'test', 'message': 'SOME INFO.'}
                # TEST VALS

                # PROD VALS
                to_kpp_kafka = {
                    'crop_id': crop_id, # not null
                    'face_id': face_id, # not null
                    'timestamp': crop_time, # not null
                    'camera_code': camera_id, # not null
                    #'crop_link': crop_path,
                    #'original_link': original_path,
                    'vector': vector_json,
                    'iin': iin,
                    'ud_code': ud_code,
                    'first_name': first_name,
                    'last_name': last_name,
                    'middle_name': second_name,
                    'similarity': int(round(similarity*100, 2)),
                    'date_folder': date_folder, 
                    'proj_code': proj_code

                }
                # PROD VALS
            else:
                iin = 'NULL'
                last_name = 'NULL'
                first_name = 'NULL'
                second_name = 'NULL'
                # TEST VALS
                # to_kpp_kafka = {'title': 'test', 'message': 'NO INFO. Dummy test'}
                # TEST VALS

                # PROD VALS
                to_kpp_kafka = {
                    'crop_id': crop_id, # not null
                    'face_id': face_id,
                    # 'original_id': original_id, # not null
                    'timestamp': crop_time, # not null
                    'camera_code': camera_id, # not null
                    #'crop_link': crop_path,
                    #'original_link': original_path,
                    'vector': vector_json,
                    'iin': iin,
                    'ud_code': ud_code,
                    'first_name': first_name,
                    'last_name': last_name,
                    'middle_name': second_name,
                    'similarity': None,
                    'date_folder': date_folder, 
                    'proj_code': proj_code
                }
                # PROD VALS
            txt = json.dumps(to_kpp_kafka).encode('utf-8')
            #print('TO_KAFKA:', txt)

            try:
                future = producer.send(FLAGS.kafka_producer_front_topic, value = txt)
                producer.flush()
            except errors.MessageSizeTooLargeError:
                print('Message is too large. max_request_size')
            except errors.KafkaError as err:
                print('Kafka error {}'.format(err))
            log_message = {'rtsp': camera_id, 'message': 'Successfully sent', 'table_name': 'fr.unique_ud_gr', 'ud_code': ud_code}
            log.debug(log_message)
            # except Exception as ex:
            #     log_message = {'rtsp': camera_id, 'server': server_id, 'table_name': 'fr.unique_ud_gr', 'exception': ex}
            #     log.debug(log_message)
            # try:
            #     cropInsert = powerPostgre.insert_into_croplist(unique_id, ud_code, face_id, crop_time, camera_id, rect_x, rect_y, height_y, similarity, width_x, iin)
            # except Exception as ex:
            #     log_message = {'rtsp': camera_id, 'server': server_id, 'table_name': 'fr.application_croplist', 'exception': ex.__class__}
            #     log.debug(log_message)
        else:
            print('Not in database')
            log_message = {'rtsp': camera_id, 'message': 'Successfully sent', 'table_name': 'fr.unique_ud_gr', 'ud_code': None}
            log.debug(log_message)
        # try:
        #     # vectorArchive = powerPostgre.insert_into_vectors_archive(unique_id, vector, camera_id, server_id)
        # except Exception as ex:
        #     log_message = {'server': server_id, 'table_name': 'fr.vectors_archive', 'exception': ex.__class__}
        #     log.debug(log_message)
        #producer.send(FLAGS.kafka_producer_topic, value = dct)
        # print(unique_id, ud_code, rect_x, rect_y, width_x, height_y, camera_id, server_id, face_id, crop_time, similarity, iin)


if __name__ == "__main__":
    insertion()
