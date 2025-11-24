import os
import json
import csv
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

def normalize_song_id(song_id):
    """标准化歌曲ID，将 xxx.xxx.0 转换为 xxx.xxx（必须包含2个点）"""
    parts = song_id.split('.')
    # 只有当有至少3部分且最后一部分是'0'时才进行合并
    if len(parts) >= 3 and parts[-1] == '0':
        return '.'.join(parts[:-1])
    return song_id

def count_notes_in_chart(json_file_path):
    """统计谱面JSON文件中的各种note数量"""
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            chart_data = json.load(f)
        
        # 初始化计数器
        counts = {
            'total': 0,
            'tap': 0,    # type=1
            'hold': 0,   # type=3 
            'drag': 0,   # type=2
            'flick': 0   # type=4
        }
        
        # 遍历所有judgeLine来统计notes
        if 'judgeLineList' in chart_data:
            for judge_line in chart_data['judgeLineList']:
                # 统计正面的notes
                if 'notesAbove' in judge_line:
                    for note in judge_line['notesAbove']:
                        note_type = note.get('type', 0)
                        if 1 <= note_type <= 4:
                            counts['total'] += 1
                            if note_type == 1:
                                counts['tap'] += 1
                            elif note_type == 3:
                                counts['hold'] += 1
                            elif note_type == 2:
                                counts['drag'] += 1
                            elif note_type == 4:
                                counts['flick'] += 1
                
                # 统计反面的notes
                if 'notesBelow' in judge_line:
                    for note in judge_line['notesBelow']:
                        note_type = note.get('type', 0)
                        if 1 <= note_type <= 4:
                            counts['total'] += 1
                            if note_type == 1:
                                counts['tap'] += 1
                            elif note_type == 2:  # 修正：type=2是hold
                                counts['hold'] += 1
                            elif note_type == 3:  # 修正：type=3是drag
                                counts['drag'] += 1
                            elif note_type == 4:
                                counts['flick'] += 1
        
        return counts
    except Exception as e:
        print(f"警告: 无法读取谱面文件 {json_file_path}: {e}")
        return {'total': 0, 'tap': 0, 'hold': 0, 'drag': 0, 'flick': 0}

def process_single_chart(chart_dir):
    """处理单个谱面文件夹"""
    song_id = chart_dir.name
    chart_result = {}
    
    # 处理各个难度
    difficulties = ['EZ', 'HD', 'IN', 'AT']
    for diff in difficulties:
        json_file = chart_dir / f"{diff}.json"
        if json_file.exists():
            counts = count_notes_in_chart(json_file)
            chart_result[diff.lower()] = counts
    
    return song_id, chart_result

