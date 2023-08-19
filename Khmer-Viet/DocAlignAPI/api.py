import flask
import requests
import os 
from flask_cors import CORS
import numpy as np

def write_data_to_file(data, file_path):
	with open(file_path , 'w', encoding='utf-8') as f:
		f.write(data)

app = flask.Flask(__name__)
app.config["DEBUG"] = True
CORS(app)

def readDataFromOutputFile(f_):
	with open(f_ , 'r') as f:
		score = np.loadtxt(f)
	return score

@app.route('/', methods=['GET'])
def home():
    return "<h1>Distant Reading Archive</h1><p>This site is a prototype API for distant reading of science fiction novels.</p>"

@app.route('/doc_align', methods=['POST'])
def doc_align():
	content = flask.request.get_json()
	print(content)
	doc_source, doc_target , type_pair  = content['source'], content['target'] , content['type']
	# #create temp file 

	if type_pair == 'vi-km':
		doc_vi = doc_source
		doc_km = doc_target
	elif type_pair =='km-vi':
		doc_vi = doc_target
		doc_km = doc_source
	else:
		return {"code":"0" , "message":"fail" , 'data':[]}

	write_data_to_file(doc_vi,'doc_vi.txt')
	write_data_to_file(doc_km,'doc_km.txt')
	print('finishing write file temp ..... ')
	# #run command line to sentene alignemnt 
	print('running api doc algin ...... ')
	command = 'python3 textalignment/document_alignment.py --input_vi doc_vi.txt --input_km doc_km.txt --lg km --single_doc'
	os.system(command)
	print('finish run api ..... ...... ')
	if os.path.exists('textalignment/result/output_singledoc.txt'):
		code , message = "1" , "success"
		score  = str(readDataFromOutputFile('textalignment/result/output_singledoc.txt'))
		data = {'score':score , 'source':doc_source , 'target':doc_target , 'type':type_pair}
		print(data)
		print('thanh cong ')
		os.system('rm textalignment/result/output_singledoc.txt')
		print('deleting file result ....')
	else:
		code , message = "0" , "fail"
		data = []
		print('that bai ')
	return {"code":code , "message":message , 'data':data}

app.run(host='0.0.0.0', port = 9113)
