from flask import Flask, jsonify, request
from FlagEmbedding import FlagModel
model = FlagModel('BAAI/bge-small-zh', query_instruction_for_retrieval="为这个句子生成表示以用于检索相关文章：",use_half=False)
app = Flask(__name__)

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
        result = model.encode_queries([data]).tolist()
    else:
        result = model.encode([data]).tolist()
    return jsonify({"msg":"ok", "data": result,"code": 200})
