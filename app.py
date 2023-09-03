import json
import sqlite3
from flask import Flask, jsonify, request
from FlagEmbedding import FlagModel
import os
import click
from flask import current_app, g
from flask.cli import with_appcontext
import faiss
from seafile_api import *

model = FlagModel('BAAI/bge-small-zh', query_instruction_for_retrieval="为这个句子生成表示以用于检索相关文章：",use_half=False)
app = Flask(__name__)

data_path = os.getenv("DATA_PATH", "./data")
sql_data_path = os.path.join(data_path, "data.db")
faiss_data_path = os.path.join(data_path, "faiss.index")
is_download_from_sf = os.getenv("IS_DOWNLOAD_FROM_SF", "N")
sf_username = os.getenv("SF_USERNAME", "admin")
sf_password = os.getenv("SF_PASSWORD", "")
sf_host_url = os.getenv("SF_HOST_URL", "")
sf_repo_id = os.getenv("SF_REPO_ID", "87faa67c-dc1c-4383-a36b-d7267c1a81ec")
sf_sql_data_path = "WEB-APP/embedding/data.db"
sf_faiss_data_path = "WEB-APP/embedding/faiss.index"
sf_token = login_sf(sf_host_url, sf_username, sf_password)
d = 512                           # dimensionality of the vectors

def init_db():
    db = get_db()
    with current_app.open_resource('schema.sql') as f:
        db.executescript(f.read().decode('utf8'))

@click.command('init-db')
@with_appcontext
def init_db_command():
    """Clear the existing data and create new tables."""
    init_db()
    click.echo('Initialized the database.')


def get_db():
    if 'db' not in g:
        # 如果sql_data_path文件不存在，则创建并初始化db
        if not os.path.exists(sql_data_path):
            if is_download_from_sf == "Y":
                download_from_sf(sf_token, sf_host_url, sf_repo_id, sf_sql_data_path, sql_data_path)
            else:
                with open(sql_data_path, 'w') as f:
                    f.write('')
                with app.app_context():
                    init_db()
        g.db = sqlite3.connect(
            sql_data_path,
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row
    return g.db

def get_faiss_index():
    if 'faiss_index' not in g:
        if os.path.exists(faiss_data_path):
            g.faiss_index = faiss.read_index(faiss_data_path)
        else:
            if is_download_from_sf == "Y":
                download_from_sf(sf_token, sf_host_url, sf_repo_id, sf_faiss_data_path, faiss_data_path)
                g.faiss_index = faiss.read_index(faiss_data_path)
            else:
                with open(faiss_data_path, 'w') as f:
                    f.write('')
                g.faiss_index = faiss.index_factory(d, "IDMap,Flat")
            print("faiss_index is trained?: ", g.faiss_index.is_trained)
    return g.faiss_index


@app.teardown_appcontext
def close_connection(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()
    faiss_index = g.pop('faiss_index', None)
    if faiss_index is not None:
        faiss.write_index(faiss_index, faiss_data_path)
    sf_token = login_sf(sf_host_url, sf_username, sf_password)
    upload_to_sf(sf_token, sf_host_url, sf_repo_id, sf_sql_data_path, sql_data_path)
    upload_to_sf(sf_token, sf_host_url, sf_repo_id, sf_faiss_data_path, faiss_data_path)

app.teardown_appcontext(close_connection)


@app.route('/')
def hello_world():
    return jsonify({"msg":"ok", "data": 'Hello, World!',"code": 200})

@app.route('/embedding', methods=['POST','GET'])
def emedding():
    if "data" in request.form:
        data = request.form['data']
    else:
        data = request.args.get('data', '')
    if data == '':
        return jsonify({"msg":"error", "data": "Empty Emedding Data!", "code": 400})
    if "type" in request.form:
        type = request.form['type']
    else:
        type = request.args.get("type", "infomation")
    if type == "query":
        vendor_result = model.encode_queries([data])
        D, I = get_faiss_index().search(vendor_result, 10)
        print("I: ", I)
        ids = [str(id) for id in I[0] if id != -1]
        print(ids)
        if len(ids) > 0:
            str_ids = ",".join(ids)
            db = get_db()
            cursor = db.execute(
                f'SELECT id, content FROM information WHERE id in ({str_ids})'
            )
            result = cursor.fetchall()
            result = [dict(row) for row in result]
            print("result:", result)
            sorted_result = []
            id_index = 0
            for id in ids:
                distence = D[0][id_index].tolist()
                for r in result:
                    if str(r['id']) == id:
                        r['distence'] = distence
                        sorted_result.append(r)
                        break
                id_index += 1
            print('sorted_result:', sorted_result)
            result = sorted_result
        else:
            result = []
    else:
        db = get_db()
        cursor = db.cursor()
        # 基于content查询数据库的记录，如果有，直接返回vendor字段
        cursor = cursor.execute(
            'SELECT * FROM information WHERE content = ?', (data,)
        )
        result = cursor.fetchone()
        if result:
            print("found: ", result)
            result = json.loads(result[2])
        else:
            vendor_result = model.encode([data])
            print("vendor_shape: ", vendor_result.shape)
            result = vendor_result.tolist()
            cursor.execute("INSERT INTO information (content, vendor) VALUES (?, ?)", (data, str(result),))
            id = cursor.lastrowid
            xb = vendor_result
            # get_faiss_index().train(xb)
            get_faiss_index().add_with_ids(xb, [id])
            print("insert id: ", id)
            db.commit()
    return jsonify({"msg":"ok", "data": result,"code": 200})

@app.route('/information', methods=['GET'])
def list_information():
    db = get_db()
    cursor = db.execute(
        'SELECT * FROM information'
    )
    data = cursor.fetchall()
    data = [dict(row) for row in data]
    return jsonify({"msg":"ok", "data": data,"code": 200})