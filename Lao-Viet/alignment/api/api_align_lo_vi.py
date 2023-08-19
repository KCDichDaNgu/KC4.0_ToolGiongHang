from flask import Flask, request
import os
import glob
import io
import json
from underthesea import sent_tokenize
from flask_cors import CORS
import shutil
from shutil import copyfile
import numpy as np
from numpy import dot
from numpy.linalg import norm
import re
import random
import sys
from random import seed as seed
import codecs

sys.path.insert(1, os.environ['VECALIGN_LO_VI'])
from align_paragraphs import align_paragraphs

app = Flask(__name__)
CORS(app)

def split_sents(path_temp_vi, path_temp_lo, embdir):
    tmp_vi = io.open(path_temp_vi, encoding='utf-8').read().split('\n')
    tmp_lo = io.open(path_temp_lo, encoding='utf-8').read().split('\n')

    path_vi = embdir + '/' + path_temp_vi.split('/')[-1]
    path_lo = embdir + '/' + path_temp_lo.split('/')[-1]

    f_vi = open(path_vi, 'w')
    for line in tmp_vi:
        if sent_tokenize(line) != []:
            for l in sent_tokenize(line):
                f_vi.write(l.strip())
                f_vi.write('\n')
    f_vi.close()

    f_lo = open(path_lo, 'w')
    for line in tmp_lo:
        if line.split('。') != '':
            for l in line.split('。'):
                if l != '':
                    f_lo.write(l.strip())
                    f_lo.write('\n')
    f_lo.close()
    return path_vi, path_lo

def preprocess_line(line):
    line = line.strip()
    if len(line) == 0:
        line = 'BLANK_LINE'
    return line

def layer(lines, num_overlaps, comb=' '):
    """
    make front-padded overlapping sentences
    """
    if num_overlaps < 1:
        raise Exception('num_overlaps must be >= 1')
    out = ['PAD', ] * min(num_overlaps - 1, len(lines))
    for ii in range(len(lines) - num_overlaps + 1):
        out.append(comb.join(lines[ii:ii + num_overlaps]))
    return out

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

def make_doc_embedding(sent2line, line_embeddings, lines, num_overlaps):
    """
    lines: sentences in input document to embed
    sent2line, line_embeddings: precomputed embeddings for lines (and overlaps of lines)
    """

    lines = [preprocess_line(line) for line in lines]

    vecsize = line_embeddings.shape[1]

    vecs0 = np.empty((num_overlaps, len(lines), vecsize), dtype=np.float32)

    for ii, overlap in enumerate(range(1, num_overlaps + 1)):
        for jj, out_line in enumerate(layer(lines, overlap)):
            try:
                line_id = sent2line[out_line]
            except KeyError:
                # logger.warning('Failed to find overlap=%d line "%s". Will use random vector.', overlap, out_line)
                line_id = None

            if line_id is not None:
                vec = line_embeddings[line_id]
            else:
                vec = np.random.random(vecsize) - 0.5
                vec = vec / np.linalg.norm(vec)

            vecs0[ii, jj, :] = vec

    return vecs0

def make_norm1(vecs0):
    """
    make vectors norm==1 so that cosine distance can be computed via dot product
    """
    for ii in range(vecs0.shape[0]):
        for jj in range(vecs0.shape[1]):
            norm = np.sqrt(np.square(vecs0[ii, jj, :]).sum())
            vecs0[ii, jj, :] = vecs0[ii, jj, :] / (norm + 1e-5)

def embed_paragraph(path_vi, path_lo_trans2vi, embdir):
    path_emb_vi = embdir + '/embed.vi'
    path_emb_lo_trans2vi = embdir + '/embed.lo_trans2vi'
    
    script_vi = 'bash $LASER/tasks/embed/embed.sh ' + path_vi + ' vi ' + path_emb_vi
    script_lo_trans2vi = 'bash $LASER/tasks/embed/embed.sh ' + path_lo_trans2vi + ' vi ' + path_emb_lo_trans2vi

    os.system(script_vi)
    os.system(script_lo_trans2vi)
    
    return path_emb_vi, path_emb_lo_trans2vi

