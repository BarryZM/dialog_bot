#coding:utf-8
import json
import datetime
import re
import random
from goal_fill.goal_fill_predict import predict_goal


actors = {'范冰冰', '黄晓明', '谢娜', '吴亦凡', '王力宏', '黄渤', '林心如', '杨幂', '周迅', '成龙', '刘若英', '舒淇', '张学友', '张柏芝', '刘德华', '郭富城', '周杰伦', '张国荣', '林志颖', '何炅', '谢霆锋'}
dataset_bug_movies = {'新边缘人', '一起飞', '阿飞正传', '金鸡2', '亚飞与亚基', '倩女幽魂Ⅲ：道道道', '城市猎人', '地球四季', '中国合伙人', '笑傲江湖', '救火英雄', '旺角黑夜', '男人四十', '无问西东', '太平轮·彼岸', '男儿本色', '新警察故事', '十二夜', '逆战', '太平轮（上）', '消失的子弹', '李米的猜想', '证人', '亚飞与亚基', '叶问2：宗师传奇', '忘不了', '苏州河', '钟无艳', '暴疯语', '鸳鸯蝴蝶', '金鸡2', '白兰', '线人', '情迷大话王', '异灵灵异-2002', '喋血街头'}
fail_cnt = 0


def fail(data):
    global fail_cnt
    fail_cnt += 1

    goal = data['goal'].split('-->')
    goal = [j.strip() for j in goal]
    kg = data['knowledge']
    info = {
        'goal': goal,
        'kg': kg
    }
    bug_movie = set()
    for i in kg:
        if i[1] == '评论' and i[0] not in actors:
            bug_movie.add(i[0])
    for i in kg:
        if '主演' == i[1] and i[2] in bug_movie:
            bug_movie.remove(i[2])
    return predict_goal(data)


