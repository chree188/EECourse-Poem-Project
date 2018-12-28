# coding:utf-8
from elasticsearch import Elasticsearch
import utils


es = Elasticsearch(['localhost:9200'])
# analyzer = "ik_smart"

def __get_item(d, k):
    if k not in d.keys() or d[k] is None:
        return ''
    else:
        return d[k]

def common_query(input_dict, cur_page=1):
    # vm_env.attachCurrentThread()
    if input_dict['searchType'] == "ancient":
        return ancient_search(input_dict, cur_page)
    elif input_dict['searchType'] == "modern":
        return cnmodern_search(input_dict, cur_page)
    elif input_dict['searchType'] == "all":
        return mixed_search(input_dict, cur_page)
    else:
        raise ValueError("Undefined Search Type")


def process_query_results(res_tmp, truncated=True):
    res = []
    # print (res_tmp[0])
    for tmp in res_tmp:
        tmp = tmp['_source']
        if tmp['imgurl'] is None or tmp['imgurl'] == '':
            tmp['imgurl'] = '/static/image/1.jpg'
        if truncated and len(tmp['text']) > utils.DISPLAY_UTILS['card_max_text']:
            tmp['text'] = tmp['text'][:utils.DISPLAY_UTILS['card_max_text']] + '...'
        if tmp['label'] is None:
            tmp['label'] = ''
        entry = {
            'imgurl': tmp['imgurl'],
            'title': tmp['title'],
            'content': tmp['text'],
            'poet': tmp['author'],
            'poemurl': '#',
            'poeturl': '/authorpage?author='+tmp['author'],
            # 'labels': [],
            'labels': [
                {
                    'label': label,
                    'labelurl': '#',
                }
                for label in tmp['label'].split()],
            'likes': 0,
        }
        res.append(entry)
    return res


def process_author_results(res_tmp, truncated=True):
    res = []
    # print (res_tmp[0])
    for tmp in res_tmp:
        tmp = tmp['_source']
        if truncated and len(tmp['desc']) > utils.DISPLAY_UTILS['card_max_text']:
            tmp['desc'] = tmp['desc'][:utils.DISPLAY_UTILS['card_max_text']] + '...'
        entry = {
            'desc': tmp['desc'],
            'name': tmp['name'],
            'poeturl': '/authorpage?author='+tmp['name'],
        }
        res.append(entry)
    return res

# querys = BooleanQuery()
#         for key, value in command_dict.items():
#             if key not in ['author', 'title', 'label', 'content']:
#                 continue
#             query = QueryParser(Version.LUCENE_CURRENT, key, self.Analyzer).parse(utils.jieba_seg(value[0]))
#             if value[1]:
#                 querys.add(query, BooleanClause.Occur.MUST)
#             else:
#                 querys.add(query, BooleanClause.Occur.SHOULD)
#         totalDocs = self.chSearcher.search(querys, utils.MAX_RESULTS).scoreDocs

def cnmodern_search(input_dict, cur_page=1, pp=utils.PAGI_SETTING['result_per_page'], truncated=True):
    search_body = {'query': {
        'bool': {
            'must': [],
            'should': [],
        },
    }}
    for key, value in input_dict.items():
        if key not in ['author', 'title_tokenized', 'label_tokenized', 'text_tokenized']:
                continue
        if 'tokenized' in key:
            match = {
                'match': {
                    key: {
                        'query': value[0],
                    }
                },
            }
        else:
            match = {
                'match': {
                    key: value[0]
                }
            }
        search_body['query']['bool'][{True: 'must', False: 'should'}[value[1]]].append(match)
    # matches, res_tmp = MPS.ch_seach(input_dict, target_range=((cur_page-1)*pp, cur_page*pp))
    try:
        matches = es.count(index='cnmodern', doc_type='cnmodern_type', body=search_body)['count']
        search_body['from'] = (cur_page - 1) * pp
        search_body['size'] = pp
        res_tmp = es.search(index='cnmodern', doc_type='cnmodern_type', body=search_body)['hits']['hits']
    except Exception as e:
        print(e)
        return 0, []
    res = process_query_results(res_tmp, truncated)
    return matches, res


def ancient_search(input_dict, cur_page=1, pp=utils.PAGI_SETTING['result_per_page'], truncated=True):
    search_body = {'query': {
        'bool': {
            'must': [],
            'should': [],
        },
    }}
    for key, value in input_dict.items():
        if key not in ['author', 'dynasty', 'label_tokenized', 'title_tokenized', 'text_tokenized']:
            continue
        if 'tokenized' in key:
            match = {
                'match': {
                    key: {
                        'query': value[0],
                    }
                },
            }
        else:
            match = {
                'match': {
                    key: value[0]
                }
            }
        search_body['query']['bool'][{True: 'must', False: 'should'}[value[1]]].append(match)
        print(match)
    try:
        matches = es.count(index='gushiwen', doc_type='gushiwen_type', body=search_body)['count']
        search_body['from'] = (cur_page - 1) * pp
        search_body['size'] = pp
        res_tmp = es.search(index='gushiwen', doc_type='gushiwen_type', body=search_body)['hits']['hits']
    except Exception as e:
        print(e)
        return 0, []
    # matches, res_tmp = APS.gushiwen_search(input_dict, target_range=((cur_page - 1) * pp, cur_page * pp))
    # print matches, res_tmp
    res = process_query_results(res_tmp, truncated)
    return matches, res


def mixed_search(input_dict, cur_page=1, pp=utils.PAGI_SETTING['result_per_page'], truncated=True):
    matches_modern, res_modern = cnmodern_search(input_dict, cur_page, pp//2, truncated)
    matches_ancient, res_ancient = ancient_search(input_dict, cur_page, pp//2, truncated)
    res = utils.alternating(res_modern, res_ancient)
    matches = matches_modern + matches_ancient
    return matches, res


def get_author(author_name, index='cnmodern', cur_page=1, pp=utils.PAGI_SETTING['result_per_page'], truncated=True):
    search_body = {'query': {
        'match_phrase': {
            'author': author_name,
        }
    }}
    try:
        matches = es.count(index=index, doc_type=index+'_type', body=search_body)['count']
        search_body['from'] = (cur_page - 1) * pp
        search_body['size'] = pp
        res_tmp = es.search(index=index, doc_type=index+'_type', body=search_body)['hits']['hits']
    except Exception as e:
        print(e)
        return 0, []
    res = process_query_results(res_tmp, truncated)
    return matches, res


def search_author(input_dict=None, cur_page=1, pp=utils.PAGI_SETTING['result_per_page'], truncated=True):
    if input_dict is None:
        search_body = {'query': {
            'match_all': {}
        }}
    else:
        return 0, []
    try:
        matches = es.count(index='author', doc_type='author_type', body=search_body)['count']
        search_body['from'] = (cur_page - 1) * pp
        search_body['size'] = pp
        res_tmp = es.search(index='author', doc_type='author_type', body=search_body)['hits']['hits']
    except Exception as e:
        print(e)
        return 0, []
    res = process_author_results(res_tmp, truncated)
    return matches, res
