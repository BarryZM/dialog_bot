import json
import datetime
import re
import random
import goal_filling
import sacrebleu
import copy



eq_relations = {
    '星座': [],
    '血型': [],
    '属相': ['属 啥', '属 什么', ],
    '成就': [],
    '主演': ['谁 演 的'],
    '类型': ['什么 歌'],
    '评论': [],  # ['唱 的 咋样', '评价', '好听 吗'],
    '导演': ['谁 导 的'],
    '简介': ['介绍', '信息'],
    '演唱': ['谁 唱 的', '主唱', '谁 的 歌'],
    '身高': ['多高', '多 高'],
    '体重': ['多重'],
    '获奖': ['哪些 奖', '什么 成就'],
    '口碑': [],
    '生日': ['什么 时候 出生', '哪 年 出生', '哪年 出生', '哪一年 出生', '的 出生 ', '出生日期', '多会 出生', '生日 是 多会'],
    '出生地': ['哪里 的 人', '哪儿 的 人', '哪里 出生', '在 哪 出生', '哪儿 出生', '哪 的', '哪里 的 籍贯', '哪里 人', '出生 地区', '出生 在 哪里'],
    '国家地区': ['国家 地区', '哪个 国家'],
    '人均价格': ['人均 价格', '消费 怎么样', '人均 消费', '平均价格'],
    '地址': ['在 哪', '具体位置', '什么 地方'],
    '评分': ['多少 分'],
    '特色菜': [],
    '日期': [],  # '问 日期' in goal[0]
    '时间': [],  # '问 时间' in goal[0]
    '新闻': ['故事'],
    '天气': []
}
difficult_info_mask = {'身高': 'height', '体重': 'weight', '评分': 'rating', '地址': 'address', '人均价格': 'expense', '导演': 'director'}


def validate(date_text):
    try:
        datetime.datetime.strptime(date_text, '%Y-%m-%d')
        return True
    except ValueError:
        return False


def check_relation(rel, qa):
    possible_rel = (eq_relations[rel] if rel in eq_relations.keys() else []) + [rel]
    for r in possible_rel:
        if r in qa:
            return True
    return False


def cal_score(triple, qa):
    score = 1 if triple[0] in qa else 0
    score += 1 if triple[1] in qa else 0
    if triple[2] in qa:
        score += 2
    else:
        common_words = [word for word in triple[3] if (word in qa and word not in ['', ' '])]
        if len(common_words) / len(triple[3]) > 0.4 or (len(common_words) > 0 and triple[1] in ['评论', '出生地']):
            score += 2

    return score


def remove_marks(x):
    return x.replace('( Live )', '').replace(' ', '').replace('（', '').replace('）', '')



def ks_in_kg(ks=None, kg=None, conversation=None):
    ks = copy.deepcopy(ks)
    for k in kg:
        strk = str(k)
        if strk in ks:
            if k[1] not in ['成就', '获奖', '评价', '简介'] or strk in conversation:
                return False
            ks.remove(strk)
    return len(ks) == 0


random.seed()
src = open('test_with_knowledge.src', 'w')
with open('test_1.json', 'r') as f:
    x = f.readlines()

# with open('test_2_goal_fill.txt', 'r') as f:
    # goals_info = f.readlines()
    # goals_info = [eval(g) for g in goals_info]
goals_info = []

with open('dialog_comment_recommends_merge.txt', 'r') as f:
    comment_recommends = f.readline()
    comment_recommends = eval(comment_recommends)
    select_comments_dict = comment_recommends.keys()

with open('dialog_celebrity_chat_merged.txt', 'r') as f:
    celebrity_chat = f.readline()
    celebrity_chat = eval(celebrity_chat)


