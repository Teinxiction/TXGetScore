from json import dumps, loads
import os
import sys
import logging

# 完全禁用所有日志输出
logging.disable(logging.CRITICAL)

from PhiCloudAction import (
    PhigrosCloud, parseSaveDict, readDifficultyFile, 
    countRks, checkSaveHistory, getB19, getB30, logger
)

# 禁用导入的logger
logger.disabled = True

def _get_latest_rks_from_history(session_token):
    """从saveHistory目录获取最新的RKS值"""
    history_file = os.path.join("saveHistory", session_token, "summaryHistory.json")
    try:
        with open(history_file, 'r', encoding='utf-8') as f:
            history_data = loads(f.read())
        
        if history_data:
            latest_timestamp = sorted(history_data.keys(), reverse=True)[0]
            latest_data = history_data[latest_timestamp]
            rks_value = latest_data.get('rks', 0.0)
            return rks_value
        return 0.0
    except FileNotFoundError:
        return 0.0
    except (KeyError, ValueError, IndexError) as e:
        return 0.0

def get_current_rks(session_token):
    """获取<sessionToken>当前RKS"""
    # 直接从saveHistory目录获取
    current_rks = _get_latest_rks_from_history(session_token)
    if current_rks > 0:
        return current_rks
    
    # 如果saveHistory没有，尝试获取新存档
    try:
        with PhigrosCloud(session_token) as cloud:
            summary = cloud.getSummary()
            save_data = cloud.getSave()
        
        # 保存存档文件
        save_dict = parseSaveDict(save_data)
        with open("PhigrosSave.json", "w", encoding="utf-8") as file:
            file.write(dumps(save_dict, indent=4, ensure_ascii=False))
        
        difficult = readDifficultyFile()
        save_dict = countRks(save_dict, difficult)
        
        # 使用B30计算RKS
        b30 = getB30(save_dict)
        count_rks = sum(b["rks"] for b in b30)
        current_rks = count_rks / 30
        
        # 保存到历史记录（直接保存到saveHistory目录）
        checkSaveHistory(session_token, summary, save_data, difficult)
        
        return current_rks
    except Exception as e:
        print(f"获取当前RKS失败: {e}")
        return 0.0

def get_user_info(session_token):
    """获取<sessionToken>当前用户信息（summaryHistory.json内容）"""
    history_file = os.path.join("saveHistory", session_token, "summaryHistory.json")
    try:
        with open(history_file, 'r', encoding='utf-8') as f:
            history_data = loads(f.read())
        
        if history_data:
            latest_timestamp = sorted(history_data.keys(), reverse=True)[0]
            return history_data[latest_timestamp]
        return {}
    except FileNotFoundError:
        return {}
    except Exception as e:
        print(f"获取用户信息失败: {e}")
        return {}

def get_save_data(session_token):
    """获取<sessionToken>存档（recordHistory.json内容）"""
    record_file = os.path.join("saveHistory", session_token, "recordHistory.json")
    try:
        with open(record_file, 'r', encoding='utf-8') as f:
            return loads(f.read())
    except FileNotFoundError:
        return {}
    except Exception as e:
        print(f"获取存档数据失败: {e}")
        return {}

def get_rks_increase(session_token):
    """获取<sessionToken>的RKS涨了多少"""
    rks_file = os.path.join("saveHistory", session_token, "rks.json")
    try:
        with open(rks_file, 'r', encoding='utf-8') as f:
            rks_data = loads(f.read())
        
        if isinstance(rks_data, list) and len(rks_data) >= 2:
            return rks_data[0] - rks_data[1]  # 最新 - 上一次
        return 0.0
    except FileNotFoundError:
        return 0.0
    except Exception as e:
        print(f"获取RKS增长失败: {e}")
        return 0.0

def clear_rks_history(session_token):
    """清空<sessionToken>的RKS历史记录（只保留最近一个）"""
    rks_file = os.path.join("saveHistory", session_token, "rks.json")
    try:
        with open(rks_file, 'r', encoding='utf-8') as f:
            rks_data = loads(f.read())
        
        if isinstance(rks_data, list):
            # 只保留最近一个记录
            new_data = rks_data[0] if rks_data else 0.0
        
        with open(rks_file, 'w', encoding='utf-8') as f:
            f.write(dumps(new_data, indent=4, ensure_ascii=False))
        
        print(f"已清空 {session_token} 的RKS历史记录")
        return True
    except Exception as e:
        print(f"清空RKS历史记录失败: {e}")
        return False

def get_b_calculated_rks(session_token, b_number=30):
    """获取<sessionToken>当前以B(数字)计算的RKS"""
    if b_number not in [19, 30]:
        raise ValueError("b_number必须是19或30")
    
    try:
        with PhigrosCloud(session_token) as cloud:
            save_data = cloud.getSave()
        
        # 保存存档文件
        save_dict = parseSaveDict(save_data)
        with open("PhigrosSave.json", "w", encoding="utf-8") as file:
            file.write(dumps(save_dict, indent=4, ensure_ascii=False))
        
        difficult = readDifficultyFile()
        save_dict = countRks(save_dict, difficult)
        
        if b_number == 19:
            b_data = getB19(save_dict)
        else:
            b_data = getB30(save_dict)
        
        count_rks = sum(b["rks"] for b in b_data)
        return count_rks / b_number
        
    except Exception as e:
        print(f"获取B{b_number}计算RKS失败: {e}")
        return 0.0

