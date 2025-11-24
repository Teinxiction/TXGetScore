from GetScore import *
from UpdateDifAndAssets import *
from apscheduler.schedulers.background import BackgroundScheduler
import datetime
import time
import json
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import random
import textwrap
import math
from image import *
current_rks = 0
save_data = {}
user_info = {}
ln = 0

def update_phigros_data():
    run_all_scripts()

def getInfoList():
    try:
        with open('chartData.json', 'r', encoding='utf-8') as f:
            chart_data = json.load(f)
        return chart_data
    except FileNotFoundError:
        return {"error": "chartData.json file not found"}
    except Exception as e:
        return {"error": f"Error reading chartData.json: {str(e)}"}

def update_all(sstk):
    global current_rks, save_data, user_info, ln
    try:
        update_rks_record(sstk)  # 这会更新本地文件
        current_rks = get_current_rks(sstk)
        save_data = get_save_data(sstk)  # 从本地文件读取
        user_info = get_user_info(sstk)  # 从本地文件读取
        ln = len(list(save_data.values())[0]) if save_data else 0
        return current_rks
    except Exception as e:
        # 重置全局变量，避免使用旧数据
        current_rks = 0
        save_data = 0
        user_info = 0
        ln = 0
        raise e

def getB(sstk, b, p, ifNoOriginalJson=True, ifNoUserData=True):
    # 强制更新数据，确保获取最新存档
    try:
        # 先更新RKS记录，这会从服务器获取最新数据并保存到本地
        update_rks_record(sstk)
        
        # 然后从本地读取最新数据
        current_save_data = get_save_data(sstk)
        
        if not current_save_data:
            return {"error": "No save data found or invalid SSTK"}
        
        # 验证数据结构是否正确
        timestamp_key = list(current_save_data.keys())[0]
        scores_data = current_save_data[timestamp_key]
        
        if not scores_data or not isinstance(scores_data, dict):
            return {"error": "Invalid save data structure"}
        
        difficulty_data = {}
        try:
            with open('info/difficulty.tsv', 'r', encoding='utf-8') as f:
                for line in f:
                    parts = line.strip().split('\t')
                    if len(parts) >= 4:
                        song_id = parts[0]
                        difficulties = {}
                        if len(parts) > 1 and parts[1]:
                            difficulties['EZ'] = float(parts[1])
                        if len(parts) > 2 and parts[2]:
                            difficulties['HD'] = float(parts[2])
                        if len(parts) > 3 and parts[3]:
                            difficulties['IN'] = float(parts[3])
                        if len(parts) > 4 and parts[4]:
                            difficulties['AT'] = float(parts[4])
                        difficulty_data[song_id] = difficulties
        except FileNotFoundError:
            return {"error": "Difficulty file not found"}
        except Exception as e:
            return {"error": f"Error reading difficulty file: {str(e)}"}
        
        all_rks = []
        
        for song_id, song_data in scores_data.items():
            if not isinstance(song_data, dict):
                continue
                
            for difficulty, score_info in song_data.items():
                if difficulty in ['EZ', 'HD', 'IN', 'AT'] and isinstance(score_info, dict):
                    acc = score_info.get('acc', 0)
                    score = score_info.get('score', 0)
                    fc = score_info.get('fc', 0)
                    
                    # 确保acc是数字类型
                    try:
                        acc = float(acc) if acc else 0
                    except (ValueError, TypeError):
                        acc = 0
                    
                    if song_id in difficulty_data and difficulty in difficulty_data[song_id]:
                        level = difficulty_data[song_id][difficulty]
                        
                        if acc >= 70.0:
                            if acc == 100.0:
                                rks = level
                            else:
                                rks = (((acc - 55) / 45) ** 2) * level
                        else:
                            rks = 0
                        
                        # 确保rks是浮点数
                        rks_value = float(rks) if rks else 0.0
                        
                        all_rks.append({
                            'id': song_id,
                            'level': f"{difficulty} Lv.{level}",
                            'score': int(score) if score else 0,
                            'acc': acc,
                            'rks': rks_value,  # 直接存储浮点数，不round
                            'fc': bool(fc),
                            'difficulty': difficulty,
                            'base_level': level
                        })
        
        # 修复排序问题：确保比较的是数字
        all_rks.sort(key=lambda x: float(x['rks']) if x['rks'] is not None else 0, reverse=True)
        
        # 现在才进行四舍五入
        for item in all_rks:
            item['rks'] = round(item['rks'], 4)
        
        best_scores = {}
        for i in range(min(int(b), len(all_rks))):
            best_scores[str(i + 1)] = all_rks[i]
        
        phi_scores = []
        for score in all_rks:
            if score['acc'] == 100.0:
                phi_scores.append({
                    'id': score['id'],
                    'level': score['level']
                })
        
        phi_result = {}
        for i in range(min(int(p), len(phi_scores))):
            phi_result[str(i + 1)] = phi_scores[i]
        
        userinfo = get_user_info(sstk)
        
        result = {
            '_best': best_scores,
            '_phi': phi_result
        }
        
        if not ifNoOriginalJson:
            result['original'] = {timestamp_key: scores_data}
        
        if not ifNoUserData:
            result['userinfo'] = userinfo
        
        return result
        
    except Exception as e:
        return {"error": f"Failed to get data: {str(e)}"}
def getChart(ID, dif):
    file_path = os.path.join("chart", str(ID), f"{dif}.json")
    
    if not os.path.exists(file_path):
        print(f"查无此人啊呸查无此谱: {file_path}")
        return None
    
    try:
        file_size = os.path.getsize(file_path)
        
        def human_readable_size(size_bytes):
            if size_bytes == 0:
                return "0B"
            size_names = ["B", "KB", "MB", "GB"]
            import math
            i = int(math.floor(math.log(size_bytes, 1024)))
            p = math.pow(1024, i)
            s = round(size_bytes / p, 2)
            return f"{s} {size_names[i]}"
        
        with open(file_path, 'r', encoding='utf-8') as f:
            chartData = json.load(f)
        
        readable_size = human_readable_size(file_size)
        print(f"已查询{ID}的{dif}难度，大小：{readable_size}")
        return chartData
        
    except Exception as e:
        print(f"读取文件失败: {e}")
        return None
if __name__ == "__main__":
    a=input("是否更新数据?(y/n):")
    if a == "y":
        update_phigros_data()

    sessiontoken=input("输入SessionToken:")
    b=input("输入B数:")
    p=input("输入P数:")
    bC=getB(sessiontoken,b,p)
    user_info = get_user_info(sessiontoken)
    name = nickname(sessiontoken)
    print(f"用户昵称: {name}")
    img = draw_B_image(bC,user_info,name)
    img.save("phigros_best_scores.png")
    print("图片已生成: phigros_best_scores.png")