import sys
import os
status = "数据已是最新版本"
def GetStatus():
    global status
    return status
def run_all_scripts():
    global status
    status = "正在更新数据"
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)
    
    # APK相对路径
    apk_path = "PhigrosApk/base.apk"
    
    print("开始顺序执行脚本...")
    
    try:
        # 1. 执行 taptap.py
        print("=" * 50)
        print("执行 taptap.py...")
        import taptap
        print("taptap.py 完成")
        
        # 2. 执行 download.py  
        print("=" * 50)
        print("执行 download.py...")
        import download
        print("download.py 完成")
        
        # 3. 执行 gameInformation.py（带参数）
        print("=" * 50)
        print("执行 gameInformation.py...")
        import gameInformation
        # 调用带参数的函数
        if hasattr(gameInformation, 'main'):
            gameInformation.main(apk_path)
        elif hasattr(gameInformation, 'analyze'):
            gameInformation.analyze(apk_path)
        else:
            print("gameInformation.py 没有main或analyze函数")
        print("gameInformation.py 完成")
        
        # 4. 执行 resource.py（带参数）
        print("=" * 50)
        print("执行 resource.py...")
        import resource
        # 调用带参数的函数
        if hasattr(resource, 'main'):
            resource.main(apk_path)
        elif hasattr(resource, 'extract'):
            resource.extract(apk_path)
        else:
            print("resource.py 没有main或extract函数")
        print("resource.py 完成")
        
        # 5. 执行更新定数表
        print("=" * 50)
        print("执行 updateLevel.py...")
        import updateLevel
        print("updateLevel.py 完成")

        print("=" * 50)
        print("执行 fsbToWav.py")
        import fsbToWav
        print("fsbToWav.py 完成")

        print("=" * 50)
        print("执行 counts.py")
        import counts
        print("counts.py 完成")
        
        print("=" * 50)
        print("所有脚本执行完成！")
        status = "数据已是最新版本"
    except Exception as e:
        print(f"执行出错: {e}")
        status = "执行错误"
if __name__ == "__main__":
    run_all_scripts()