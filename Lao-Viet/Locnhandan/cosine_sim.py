import io
import os
import re
from glob import glob
from trans_lo_vi import trans_lo_vi
import random
import numpy as np
import argparse
from numpy import dot
from numpy.linalg import norm

parser = argparse.ArgumentParser('Sentence alignment using sentence embeddings and FastDTW',
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)

parser.add_argument('-i', '--input', type=str, required=True,
                    help='')
parser.add_argument('-o', '--output', type=str, required=True,
                    help='')

args = parser.parse_args()

def get_emb_file(los, vis, los_trans2_vis):
	path_tmp_lo = emb_dir + '/tmp_lo' + str(random.randint(0, 1000)) + '.txt'
	while os.path.isdir(path_tmp_lo):
	    path_tmp_lo = emb_dir + '/tmp_lo' + str(random.randint(0, 1000)) + '.txt'
	    
	path_tmp_vi = emb_dir + '/tmp_vi' + str(random.randint(0, 1000)) + '.txt'
	while os.path.isdir(path_tmp_vi):
	    path_tmp_vi = emb_dir + '/tmp_vi' + str(random.randint(0, 1000)) + '.txt'
	    
	path_tmp_trans2vi = emb_dir + '/tmp_trans2vis' + str(random.randint(0, 1000)) + '.txt'
	while os.path.isdir(path_tmp_trans2vi):
	    path_tmp_trans2vi = emb_dir + '/tmp_trans2vis' + str(random.randint(0, 1000)) + '.txt'

	f_lo = open(path_tmp_lo, 'w')
	f_vi = open(path_tmp_vi, 'w')
	f_trans2vi = open(path_tmp_trans2vi, 'w')
	    
	for i in range(len(los)):
	    f_lo.write(los[i] + '\n')
	    f_vi.write(vis[i] + '\n')
	    f_trans2vi.write(los_trans2_vis[i] + '\n')
	f_lo.close()
	f_vi.close()
	f_trans2vi.close()

	return path_tmp_vi, path_tmp_lo, path_tmp_trans2vi


def read_in_embeddings(text_file, embed_file):
    """
    Given a text file with candidate sentences and a corresponing embedding file,
       make a maping from candidate sentence to embedding index, 
       and a numpy array of the embeddings
    """
    sent2line = dict()
    with open(text_file, 'rt', encoding="utf-8") as fin:
        for ii, line in enumerate(fin):
#             if line.strip() in sent2line:
#                 raise Exception('got multiple embeddings for the same line')
            sent2line[line.strip()] = ii

    line_embeddings = np.fromfile(embed_file, dtype=np.float32, count=-1)
    if line_embeddings.size == 0:
        raise Exception('Got empty embedding file')

    laser_embedding_size = line_embeddings.size // len(sent2line)  # currently hardcoded to 1024
    if laser_embedding_size != 1024:
        laser_embedding_size = 1024
#     logger.info('laser_embedding_size determined to be %d', laser_embedding_size)
    line_embeddings.resize(line_embeddings.shape[0] // laser_embedding_size, laser_embedding_size)
    return sent2line, line_embeddings


def cosim_two_embed(path_temp_vi, path_tmp_trans2vi):
    _, vis_emb = read_in_embeddings(path_temp_vi, path_temp_vi+'.emb')
    _, trans2vis_emb = read_in_embeddings(path_tmp_trans2vi, path_tmp_trans2vi+'.emb')
    
    list_score = []
    for i in range(len(vis_emb)):
        cosine_line = dot(vis_emb[i], trans2vis_emb[i].transpose())/(norm(vis_emb[i])*norm(trans2vis_emb[i]))
        if cosine_line > 1:
        	cosine_line = 1 - (cosine_line - 1)
        if cosine_line == 1:
        	cosine_line -= random.uniform(0, 1)
        list_score.append(cosine_line)
    return list_score


if __name__ == '__main__':
	input_folder = args.input
	output_folder = args.output

	if input_folder[-1] != '/':
		input_folder += '/'

	if output_folder[-1] != '/':
		output_folder += '/'

	for index_file, path in enumerate(glob(input_folder + '*')):

		lines = io.open(path, encoding='utf-8').read().split('\n')

		los = [line.split('\t')[0] for line in lines if line != '']
		vis = [line.split('\t')[1] for line in lines if line != '']

		los_trans2_vis = trans_lo_vi(los)

		emb_dir = '/tmp/emb_dir_' + str(random.randint(0, 1000))
		while os.path.isdir(emb_dir):
		    emb_dir = '/tmp/emb_dir_' + str(random.randint(0, 1000))
		os.mkdir(emb_dir)

		path_tmp_vi, path_tmp_lo, path_tmp_trans2vi = get_emb_file(los, vis, los_trans2_vis)

		script_emb_vi = 'bash $LASER/tasks/embed/embed.sh ' + path_tmp_vi + ' vi ' + path_tmp_vi + '.emb'
		script_emb_trans2vi = 'bash $LASER/tasks/embed/embed.sh ' + path_tmp_trans2vi + ' vi ' + path_tmp_trans2vi + '.emb'

		print (os.system(script_emb_vi))
		print (os.system(script_emb_trans2vi))

		list_score = cosim_two_embed(path_tmp_vi, path_tmp_trans2vi)

		f = open(output_folder + 'output_' + str(index_file) + '.txt', 'w')

		for ii in range(len(vis)):
			f.write(str(list_score[ii])[:6] + '\t' + los[ii] + '\t' + vis[ii] + '\n')
		f.close()