def fill_goal(i):
    """
        fill the blanks of goals in the test
        Input: a json record
        Output: a list of what's missing in i
    """
    goal = i['goal'].split('-->')
    goal = [j.strip() for j in goal]
    if "......" in goal:
        goal.remove("......")
    if goal[2].startswith('[3]再见'):  # goal is already complete
        return []

    # find entities
    kg = i['knowledge']
    accept_movies = i['user_profile']['接受的电影'] if '接受的电影' in i['user_profile'].keys() else {}
    accept_songs = i['user_profile']['接受的音乐']if '接受的音乐' in i['user_profile'].keys() else {}
    favorite_movies = i['user_profile']['喜欢的电影'] if '喜欢的电影' in i['user_profile'].keys() else {}
    favorite_songs = i['user_profile']['喜欢的音乐'] if '喜欢的音乐' in i['user_profile'].keys() else {}
    # accept_movies = [p.replace(" ","") for p in accept_movies]
    # accept_songs = [p.replace(" ","") for p in accept_songs]
    # favorite_movies = [p.replace(" ","") for p in favorite_movies]
    # favorite_songs = [p.replace(" ","") for p in favorite_songs]

    if 'history' in i.keys():
        conversation = i['history']
    else:
        conversation = i['conversation']
    songs = list()
    movies = list()
    movies0 = list()
    restaurant = list()
    like = list()
    birthday_person = ''
    singer = ''
    news_of = ''
    news = ''
    actor = ''
    actor0=''
    food = ''
    weather = ''
    address = i['user_profile']['居住地'] if "居住地" in i['user_profile'].keys() else ''
    for j in kg:
        entity, relation, info = j
        entity, relation, info = entity.replace(" ",""), relation.replace(" ",""), info.replace(" ","")
        if relation == '新闻':
            news_of, news = entity, info
        if relation == '演唱' and info not in goal[0].replace(" ","") and info not in accept_songs:
            if info not in songs:
                songs.append(info)
            singer = entity
        if relation == '生日':
            birthday_person = entity
        if relation == '主演' and entity in actors:  # avoid sth like ["星月童话", "主演", "张国荣   常盘贵子"]
            if actor == '' or entity == actor:
                if info not in movies and info not in goal[0].replace(" ",""):
                    if '电影推荐' not in goal[1]:# movie：亲爱的 song:亲爱的小孩
                        movies.append(info)
                    elif '电影推荐' in goal[1] and info not in goal[1].replace(" ",""):
                        movies.append(info)
                    actor = entity
            elif actor != '' and entity != actor and '电影推荐' not in goal[1]: # '电影推荐', '电影推荐'
                actor0 = actor
                movies0 = movies
                actor = ''
                movies = []   
        if relation in ['适合吃', '特色菜']:
            food = info
        if relation == '地址':
            restaurant.append(entity)
        if relation == '评论' and entity.replace(' ', '') in dataset_bug_movies and entity not in movies and entity not in songs and entity not in actors and entity not in goal[0].replace(" ","") and entity not in goal[1].replace(" ",""):  # dataset bug: no acting knowledge
            movies.append(entity)
        if entity == address:
            weather = info
        if relation == "喜欢":
            like.append(info)
        if relation == "喜欢的新闻":
            like.append([info,'最喜欢的新闻'])
        for idx,p in enumerate(like):
            if not isinstance(p,list):
                if relation == "演唱"  and p == info: 
                    like[idx] = [p, "最喜欢的歌曲"]
                # ["林心如", "主演", "大喜临门"]
                if relation == '主演' and entity in actors and p == info:# 问 User 最喜欢的电影 名 ？ ["孙芳倩", "喜欢", "大喜临门"]
                    like[idx] = [p, "最喜欢的电影"]
                if relation == '主演' and entity in actors and p == entity: # 问 User 最 喜欢   『 大喜临门 』   的 哪个 主演 ["孙芳倩", "喜欢", "林心如"] 
                    like[idx] = [p, "最喜欢的主演"]
    for idx,p in enumerate(like):
        if not isinstance(p,list):
            like[idx] = [p, "最喜欢的明星"]
    # if size of items is more than two, delete accepted item
    if len(movies) > 1:
        movies = [m for m in movies if (m not in accept_movies and m not in favorite_movies)]
    if len(songs) > 1:
        songs = [s for s in songs if (s not in accept_songs and s not in favorite_songs)]

    # goal sequence length is four
    if goal[2].startswith('[4]再见'):
        goal_fill = [[2, '']]
        if goal[1].startswith('[3]新闻推荐'):  
            if like != []:
                # (4):1 寒暄  2 提问  3 新闻推荐
                goal_fill = [[2, '提问', '最喜欢的新闻']]
            else:
                # ['问日期'/'问答', '关于明星的聊天', '新闻推荐', '再见']
                celebrity = re.findall('『[^』]*』', goal[1])[0][1:-1].replace(" ","")
                goal_fill = [[2, '关于明星的聊天', celebrity]]
        elif goal[1].startswith('[3]兴趣点推荐'):  # (6):1 问天气  2 美食推荐  3 兴趣点推荐
            goal_fill = [[2, '美食推荐', food]]
        elif goal[1].startswith('[3]电影推荐'):  # (12):1 问答  2 关于明星的聊天  3 电影推荐  or (13):1 问日期  2 关于明星的聊天  3 电影推荐
            if goal[0].startswith('[1]问答'):
                celebrity = re.findall('『[^』]*』', goal[0])[1][1:-1]
            else:
                celebrity = birthday_person
            goal_fill = [[2, '关于明星的聊天', celebrity]]

            if celebrity == '' or celebrity == None:
                if actor0 != '' and len(movies0) != 0:
                    # ['寒暄', '电影推荐', '电影推荐', '再见']
                    goal_fill = [[2, '电影推荐', movies0]]
                else:
                    goal_fill = fail(i)

        elif goal[1].startswith('[3]播放音乐'):  # (22):1 音乐点播/问天气/寒暄  2 音乐推荐  3 播放音乐
            play_song = re.findall('『[^』]*』', goal[1])[0][1:-1].replace(" ","")
            songs.remove(play_song)
            songs = songs + [play_song]
            goal_fill = [[2, '音乐推荐', songs]]
            if len(songs) == 0:
                goal_fill = fail(i)
        elif goal[1].startswith('[3]美食推荐'):
            # ['寒暄'/问时间, '天气信息推送', '美食推送', '再见']
            goal_fill = [[2, "天气信息推送"]]
        else:
            goal_fill = fail(i)

        return goal_fill

    # goal sequence is five
    elif goal[2].startswith('[5]再见'):
        if goal[1].startswith('[4]新闻推荐'):
            celebrity = re.findall('『[^』]*』', goal[1])[0][1:-1].replace(" ","")

            if celebrity == '' or celebrity == None:
                goal_fill = fail(i)

            if len(songs) > 0:  # #(3):1 寒暄/问天气/音乐点播  2 音乐推荐  3 关于明星的聊天  4 新闻推荐
                goal_fill = [[2, '音乐推荐', songs], [3, '关于明星的聊天', celebrity]]

            elif len(movies) > 0:   # (24):1 寒暄  2 电影推荐  3 关于明星的聊天  4 新闻推荐
                goal_fill = [[2, '电影推荐', movies], [3, '关于明星的聊天', celebrity]]
            elif like != []:
                # ['寒暄', '提问', '关于明星的聊天', '新闻推荐', '再见']
                goal_fill = [[2, '提问', like[0][1]], [3, '关于明星的聊天', celebrity]]
            else:    
                goal_fill = fail(i)

        elif goal[1].startswith('[4]电影推荐'):
            if goal[0].startswith('[1]问答'):  # (9):1 问答  2 关于明星的聊天  3 电影推荐  4 电影推荐
                celebrity = re.findall('『[^』]*』', goal[0])[1][1:-1]
                goal_fill = [[2, '关于明星的聊天', celebrity], [3, '电影推荐', movies]]
            elif goal[0].startswith('[1]问日期'):  # (10):1 问日期  2 关于明星的聊天  3 电影推荐  4 电影推荐
                goal_fill = [[2, '关于明星的聊天', birthday_person], [3, '电影推荐', movies]]

                if birthday_person == '' or birthday_person == None or len(movies) == 0:
                    goal_fill = fail(i)
            elif goal[0].startswith('[1]寒暄'):  # (11):1 寒暄  2 音乐推荐  3 关于明星的聊天  4 电影推荐
                if len(songs) > 0:
                    goal_fill = [[2, '音乐推荐', songs], [3, '关于明星的聊天', singer]]

                    if singer == '' or singer == None:
                        goal_fill = fail(i)

                elif news != '' and news_of != '':  # (25):1 寒暄  2 新闻推荐  3 关于明星的聊天  4 电影推荐
                    goal_fill = [[2, '新闻推荐', news_of, news], [3, '关于明星的聊天', actor]]
                    # print(goal_fill)

                    if actor == '' or actor == None:
                        goal_fill = fail(i)

                elif like != []: # ['寒暄', '提问', '关于明星的聊天', '电影推荐', '再见']
                    goal_fill = [[2, '提问', like[0][1]], [3, '关于明星的聊天', actor]]
                    if actor == '' or actor == None:
                        goal_fill = fail(i)
                else:
                    goal_fill = fail(i)

            elif goal[0].startswith('[1]新闻点播'):
                # ['新闻点播', '新闻推荐', '关于明星的聊天', '电影推荐', '再见']
                goal_fill = [[2, '新闻推荐', news_of, news], [3, '关于明星的聊天', news_of], [4, '电影推荐', movies]]

                if news_of == '' or news_of == None or news == '' or news == None or len(movies) == 0:
                    goal_fill = fail(i)

            elif goal[0].startswith('[1]问天气') or goal[0].startswith('[1]音乐点播'):
                if len(songs) > 0:
                    # ['音乐点播'/问天气, '音乐推荐', '关于明星的聊天', '电影推荐', '再见']
                    goal_fill = [[2, '音乐推荐', songs], [3, '关于明星的聊天', singer]]

                if singer == '' or singer == None:
                    goal_fill = fail(i)
            else:
                goal_fill = fail(i)

        elif goal[1].startswith('[4]播放音乐'):  
            play_song = re.findall('『[^』]*』', goal[1])[0][1:-1].replace(" ","")
            songs.remove(play_song)
            songs = songs + [play_song]
            if goal[0].startswith('[1]问答') or goal[0].startswith('[1]问日期'):# (19):1 问答  2 关于明星的聊天  3 音乐推荐  4 播放音乐  (20):1 问日期  2 关于明星的聊天  3 音乐推荐  4 播放音乐
                goal_fill = [[2, '关于明星的聊天', singer], [3, '音乐推荐', songs]]

                if singer == '' or singer == None or len(songs) == 0:
                    goal_fill = fail(i)

            elif goal[0].startswith('[1]寒暄') or goal[0].startswith('[1]问时间'): # ['寒暄'/问时间, '天气信息推送', '音乐推荐', '播放音乐', '再见']
                goal_fill = [[2, '天气信息推送'], [3, '音乐推荐', songs]]

                if len(songs) == 0:
                    goal_fill = fail(i)

            else:
                goal_fill = fail(i)

        elif goal[1].startswith('[4]兴趣点推荐'):  # ['寒暄'/问时间, '天气信息推送', '美食推送', 'POI推荐', '再见']
            goal_fill = [[2, '天气信息推送'], [3, '美食推荐', food]]
        else:
            goal_fill = fail(i)
        try:
            return goal_fill
        except:
            print()

    # goal sequence is six
    elif goal[2].startswith('[6]再见'):
        if goal[1].startswith('[5]问User爱好'):  #(14):1 寒暄  2 问User姓名  3 问User性别  4 问User年龄  5 问 User 爱好
            goal_fill = [[2, '问User姓名'],  [3, '问User性别'],  [4, '问User年龄']]
        elif goal[1].startswith('[5]电影推荐'):
            if len(like) == 0 and news_of != '' and news!= '' or goal[0].startswith('[1]新闻点播'):
                # (7):1 寒暄/新闻点播  2 新闻推荐  3 关于明星的聊天  4 电影推荐  5 电影推荐
                goal_fill = [[2, '新闻推荐', news_of, news], [3, '关于明星的聊天', news_of], [4, '电影推荐', movies]]

                if news_of == '' or news_of == None or news == '' or news == None or len(movies) == 0:
                    goal_fill = fail(i)
            elif len(like) > 1:
                # (8):1 寒暄  2 提问  3 提问  4 关于明星的聊天  5 电影推荐
                goal_fill = [[2, '提问', '最喜欢的电影'], [3, '提问', '最喜欢的主演'], [4, '关于明星的聊天', actor]]

                if actor == '' or actor == None:
                    goal_fill = fail(i)
            elif weather != '':
                # ['问时间'/寒暄, '天气信息推送', '音乐推荐', '关于明星的聊天', '电影推荐', '再见']
                goal_fill = [[2, '天气信息推送'], [3, '音乐推荐', songs], [4, '关于明星的聊天', singer]]
                if singer == '' or singer == None or len(movies) == 0 or len(songs) == 0:
                    goal_fill = fail(i)
            elif goal[0].startswith('[1]寒暄') and len(like) > 0:
                if news == '' or news_of == '':
                    # ['寒暄', '提问', '关于明星的聊天', '电影推荐', '电影推荐', '再见']
                    goal_fill = [[2, '提问', like[0][1]], [3, '关于明星的聊天', actor], [4, '电影推荐', movies]]

                    if actor == '' or actor == None or len(movies) == 0:
                        goal_fill = fail(i)
                else:
                    # ['寒暄', '提问', '新闻推荐', '关于明星的聊天', '电影推荐', '再见']
                    goal_fill = [[2, '提问', like[0][1]], [3, '新闻推荐', news_of, news], [4, '关于明星的聊天', actor]]

                    if actor == '' or actor == None or len(movies) == 0:
                        goal_fill = fail(i)

            elif len(songs) > 0:
                # ['寒暄'/问天气/音乐点播, '音乐推荐', '关于明星的聊天', '电影推荐', '电影推荐', '再见']
                goal_fill = [[2, '音乐推荐', songs], [3, '关于明星的聊天', actor], [4, '电影推荐', movies]]

                if actor == '' or actor == None or len(movies) == 0:
                    goal_fill = fail(i)
            else:
                goal_fill = fail(i)

        elif goal[1].startswith('[5]播放音乐'): 
            play_song = re.findall('『[^』]*』', goal[1])[0][1:-1].replace(" ","")
            songs.remove(play_song)
            songs = songs + [play_song]
            if goal[0].startswith('[1]问日期') or goal[0].startswith('[1]问答'):
                if goal[0].startswith('[1]问日期'):  # (16):1 问日期  2 关于明星的聊天  3 电影推荐  4 音乐推荐  5 播放音乐
                    celebrity = birthday_person
                else:  # (15):1 问答  2 关于明星的聊天  3 电影推荐  4 音乐推荐  5 播放音乐
                    celebrity = re.findall('『[^』]*』', goal[0])[1][1:-1]
                goal_fill = [[2, '关于明星的聊天', celebrity], [3, '电影推荐', movies], [4, '音乐推荐', songs]]

                if celebrity == '' or celebrity == None or len(movies) == 0 or len(songs) == 0:
                    goal_fill = fail(i)
            elif len(movies) != 0:  # (18):1 寒暄  2 电影推荐  3 关于明星的聊天  4 音乐推荐  5 播放音乐
                goal_fill = [[2, '电影推荐', movies], [3, '关于明星的聊天', actor], [4, '音乐推荐', songs]]

                if len(movies) == 0 or actor == '' or actor == None or len(songs) == 0:
                    goal_fill = fail(i)
            elif len(like) > 0:  # (17):1 寒暄  2 提问  3 关于明星的聊天  4 音乐推荐  5 播放音乐
                goal_fill = [[2, '提问', '最喜欢的歌曲'], [3, '关于明星的聊天', singer], [4, '音乐推荐', songs]]

                if singer == '' or singer == None or len(songs) == 0:
                    goal_fill = fail(i)
            elif news != '' and news_of != '':
                # ['寒暄'/新闻点播, '新闻推荐', '关于明星的聊天', '音乐推荐', '播放音乐', '再见']
                goal_fill = [[2, '新闻推荐', news_of, news], [3, '关于明星的聊天', news_of], [4, '音乐推荐', songs]]
                if len(songs) == 0:
                        goal_fill = fail(i)
            elif actor0 != '' and len(movies0) != 0:
                # ['寒暄', '电影推荐', '电影推荐', '音乐推荐', '播放音乐', '再见']
                goal_fill = [[2, '电影推荐', movies0], [3, '电影推荐', movies], [4, '音乐推荐', songs]]
                if len(songs) == 0 or len(movies) == 0:
                        goal_fill = fail(i)
            else:
                goal_fill = fail(i)
        elif goal[1].startswith('[5]新闻推荐'):
            if weather != '':
                # ['问时间'/寒暄, '天气信息推送', '音乐推荐', '关于明星的聊天', '新闻推荐', '再见']
                goal_fill = [[2, '天气信息推送'], [3, '音乐推荐', songs], [4, '关于明星的聊天', singer]]
                if singer == '' or singer == None or len(movies) == 0 or len(songs) == 0:
                    goal_fill = fail(i)
            elif len(like) > 1:
                # ['寒暄', '提问', '提问', '关于明星的聊天', '新闻推荐', '再见']
                goal_fill = [[2, '提问', like[0][1]], [3, '提问', like[1][1]], [4, '关于明星的聊天', like[1][0]]]
            elif actor0 != '' and len(movies0) != 0:
                # ['寒暄', '电影推荐', '电影推荐', '关于明星的聊天', '新闻推荐', '再见']
                goal_fill = [[2, '电影推荐', movies0], [3, '电影推荐', movies], [4, '关于明星的聊天', actor]]
                if len(songs) == 0 or len(movies) == 0 or actor == '':
                        goal_fill = fail(i)
            else:
                goal_fill = fail(i)
        else:
            goal_fill = fail(i)
        return goal_fill

    elif goal[2].startswith("[7]再见"):
        if goal[1].startswith('[6]播放音乐'):
            play_song = re.findall('『[^』]*』', goal[1])[0][1:-1].replace(" ","")
            songs.remove(play_song)
            songs = songs + [play_song]
            if goal[0].startswith('[1]新闻点播'):
                # ['新闻点播', '新闻推荐', '关于明星的聊天', '电影推荐', '音乐推荐', '播放音乐', '再见']
                goal_fill = [[2, '新闻推荐', news_of, news], [3, '关于明星的聊天', actor], [4, '电影推荐', movies], [5, '音乐推荐', songs]]
                if actor == '' or actor == None or len(movies) == 0 or len(songs) == 0:
                    goal_fill = fail(i)
            elif news != '' and news_of != '' and len(like) == 0:
                # ['寒暄', '新闻推荐', '关于明星的聊天', '电影推荐', '音乐推荐', '播放音乐', '再见']
                goal_fill = [[2, '新闻推荐', news_of, news], [3, '关于明星的聊天', actor], [4, '电影推荐', movies], [5, '音乐推荐', songs]]

                if actor == '' or actor == None or len(movies) == 0 or len(songs) == 0:
                    goal_fill = fail(i)
            elif news != '' and news_of != '' and len(like) > 0:
                # ['寒暄', '提问', '新闻推荐', '关于明星的聊天', '音乐推荐', '播放音乐', '再见']
                goal_fill = [[2, '提问', like[0][1]], [3, '新闻推荐', news_of, news], [4, '关于明星的聊天', singer], [5, '音乐推荐', songs]]

                if singer == '' or singer == None or len(movies) == 0 or len(songs) == 0:
                    goal_fill = fail(i)
            elif len(like) > 0 and len(movies) > 0:
                # ['寒暄', '提问', '关于明星的聊天', '电影推荐', '音乐推荐', '播放音乐', '再见']
                goal_fill = [[2, '提问', like[0][1]], [3, '关于明星的聊天', actor], [4, '电影推荐', movies], [5, '音乐推荐', songs]]

                if actor == '' or actor == None or len(movies) == 0 or len(songs) == 0:
                    goal_fill = fail(i)
            elif len(like) > 1:
                # ['寒暄', '提问', '提问', '关于明星的聊天', '音乐推荐', '播放音乐', '再见']
                goal_fill = [[2, '提问', like[0][1]], [3, '提问', like[1][1]], [4, '关于明星的聊天', singer], [5, '音乐推荐', songs]]

                if singer == '' or singer == None or len(songs) == 0:
                    goal_fill = fail(i)
            elif actor0 != 0 and len(movies0) != 0:
                # ['寒暄', '电影推荐', '电影推荐', '关于明星的聊天', '音乐推荐', '播放音乐', '再见']
                goal_fill = [[2, '电影推荐', movies0], [3, '电影推荐', movies], [4, '关于明星的聊天', singer], [5, '音乐推荐', songs]]

                if singer == '' or singer == None or len(songs) == 0 or len(movies) == 0:
                    goal_fill = fail(i)
            else:
                goal_fill = fail(i)

        elif goal[1].startswith('[6]新闻推荐'):
            # ['寒暄', '电影推荐', '电影推荐', '音乐推荐', '关于明星的聊天', '新闻推荐', '再见']
            if actor0 != 0 and len(movies0) != 0:
                goal_fill = [[2, '电影推荐', movies0], [3, '电影推荐', movies], [4, '音乐推荐', songs], [5, '关于明星的聊天', singer]]

                if singer == '' or singer == None or len(songs) == 0 or len(movies) == 0:
                    goal_fill = fail(i)
        elif goal[1].startswith('[6]电影推荐'):
            if weather != '' and weather != None:
                # ['寒暄'/问时间, '天气信息推送', '音乐推荐', '关于明星的聊天', '电影推荐', '电影推荐', '再见']
                goal_fill = [[2, '天气信息推送'], [3, '音乐推荐', songs], [4, '关于明星的聊天', singer], [5, '电影推荐', movies]]
                if singer == '' or singer == None or len(movies) == 0 or len(songs) == 0:
                    goal_fill = fail(i)
            elif len(like) > 0 and news != '' and news_of != '':
                # ['寒暄', '提问', '新闻推荐', '关于明星的聊天', '电影推荐', '电影推荐', '再见']
                goal_fill = [[2, '提问', '最喜欢的新闻'], [3, '新闻推荐', news_of, news], [4, '关于明星的聊天', actor], [5, '电影推荐', movies]]

                if actor == '' or actor == None or len(movies) == 0:
                    goal_fill = fail(i)
            elif len(like) > 1:
                # ['寒暄', '提问', '提问', '关于明星的聊天', '电影推荐', '电影推荐', '再见']
                goal_fill = [[2, '提问', like[0][1]], [2, '提问', like[1][1]], [4, '关于明星的聊天', actor], [5, '电影推荐', movies]]

                if singer == '' or singer == None or actor == '' or actor == None or len(movies) == 0:
                    goal_fill = fail(i)
            else:
                goal_fill = fail(i)
        else:
            goal_fill = fail(i)
        return goal_fill

    elif goal[2].startswith("[8]再见"):
        play_song = re.findall('『[^』]*』', goal[1])[0][1:-1].replace(" ","")
        songs.remove(play_song)
        songs = songs + [play_song]
        if news != '' and news_of != '':
            # ['寒暄', '提问', '新闻推荐', '关于明星的聊天', '电影推荐', '音乐推荐', '播放音乐', '再见']
            goal_fill = [[2, '提问', '最喜欢的新闻'], [3, '新闻推荐', news_of, news], [4, '关于明星的聊天', actor], [5, '电影推荐', movies], [6, '音乐推荐', songs]]

            if actor == '' or actor == None or len(movies) == 0 or len(songs) == 0:
                goal_fill = goal(i)
        elif len(like) > 1:
            # ['寒暄', '提问', '提问', '关于明星的聊天', '电影推荐', '音乐推荐', '播放音乐', '再见']   
            goal_fill = [[2, '提问', like[0][1]], [2, '提问', like[1][1]], [4, '关于明星的聊天', actor], [5, '电影推荐', movies], [6, '音乐推荐', songs]]

            if singer == '' or singer == None or actor == '' or actor == None or len(movies) == 0 or len(songs) == 0:
                goal_fill = fail(i)
        else:
            goal_fill = fail(i)
        return goal_fill

    else:
        goal_fill = fail(i)
        return goal_fill

