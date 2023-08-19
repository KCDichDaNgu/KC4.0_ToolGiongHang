# -*- coding: utf-8 -*-
import os
import io
from underthesea import sent_tokenize
import re
from underthesea import word_tokenize
from deep_translator import GoogleTranslator

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
        "óòỏõọôốồổỗộơớờởỡợúùủũụưứừửữựýỳỷỹỵđ "
    )
    telex_words = list("áàảãạăắằẳẵặâấầẩẫậéèẻẽẹêếềểễệíìỉĩịóòỏõọôốồổỗộơớờởỡợúùủũụưứừửữựđ")
    number = list("0123456789")
    alphabel = telex_words + letters + number
    s = s.lower()
    for c in s:
        if c not in alphabel:
            s = s.replace(c, '')
    s = re.sub(" +", ' ', s)
    s = s.strip()
    return s

def trans_lo_vi(los):
    los_trans2_vis = []
    for line in los:
        new_line = clean_text(line)
        if new_line.strip() != '':
            los_trans2_vis.append(GoogleTranslator(source='lo', target='vi').translate(text=new_line))
    return los_trans2_vis