def nickname(session_token):
    """获取玩家昵称"""
    try:
        with PhigrosCloud(session_token) as cloud:
            nickname = cloud.getNickname()
            return nickname
    except Exception as e:
        print(f"获取昵称失败: {e}")
        return "未知玩家"

def update_rks_record(session_token):
    """更新RKS记录"""
    # 获取之前的RKS
    previous_rks = _get_previous_rks_from_json(session_token)
    
    # 获取最新存档和RKS
    try:
        with PhigrosCloud(session_token) as cloud:
            print(f"玩家昵称：{cloud.getNickname()}")
            summary = cloud.getSummary()
            save_data = cloud.getSave()
        
        # 保存存档文件
        save_dict = parseSaveDict(save_data)
        with open("PhigrosSave.json", "w", encoding="utf-8") as file:
            file.write(dumps(save_dict, indent=4, ensure_ascii=False))
        print("获取存档成功！")
        
        difficult = readDifficultyFile()
        save_dict = countRks(save_dict, difficult)
        
        # 计算B30 RKS
        b30 = getB30(save_dict)
        count_rks_b30 = sum(b["rks"] for b in b30)
        current_rks = count_rks_b30 / 30
        print(f"B30计算出来的RKS：{current_rks:.4f}")
        
        # 保存到历史记录
        checkSaveHistory(session_token, summary, save_data, difficult)
        
    except Exception as e:
        print(f"获取存档失败: {e}")
        current_rks = get_b_calculated_rks(session_token, 30)
    
    # 更新rks.json
    _update_rks_json(session_token, current_rks, previous_rks)
    
    return current_rks, previous_rks

def _get_previous_rks_from_json(session_token):
    """从rks.json中获取上一次的RKS值"""
    rks_file = os.path.join("saveHistory", session_token, "rks.json")
    try:
        with open(rks_file, 'r', encoding='utf-8') as f:
            rks_data = loads(f.read())
        
        if isinstance(rks_data, list) and len(rks_data) > 0:
            return rks_data[0]  # 返回最新的记录
        elif isinstance(rks_data, (int, float)):
            return rks_data
        return 0.0
    except FileNotFoundError:
        return 0.0
    except Exception as e:
        return 0.0

def _update_rks_json(session_token, current_rks, previous_rks):
    """更新rks.json文件"""
    rks_file = os.path.join("saveHistory", session_token, "rks.json")
    
    # 读取现有的rks.json
    try:
        with open(rks_file, 'r', encoding='utf-8') as f:
            existing_data = loads(f.read())
    except FileNotFoundError:
        existing_data = []
    
    # 更新数据
    if isinstance(existing_data, list):
        # 将当前RKS插入到第一位，最多保留5个记录
        new_list = [current_rks]
        for i, old_rks in enumerate(existing_data):
            if i < 4:  # 最多保留4个旧记录
                new_list.append(old_rks)
        
        new_data = new_list
    else:
        # 如果是单个值，转换为列表
        new_data = [current_rks, existing_data] if existing_data else [current_rks]
    
    # 保存到文件
    with open(rks_file, 'w', encoding='utf-8') as f:
        f.write(dumps(new_data, indent=4, ensure_ascii=False))

def getB(session_token, best_count=30, phi_count=3):
    """获取B数和P数数据"""
    try:
        with PhigrosCloud(session_token) as cloud:
            save_data = cloud.getSave()
        
        save_dict = parseSaveDict(save_data)
        difficult = readDifficultyFile()
        save_dict = countRks(save_dict, difficult)
        
        # 获取B30数据
        b_data = getB30(save_dict)
        
        # 计算B数和P数
        b_count = len([b for b in b_data if b.get('score', 0) >= 960000])  # B数：960000分以上
        phi_count = len([b for b in b_data if b.get('score', 0) >= 1000000])  # P数：1000000分
        
        return [b_count, phi_count]
        
    except Exception as e:
        print(f"获取B数P数失败: {e}")
        return [0, 0]

def update_phigros_data():
    """更新Phigros数据（用于定时任务）"""
    # 这里可以添加需要定期更新的数据逻辑
    print("更新Phigros数据...")
    return "数据更新完成"

if __name__ == "__main__":
    if len(sys.argv) == 1:
        session_token = ""
    else:
        session_token = sys.argv[1]
    
    real_rks = get_current_rks(session_token)
    current_rks, previous_rks = update_rks_record(session_token)
    
    if previous_rks > 0:
        rks_change = current_rks - previous_rks
        change_symbol = "+" if rks_change > 0 else ""
        print(f"RKS变化: {previous_rks:.4f} → {current_rks:.4f} ({change_symbol}{rks_change:.4f})")
    else:
        print(f"当前RKS: {current_rks:.4f}")
    
    user_info = get_user_info(session_token)
    save_data = get_save_data(session_token)
    rks_increase = get_rks_increase(session_token)
    b19_rks = get_b_calculated_rks(session_token, 19)
    
    if user_info:
        print(f"用户昵称: {user_info.get('nickname', '未知')}")
    print(f"RKS增长: {rks_increase:.4f}")
    print(f"B19计算RKS: {b19_rks:.4f}")
    print(f"实际RKS： {real_rks}")