def action_space(input_action):
    if input_action == '音乐推荐':
        input_action = '音乐推荐'
    if input_action == '美食推荐':
        input_action = '美食推荐'
    if input_action == '兴趣点推荐':
        input_action = '兴趣点推荐'
    if input_action == '电影推荐':
        input_action = '电影推荐'    
    if input_action == '播放音乐':
        input_action = '播放音乐'  
    if input_action == '音乐点播':
        input_action = '音乐点播' 
    if input_action == '问时间':
        input_action = '问时间' 
    if input_action == '问日期':
        input_action = '问日期'    
    if input_action == '天气信息推送':
        input_action = '天气信息推送'  
    if input_action == '问天气':
        input_action = '问天气'     
    if input_action == '关于明星的聊天':
        input_action = '关于明星的聊天' 
    return input_action


def extract_info_from_goal(goal):
    no = int(re.findall('\[([1-9])\]', goal)[0])
    if ']再见' in goal or ']再见' in goal:
        return [no, '再见']
    action = re.findall(']\s*([^(]*?)\s*\(', goal)[0]
    # action = action_space(action)
    sth = re.findall('『[^』]*』', goal)
    sth = [s[1:-1].replace(" ","") for s in sth]
    if action == '问答':
        return [no, action, sth[0], sth[1]]
    if action == '提问':
        if '最喜欢谁的新闻' in goal:
            aspect = '最喜欢的新闻'
        elif '最喜欢的歌曲' in goal:
            aspect = '最喜欢的歌曲'
        elif '的哪个主演' in goal and '最喜欢' in goal:
            aspect = '最喜欢的主演'
        elif '最喜欢的电影' in goal:
            aspect = '最喜欢的电影'
        else:
            print(goal)
        return [no, action, aspect]
    if action == '兴趣点推荐':
        return [no, action, sth[0]]
    if action in ['新闻点播', '新闻推荐']:
        # if len(sth) < 2:
            # print(data_cnt)
        # print(goal)
        return [no, action, sth[0], sth[1]]
    if action in ['电影推荐', '音乐推荐']:
        movies = [sth[0]]
        if '；' in goal:
            movies.append(sth[3])
        return [no, action, movies]
    if action in ['播放音乐', '音乐点播']:
        return [no, action, sth[0]]
    if action == '关于明星的聊天':
        if sth[0] in actors:
            return [no, action, sth[0]]
        else:
            return [no, action, sth[1]]  # [3] 关于明星的聊天 ( Bot 主动 ， Bot 主动 从   『 嫁个100分男人 』   聊到 他 的 主演   『 谢娜 』
    if action == '美食推荐':
        return [no, action, sth[0]]
    return [no, action]


def fill_test(i):

    goals_fill = fill_goal(i)
    goals = i['goal']
    goals_info = [extract_info_from_goal(j) for j in goals.split('-->') if "......" not in j]
    if goals_fill == None:
        return goals_info
    else:
        goals_info_complete = [goals_info[0]] + goals_fill + goals_info[1:]
        return goals_info_complete



if __name__ == '__main__':
    data_cnt = 0
    with open('test_2.txt', 'r', encoding='utf-8') as f:
        x = f.readlines()

    f = open('./goal_fill/test_2_goal_fill.txt', 'w', encoding='utf-8')
    # debug = open('./goal_fill/test_2_goal_fill_debug.txt', 'w', encoding='utf-8')
    for line in x:
        data_cnt += 1
        data = json.loads(line)
        print(str(fill_test(data)).replace(" ",""), file=f)
    print('fail_cnt:', fail_cnt)