def cosim_two_embed(path_temp_vi, path_temp_lo_trans2vi, embdir):
    path_vi, path_lo_trans2vi = split_sents(path_temp_vi, path_temp_lo_trans2vi, embdir)
    
    path_emb_vi, path_emb_lo_trans2vi = embed_paragraph(path_vi, path_lo_trans2vi, embdir)
    
    src_sent2line, src_line_embeddings = read_in_embeddings(path_vi, path_emb_vi)
    tgt_sent2line, tgt_line_embeddings = read_in_embeddings(path_lo_trans2vi, path_emb_lo_trans2vi)
    
    vi = io.open(path_vi, encoding='utf-8').read().split('\n')
    lo_trans2vi = io.open(path_lo_trans2vi, encoding='utf-8').read().split('\n')
    tmp_vi = io.open(path_temp_vi, encoding='utf-8').read().split('\n')
    tmp_lo_trans2vi = io.open(path_temp_lo_trans2vi, encoding='utf-8').read().split('\n')
    
    vecs_vis = make_doc_embedding(src_sent2line, src_line_embeddings, vi, 1)
    vecs_lo_trans2vis = make_doc_embedding(tgt_sent2line, tgt_line_embeddings, lo_trans2vi, 1)


    make_norm1(vecs_vis)
    make_norm1(vecs_lo_trans2vis)

    vecs_vi = vecs_vis[0]
    vecs_lo_trans2vi = vecs_lo_trans2vis[0]
    
    all_max_cos_sim = []
    vecs_emb_vi = []
    vecs_emb_lo_trans2vi = []

    id_sent_vi = 0
    id_vec_vi = 0
    while id_sent_vi < len(tmp_vi):

        vec_visted_vi = vecs_vi[id_vec_vi:id_vec_vi+len(sent_tokenize(tmp_vi[id_sent_vi]))]

        if vec_visted_vi.shape[0] > 0:
            nSentx = vec_visted_vi.shape[0]
            vec_x = np.average(vec_visted_vi, axis=0)
            vec_x = np.expand_dims(vec_x, axis=0)


            id_sent_lo_trans2vi = 0
            id_vec_lo_trans2vi = 0
            max_cos_similarity = 0.0
            while id_sent_lo_trans2vi < len(tmp_lo_trans2vi):
                split_lo_trans2vi = tmp_lo_trans2vi[id_sent_lo_trans2vi].split('。')
                while '' in split_lo_trans2vi:
                    split_lo_trans2vi.remove('')
                vec_visted_lo_trans2vi = vecs_lo_trans2vi[id_vec_lo_trans2vi:id_vec_lo_trans2vi+len(split_lo_trans2vi)]

                if vec_visted_lo_trans2vi.shape[0] > 0:
                    nSenty = vec_visted_lo_trans2vi.shape[0]
                    vec_y = np.average(vec_visted_lo_trans2vi, axis=0)
                    vec_y = np.expand_dims(vec_y, axis=0)

                    cos_x_y = dot(vec_x, vec_y.transpose())/(norm(vec_x)*norm(vec_y))

                    sum_x_ys = 0
                    for vec_ys in vec_visted_lo_trans2vi:
                        vec_ys = np.expand_dims(vec_ys, axis=0)
                        cos_x_ys = dot(vec_x, vec_ys.transpose())/(norm(vec_x)*norm(vec_ys))
                        sum_x_ys += 1 - cos_x_ys

                    sum_xs_y = 0
                    for vec_xs in vec_visted_vi:
                        vec_xs = np.expand_dims(vec_xs, axis=0)
                        cos_xs_y = dot(vec_xs, vec_y.transpose())/(norm(vec_xs)*norm(vec_y))
                        sum_xs_y += 1 - cos_xs_y

                    cos_similarity = (1 - cos_x_y)*nSentx*nSenty / (sum_x_ys + sum_xs_y)
                    cos_similarity = cos_similarity[0][0]

                    if cos_similarity == 0.5:
                        cos_similarity = cos_x_y[0][0]

                    if max_cos_similarity < cos_similarity:
                        max_cos_similarity = cos_similarity

                if len(split_lo_trans2vi) == 0:
                    count = 0
                else:
                    count = len(split_lo_trans2vi)
                id_sent_lo_trans2vi += 1
                id_vec_lo_trans2vi += count

            all_max_cos_sim.append(max_cos_similarity)



        if len(sent_tokenize(tmp_vi[id_sent_vi])) == 0:
            count = 0
        else:
            count = len(sent_tokenize(tmp_vi[id_sent_vi]))
        id_sent_vi += 1
        id_vec_vi += count
    return sum(all_max_cos_sim) / len(all_max_cos_sim)

