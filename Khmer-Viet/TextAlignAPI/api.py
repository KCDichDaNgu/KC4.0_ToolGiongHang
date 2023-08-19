import flask
import requests
import os 
from flask_cors import CORS


def write_data_to_file(data, file_path):
    with open(file_path , 'w', encoding='utf8') as f:
        f.write(data)

app = flask.Flask(__name__)
app.config["DEBUG"] = True
CORS(app)


def readDataFromOutputFile():
    with open('output.txt' , 'r') as f:
        lines = f.readlines()
        lines = [line.strip() for line in lines]
    list_result = []
    for line in lines :
        score , source , target = line.split('\t')
        list_result.append({'score':score , 'source':source , 'target':target})
    return list_result

@app.route('/', methods=['GET'])
def home():
    return "<h1>Distant Reading Archive</h1><p>This site is a prototype API for distant reading of science fiction novels.</p>"

@app.route('/sen_align', methods=['POST'])
def sen_align():
    content = flask.request.get_json()
    print(content)
    result = content
    result['encode'] = '1'
    #create temp file 
    write_data_to_file(content['doc_source'],'doc_source.txt')
    write_data_to_file(content['doc_target'],'doc_target.txt')
    print('finishing write file temp ..... ')
    #run command line to sentene alignemnt 
    command = 'python3 /workspace/huonglt/KC-4.0/kc_senalign/senalign.py -s doc_source.txt -t doc_target.txt -o output.txt -lang ' + result['lg']+' -pair 1'
    print('running api sentence algin ...... ')
    os.system(command)
    print('finish run api ..... ...... ')
    if os.path.exists('output.txt'):
        code , message = 1 , "success"
        data  = readDataFromOutputFile()
    else:
        code , message = 0 , "fail"
        data = []
    os.system('rm output.txt')
    return {"code":code , "message":message , 'data':data}

app.run(host='0.0.0.0', port = 5123)
