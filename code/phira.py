import os
import shutil
from zipfile import ZipFile, BadZipFile, ZIP_DEFLATED
import concurrent.futures
from threading import Lock

levels = ["EZ", "HD", "IN", "AT"]

# 创建线程安全的打印锁
print_lock = Lock()

def safe_print(*args, **kwargs):
    """线程安全的打印函数"""
    with print_lock:
        print(*args, **kwargs)

def create_zip_for_chart(id, info, level, level_index):
    """为指定谱面创建ZIP文件"""
    try:
        zip_path = f"phira/{level}/{id}-{level}.zip"
        
        # 检查是否已存在，避免重复创建
        if os.path.exists(zip_path):
            safe_print(f"跳过已存在的文件：{zip_path}")
            return True
            
        with ZipFile(zip_path, "w", compression=ZIP_DEFLATED) as zip_file:
            # 写入 info.txt 内容
            info_txt_content = (
                f"#\n"
                f"Name: {info['Name']}\n"
                f"Song: {id}.wav\n"
                f"Picture: {id}.png\n"
                f"Chart: {id}.json\n"
                f"Level: {level} Lv.{info['difficulty'][level_index]}\n"
                f"Composer: {info['Composer']}\n"
                f"Illustrator: {info['Illustrator']}\n"
                f"Charter: {info['Chater'][level_index]}"
            )
            zip_file.writestr("info.txt", info_txt_content)

            # 添加文件到 ZIP 压缩包
            files_added = 0
            
            # 添加图表文件
            chart_path = f"chart/{id}.0/{level}.json"
            if os.path.exists(chart_path):
                zip_file.write(chart_path, f"{id}.json")
                files_added += 1
            else:
                safe_print(f"警告：未找到 {id} 的 {level} 图表文件 ({chart_path})")

            # 添加插图文件
            illustration_path = f"illustration/{id}.png"
            if os.path.exists(illustration_path):
                zip_file.write(illustration_path, f"{id}.png")
                files_added += 1
            else:
                safe_print(f"警告：未找到 {id} 的插图文件 ({illustration_path})")

            # 添加音乐文件 (优先使用wav，如果不存在则尝试ogg)
            music_wav_path = f"music-wav/{id}.wav"
            music_ogg_path = f"music-ogg/{id}.ogg"
            if os.path.exists(music_wav_path):
                zip_file.write(music_wav_path, f"{id}.wav")
                files_added += 1
            elif os.path.exists(music_ogg_path):
                zip_file.write(music_ogg_path, f"{id}.ogg")
                files_added += 1
                safe_print(f"信息：使用OGG格式音乐文件 {music_ogg_path}")
            else:
                safe_print(f"警告：未找到 {id} 的音乐文件 ({music_wav_path} 或 {music_ogg_path})")

        if files_added > 0:
            safe_print(f"成功创建：{zip_path} (包含 {files_added} 个文件)")
            return True
        else:
            safe_print(f"错误：{zip_path} 未添加任何文件，删除空文件")
            try:
                os.remove(zip_path)
            except:
                pass
            return False

    except BadZipFile as e:
        safe_print(f"错误：创建ZIP文件 {zip_path} 时出错 - {e}")
        return False
    except Exception as e:
        safe_print(f"错误：写入ZIP文件 {zip_path} 时出错 - {e}")
        return False

def process_single_chart(item):
    """处理单个谱面的函数，用于多线程执行"""
    id, info = item
    try:
        safe_print(f"正在处理：{info['Name']}，作曲者：{info['Composer']}")
        
        results = []
        for level_index in range(len(info.get("difficulty", []))):
            level = levels[level_index]
            result = create_zip_for_chart(id, info, level, level_index)
            results.append(result)
            
        return all(results)
        
    except KeyError as e:
        safe_print(f"错误：ID {id} 缺少必要的键 {e}。")
        return False
    except Exception as e:
        safe_print(f"意外错误：处理 ID {id} 时发生错误 - {e}")
        return False

def main():
    """主函数"""
    # 删除旧目录并创建新目录
    try:
        shutil.rmtree("phira", True)
        os.makedirs("phira", exist_ok=True)
        for level in levels:
            os.makedirs(f"phira/{level}", exist_ok=True)
    except Exception as e:
        safe_print(f"错误：创建或删除目录时出错 - {e}")
        return

    # 读取并解析 info.tsv 文件
    infos = {}
    try:
        with open("info/info.tsv", encoding="utf8") as f:
            for line in f:
                line = line.strip().split("\t")
                if len(line) >= 5:  # 确保有足够的数据
                    infos[line[0]] = {
                        "Name": line[1],
                        "Composer": line[2],
                        "Illustrator": line[3],
                        "Chater": line[4:]
                    }
    except FileNotFoundError:
        safe_print("错误：未找到 info.tsv 文件。请检查 info 目录是否存在且包含该文件。")
        return
    except Exception as e:
        safe_print(f"错误：读取 info.tsv 时出错 - {e}")
        return

    # 读取并解析 difficulty.tsv 文件
    try:
        with open("info/difficulty.tsv", encoding="utf8") as f:
            for line in f:
                line = line.strip().split("\t")
                if line and line[0] in infos:
                    infos[line[0]]["difficulty"] = line[1:]
                elif line and line[0]:
                    safe_print(f"警告：difficulty.tsv 中的 ID {line[0]} 在 info.tsv 中未找到。")
    except FileNotFoundError:
        safe_print("错误：未找到 difficulty.tsv 文件。请检查 info 目录是否存在且包含该文件。")
        return
    except Exception as e:
        safe_print(f"错误：读取 difficulty.tsv 时出错 - {e}")
        return

    # 使用多线程处理所有谱面
    safe_print(f"开始处理 {len(infos)} 个谱面...")
    
    # 根据CPU核心数设置线程数，但不超过谱面数量
    max_workers = min(os.cpu_count() or 4, len(infos))
    safe_print(f"使用 {max_workers} 个线程进行处理")
    
    successful_count = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有任务
        future_to_id = {executor.submit(process_single_chart, item): item[0] for item in infos.items()}
        
        # 收集结果
        for future in concurrent.futures.as_completed(future_to_id):
            id = future_to_id[future]
            try:
                if future.result():
                    successful_count += 1
            except Exception as e:
                safe_print(f"处理 {id} 时发生未预期错误: {e}")

    safe_print(f"处理完成！成功处理 {successful_count}/{len(infos)} 个谱面")


main()