def clean_text(s):
    s = re.sub('\ufeff', '', s)
    s = re.sub('\u200b', '', s)
    s = re.sub('"', '', s)
    s = re.sub("'", '', s)
    s = re.sub(" +", ' ', s)
    s = s.strip()
    return s

def clear_text(s):
    letters = list(
        "abcdefghijklmnopqrstuvwxyzáàảãạăắằẳẵặâấầẩẫậéèẻẽẹêếềểễệíìỉĩị"
        "ABCDEFGHIJKLMNOPQRSTUVWXYZÁÀẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬÉÈẺẼẸÊẾỀỂỄỆÍÌỈĨỊ"
        "óòỏõọôốồổỗộơớờởỡợúùủũụưứừửữựýỳỷỹỵđ "
        "ÓÒỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÚÙỦŨỤƯỨỪỬỮỰÝỲỶỸỴĐ "
    )
    telex_words = list("áàảãạăắằẳẵặâấầẩẫậéèẻẽẹêếềểễệíìỉĩịóòỏõọôốồổỗộơớờởỡợúùủũụưứừửữựđÁÀẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬÉÈẺẼẸÊẾỀỂỄỆÍÌỈĨỊÓÒỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÚÙỦŨỤƯỨỪỬỮỰĐ")
    number = list("0123456789")
    alphabel = telex_words + letters + number
    s = s.lower()
    for c in s:
        if c != '\n' and c not in alphabel:
            s = s.replace(c, '')
    s = re.sub(" +", ' ', s)
    s = s.strip()
    return s

@app.route('/', methods=['GET'])
def home():
    return "<h1>Distant Reading Archive</h1><p>This site is a prototype API for distant reading of science fiction novels.</p>"