def process_chart_data():
    """处理所有数据并生成最终的JSON"""
    result = {}
    
    # 步骤1: 并行处理谱面数据
    chart_data = {}
    chart_path = Path("chart")
    if chart_path.exists():
        chart_dirs = [d for d in chart_path.iterdir() if d.is_dir()]
        total_dirs = len(chart_dirs)
        print(f"找到 {total_dirs} 个谱面文件夹")
        print(f"开始并行处理，同时处理20个文件夹...")
        
        start_time = time.time()
        completed = 0
        
        with ThreadPoolExecutor(max_workers=20) as executor:
            # 提交所有任务
            future_to_dir = {executor.submit(process_single_chart, chart_dir): chart_dir for chart_dir in chart_dirs}
            
            # 处理完成的任务
            for future in as_completed(future_to_dir):
                try:
                    song_id, chart_result = future.result()
                    chart_data[song_id] = chart_result
                    completed += 1
                    
                    # 计算进度和预计剩余时间
                    elapsed_time = time.time() - start_time
                    avg_time_per_item = elapsed_time / completed
                    remaining_items = total_dirs - completed
                    estimated_remaining_time = avg_time_per_item * remaining_items
                    
                    # 每完成一个就显示进度
                    progress_percent = (completed / total_dirs) * 100
                    print(f"进度: {completed}/{total_dirs} ({progress_percent:.1f}%) - 预计剩余: {estimated_remaining_time:.1f}秒 - 已完成: {song_id}")
                    
                except Exception as e:
                    chart_dir = future_to_dir[future]
                    print(f"处理失败: {chart_dir.name}: {e}")
                    completed += 1
        
        total_time = time.time() - start_time
        print(f"谱面数据处理完成，耗时: {total_time:.2f}秒")
    else:
        print("警告: chart 文件夹不存在")
        return {}
    
    # 步骤2: 读取info.tsv
    info_data = {}
    info_tsv_path = Path("info/info.tsv")
    if info_tsv_path.exists():
        print("读取info.tsv...")
        with open(info_tsv_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                parts = line.split('\t')
                if len(parts) >= 7:
                    song_id = parts[0]
                    normalized_id = normalize_song_id(song_id)
                    info_data[normalized_id] = {
                        'name': parts[1],
                        'composer': parts[2],
                        'ill': parts[3],
                        'ez_charter': parts[4],
                        'hd_charter': parts[5],
                        'in_charter': parts[6],
                        'at_charter': parts[7] if len(parts) > 7 else ''
                    }
                else:
                    print(f"警告: info.tsv 第{line_num}行格式错误: {line}")
        print(f"从info.tsv读取了 {len(info_data)} 首歌曲信息")
    else:
        print("警告: info/info.tsv 文件不存在")
    
    # 步骤3: 读取difficulty.tsv
    difficulty_data = {}
    diff_tsv_path = Path("info/difficulty.tsv")
    if diff_tsv_path.exists():
        print("读取difficulty.tsv...")
        with open(diff_tsv_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                parts = line.split('\t')
                if len(parts) >= 3:
                    song_id = parts[0]
                    normalized_id = normalize_song_id(song_id)
                    difficulty_data[normalized_id] = {
                        'ez_level': parts[1],
                        'hd_level': parts[2],
                        'in_level': parts[3] if len(parts) > 3 else '',
                        'at_level': parts[4] if len(parts) > 4 else ''
                    }
                else:
                    print(f"警告: difficulty.tsv 第{line_num}行格式错误: {line}")
        print(f"从difficulty.tsv读取了 {len(difficulty_data)} 首歌曲难度")
    else:
        print("警告: info/difficulty.tsv 文件不存在")
    
    # 步骤4: 合并所有数据（应用ID标准化）
    print("合并数据并标准化ID...")
    all_song_ids = set()
    
    # 标准化chart_data中的ID
    normalized_chart_data = {}
    for song_id, data in chart_data.items():
        normalized_id = normalize_song_id(song_id)
        # 如果已经存在相同标准化的ID，合并数据
        if normalized_id in normalized_chart_data:
            # 合并难度数据，优先使用非.0版本
            for diff in ['ez', 'hd', 'in', 'at']:
                if diff in data and data[diff].get('total', 0) > 0:
                    normalized_chart_data[normalized_id][diff] = data[diff]
        else:
            normalized_chart_data[normalized_id] = data
    
    all_song_ids = set(normalized_chart_data.keys()) | set(info_data.keys()) | set(difficulty_data.keys())
    
    # 记录合并信息
    merged_count = len(chart_data) - len(normalized_chart_data)
    if merged_count > 0:
        print(f"合并了 {merged_count} 个重复的歌曲ID")
    
    for song_id in all_song_ids:
        result[song_id] = {
            'name': info_data.get(song_id, {}).get('name', ''),
            'composer': info_data.get(song_id, {}).get('composer', ''),
            'ill': info_data.get(song_id, {}).get('ill', ''),
        }
        
        # 处理各个难度
        difficulties = ['ez', 'hd', 'in', 'at']
        for diff in difficulties:
            diff_data = normalized_chart_data.get(song_id, {}).get(diff, {})
            
            if diff_data:  # 如果该难度存在
                result[song_id][diff] = {
                    'level': difficulty_data.get(song_id, {}).get(f'{diff}_level', ''),
                    'notes': diff_data.get('total', 0),
                    'tap': diff_data.get('tap', 0),
                    'hold': diff_data.get('hold', 0),  # 修正：type=2是hold
                    'drag': diff_data.get('drag', 0),  # 修正：type=3是drag
                    'flick': diff_data.get('flick', 0),
                    'charter': info_data.get(song_id, {}).get(f'{diff}_charter', ''),
                    'duration': 0
                }
    
    return result

def main():
    """主函数"""
    print("开始处理数据..")
    
    # 处理数据
    chart_data = process_chart_data()
    
    # 保存为JSON文件
    output_file = "chartData.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(chart_data, f, ensure_ascii=False, indent=2)
    
    print(f"数据处理完成！结果已保存到 {output_file}")
    
    # 打印统计信息
    print(f"\n统计信息:")
    print(f"总共处理了 {len(chart_data)} 首歌曲")
    
    # 按歌曲显示详细信息
    for song_id, data in chart_data.items():
        print(f"\n{data['name']} (ID: {song_id})")
        for diff in ['ez', 'hd', 'in', 'at']:
            if diff in data:
                diff_data = data[diff]
                print(f"  {diff.upper()}: 定数 {diff_data['level']}, 音符数 {diff_data['notes']} (T:{diff_data['tap']} H:{diff_data['hold']} D:{diff_data['drag']} F:{diff_data['flick']})")


main()