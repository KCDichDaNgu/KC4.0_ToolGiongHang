#Đây là mã nguồn API dùng để tách từ tiếng Lào, gióng hàng 2 văn bản tiếng Việt-Lào (và ngược lại)
# và gióng hàng câu giữa hai văn bản tiếng Việt-Lào (và ngược lại)
#mã nguồn được viết trên nền tảng Django
#để chạy mã nguồn hãy tạo một Django project, cài rest_framework, pickle, numpy sau đó đưa mã nguồn này vào file views.py và thiết lập đường dẫn trong urls.py để truy cập
from rest_framework.views import APIView
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
import pickle
import string
import numpy
import unicode_process
removepuncs = str.maketrans({key: ' ' for key in string.punctuation+'…“”'})

#load từ điển để tách từ
#dictvietnum: ánh xạ từ Việt thành số
#num2viet: ánh xạ số thành từ Việt
#dictlaonum: ánh xạ từ Lào thành số
#num2lao: ánh xạ số thành từ Lào
with open('dict-map-num.pickle','rb') as ff:
    dictvietnum,num2viet,dictlaonum,num2lao = pickle.load(ff)

#tạo danh sách từ Việt và Lào theo chiều dài giảm dần
lao_word_order = [x for x in dictlaonum]
lao_word_order.sort(key=lambda x:(-len(x.replace(' ','')),x))
viet_word_order = [x for x in dictvietnum]
viet_word_order.sort(key=lambda x:(-len(x.split(' ')),x))

def add_cors(response, request):
    if (request.method == "OPTIONS"  and "HTTP_ACCESS_CONTROL_REQUEST_METHOD" in request.META):
        response = http.HttpResponse()
        response["Content-Length"] = "0"
        response["Access-Control-Max-Age"] = 86400
    response["Access-Control-Allow-Origin"] = '*'
    response["Access-Control-Allow-Methods"] = "GET, OPTIONS, POST"
    response["Access-Control-Allow-Headers"] = "accept, accept-encoding, authorization, content-type, dnt, origin, user-agent, x-csrftoken, x-requested-with, token, accept-language, http-token"
    return response

