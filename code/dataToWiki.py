import json
import re

def json_to_wiki_table(json_file_path, output_file_path):
    # 读取JSON文件
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    wiki_tables = []
    
    for song_id, song_data in data.items():
        # 提取基本信息并用nowiki包裹
        name = song_data.get('name', '')
        composer = song_data.get('composer', '')
        ill = song_data.get('ill', '')
        
        # 检查是否存在AT难度
        has_at = 'at' in song_data and song_data['at'] is not None
        
        # 构建表格 - 使用正确的Wiki表格语法
        table = f'[[File:{song_id}.png|300px]]\n'
        table += '{| class="wikitable"\n'
        table += f'|+ <nowiki>{name}</nowiki>\n'
        table += '|-\n'
        
        # 第一行：曲师和难度标题（动态处理AT列）
        if has_at:
            table += f'! 曲师：<nowiki>{composer}</nowiki> !! EZ !! HD !! IN !! AT\n'
        else:
            table += f'! 曲师：<nowiki>{composer}</nowiki> !! EZ !! HD !! IN\n'
        table += '|-\n'
        
        # 第二行：画师和各难度定数
        ez_level = song_data.get('ez', {}).get('level', '') if song_data.get('ez') else ''
        hd_level = song_data.get('hd', {}).get('level', '') if song_data.get('hd') else ''
        in_level = song_data.get('in', {}).get('level', '') if song_data.get('in') else ''
        at_level = song_data.get('at', {}).get('level', '') if song_data.get('at') else ''
        
        if has_at:
            table += f'| 画师：<nowiki>{ill}</nowiki> || 定数：<nowiki>{ez_level}</nowiki> || 定数：<nowiki>{hd_level}</nowiki> || 定数：<nowiki>{in_level}</nowiki> || 定数：<nowiki>{at_level}</nowiki>\n'
        else:
            table += f'| 画师：<nowiki>{ill}</nowiki> || 定数：<nowiki>{ez_level}</nowiki> || 定数：<nowiki>{hd_level}</nowiki> || 定数：<nowiki>{in_level}</nowiki>\n'
        table += '|-\n'
        
        # 第三行：ID和各难度Note数详情（Note总数用nowiki，详细数量用small和换行）
        ez_notes = format_notes_info(song_data.get('ez', {})) if song_data.get('ez') else ''
        hd_notes = format_notes_info(song_data.get('hd', {})) if song_data.get('hd') else ''
        in_notes = format_notes_info(song_data.get('in', {})) if song_data.get('in') else ''
        at_notes = format_notes_info(song_data.get('at', {})) if song_data.get('at') else ''
        
        if has_at:
            table += f'| ID:<nowiki>{song_id}</nowiki> || {ez_notes} || {hd_notes} || {in_notes} || {at_notes}\n'
        else:
            table += f'| ID:<nowiki>{song_id}</nowiki> || {ez_notes} || {hd_notes} || {in_notes}\n'
        table += '|-\n'
        
        # 第四行：各难度谱师
        ez_charter = song_data.get('ez', {}).get('charter', '') if song_data.get('ez') else ''
        hd_charter = song_data.get('hd', {}).get('charter', '') if song_data.get('hd') else ''
        in_charter = song_data.get('in', {}).get('charter', '') if song_data.get('in') else ''
        at_charter = song_data.get('at', {}).get('charter', '') if song_data.get('at') else ''
        
        if has_at:
            table += f'|  || 谱师：<nowiki>{ez_charter}</nowiki> || 谱师：<nowiki>{hd_charter}</nowiki> || 谱师：<nowiki>{in_charter}</nowiki> || 谱师：<nowiki>{at_charter}</nowiki>\n'
        else:
            table += f'|  || 谱师：<nowiki>{ez_charter}</nowiki> || 谱师：<nowiki>{hd_charter}</nowiki> || 谱师：<nowiki>{in_charter}</nowiki>\n'
        table += '|}\n'  # 表格结束添加换行
        
        wiki_tables.append(table)
    
    # 用<br>----<br>连接所有表格，确保正确的换行
    final_output = '<br>\n----\n<br>\n'.join(wiki_tables)
    
    # 添加页脚
    final_output += '\n{{PhigrosWiki}}\n[[Category:谱面信息]]'
    
    # 写入输出文件
    with open(output_file_path, 'w', encoding='utf-8') as f:
        f.write(final_output)
    
    print(f"转换完成！共处理 {len(wiki_tables)} 个歌曲表格。")
    print(f"输出文件：{output_file_path}")

def format_notes_info(difficulty_data):
    """格式化Note数信息，Note总数用nowiki，详细数量用small和换行"""
    if not difficulty_data:
        return "Note数："
    
    notes = difficulty_data.get('notes', 0)
    tap = difficulty_data.get('tap', 0)
    hold = difficulty_data.get('hold', 0)
    drag = difficulty_data.get('drag', 0)
    flick = difficulty_data.get('flick', 0)
    
    notes_info = f"Note数：<nowiki>{notes}</nowiki><br><small>Tap:{tap}<br>Hold:{hold}<br>Drag:{drag}<br>Flick:{flick}</small>"
    return notes_info

def main():
    input_file = "chartData.json"  # 输入JSON文件路径
    output_file = "wiki_tables.txt"  # 输出文件路径
    
    try:
        json_to_wiki_table(input_file, output_file)
    except FileNotFoundError:
        print(f"错误：找不到文件 {input_file}")
    except json.JSONDecodeError:
        print(f"错误：{input_file} 不是有效的JSON文件")
    except Exception as e:
        print(f"发生错误：{e}")

if __name__ == "__main__":
    main()