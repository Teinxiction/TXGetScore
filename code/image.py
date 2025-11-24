from PIL import Image, ImageDraw, ImageFont, ImageFilter
import random
import os
import textwrap
import math

def calculate_single_rks(acc, level):
    """计算单曲RKS - acc已经是百分数"""
    if acc < 70.00:  # acc已经是百分比值
        return 0.0
    elif acc == 70.00:
        return level / 9.0
    else:
        # 因为acc已经是百分数，所以直接使用
        return ((acc - 55) / 45) ** 2 * level

def get_improvement_suggestion(current_acc, current_rks, level):
    """获取推分建议 - 通过枚举法，current_acc已经是百分数"""
    if current_acc >= 100.00:  # current_acc已经是百分比值
        return "无法推分"
    
    target_rks = current_rks + 0.01
    if target_rks > level:  # 单曲RKS不能大于定数
        return "无法推分"
    
    # 枚举法：每次+0.01% ACC直到RKS涨0.01
    test_acc = current_acc + 0.01  # 直接加0.01，因为已经是百分数
    while test_acc <= 100.00:
        test_rks = calculate_single_rks(test_acc, level)
        if test_rks >= target_rks:
            return f"推分建议：{test_acc:.2f}%"
        test_acc += 0.01
    
    return "无法推分"

def get_rank(score, fc):
    """获取评级"""
    if score == 1000000:
        return "AP"
    elif fc:
        return "FC"
    elif score >= 960000:
        return "V"
    elif score >= 920000:
        return "S"
    elif score >= 880000:
        return "A"
    elif score >= 820000:
        return "B"
    elif score >= 700000:
        return "C"
    else:
        return "F"

def format_challenge(challenge):
    """格式化课题模式显示"""
    try:
        challenge_str = str(challenge)
        if len(challenge_str) == 0:
            return "0"
        
        # 获取第一个数字
        first_digit = int(challenge_str[0])
        if first_digit < 1 or first_digit > 5:
            return "0"
        
        # 获取剩余数字
        remaining = challenge_str[1:] if len(challenge_str) > 1 else challenge_str
        
        color_map = {
            1: "绿",
            2: "蓝", 
            3: "红",
            4: "金",
            5: "彩"
        }
        
        return f"{color_map[first_digit]}{remaining}"
    except:
        return "0"

def parse_xml_background(xml_content, img_width, img_height):
    """解析XML背景设置"""
    try:
        # 这里可以添加XML解析逻辑
        # 目前先返回默认背景
        return None
    except:
        return None