class AlignApi(APIView):
    permission_classes = []
    #chuyển text thành số theo từ điển
    #text cần chuyển
    #word_order danh sách từ đã sort giảm dần theo chiều dài
    #dictnum từ điển ánh xạ từ thành số
    #islao là tiếng Lào hay không
    #trả về chuỗi các số
    def word2num(self, text, word_order, dictnum, islao):
        text = unicode_process.fix_text(text.lower().translate(removepuncs))
        for w in word_order:
            if len(w)<=1:
                continue
            if islao:
                text = text.replace(w," "+str(dictnum[w])+" ") #đổi từ thành số
            else:
                text = text.replace(" "+w+" "," "+str(dictnum[w])+" ") #đổi từ thành số
        return text
    #tách từ
    #text văn bản cần tách
    #word_order danh sách từ đã sort giảm dần theo chiều dài
    #trả về văn bản đã tách các từ cách nhau 1 khoảng trắng
    def wordseg(self, text, word_order):
        allidx = []
        for idx in range(len(word_order)):
            w = word_order[idx]
            if len(w)<=1:
                continue
            allidx.append(idx)
            text = text.replace(w, " __"+str(idx)+"__ ") #đổi từ thành số sau đó đổi ngược lại thành từ để tránh trường hợp từ ngắn nằm trong từ dài
        allidx.sort(key=lambda x:-x)
        for idx in allidx:
            text = text.replace(" __"+str(idx)+"__ "," " + word_order[idx] + " ")
        while '  ' in text:
            text = text.replace('  ', " ") #đổi từ thành số
        return text
    #chuyển văn bản Lào thành chuỗi số
    def lao2num(self, text):
        return self.word2num(text, lao_word_order, dictlaonum,islao=True)
    #chuyển văn bản Việt thành chuỗi số
    def viet2num(self, text):
        return self.word2num(text, viet_word_order, dictvietnum,islao=False)
    #tính điểm giữa hai văn bản
    #doc1 là văn bản nguồn đã chuyển thành dạng số
    #doc1 là văn bản đích đã chuyển thành dạng số
    #trả về điểm số khớp giữa hai tài liệu và danh sách gióng hàng các đoạn
    def calc_score(self, doc1, doc2):
        while '  ' in doc1:
            doc1 = doc1.replace('  ',' ')
        while '  ' in doc2:
            doc2 = doc2.replace('  ',' ')
        #tách đoạn, mỗi đoạn cách nhau 1 ký tự xuống dòng
        para1 = [x for x in doc1.split('\n') if x.strip()]
        para2 = [x for x in doc2.split('\n') if x.strip()]
        scored_para = {}
        for pv in range(len(para1)):
            #các đoạn lân cận cách đoạn đang xét không qua 3 đơn vị
            idxs = max(0, pv-3)
            idxe = min(len(para2),pv+4)
            vietpr = para1[pv].strip()
            if idxs>=idxe or len(vietpr.split(' '))<2: #có ít hơn 2 từ thì bỏ qua
                break
            #chuyển thành tập hợp các từ dạng số
            pvset = set(vietpr.split(' '))
            #xét các đoạn lào lân cận
            for pl in range(idxs,idxe):
                laopr = para2[pl].strip().split(' ')
                if len(laopr)<=2:
                    continue
                plset = set(laopr)
                #tính % giống nhau
                percent = len(pvset.intersection(plset))*2/(len(pvset)+len(plset))
                if len(pvset)!=len(plset) and percent>0:
                    percent = percent*.7 + .3/abs(len(pvset)-len(plset)) #cộng thêm hệ số chênh lệch độ dài
                #nếu đoạn trước điểm nhỏ hơn thì lấy đoạn này
                if pv not in scored_para or scored_para[pv][1]<percent:
                    scored_para[pv]=[pl, percent]
        totalsc = 0
        for pv in scored_para:
            totalsc += scored_para[pv][1]
        return {'score':totalsc/len(para1),'maps':scored_para} #% trùng bình trên 1 đoạn
    #tách câu của văn bản
    #trả về chuỗi theo qui tắc: các câu cách nhau 1 ký tự xuống dòng, các đoạn cách nhau 2 ký tự xuống dòng.
    def split_sents(self, text, debug=False):
        paras = [x.strip() for x in text.strip().split('\n')]
        content = []
        for pr in paras:
            prsents = []
            prs = pr
            start = 0
            punc = ['.','!','?']
            while prs:
                #tìm vị trí 3 dấu câu ở trên
                idxs = numpy.array([prs.find(punc[0],start),prs.find(punc[1],start),prs.find(punc[2],start)])
                idxs[idxs<0] = 1000000
                #lấy dấu có vị trí nhỏ nhất
                minidx = numpy.argmin(idxs)
                #nếu không tìm thấy dấu nào
                if idxs[minidx]==1000000:
                    prsents.append(prs)
                    break
                #nếu là dấu ở đầu câu thì bỏ đi
                if idxs[minidx]==0:
                    prs = prs[1:]
                    continue
                
                if minidx==0 and idxs[minidx]+1<len(prs): #là dấu chấm thì xét xem có phải là số không
                    if (prs[idxs[minidx]-1].isnumeric() and prs[idxs[minidx]+1].isnumeric()) or prs[idxs[minidx]-2:idxs[minidx]+1].lower()=="tp.": #là số vd: 2.3
                        start = idxs[minidx]+1
                        continue
                sent = prs[:idxs[minidx]+1].strip() #+1 để lấy dấu câu
                if sent.strip(string.punctuation+'…“” ').isnumeric(): #là dạng số thứ tự đứng đầu câu như "2. ..."
                    start = idxs[minidx]+1
                    continue
                prsents.append(sent)
                prs = prs[idxs[minidx]+1:].strip()
                start = 0
            if prsents:
                if debug:
                    for ss in prsents:
                        print('**> ',ss)
                    print('----')
                content.append("\n".join(prsents)) #mỗi câu 1 dòng
        content = "\n\n".join(content) #mỗi đoạn cách nhau 2 dòng
        return content
    #tính điểm giữa các câu
    #sentnumsource danh sách câu nguồn đã chuyển thành dạng số
    #sentnumtarget danh sách câu đích đã chuyển thành dạng số
    #trả về từ điển key là số thứ tự câu nguồn, value là mảng gồm số thứ tự câu nguồn và điểm số giữa 2 câu
    def calc_score_dict(self, sentnumsource, sentnumtarget):
        #mỗi dòng là 1 câu nguồn, mỗi cột là 1 câu đích
        mxscores = numpy.zeros((len(sentnumsource),len(sentnumtarget)))
        for r in range(len(sentnumsource)):
            if len(sentnumsource[r].strip())==0:
                continue
            sentscset = set([x for x in sentnumsource[r].split(' ') if x])
            for c in range(len(sentnumtarget)):
                if len(sentnumtarget[c].strip())==0:
                    continue
                senttgset = set([x for x in sentnumtarget[c].split(' ') if x])
                percent = len(sentscset.intersection(senttgset))*2/(len(sentscset)+len(senttgset))
                if len(sentscset)!=len(senttgset) and percent>0:
                    percent = percent*.7 + .3/abs(len(sentscset)-len(senttgset)) #cộng thêm hệ số chênh lệch độ dài
                            #nếu đoạn trước điểm nhỏ hơn thì lấy đoạn này
                mxscores[r][c] = percent
        #lấy argmax theo dòng 
        maxidxs = numpy.argmax(mxscores, axis=1)
        dtscores = {}
        for s in range(len(maxidxs)):
            score = mxscores[s][maxidxs[s]]
            if score>0:
                dtscores[s]=[maxidxs[s], score]
        return dtscores

    @csrf_exempt
    def post(self, request, pk=None):
        result={"isvalid":False,"msg":"Invalid access"}
        source = str(request.data.get('source','')).strip()
        typealign = request.data.get('type','')
        
        #là yêu cầu tách từ, chỉ xét tách từ tiếng Lào
        if pk=="wordseg":
            source = self.wordseg(source, lao_word_order)
            result={"isvalid":True, "text":source}
            return Response(result)
        target = str(request.data.get('target','')).strip()
        sort = request.data.get('sort','true')
        sort = sort=='true' or sort==True
        if typealign!='vl' and typealign!='lv':
            result={"isvalid":False, "msg":"type must be vl or lv"}
            return Response(result)
        if not source or not target:
            result={"isvalid":False, "msg":"Missing source or target document"}
            return Response(result)
        lao = source
        viet = target
        if typealign=='vl':
            viet = source
            lao = target
        #là gióng hàng câu
        if pk=="sentences": #tách câu trước khi đổi thành số
            lao = self.split_sents(lao)
            viet = self.split_sents(viet)
        #chuyển thành dạng số
        laonum = self.lao2num(lao)
        vietnum= self.viet2num(viet)
        #là gióng hàng văn bản, trả về điểm số giữa hai văn bản và kết quả gióng hàng các đoạn của 2 văn bản
        if pk=='document':
            if typealign=='lv':
                scores = self.calc_score(laonum, vietnum)
                para1 = [x for x in lao.split('\n') if x.strip()]
                para2 = [x for x in viet.split('\n') if x.strip()]
            else:
                scores = self.calc_score(vietnum, laonum)
                para1 = [x for x in viet.split('\n') if x.strip()]
                para2 = [x for x in lao.split('\n') if x.strip()]
            scores['isvalid'] = True
            maps = scores['maps']
            maps2 = []
            for p1 in maps:
                maps2.append({'source':para1[p1],'target':para2[maps[p1][0]],'score':maps[p1][1]})
            del scores['maps']
            if sort:
                maps2.sort(key=lambda x: -x['score'])
            scores['paragraphs']=maps2
            return Response(scores)
        #là gióng hàng câu, trả về danh sách câu kèm câu gióng hàng và điểm số của nó.
        if pk=="sentences":
            if typealign=='vl':
                senttxtsource = viet.replace('\n\n','\n').split('\n')
                senttxttarget = lao.replace('\n\n','\n').split('\n')
                sentnumsource = vietnum.replace('\n\n','\n').split('\n')
                sentnumtarget = laonum.replace('\n\n','\n').split('\n')
            else:
                senttxtsource = lao.replace('\n\n','\n').split('\n')
                senttxttarget = viet.replace('\n\n','\n').split('\n')
                sentnumsource = laonum.replace('\n\n','\n').split('\n')
                sentnumtarget = vietnum.replace('\n\n','\n').split('\n')
            sentscores = self.calc_score_dict(sentnumsource, sentnumtarget)
            paradictmap=[]
            for s in sentscores:
                tscore = sentscores[s] #stt câu target, điểm
                #lưu score gồm 3 thông tin: stt câu nguồn, stt câu đích, điểm
                #para gồm stt đoạn nguồn, stt đoạn đích
                paradictmap.append({'source':senttxtsource[s],'target':senttxttarget[tscore[0]],'score':tscore[1]})
            if sort:
                paradictmap.sort(key=lambda x: -x['score'])
            result={"isvalid":True,'sentences':paradictmap}
        # print(Response(result))
        return add_cors(Response(result),request)
        # return Response(result)
            
    def get(self, request, pk=None):
        pass