num = -1
weather_dict = dict()
recommend_round = dict()
mask_info = dict()
entity_dicts = []
news_dict = dict()
questions = []
multi_actors_answers = dict()
chat_round = dict()
for i in x:
    num += 1
    # i = i.replace(' ', '')
    i = json.loads(i)
    goal_origin = i['goal'].split('-->')

    if len(i['history']) == 0:
        hello_info = ['寒暄', i['situation']]
        if '带 User 名字' in goal_origin[0]:
            hello_info.append('name')
            hello_info.append(i['user_profile']['性别'])
            if '年龄区间' in str(i['user_profile']):
                hello_info.append(i['user_profile']['年龄区间'])
        print(*hello_info, file=src, end='')
        print('φ', file=src)
        entity_dicts.append({i['user_profile']['姓名']: 'name'})
        questions.append('')
        # goals_info.append(goal_filling.fill_test(i))
        continue
    

    # fill goal
    goal = goal_filling.fill_test(i)
    goals_info.append(goal)

    # find replace entity
    entity_cnt = 0
    entity_dict = dict()
    recommend_entity = ''
    for g in goal:
        if len(g) < 2:
            continue
        action = g[1]
        if action == '兴趣点 推荐':
            entity_dict[g[2]] = 'restaurant_' + str(entity_cnt)
            entity_cnt += 1
            continue
        if action in ['电影 推荐', '音乐 推荐', '音乐 点播']:
            #print(num, g)
            if type(g[2]) != type(list()):
                g[2] = [g[2]]
            entity_cnt += len(g[2])
            for r in g[2][::-1]:
                entity_cnt -= 1
                if r in entity_dict.keys():
                    continue
                entity_dict[r] = ('movie_' if action == '电影 推荐' else 'song_') + str(entity_cnt)
            entity_cnt = len(entity_dict)
            continue

    # add goal transition
    conversation = ' '.join(i['history'])
    conversation = conversation.replace('[ 1', '[1]').replace('[ 2', '[2]').replace('[ 3', '[3]').replace('[ 4', '[4]').replace('[ 5', '[5]').replace('[ 6', '[6]')
    current_goal_stage = max(len(set(re.findall('\[[1-9]\]', conversation))), 1)
    comment = ''
    goal_transition = eval(str(goal[current_goal_stage - 1:current_goal_stage + 1]))
    # print(num, current_goal_stage, goal_transition, goal)
    if '新闻' in goal_transition[0][1]:
        goal_transition[0][3] = ''
    if len(goal_transition) > 1 and '新闻' in goal_transition[1][1]:
        goal_transition[1][3] = ''
    if goal_transition[0][1] in ['音乐 推荐', '播放 音乐', '音乐 点播'] or '电影' in goal_transition[0][1] or '兴趣点 推荐' == goal_transition[0][1]:
        # print(goal_transition[0])
        goal_transition[0][2] = [entity_dict[e] for e in goal_transition[0][2]] if \
                                 type(goal_transition[0][2]) is type(list()) else entity_dict[goal_transition[0][2]]
    if len(goal_transition) > 1 and (goal_transition[1][1] in ['音乐 推荐', '播放 音乐', '音乐 点播'] or '电影' in goal_transition[1][1] or '兴趣点 推荐' == goal_transition[1][1]):
        goal_transition[1][2] = [entity_dict[e] for e in goal_transition[1][2]] if \
                                type(goal_transition[1][2]) is type(list()) else entity_dict[goal_transition[1][2]]
    goal_transition = str(goal_transition)
    print(goal_transition, file=src, end='φ')


    if len(i['history']) == 1 and ('问 时间' in goal_origin[0] or '问 日期' in goal_origin[0]):
        print(i['situation'], i['history'][0], file=src, sep='φ')
        entity_dicts.append(dict())
        questions.append(i['situation'] + i['history'][0])
        continue

    kg = i['knowledge']
    # fix bug when song contain "   "
    for j in range(len(kg)):
        if kg[j][1] != '评论' and '评论' in kg[j][1]:
            kg[j][0] += ' ' + kg[j][1].replace(' 评论', '')
            kg[j][1] = '评论'


    current_goal_length = 0
    current_goal_dialog = ''
    for j in i['history'][::-1]:
        current_goal_length += 1
        current_goal_dialog += j
        if j[0] == '[':
            break
    current_round = 0
    for u in i['history'][::-1]:
        # if goal[current_goal_stage-1][1] == '关于 明星 的 聊天':
            # print(u)
        current_round += 1
        if u[0] == '[':
            break
    # if goal[current_goal_stage-1][1] == '关于 明星 的 聊天':
        # print(current_goal_stage, current_round)
    history = ' '.join(i['history'][:-1])
    question = i['history'][-1]
    # if question[0] == '[':
        # question = question[4:]


    # recommend movie, song, restaurant
    recommend_movie, recommend_song, recommend_restaurant, broadcast_news = '', '', '', []
    next_goal = [goal[current_goal_stage - 1]]
    if ((goal[current_goal_stage - 1][1] == '关于 明星 的 聊天' or goal[current_goal_stage - 1][1] == '寒暄') and current_goal_length > 3) or \
        ((goal[current_goal_stage - 1][1] == '美食 推荐' ) and current_goal_length > 2) or \
        (goal[current_goal_stage - 1][1] != '关于 明星 的 聊天' and goal[current_goal_stage - 1][1] != '寒暄' and goal[current_goal_stage - 1][1] != '美食 推荐' and current_goal_length > 1):
        next_goal = goal[current_goal_stage - 1: current_goal_stage + 1]
    for g in next_goal:  # search the first entity not appeared in conversation
        # from the current goal and the next goal
        if len(recommend_song) + len(recommend_movie) + len(recommend_restaurant) != 0:
            break
        action = g[1]
        if action == '兴趣点 推荐' and remove_marks(g[2]) not in remove_marks(conversation):
            recommend_restaurant = g[2]
            recommend_entity = entity_dict[recommend_restaurant]
        if action in ['电影 推荐', '音乐 推荐']:
            for r in g[2]:
                if remove_marks(r) not in remove_marks(conversation):
                    for k in kg:
                        if remove_marks(k[0]) != remove_marks(r) or k[1] != '评论':
                            continue
                        if k[2] == k[0] + ' :':
                            continue
                        k = str(k)
                        if k in select_comments_dict:
                            recommend_round[num] = k
                            comment = k.replace(r, entity_dict[r])
                            # print(num+1, comment)
                            # input()
                            break

                    # if r in select_comments_dict.keys():
                        # comment_set = select_comments_dict[r]
                        # print(comment_set)
                    if action == '电影 推荐':
                        recommend_movie = r
                        recommend_entity = entity_dict[r]
                        break
                    else:
                        recommend_song = r
                        recommend_entity = entity_dict[r]
                        break

        if action in ['新闻 推荐', '新闻 点播']:
            news_of, news = g[2], g[3]
            # news_words = set(news.split(' '))
            # conversation_words = set(conversation.split(' '))
            # appear_ratio = len(news_words.intersection(conversation)) / len(news_words)
            bleu = sacrebleu.corpus_bleu([news], [[current_goal_dialog]]).score            
            # print(bleu, news, current_goal_dialog)
            # input()
            if bleu < 2:
                
                # print(num, g)
                broadcast_news = [news_of, '新闻', news]
                # print(broadcast_news)
                break

    using_k = set()
    max_knowledge = 3



    for j in range(len(kg)):
        if max_knowledge == 0:
            break

        if kg[j][1] in ['导演', '主演'] and '   ' in kg[j][2]:  # ["喜剧之王", "导演", "周星驰   李 力持"]
                kg[j][2] = kg[j][2].replace('   ', ' ， ')


        if (kg[j][0].replace(' ', '') in [recommend_movie.replace(' ', ''), recommend_song.replace(' ', '')] and kg[j][1] == '评论' and comment == '') or \
                (kg[j][0].replace(' ', '') == recommend_restaurant.replace(' ', '') and kg[j][1] == '特色菜' and kg[j][2] in conversation):
            # if this comment has been used in trainin set, we already select it in above
            # otherwise, use a comment that is not too short and too problembatic
            if kg[j][1] == '评论':
                if len(kg[j][2]) > 88:
                    kg[j][2] = kg[j][2][:88]
                if kg[j][2] == kg[j][0] + ' :':
                    continue
            kg[j][0] = recommend_entity
            comment = str(kg[j])


        if kg[j][1] == '新闻':  # news knowledge is already handled
            continue
        if kg[j][1] == '订单量':   # strange 
            continue
        if str(kg[j]) in using_k:
            continue

        if check_relation(kg[j][1], question) and kg[j][0] != i['user_profile']['姓名'] and\
                (( remove_marks(kg[j][0]) in remove_marks(conversation) ) ^ ( remove_marks(kg[j][2]) in remove_marks(conversation))or \
                (kg[j][0].replace(' ', '') in conversation.replace(' ', '') and kg[j][2].isdigit() )):
            for key in entity_dict.keys():
                if remove_marks(kg[j][0]) == remove_marks(key):
                    kg[j][0] = entity_dict[key]
            if kg[j][1] == '主演' and ' ， 'in kg[j][2]:
                actors = kg[j][2].split(' ， ')
                # print(actors)
                if '还有' in question or '还 有些' in question:
                    actors = [actor for actor in actors if actor not in conversation]
                    kg[j][2] = ' ， '.join(actors)
                    answer = '主演 还有 ' + ' 、 '.join(actors) + ' 哦'
                else:
                    answer = '这部 电影 的 主演 有 ' + ' 、 '.join(actors) + ' 哦'
                multi_actors_answers[num] = answer
                    
            # if kg[j][1] == '新闻':
                # news[num] = kg[j][2]
            # digits = re.findall('[0-9.]*', kg[j][2])
            # print(digits)
            if kg[j][1] in difficult_info_mask.keys():
                mask = difficult_info_mask[kg[j][1]]
                if num not in mask_info.keys():
                    mask_info[num] = dict()
                mask_info[num][mask] = ' ' + kg[j][2] + ' '
                kg[j][2] = mask
            using_k.add(str(kg[j]))
            max_knowledge -= 1
        else:

            if (validate(kg[j][1]) and ((goal[1][1] == '天气 信息 推送' and len(i['history']) == 3) or
                                        (goal[0][1] == '问 天气' and len(i['history']) == 1))) or \
                    ('适合' in kg[j][1] and len(i['history']) == 3) or \
                    ('生日' == kg[j][1] and goal[0][1] == '问 日期' and len(i['history']) == 3):
                if validate(kg[j][1]):
                    kg[j][1] = '天气'
                    weather_dict[num] = kg[j][2]
                using_k.add(str(kg[j]))
                max_knowledge -= 1
    if len(using_k) == 0:   
        # chat about celebrity, add knowledge set that used in training set 
        if (goal[current_goal_stage-1][1] == '关于 明星 的 聊天' and current_round < 4) or (current_goal_stage < len(goal) and current_round >= 2 and goal[current_goal_stage][1] == '关于 明星 的 聊天'):
            #print(num)
            celebrity = goal[current_goal_stage - 1][2] if goal[current_goal_stage-1][1] == '关于 明星 的 聊天' else \
                goal[current_goal_stage][2]
            # print(celebrity)
            # input()
            chat = celebrity_chat[celebrity]
            for ks, r in zip(chat.keys(), chat.values()):
                ks = eval(ks)
                if ks_in_kg(ks, kg, conversation):
                    chat_round[num] = r
                    using_k = ks
                    # print(num, using_k)
                    # input()
                    break
    
    print(*using_k, end='φ', sep=' ', file=src)



    # replace entity in diaglog
    for j in range(len(i['history'])):
        for entity, entity_no in zip(entity_dict.keys(), entity_dict.values()):
            i['history'][j] = i['history'][j].replace(entity, entity_no)

    question = i['history'][-1]
    if max_knowledge == 3:
        if recommend_movie != '' or recommend_song != '' or recommend_restaurant != '' or broadcast_news != []:
            print(comment if broadcast_news == [] else broadcast_news, end='φ', file=src)
            if broadcast_news != []:
                news_dict[num] = broadcast_news[2]
        elif '再见' not in question and '拜拜' not in question:
            # add history
            add_history = []
            pos_h = j - 1
            delta_goal_stage = 0
            goal_stage_milestone = set()
            for ih in range(len(i['history'])):
                if i['history'][ih][0] == '[':
                    goal_stage_milestone.add(ih)

            while len(' '.join(add_history) + i['history'][pos_h]) < 128 and pos_h >= 0:
                add_history.append(i['history'][pos_h].strip())
                pos_h -= 1
                if pos_h in goal_stage_milestone:
                    if pos_h in goal_stage_milestone:
                        break
                    add_history[-1] += '\t'
                    delta_goal_stage += 1
            
            # add_history = [c + ' 。' if c[-1] not in ['！', '？', '。'] else c for c in add_history]
            print(*add_history[::-1], sep='φ', end='φ', file=src)
            # if question[-1] == '？':
                # print(question)
    else:
        if num in chat_round.keys():  # when chatting about celebrity, user ask some information
            chat_round.pop(num)
            print(num)
    print(question, file=src)
    questions.append(question)
    entity_dicts.append(entity_dict)