def draw_B_image(B_content, userdata, name, text=None, xml=None):
    # 创建图片 - 增加高度避免裁剪水印
    img_width = 1200
    img_height = 3000  # 进一步增加高度确保水印不被裁剪
    img = Image.new('RGB', (img_width, img_height), color=(30, 30, 30))
    draw = ImageDraw.Draw(img)
    
    # 尝试加载中文字体
    font_paths = [
        "msyh.ttc",  # 微软雅黑
        "simhei.ttf",  # 黑体
        "simsun.ttc",  # 宋体
        "arial.ttf",   # 英文字体作为备选
        "/System/Library/Fonts/PingFang.ttc"  # macOS 苹方
    ]
    
    title_font = None
    header_font = None
    normal_font = None
    small_font = None
    tiny_font = None
    
    for font_path in font_paths:
        try:
            if title_font is None:
                title_font = ImageFont.truetype(font_path, 36)
            if header_font is None:
                header_font = ImageFont.truetype(font_path, 24)
            if normal_font is None:
                normal_font = ImageFont.truetype(font_path, 20)
            if small_font is None:
                small_font = ImageFont.truetype(font_path, 16)
            if tiny_font is None:
                tiny_font = ImageFont.truetype(font_path, 12)
            break
        except:
            continue
    
    # 如果都没找到，使用默认字体
    if title_font is None:
        title_font = ImageFont.load_default()
        header_font = ImageFont.load_default()
        normal_font = ImageFont.load_default()
        small_font = ImageFont.load_default()
        tiny_font = ImageFont.load_default()
    
    # 读取info.tsv文件获取曲名映射
    song_name_mapping = {}
    tsv_path = "info/info.tsv"
    if os.path.exists(tsv_path):
        try:
            with open(tsv_path, 'r', encoding='utf-8') as f:
                for line in f:
                    parts = line.strip().split('\t')
                    if len(parts) >= 2:
                        song_id = parts[0]
                        display_name = parts[1]
                        song_name_mapping[song_id] = display_name
        except Exception as e:
            print(f"读取info.tsv失败: {e}")
    
    # 设置背景图片 - 支持XML自定义
    background_path = "illustration"
    custom_bg = None
    
    if xml:
        custom_bg = parse_xml_background(xml, img_width, img_height)
    
    if custom_bg:
        # 使用XML自定义背景
        img.paste(custom_bg, (0, 0))
    elif os.path.exists(background_path):
        try:
            bg_files = [f for f in os.listdir(background_path) if f.endswith(('.png', '.jpg', '.jpeg'))]
            if bg_files:
                bg_file = random.choice(bg_files)
                bg_image = Image.open(os.path.join(background_path, bg_file))
                # 调整背景图片大小并模糊
                bg_image = bg_image.resize((img_width, img_height))
                bg_image = bg_image.filter(ImageFilter.GaussianBlur(10))
                # 创建半透明黑色遮罩
                overlay = Image.new('RGBA', (img_width, img_height), (0, 0, 0, 180))
                img.paste(bg_image, (0, 0))
                img.paste(overlay, (0, 0), overlay)
                draw = ImageDraw.Draw(img)
        except:
            pass
    
    y_position = 30
    
    # 绘制标题 - 固定标题
    title_bbox = draw.textbbox((0, 0), "Phigros Best成绩统计", font=title_font)
    title_width = title_bbox[2] - title_bbox[0]
    draw.text(((img_width - title_width) // 2, y_position), "Phigros Best成绩统计", 
              fill=(255, 255, 255), font=title_font)
    y_position += 60
    
    # 绘制用户信息框
    user_bg_color = (40, 40, 40, 200)
    user_bg = Image.new('RGBA', (img_width-60, 120), user_bg_color)
    img.paste(user_bg, (30, y_position), user_bg)
    
    # 玩家信息 - 居左显示
    avatar_text = f"头像: {userdata.get('avatar', '未知')}"
    name_text = f"名称: {name}"
    
    draw.text((50, y_position + 20), avatar_text, fill=(255, 255, 255), font=header_font)
    draw.text((50, y_position + 50), name_text, fill=(255, 255, 255), font=header_font)
    
    # RKS和Challenge信息 - RKS保留6位小数，格式化Challenge
    formatted_challenge = format_challenge(userdata.get('challenge', 0))
    rks_challenge_text = f"RKS: {userdata.get('rks', 0):.6f} | Challenge: {formatted_challenge}"
    draw.text((50, y_position + 80), rks_challenge_text, 
              fill=(200, 200, 200), font=normal_font)
    
    # 四难度统计表格 - 居右显示，使用HTML表格样式
    stats_data = [
        ("EZ", userdata.get('EZ', [0,0,0]), (0, 200, 0)),
        ("HD", userdata.get('HD', [0,0,0]), (255, 165, 0)),
        ("IN", userdata.get('IN', [0,0,0]), (255, 0, 0)),
        ("AT", userdata.get('AT', [0,0,0]), (160, 32, 240))
    ]
    
    # 表格参数
    table_x = img_width - 300  # 表格右侧位置
    table_y = y_position + 20
    col_width = 60  # 列宽
    row_height = 25  # 行高
    
    # 绘制表头背景
    header_bg = Image.new('RGBA', (col_width * 4, row_height), (60, 60, 60, 200))
    img.paste(header_bg, (table_x, table_y), header_bg)
    
    # 绘制表头
    headers = ["", "Clear", "FC", "Phi"]
    for i, header in enumerate(headers):
        x_pos = table_x + i * col_width
        header_bbox = draw.textbbox((0, 0), header, font=small_font)
        header_width = header_bbox[2] - header_bbox[0]
        draw.text((x_pos + (col_width - header_width) // 2, table_y + (row_height - (header_bbox[3] - header_bbox[1])) // 2), 
                 header, fill=(255, 255, 255), font=small_font)
    
    # 绘制表格数据
    for i, (diff, data, color) in enumerate(stats_data):
        y_pos = table_y + (i + 1) * row_height
        
        # 行背景（交替颜色）
        row_bg_color = (50, 50, 50, 200) if i % 2 == 0 else (45, 45, 45, 200)
        row_bg = Image.new('RGBA', (col_width * 4, row_height), row_bg_color)
        img.paste(row_bg, (table_x, y_pos), row_bg)
        
        # 难度列
        diff_bbox = draw.textbbox((0, 0), diff, font=small_font)
        diff_width = diff_bbox[2] - diff_bbox[0]
        draw.text((table_x + (col_width - diff_width) // 2, y_pos + (row_height - (diff_bbox[3] - diff_bbox[1])) // 2), 
                 diff, fill=color, font=small_font)
        
        # 数据列
        for j, value in enumerate(data):
            x_pos = table_x + (j + 1) * col_width
            value_bbox = draw.textbbox((0, 0), str(value), font=small_font)
            value_width = value_bbox[2] - value_bbox[0]
            draw.text((x_pos + (col_width - value_width) // 2, y_pos + (row_height - (value_bbox[3] - value_bbox[1])) // 2), 
                     str(value), fill=(255, 255, 255), font=small_font)
    
    # 绘制表格边框
    table_width = len(headers) * col_width
    table_total_height = (len(stats_data) + 1) * row_height
    draw.rectangle([table_x - 2, table_y - 2, table_x + table_width + 2, table_y + table_total_height + 2], 
                  outline=(100, 100, 100), width=2)
    
    y_position += 150
    
    # 绘制Phi成绩（每3个一行）
    phi_data = B_content.get('_phi', {})
    if phi_data:
        # Phi标题
        phi_title_bbox = draw.textbbox((0, 0), "Phi成绩", font=header_font)
        phi_title_width = phi_title_bbox[2] - phi_title_bbox[0]
        draw.text(((img_width - phi_title_width) // 2, y_position), "Phi成绩", 
                  fill=(255, 255, 255), font=header_font)
        y_position += 40
        
        # 绘制Phi卡片
        phi_ranks = sorted(phi_data.keys(), key=lambda x: int(x))
        for i in range(0, len(phi_ranks), 3):
            row_ranks = phi_ranks[i:i+3]
            row_height = 0
            
            for j, rank in enumerate(row_ranks):
                phi_song = phi_data[rank]
                card_x = 50 + j * 380
                card_y = y_position
                
                # 卡片尺寸
                card_width = 360
                card_height = 180
                image_size = 160  # 曲绘和成绩框大小
                
                # 绘制卡片背景
                card_bg = Image.new('RGBA', (card_width, card_height), (50, 50, 50, 200))
                img.paste(card_bg, (card_x, card_y), card_bg)
                
                # 曲绘区域 - 单独框，向下移动
                image_x = card_x + 10
                image_y = card_y + 20  # 向下移动10像素
                
                # 尝试加载歌曲图片 - 保持2048:1080比例
                song_id = phi_song.get('id', '')
                song_image_path = f"illustration/{song_id}.png"
                song_img_loaded = None
                if os.path.exists(song_image_path):
                    try:
                        song_img_loaded = Image.open(song_image_path)
                        # 保持2048:1080比例，调整为160x84
                        target_width = image_size
                        target_height = int(target_width * 1080 / 2048)
                        song_img_loaded = song_img_loaded.resize((target_width, target_height))
                    except:
                        song_img_loaded = None
                
                # 绘制曲绘框
                draw.rectangle([image_x, image_y, image_x + image_size, image_y + image_size], 
                             outline=(100, 100, 100), width=2, fill=(80, 80, 80))
                
                if song_img_loaded:
                    # 计算居中位置
                    paste_x = image_x + (image_size - song_img_loaded.width) // 2
                    paste_y = image_y + (image_size - song_img_loaded.height) // 2
                    img.paste(song_img_loaded, (paste_x, paste_y))
                
                # 在曲绘左上角显示编号 - 1/9大小
                rank_bg_size = image_size // 3  # 1/9面积，边长1/3
                rank_bg = Image.new('RGBA', (rank_bg_size, rank_bg_size), (0, 0, 0, 200))
                img.paste(rank_bg, (image_x, image_y), rank_bg)
                rank_text = f"P{rank}"
                rank_bbox = draw.textbbox((0, 0), rank_text, font=small_font)
                rank_width = rank_bbox[2] - rank_bbox[0]
                rank_height = rank_bbox[3] - rank_bbox[1]
                draw.text((image_x + (rank_bg_size - rank_width) // 2, image_y + (rank_bg_size - rank_height) // 2), 
                         rank_text, fill=(255, 255, 255), font=small_font)
                
                # 成绩区域（与曲绘框分开，同样向下移动）
                info_x = image_x + image_size + 10
                info_y = image_y  # 同样向下移动
                info_width = image_size
                info_height = image_size
                
                # 绘制成绩框
                draw.rectangle([info_x, info_y, info_x + info_width, info_y + info_height], 
                             outline=(100, 100, 100), width=2, fill=(60, 60, 60, 200))
                
                # 获取显示名称
                display_name = song_name_mapping.get(song_id, song_id)
                
                # 自动调整曲名字体大小
                name_font_size = 16
                name_font = small_font
                name_bbox = draw.textbbox((0, 0), display_name, font=name_font)
                name_text_width = name_bbox[2] - name_bbox[0]
                
                # 如果曲名太长，缩小字体
                while name_text_width > info_width - 10 and name_font_size > 10:
                    name_font_size -= 1
                    try:
                        name_font = ImageFont.truetype(font_paths[0] if font_paths else "arial.ttf", name_font_size)
                    except:
                        name_font = ImageFont.load_default()
                    name_bbox = draw.textbbox((0, 0), display_name, font=name_font)
                    name_text_width = name_bbox[2] - name_bbox[0]
                
                # 显示曲名
                draw.text((info_x + 5, info_y + 5), display_name, fill=(255, 255, 255), font=name_font)
                
                # 显示ID（小字）
                id_font_size = 10
                id_font = tiny_font
                id_bbox = draw.textbbox((0, 0), song_id, font=id_font)
                id_text_width = id_bbox[2] - id_bbox[0]
                
                # 如果ID太长，缩小字体
                while id_text_width > info_width - 10 and id_font_size > 6:
                    id_font_size -= 1
                    try:
                        id_font = ImageFont.truetype(font_paths[0] if font_paths else "arial.ttf", id_font_size)
                    except:
                        id_font = ImageFont.load_default()
                    id_bbox = draw.textbbox((0, 0), song_id, font=id_font)
                    id_text_width = id_bbox[2] - id_bbox[0]
                
                draw.text((info_x + 5, info_y + 30), song_id, fill=(180, 180, 180), font=id_font)
                
                # 难度和等级
                level_text = phi_song.get('level', 'IN Lv.0.0')
                difficulty = level_text.split(' ')[0]
                base_level = float(level_text.split('Lv.')[-1])
                diff_color = {
                    'EZ': (0, 200, 0),
                    'HD': (255, 165, 0),
                    'IN': (255, 0, 0),
                    'AT': (160, 32, 240)
                }.get(difficulty, (255, 255, 255))
                
                # 计算单曲RKS（Phi成绩默认定数）
                single_rks = base_level
                level_rks_text = f"{level_text}|{single_rks:.4f}"
                draw.text((info_x + 5, info_y + 50), level_rks_text, fill=diff_color, font=tiny_font)
                
                # Phi成绩没有分数和ACC，显示特殊信息
                draw.text((info_x + 5, info_y + 70), "Phi成绩", fill=(200, 200, 200), font=small_font)
                draw.text((info_x + 5, info_y + 90), f"单曲RKS: {single_rks:.4f}", fill=(200, 200, 200), font=tiny_font)
                draw.text((info_x + 5, info_y + 105), "无法推分", fill=(150, 150, 150), font=tiny_font)
                
                row_height = max(row_height, card_height)
            
            y_position += row_height + 20
    
    # 绘制Best成绩
    best_data = B_content.get('_best', {})
    if best_data:
        # Best标题
        y_position += 20
        best_title_bbox = draw.textbbox((0, 0), "Best成绩", font=header_font)
        best_title_width = best_title_bbox[2] - best_title_bbox[0]
        draw.text(((img_width - best_title_width) // 2, y_position), "Best成绩", 
                  fill=(255, 255, 255), font=header_font)
        y_position += 40
        
        # 分割B27和之后的成绩
        best_ranks = sorted(best_data.keys(), key=lambda x: int(x))
        b27_ranks = [r for r in best_ranks if int(r) <= 27]
        overflow_ranks = [r for r in best_ranks if int(r) > 27]
        
        # 绘制B27内的成绩（每3个一行）
        for i in range(0, len(b27_ranks), 3):
            row_ranks = b27_ranks[i:i+3]
            row_height = 0
            
            for j, rank in enumerate(row_ranks):
                song_data = best_data[rank]
                card_x = 50 + j * 380
                card_y = y_position
                
                # 卡片尺寸
                card_width = 360
                card_height = 180
                image_size = 160  # 曲绘和成绩框大小
                
                # 绘制卡片背景
                card_bg = Image.new('RGBA', (card_width, card_height), (50, 50, 50, 200))
                img.paste(card_bg, (card_x, card_y), card_bg)
                
                # 曲绘区域 - 单独框，向下移动
                image_x = card_x + 10
                image_y = card_y + 20  # 向下移动10像素
                
                # 歌曲图片 - 保持2048:1080比例
                song_id = song_data.get('id', '')
                song_image_path = f"illustration/{song_id}.png"
                song_img_loaded = None
                if os.path.exists(song_image_path):
                    try:
                        song_img_loaded = Image.open(song_image_path)
                        # 保持2048:1080比例，调整为160x84
                        target_width = image_size
                        target_height = int(target_width * 1080 / 2048)
                        song_img_loaded = song_img_loaded.resize((target_width, target_height))
                    except:
                        song_img_loaded = None
                
                # 检查是否为AP
                is_ap = song_data.get('score', 0) == 1000000
                
                # 绘制曲绘框 - AP时金色描边
                border_color = (255, 215, 0) if is_ap else (100, 100, 100)
                draw.rectangle([image_x, image_y, image_x + image_size, image_y + image_size], 
                             outline=border_color, width=3 if is_ap else 2, fill=(80, 80, 80))
                
                if song_img_loaded:
                    # 计算居中位置
                    paste_x = image_x + (image_size - song_img_loaded.width) // 2
                    paste_y = image_y + (image_size - song_img_loaded.height) // 2
                    img.paste(song_img_loaded, (paste_x, paste_y))
                
                # 在曲绘左上角显示编号 - 1/9大小
                rank_bg_size = image_size // 3  # 1/9面积，边长1/3
                rank_bg = Image.new('RGBA', (rank_bg_size, rank_bg_size), (0, 0, 0, 200))
                img.paste(rank_bg, (image_x, image_y), rank_bg)
                rank_text = f"B{rank}"
                rank_bbox = draw.textbbox((0, 0), rank_text, font=small_font)
                rank_width = rank_bbox[2] - rank_bbox[0]
                rank_height = rank_bbox[3] - rank_bbox[1]
                draw.text((image_x + (rank_bg_size - rank_width) // 2, image_y + (rank_bg_size - rank_height) // 2), 
                         rank_text, fill=(255, 255, 255), font=small_font)
                
                # 成绩区域（与曲绘框分开，同样向下移动）
                info_x = image_x + image_size + 10
                info_y = image_y  # 同样向下移动
                info_width = image_size
                info_height = image_size
                
                # 绘制成绩框
                draw.rectangle([info_x, info_y, info_x + info_width, info_y + info_height], 
                             outline=(100, 100, 100), width=2, fill=(60, 60, 60, 200))
                
                # 获取显示名称
                display_name = song_name_mapping.get(song_id, song_id)
                
                # 自动调整曲名字体大小
                name_font_size = 16
                name_font = small_font
                name_bbox = draw.textbbox((0, 0), display_name, font=name_font)
                name_text_width = name_bbox[2] - name_bbox[0]
                
                # 如果曲名太长，缩小字体
                while name_text_width > info_width - 10 and name_font_size > 10:
                    name_font_size -= 1
                    try:
                        name_font = ImageFont.truetype(font_paths[0] if font_paths else "arial.ttf", name_font_size)
                    except:
                        name_font = ImageFont.load_default()
                    name_bbox = draw.textbbox((0, 0), display_name, font=name_font)
                    name_text_width = name_bbox[2] - name_bbox[0]
                
                # 显示曲名
                draw.text((info_x + 5, info_y + 5), display_name, fill=(255, 255, 255), font=name_font)
                
                # 显示ID（小字）
                id_font_size = 10
                id_font = tiny_font
                id_bbox = draw.textbbox((0, 0), song_id, font=id_font)
                id_text_width = id_bbox[2] - id_bbox[0]
                
                # 如果ID太长，缩小字体
                while id_text_width > info_width - 10 and id_font_size > 6:
                    id_font_size -= 1
                    try:
                        id_font = ImageFont.truetype(font_paths[0] if font_paths else "arial.ttf", id_font_size)
                    except:
                        id_font = ImageFont.load_default()
                    id_bbox = draw.textbbox((0, 0), song_id, font=id_font)
                    id_text_width = id_bbox[2] - id_bbox[0]
                
                draw.text((info_x + 5, info_y + 30), song_id, fill=(180, 180, 180), font=id_font)
                
                # 难度和等级
                level_text = song_data.get('level', 'IN Lv.0.0')
                difficulty = song_data.get('difficulty', 'IN')
                base_level = song_data.get('base_level', 0.0)
                diff_color = {
                    'EZ': (0, 200, 0),
                    'HD': (255, 165, 0),
                    'IN': (255, 0, 0),
                    'AT': (160, 32, 240)
                }.get(difficulty, (255, 255, 255))
                
                # 计算单曲RKS - acc已经是百分比值
                acc = song_data.get('acc', 0)  # 这里直接使用，已经是百分比
                single_rks = calculate_single_rks(acc, base_level)
                level_rks_text = f"{level_text}|{single_rks:.4f}"
                draw.text((info_x + 5, info_y + 50), level_rks_text, fill=diff_color, font=tiny_font)
                
                # 分数和评级
                score = song_data.get('score', 0)
                fc = song_data.get('fc', False)
                rank_text = get_rank(score, fc)
                
                # 分数颜色
                score_color = (255, 215, 0) if rank_text == "AP" else (0, 200, 255) if rank_text == "FC" else (255, 255, 255)
                
                score_display = f"{score:,} {rank_text}"
                draw.text((info_x + 5, info_y + 70), score_display, fill=score_color, font=small_font)
                
                # ACC和推分建议 - acc已经是百分比值
                acc_text = f"{acc:.2f}%"  # 直接显示，已经是百分比
                improvement = get_improvement_suggestion(acc, single_rks, base_level)
                
                draw.text((info_x + 5, info_y + 90), acc_text, fill=(200, 200, 200), font=tiny_font)
                draw.text((info_x + 5, info_y + 105), improvement, fill=(150, 150, 150), font=tiny_font)
                
                row_height = max(row_height, card_height)
            
            y_position += row_height + 20
        
        # 绘制OVER FLOW分割线
        if overflow_ranks:
            y_position += 20
            overflow_bbox = draw.textbbox((0, 0), "--- OVER FLOW ---", font=header_font)
            overflow_width = overflow_bbox[2] - overflow_bbox[0]
            draw.text(((img_width - overflow_width) // 2, y_position), "--- OVER FLOW ---", 
                      fill=(255, 100, 100), font=header_font)
            y_position += 40
            
            # 绘制OVER FLOW成绩（每3个一行）
            for i in range(0, len(overflow_ranks), 3):
                row_ranks = overflow_ranks[i:i+3]
                row_height = 0
                
                for j, rank in enumerate(row_ranks):
                    song_data = best_data[rank]
                    card_x = 50 + j * 380
                    card_y = y_position
                    
                    # 卡片尺寸
                    card_width = 360
                    card_height = 180
                    image_size = 160  # 曲绘和成绩框大小
                    
                    # 绘制卡片背景（颜色稍暗）
                    card_bg = Image.new('RGBA', (card_width, card_height), (40, 40, 40, 200))
                    img.paste(card_bg, (card_x, card_y), card_bg)
                    
                    # 曲绘区域 - 单独框，向下移动
                    image_x = card_x + 10
                    image_y = card_y + 20  # 向下移动10像素
                    
                    # 歌曲图片 - 保持2048:1080比例
                    song_id = song_data.get('id', '')
                    song_image_path = f"illustration/{song_id}.png"
                    song_img_loaded = None
                    if os.path.exists(song_image_path):
                        try:
                            song_img_loaded = Image.open(song_image_path)
                            # 保持2048:1080比例，调整为160x84
                            target_width = image_size
                            target_height = int(target_width * 1080 / 2048)
                            song_img_loaded = song_img_loaded.resize((target_width, target_height))
                        except:
                            song_img_loaded = None
                    
                    # 检查是否为AP
                    is_ap = song_data.get('score', 0) == 1000000
                    
                    # 绘制曲绘框 - AP时金色描边
                    border_color = (255, 215, 0) if is_ap else (80, 80, 80)
                    draw.rectangle([image_x, image_y, image_x + image_size, image_y + image_size], 
                                 outline=border_color, width=3 if is_ap else 2, fill=(60, 60, 60))
                    
                    if song_img_loaded:
                        # 计算居中位置
                        paste_x = image_x + (image_size - song_img_loaded.width) // 2
                        paste_y = image_y + (image_size - song_img_loaded.height) // 2
                        img.paste(song_img_loaded, (paste_x, paste_y))
                    
                    # 在曲绘左上角显示编号 - 1/9大小
                    rank_bg_size = image_size // 3  # 1/9面积，边长1/3
                    rank_bg = Image.new('RGBA', (rank_bg_size, rank_bg_size), (0, 0, 0, 200))
                    img.paste(rank_bg, (image_x, image_y), rank_bg)
                    rank_text = f"B{rank}"
                    rank_bbox = draw.textbbox((0, 0), rank_text, font=small_font)
                    rank_width = rank_bbox[2] - rank_bbox[0]
                    rank_height = rank_bbox[3] - rank_bbox[1]
                    draw.text((image_x + (rank_bg_size - rank_width) // 2, image_y + (rank_bg_size - rank_height) // 2), 
                             rank_text, fill=(200, 200, 200), font=small_font)
                    
                    # 成绩区域（与曲绘框分开，同样向下移动）
                    info_x = image_x + image_size + 10
                    info_y = image_y  # 同样向下移动
                    info_width = image_size
                    info_height = image_size
                    
                    # 绘制成绩框
                    draw.rectangle([info_x, info_y, info_x + info_width, info_y + info_height], 
                                 outline=(80, 80, 80), width=2, fill=(50, 50, 50, 200))
                    
                    # 获取显示名称
                    display_name = song_name_mapping.get(song_id, song_id)
                    
                    # 自动调整曲名字体大小
                    name_font_size = 16
                    name_font = small_font
                    name_bbox = draw.textbbox((0, 0), display_name, font=name_font)
                    name_text_width = name_bbox[2] - name_bbox[0]
                    
                    # 如果曲名太长，缩小字体
                    while name_text_width > info_width - 10 and name_font_size > 10:
                        name_font_size -= 1
                        try:
                            name_font = ImageFont.truetype(font_paths[0] if font_paths else "arial.ttf", name_font_size)
                        except:
                            name_font = ImageFont.load_default()
                        name_bbox = draw.textbbox((0, 0), display_name, font=name_font)
                        name_text_width = name_bbox[2] - name_bbox[0]
                    
                    # 显示曲名
                    draw.text((info_x + 5, info_y + 5), display_name, fill=(200, 200, 200), font=name_font)
                    
                    # 显示ID（小字）
                    id_font_size = 10
                    id_font = tiny_font
                    id_bbox = draw.textbbox((0, 0), song_id, font=id_font)
                    id_text_width = id_bbox[2] - id_bbox[0]
                    
                    # 如果ID太长，缩小字体
                    while id_text_width > info_width - 10 and id_font_size > 6:
                        id_font_size -= 1
                        try:
                            id_font = ImageFont.truetype(font_paths[0] if font_paths else "arial.ttf", id_font_size)
                        except:
                            id_font = ImageFont.load_default()
                        id_bbox = draw.textbbox((0, 0), song_id, font=id_font)
                        id_text_width = id_bbox[2] - id_bbox[0]
                    
                    draw.text((info_x + 5, info_y + 30), song_id, fill=(150, 150, 150), font=id_font)
                    
                    # 难度和等级
                    level_text = song_data.get('level', 'IN Lv.0.0')
                    difficulty = song_data.get('difficulty', 'IN')
                    base_level = song_data.get('base_level', 0.0)
                    diff_color = {
                        'EZ': (0, 150, 0),
                        'HD': (200, 130, 0),
                        'IN': (200, 0, 0),
                        'AT': (130, 25, 200)
                    }.get(difficulty, (200, 200, 200))
                    
                    # 计算单曲RKS - acc已经是百分比值
                    acc = song_data.get('acc', 0)  # 这里直接使用，已经是百分比
                    single_rks = calculate_single_rks(acc, base_level)
                    level_rks_text = f"{level_text}|{single_rks:.4f}"
                    draw.text((info_x + 5, info_y + 50), level_rks_text, fill=diff_color, font=tiny_font)
                    
                    # 分数和评级
                    score = song_data.get('score', 0)
                    fc = song_data.get('fc', False)
                    rank_text = get_rank(score, fc)
                    
                    # 分数颜色
                    score_color = (255, 215, 0) if rank_text == "AP" else (0, 180, 230) if rank_text == "FC" else (180, 180, 180)
                    
                    score_display = f"{score:,} {rank_text}"
                    draw.text((info_x + 5, info_y + 70), score_display, fill=score_color, font=small_font)
                    
                    # ACC和推分建议 - acc已经是百分比值
                    acc_text = f"{acc:.2f}%"  # 直接显示，已经是百分比
                    improvement = get_improvement_suggestion(acc, single_rks, base_level)
                    
                    draw.text((info_x + 5, info_y + 90), acc_text, fill=(150, 150, 150), font=tiny_font)
                    draw.text((info_x + 5, info_y + 105), improvement, fill=(120, 120, 120), font=tiny_font)
                    
                    row_height = max(row_height, card_height)
                
                y_position += row_height + 20
    
    # 添加自定义文案（如果有）
    if text:
        y_position += 20
        # 绘制自定义文案
        text_lines = textwrap.wrap(text, width=80)  # 每行最多80个字符
        for line in text_lines:
            text_bbox = draw.textbbox((0, 0), line, font=normal_font)
            text_width = text_bbox[2] - text_bbox[0]
            draw.text(((img_width - text_width) // 2, y_position), line, 
                      fill=(200, 200, 200), font=normal_font)
            y_position += 30
    
    # 先裁剪图片到实际内容高度
    actual_content_height = y_position + 100  # 留出足够空间给水印
    img = img.crop((0, 0, img_width, min(actual_content_height, img_height)))
    
    # 重新创建draw对象
    draw = ImageDraw.Draw(img)
    
    # 在裁剪后的图片底部添加水印
    watermark = "Generated by TeinxictionMC"
    watermark_bbox = draw.textbbox((0, 0), watermark, font=small_font)
    watermark_width = watermark_bbox[2] - watermark_bbox[0]
    
    # 水印位置在图片底部
    watermark_y = img.height - 30
    
    draw.text(((img_width - watermark_width) // 2, watermark_y), watermark, 
              fill=(100, 100, 100, 180), font=small_font)
    
    return img