@app.route('/scores/sentences', methods=['POST'])
def sentences_align():
    
    data_receive = request.json
    script_clear_trash = 'python ' + os.environ['VECALIGN_LO_VI'] + '/clear_trash.py -i /workspace/ntha/Lao_Viet/alignment/api/tmp_emb'
    os.system(script_clear_trash)
    result = dict()

    if data_receive['type'] == 'vl':

        embed_dir = '/workspace/ntha/Lao_Viet/alignment/api/tmp_emb/embedd' + str(random.randint(0, 1000))
        while os.path.isdir(embed_dir):
            embed_dir = '/workspace/ntha/Lao_Viet/alignment/api/tmp_emb/embedd' + str(random.randint(0, 1000))
        print ("path_to_embed_folder\t: ", embed_dir)
        os.mkdir(embed_dir)

        src_file_name = embed_dir + '/doc_src.txt'
        temp_src_file_name = embed_dir + '/temp_doc_src.txt'
        tgt_file_name = embed_dir + '/doc_tgt.txt'

        f_src = open(src_file_name, 'w')
        f_temp_src = open(temp_src_file_name, 'w')
        f_tgt = open(tgt_file_name, 'w')

        for line in data_receive['source'].split('\n'):
            if line.strip() != '':
                f_src.write(line.strip())
                f_src.write('\n')
                f_temp_src.write(clear_text(line.strip()))
                f_temp_src.write('\n')

        for line in data_receive['target'].split("\n"):
            if line.strip() != '':
                f_tgt.write(line.strip())
                f_tgt.write('\n')
        f_src.close()
        f_temp_src.close()
        f_tgt.close()

        output_file = embed_dir + '/aligned_sentences.txt'
        file_lo_trans2vi = embed_dir + '/file_lo_trans2vi.txt'

        script_trans2vi = 'python ' + os.environ['VECALIGN_LO_VI'] + '/trans_lo_vi.py -i ' + tgt_file_name + ' -o ' + file_lo_trans2vi
        os.system(script_trans2vi)

        path_temp_file_vi, path_temp_file_lo_trans2vi, path_temp_file_vi_raw, path_temp_file_lo = align_paragraphs(temp_src_file_name, file_lo_trans2vi, src_file_name, tgt_file_name, embed_dir)
        script = 'bash ' + os.environ['VECALIGN_LO_VI'] + '/align_sentences.sh ' + path_temp_file_vi + ' ' + path_temp_file_lo_trans2vi + ' ' + output_file + ' ' + path_temp_file_vi_raw + ' ' + path_temp_file_lo
        os.system(script)

        result['code'] = 1
        result['data'] = []

        lines = io.open(output_file, encoding='utf-8').read().strip().split('\n')
        for line in lines:
            result_for_file = dict()
            if len(line.split('\t')) == 3 and line.split('\t')[0] != '':
                result_for_file['score'] = line.split('\t')[0].strip()
                result_for_file['source'] = line.split('\t')[1].strip()
                result_for_file['target'] = line.split('\t')[2].strip()
                result_for_file['type'] = data_receive['type'].strip()
            result['data'].append(result_for_file)
        if result['data'] != []:
            result['message'] = 'successful'
        else:
            result['code'] = 0
            result['message'] = 'No successful'
        for f in os.listdir(embed_dir):
            os.remove(os.path.join(embed_dir, f))
        os.rmdir(embed_dir)

    return result

@app.route('/scores/doc_align', methods=['POST'])
def doc_align(): 
    data_receive = request.json

    script_clear_trash = 'python ' + os.environ['VECALIGN_LO_VI'] + '/clear_trash.py -i /workspace/ntha/Lao_Viet/alignment/api/tmp_emb'
    os.system(script_clear_trash)


    result = dict()

    if data_receive['type'] == 'vl':

        embed_dir = '/workspace/ntha/Lao_Viet/alignment/api/tmp_emb/embedd' + str(random.randint(0, 1000))
        while os.path.isdir(embed_dir):
            embed_dir = '/workspace/ntha/Lao_Viet/alignment/api/tmp_emb/embedd' + str(random.randint(0, 1000))
        print ("path_to_embed_folder\t: ", embed_dir)
        os.mkdir(embed_dir)

        src_file_name = embed_dir + '/doc_src.txt'
        tgt_file_name = embed_dir + '/doc_tgt.txt'

        f_src = open(src_file_name, 'w')
        f_tgt = open(tgt_file_name, 'w')

        for line in sent_tokenize(data_receive['source']):
            f_src.write(line)
            f_src.write('\n')

        for line in data_receive['target'].split('\n'):
            f_tgt.write(line)
            f_tgt.write('\n')
        f_src.close()
        f_tgt.close()

        path_temp_file_lo_trans2vi = embed_dir + '/path_temp_file_lo_trans2vi.txt'
        script_trans2vi = 'python ' + os.environ['VECALIGN_LO_VI'] + '/trans_lo_vi.py -i ' + tgt_file_name + ' -o ' + path_temp_file_lo_trans2vi
        os.system(script_trans2vi)
        cos_sim = cosim_two_embed(src_file_name, path_temp_file_lo_trans2vi, embed_dir)
        
        data_result = dict()
        data_result['score'] = str(cos_sim)
        data_result['source'] = data_receive['source']
        data_result['taget'] = data_receive['target']
        data_result['type'] = data_receive['type']

        result = dict()
        result['code'] = '1'
        result['data'] = data_result

        if len(result['data']) != 0:
            result['message'] = 'successful'
        else:
            result['code'] = '0'
            result['message'] = 'No successful'

        for f in os.listdir(embed_dir):
            os.remove(os.path.join(embed_dir, f))
        os.rmdir(embed_dir)

    return result

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9988, debug=True)