if True:

    with open('test_anti_trick.txt') as f:
        no_use = f.readlines()
    with open('test_hypo.txt', 'r') as f:
        x = f.readlines()

    with open('dialog_news_response_2.txt', 'r') as f:
        news_response = f.readline()
        news_response = eval(news_response)

    gg = open('mbart_test_0517.txt', 'w')
    for i in range(len(x)):
        x[i] = x[i].strip()
        x[i] = x[i].replace(',', '，').replace('?', '？').replace('!', '！').replace('°C', '℃').\
            replace('(', '（').replace(')', '）')

        question = questions[i]
        # print(question)
        #　input()
        if '几点' in question and ('点' not in x[i] and ':' not in x[i]):
            print(question, x[i])
            #　input()

        if i in chat_round.keys():
            print(chat_round[i], file=gg)
            # print(i+1, chat_round[i], x[i])
            continue

        if False and i in news_dict.keys():     
            # print(i+1, news_dict[i])
            # input()
            if news_dict[i] not in news_response.keys():
                print(news_dict[i])
            print(news_response[news_dict[i]] if news_dict[i] in news_response.keys() else news_dict[i], file=gg)
            # print(news_dict[i].replace('    ', ' ').replace('   ', ' ').replace('  ', ' '), file=gg)
            continue

        if False and i in multi_actors_answers.keys():
            print(multi_actors_answers[i], file=gg)
            print(x[i], multi_actors_answers[i])
            continue

        if i in weather_dict.keys():
            x[i] = x[i].replace(' 零下 ', ' - ').replace(' ， ', ' ,   ').replace('℃ 最', '℃ ,   最').replace('风 最', '风 ,   最').replace(' ，', ' ,   ').replace('你 最高 气温', '最高 气温').replace('你 最低气温', '最低气温').replace('我 最高 气温', '最高 气温').replace('我 最低气温', '最低气温')        
            weather = weather_dict[i]
            true_temperature = re.findall('-? [0-9][0-9]? ', weather)
            generate_temperature = re.findall('-? [0-9][0-9]? ', x[i])
            if len(true_temperature) == len(generate_temperature) and true_temperature != generate_temperature:
                x[i] = x[i].replace(generate_temperature[0], 'high')
                x[i] = x[i].replace(generate_temperature[1], 'low')
                x[i] = x[i].replace('high', true_temperature[0])
                x[i] = x[i].replace('low', true_temperature[1])


            generate_temperature = re.findall('-? [0-9][0-9]? ', x[i])
            if true_temperature != generate_temperature:
                print(i, true_temperature, generate_temperature)
                print(weather, file=gg)
                continue
        # if -i in weather_dict.keys():
            # x[i] += weather_dict[-i]

        if i in mask_info.keys():
            for key, value in zip(mask_info[i].keys(), mask_info[i].values()):
                # print(key, value)
                x[i] = x[i].replace(key, value)
        entity_dict = entity_dicts[i]
        for key, value in zip(entity_dict.keys(), entity_dict.values()):
            x[i] = x[i].replace(value, key)

        #　if i in recommend_round.keys() and recommend_round[i] not in comment_recommends.keys():
            # print(recommend_round[i])

        # compare the generated response with those in dataset, and select the most likely one
        if i in recommend_round.keys() and recommend_round[i] in comment_recommends.keys():
            origins = comment_recommends[recommend_round[i]]
            max_bleu = -1.0
            most_similar_response = ''
            # print(x[i])
            for o in origins:
                bleu = sacrebleu.corpus_bleu([x[i]], [[o]]).score
                # print(bleu, o)
                if bleu > max_bleu:
                    max_bleu = bleu
                    most_similar_response = o
            # print(x[i], most_similar_response)
            x[i] = most_similar_response


        # fix bug: question about weight
        if False and '身高 是 height' in x[i]:
            if i in mask_info.keys() and 'weight' in mask_info[i].keys():
                x[i] = x[i].replace('身高 是 height', '体重 是 ' + mask_info[i]['weight'])
        print(x[i].strip(), file=gg)
