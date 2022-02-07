import psycopg2
from sqlalchemy import create_engine
import pandas as pd
import numpy as np
from shutil import copyfile


class PowerPost:
    def __init__(self, host, port, dbname, user, pwd):
        self.host = host
        self.port = port
        self.dbname = dbname
        self.user = user
        self.pwd = pwd
        while True:
            try:
                conn = psycopg2.connect(host = self.host, port=self.port, dbname=self.dbname, user=self.user, password=self.pwd)
                conn.close()
                break
            except (Exception, psycopg2.DatabaseError) as error:
                print('Error: ' + str(error))
        self.engine = create_engine('postgresql://'+self.user+':'+self.pwd+'@'+self.host+':'+str(self.port)+'/'+self.dbname,echo=False)


    def get_iin_from_unique_ud_gr(self, ud_code):
        # Search from gbdfl according to given red_id from faiss index with face vectors
        conn = None
        iin = None
        try:
            # connect to the PostgresQL database
            conn = psycopg2.connect(host = self.host, port=self.port, dbname=self.dbname, user=self.user, password=self.pwd)
            # create a new cursor object
            cur = conn.cursor()
            # execute the INSERT statement
            cur.execute("SELECT gr_code FROM fr.unique_ud_gr WHERE ud_code='{ud_code}'".format(ud_code=ud_code))
            # commit the changes to the database
            iin = cur.fetchone()
            # close the communication with the PostgresQL database
            cur.close()
        except (Exception, psycopg2.DatabaseError) as error:
            print('Error: ' + str(error))
            return None
        finally:
            if conn is not None:
                conn.close()
        return iin[0]


    def get_info_from_unique_ud_gr(self, ud_code):
        # Search from gbdfl according to given red_id from faiss index with face vectors
        conn = None
        info = None
        try:
            # connect to the PostgresQL database
            conn = psycopg2.connect(host = self.host, port=self.port, dbname=self.dbname, user=self.user, password=self.pwd)
            # create a new cursor object
            cur = conn.cursor()
            # execute the INSERT statement
            if len(ud_code) == 1:
                sql_str = "SELECT gr_code,lastname,firstname,secondname, ud_code FROM fr.unique_ud_gr WHERE ud_code = '{ids}'".format(ids=ud_code[0])
            else:
                sql_str = "SELECT gr_code,lastname,firstname,secondname, ud_code FROM fr.unique_ud_gr WHERE ud_code in {ids}".format(ids=ud_code)
            # print(sql_str)
            cur.execute(sql_str)
            # commit the changes to the database
            info = cur.fetchall()
            # close the communication with the PostgresQL database
            cur.close()
        except (Exception, psycopg2.DatabaseError) as error:
            print('Error: ' + str(error))
            return None
        finally:
            if conn is not None:
                conn.close()
        # print(info)
        if len(info) > 0:
            return info[0]
        else:
            return info


    def search_from_blacklist_faiss(self, faiss_index, one_vector, top_n, threshold):
        try:
            topn = 1
            if faiss_index.ntotal >= top_n:
                topn = top_n
            else:
                topn = faiss_index.ntotal
            if faiss_index.ntotal > 1000000:
                faiss_index.nprobe = 10000
            else:
                faiss_index.nprobe = 256
            query = np.array([one_vector], dtype=np.float32)
            D, I = faiss_index.search(query, topn)
            distance = float(threshold)/100.0

            if D[0][0] >= distance:
                return D[0], I[0]
            else:
                return None, None
        except:
            return None, None


    def search_from_gbdfl_faiss(self, faiss_index, one_vector, top_n, threshold):
        try:
            topn = 1
            if faiss_index.ntotal >= top_n:
                topn = top_n
            else:
                topn = faiss_index.ntotal
            if faiss_index.ntotal > 1000000:
                faiss_index.nprobe = 10000
            else:
                faiss_index.nprobe = 256
            query = np.array([one_vector], dtype=np.float32)
            D, I = faiss_index.search(query, topn)
            distance = float(threshold)/100.0

            if D[0][0] >= distance:
                return D, I
            else:
                return None, None
        except:
            return None, None


    def search_from_blacklist(self, feature, threshold):
        res = None
        # connect to the PostgresQL database
        # FLAGS.psql_server, FLAGS.psql_server_port, FLAGS.psql_db, FLAGS.psql_user, FLAGS.psql_user_pass
        conn = psycopg2.connect(host=self.host, port=self.port, dbname=self.dbname, user=self.user,
                                password=self.pwd)
        # create a new cursor object
        cur = conn.cursor()
        select_query = '''SELECT fr.blacklist.red_id, fr.blacklist.vector,
                      (CUBE(array[{vector}]) <-> fr.blacklist.vector) as distance
                      FROM fr.blacklist
                      ORDER BY (CUBE(array[{vector}]) <-> vector)
                      ASC LIMIT 10'''.format(vector=','.join(str(s) for s in feature),)
        cur.execute(select_query)
        result = cur.fetchall()
        cur.close()
        distance = float(threshold) / 100
        idx = None
        dist = None
        for row in result:
            vec = np.fromstring(row[1][1:-1], dtype=float, sep=',')
            dist = np.dot(vec,feature)
            if dist > distance:
                idx = row[0]
                #print(dist)
        return idx, dist


    def insertIntoBlacklist(self, red_id, vector):
        conn = None
        try:
            # connect to the PostgresQL database
            conn = psycopg2.connect(host = self.host, port=self.port, dbname=self.dbname, user=self.user, password=self.pwd)
            # create a new cursor object
            cur = conn.cursor()
            # execute the INSERT statement
            cur.execute("INSERT INTO fr.blacklist(id, vector) VALUES ('{}', CUBE(array[{}]))".format(red_id, ','.join(str(s) for s in vector), ))
            # commit the changes to the database
            conn.commit()
            # close the communication with the PostgresQL database
            cur.close()
        except (Exception, psycopg2.DatabaseError) as error:
            print('Error: ' + str(error))
            return False
        finally:
            if conn is not None:
                conn.close()
        return True


    def deleteFromBlacklist(self, red_id):
        conn = None
        try:
            # connect to the PostgresQL database
            conn = psycopg2.connect(host = self.host, port=self.port, dbname=self.dbname, user=self.user, password=self.pwd)
            # create a new cursor object
            cur = conn.cursor()
            # execute the INSERT statement
            cur.execute("DELETE FROM fr.blacklist WHERE id = {}".format(red_id))
            # commit the changes to the database
            conn.commit()
            # close the communication with the PostgresQL database
            cur.close()
        except (Exception, psycopg2.DatabaseError) as error:
            print('Error: ' + str(error))
            return False
        finally:
            if conn is not None:
                conn.close()
        return True


    def writeFrames(self, timestamp, extension, coord_x, coord_y, width_x, height_y, similarity, source_ip_camera, server_id):
        conn = None
        # img = open(img, 'rb').read()
        try:
            # connect to the PostgresQL database
            conn = psycopg2.connect(host = self.host, port=self.port, dbname=self.dbname, user=self.user, password=self.pwd)
            # create a new cursor object
            cur = conn.cursor()
            # execute the INSERT statement
            cur.execute("INSERT INTO fr.frames(unique_id, i_extension, coord_x, coord_y, width_x, height_y, similarity, source_ip_camera, server_id) VALUES({timestamp}, '{extension}', '{coord_x}', '{coord_y}', '{width_x}', '{height_y}', {similarity}, {source_ip_camera}, {server_id})".format(timestamp=timestamp, extension=extension, coord_x=coord_x, coord_y=coord_y, width_x=width_x, height_y=height_y, similarity=similarity, source_ip_camera=source_ip_camera, server_id=server_id))
            # commit the changes to the database
            conn.commit()
            # close the communication with the PostgresQL database
            cur.close()
        except (Exception, psycopg2.DatabaseError) as error:
            print('Error: ' + str(error))
            return False
        finally:
            if conn is not None:
                conn.close()
        return True


    def getOriginalFrame(self, unique_id, camera_id):
        conn = None
        blob = None
        try:
            # connect to the PostgresQL database
            conn = psycopg2.connect(host = self.host, port=self.port, dbname=self.dbname, user=self.user, password=self.pwd)
            # create a new cursor object
            cur = conn.cursor()
            # execute the INSERT statement
            cur.execute("SELECT * FROM fr.frames WHERE unique_id={unique_id} and source_ip_camera={camera_id}".format(unique_id=unique_id, camera_id=camera_id))
            # commit the changes to the database
            blob = cur.fetchone()
            # close the communication with the PostgresQL database
            cur.close()
        except (Exception, psycopg2.DatabaseError) as error:
            print('Error: ' + str(error))
            return None
        finally:
            if conn is not None:
                conn.close()
        return blob


    def getSimilarityRed(self, vector, distance):
        res = None
        try:
            # data = pd.read_sql('SELECT * FROM fr.blacklist', self.engine)
            names = self.red_database['id']
            vectors = self.red_database['vector']
        except:
            print('Could not get data from fr.blacklist')
            return res
        distance = float(distance)/100
        try:
            for i in range(len(vectors)):
                vec = np.fromstring(vectors[i][1:-1], dtype=float, sep=',')
                dist = np.dot(vector, vec)
                if dist > distance:
                    res = {'red_id': names[i], 'score': dist}
        except:
            print('Could not compare features')

        return res

    #unique_id, face_id, crop_time, camera_id, rect_x, rect_y, height_y, width_x
    def insert_into_croplist(self, unique_id, ud_code, face_id, insert_date, camera_id, rect_x, rect_y, height_y, similarity, width_x, iin):
        conn = None
        try:
            # connect to the PostgresQL database
            conn = psycopg2.connect(host = self.host, port=self.port, dbname=self.dbname, user=self.user, password=self.pwd)
            # create a new cursor object
            cur = conn.cursor()
            # execute the INSERT statement
            cur.execute("""INSERT INTO fr.application_croplist(unique_id,
                                                               red_id,
                                                               insert_date,
                                                               camera_id,
                                                               crop_id,
                                                               coord_x,
                                                               coord_y,
                                                               height_y,
                                                               similarity,
                                                               width_x,
                                                               iin) VALUES (
                                                                          {unique_id},
                                                                          '{red_id}',
                                                                          '{insert_date}',
                                                                          '{camera_id}',
                                                                          {face_id},
                                                                          {coord_x},
                                                                          {coord_y},
                                                                          {height_y},
                                                                          {similarity},
                                                                          {width_x},
                                                                          '{iin}')""".format(
                                                                                          unique_id=unique_id,
                                                                                          red_id=ud_code,
                                                                                          insert_date=insert_date,
                                                                                          camera_id=camera_id,
                                                                                          face_id=face_id,
                                                                                          coord_x=rect_x,
                                                                                          coord_y=rect_y,
                                                                                          height_y=height_y,
                                                                                          similarity=similarity,
                                                                                          width_x=width_x,
                                                                                          iin=iin))
            # commit the changes to the database
            conn.commit()
            # close the communication with the PostgresQL database
            cur.close()
        except (Exception, psycopg2.DatabaseError) as error:
            print('Error: ' + str(error))
            return False
        finally:
            if conn is not None:
                conn.close()
        return True


    def insert_into_vectors_archive(self, unique_id, vector, camera_id, server_id):
        conn = None
        try:
            # connect to the PostgresQL database
            conn = psycopg2.connect(host = self.host, port=self.port, dbname=self.dbname, user=self.user, password=self.pwd)
            # create a new cursor object
            cur = conn.cursor()
            # execute the INSERT statement
            cur.execute("INSERT INTO fr.vectors_archive(unique_id, vector, camera_id, server_id) VALUES ({}, CUBE(array[{}]), '{}', {})".format(unique_id, ','.join(str(s) for s in vector), camera_id, server_id))
            # commit the changes to the database
            conn.commit()
            # close the communication with the PostgresQL database
            cur.close()
        except (Exception, psycopg2.DatabaseError) as error:
            print('Error: ' + str(error))
            return False
        finally:
            if conn is not None:
                conn.close()
        return True


    def update_application_croplist(self, red_id, similarity, unique_id):
        conn = None
        try:
            # connect to the PostgresQL database
            conn = psycopg2.connect(host = self.host, port=self.port, dbname=self.dbname, user=self.user, password=self.pwd)
            # create a new cursor object
            cur = conn.cursor()
            # execute the INSERT statement
            cur.execute("""UPDATE fr.application_croplist SET red_id={red_id}, similarity={similarity} WHERE unique_id={unique_id}""".format(red_id=red_id, similarity=similarity, unique_id=unique_id))
            # commit the changes to the database
            conn.commit()
            # close the communication with the PostgresQL database
            cur.close()
        except (Exception, psycopg2.DatabaseError) as error:
            print('Error: ' + str(error))
            return False
        finally:
            if conn is not None:
                conn.close()
        return True


    def search_new_person(self, vector, distance):
        res = None
        try:
            vectors_archive = pd.read_sql('SELECT * FROM fr.vectors_archive', self.engine)
            # if this does not work, try to divide table into multiple dataframes
            unique_id = vectors_archive['unique_id']
            vectors = vectors_archive['vector']
            cameras = vectors_archive['camera_id']
            # servers = vectors_archive['server_id']
        except:
            print('Could not get data from fr.vectors_archive')
            return res
        distance = float(distance)/100
        try:
            res = {'person': []}
            for i in range(len(vectors)):
                vec = np.fromstring(vectors[i][1:-1], dtype=float, sep=',')
                dist = np.dot(vector, vec)
                if dist > distance:
                    dct = {'unique_id': unique_id[i], 'score': dist, 'camera': cameras[i]}
                    res['person'].append(dct)
                    copyfile('/home/dastrix/PROJECTS/face_reco_2_loc/face_reco_2_loc/application/static/frames_folder/' + str(unique_id[i]) + '_' + str(cameras[i]) + '.jpg', '/home/dastrix/PROJECTS/face_reco_2_loc/face_reco_2_loc/application/static/search_result/' + str(unique_id[i]) + '_' + str(cameras[i]) + '.jpg')
        except:
            print('Could not compare features')

        return res


    def get_blob_from_ud_gr(self, ids):
        # Search from gbd fl according to given red_id from faiss index with face vectors
        conn = None
        iin = None
        try:
            # connect to the PostgresQL database
            conn = psycopg2.connect(host=self.host, port=self.port, dbname=self.dbname, user=self.user, password=self.pwd)
            # create a new cursor object
            cur = conn.cursor()
            # execute the INSERT statement
            if len(ids) == 1:
                sql_str = "SELECT ud_code,gr_code,lastname,firstname,secondname FROM fr.unique_ud_gr WHERE ud_code = '{ids}'".format(ids=ids[0])
            else:
                sql_str = "SELECT ud_code,gr_code,lastname,firstname,secondname FROM fr.unique_ud_gr WHERE ud_code in {ids}".format(ids=ids)
            #print(sql_str)
            cur.execute(sql_str)
            # commit the changes to the database
            blob = cur.fetchall()
            # print(blob)
            # close the communication with the PostgresQL database
            cur.close()
        except Exception as error:
            print('Error: ' + str(error))
            return None
        finally:
            if conn is not None:
                conn.close()
        return blob