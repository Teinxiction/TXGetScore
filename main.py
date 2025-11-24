from flask import Flask, request, jsonify, render_template, session, redirect, url_for, Response, send_from_directory
import base64
import io
import sys
import os
import traceback
import threading
import time
import schedule
from datetime import datetime
import logging
from functools import wraps
import hashlib
import secrets
import re
import html
import atexit
import subprocess
import select
import json
import uuid

print("测试已经重启")

# 预加载404页面
try:
    pagenotfound = open('404.html', 'r', encoding='utf-8').read()
except FileNotFoundError:
    pagenotfound = '''
    <!DOCTYPE html>
    <html>
    <head><title>404 Not Found - TX查分器</title></head>
    <body>
        <h1>页面被玩家Miss了...</h1>
        <p>404：页面不存在</p>
        <p><a href="/">返回首页</a></p>
    </body>
    </html>
    '''

app = Flask(__name__, 
           template_folder=os.path.dirname(os.path.abspath(__file__)),
           static_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static'))

app.secret_key = secrets.token_hex(32)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# 页面索引配置
PAGE_INDEX = {
    "": "index.html",                    # 首页
    "home": "index.html",                # 主页别名
    "agreement": "agreement.html",       # 用户协议
    "dashboard": "dash.html"             # 仪表板
}

# 静态文件目录配置
STATIC_DIRS = {}

# API帮助文档配置
API_HELP_CONFIG = {
    "sessiontoken": "SessionToken",
    "best": "B数（整数）", 
    "phi": "P数（整数）",
    "ifNotImage": "是否不要图片（true/false）",
    "text": "自定义文案（可选）",
    "xml": "自定义XML数据（可选）",
    "type": "请求类型：get（获取数据）/help（帮助）/image（直接返回图片）/data（获取谱面数据）"
}

update_status = {
    "last_run": None, "last_success": None, "last_error": None,
    "is_running": False, "scheduler_enabled": True
}

scheduler_running = True

ADMIN_CONFIG_FILE = 'AdminPassword.txt'
SALT_FILE = 'admin_salt.txt'
DEFAULT_USERNAME = 'Admin'
DEFAULT_PASSWORD = 'YourPassword'  #使用本项目前请务必将这个玩意改为你自己的密码！！！

# 用户数据文件
USER_DATA_FILE = 'user_data.json'

SQL_INJECTION_PATTERNS = [
    r'(\bOR\b|\bAND\b)\s+\d+=\d+', r'\bUNION\s+SELECT\b', r'\bSELECT\b.*\bFROM\b',
    r'\bINSERT\b.*\bINTO\b', r'\bDROP\b.*\bTABLE\b', r'\bDELETE\b.*\bFROM\b',
    r'\bUPDATE\b.*\bSET\b', r"'.*--", r"'.*;", r"1=1", r"' OR '1'='1"
]

# 用户数据管理函数
def init_user_data():
    """初始化用户数据文件"""
    if not os.path.exists(USER_DATA_FILE):
        with open(USER_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump({}, f, ensure_ascii=False, indent=2)

def load_user_data():
    """加载用户数据"""
    try:
        with open(USER_DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

def save_user_data(data):
    """保存用户数据"""
    with open(USER_DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def generate_user_id():
    """生成唯一用户ID"""
    return str(uuid.uuid4())

def hash_user_password(password, salt=None):
    """哈希用户密码"""
    if salt is None:
        salt = secrets.token_hex(16)
    password_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000).hex()
    return password_hash, salt

def verify_user_password(password, stored_hash, salt):
    """验证用户密码"""
    try:
        new_hash, _ = hash_user_password(password, salt)
        return secrets.compare_digest(new_hash, stored_hash)
    except:
        return False

def username_exists(username):
    """检查用户名是否存在"""
    user_data = load_user_data()
    for user_id, user_info in user_data.items():
        if user_info.get('username') == username:
            return True
    return False

def get_user_by_username(username):
    """通过用户名获取用户信息"""
    user_data = load_user_data()
    for user_id, user_info in user_data.items():
        if user_info.get('username') == username:
            return user_id, user_info
    return None, None

def get_user_by_sessiontoken(sessiontoken):
    """通过SessionToken获取用户信息"""
    user_data = load_user_data()
    for user_id, user_info in user_data.items():
        if user_info.get('sessiontoken') == sessiontoken:
            return user_id, user_info
    return None, None

def generate_default_username():
    """生成默认用户名"""
    user_data = load_user_data()
    base_username = "user"
    counter = 1
    
    while True:
        username = f"{base_username}{counter}"
        if not username_exists(username):
            return username
        counter += 1

def auto_bind_account(user_id, sessiontoken):
    """自动为新用户绑定默认用户名和密码"""
    user_data = load_user_data()
    
    if user_id not in user_data:
        return False
    
    # 生成默认用户名
    default_username = generate_default_username()
    default_password = "123456"
    
    # 哈希密码
    password_hash, salt = hash_user_password(default_password)
    
    # 更新用户信息
    user_data[user_id]['username'] = default_username
    user_data[user_id]['password_hash'] = password_hash
    user_data[user_id]['salt'] = salt
    
    save_user_data(user_data)
    
    logging.info(f"自动绑定账号: {default_username} (用户ID: {user_id})")
    return default_username

def login_required(f):
    """登录装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_logged_in'):
            return jsonify({"code": 401, "error": "请先登录"}), 401
        return f(*args, **kwargs)
    return decorated_function

def admin_login_required(f):
    """管理员登录装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return jsonify({"code": 401, "error": "请先登录管理员账户"}), 401
        return f(*args, **kwargs)
    return decorated_function

def detect_sql_injection(input_str):
    if not input_str: return False
    input_upper = input_str.upper()
    for pattern in SQL_INJECTION_PATTERNS:
        if re.search(pattern, input_upper, re.IGNORECASE):
            logging.warning(f"SQL注入攻击检测: {input_str}")
            return True
    dangerous_sequences = ["' OR", "' AND", "';", "' --", "/*", "*/"]
    for seq in dangerous_sequences:
        if seq in input_upper: return True
    return False

def hash_password(password, salt=None):
    if salt is None: salt = secrets.token_hex(16)
    password_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000).hex()
    return password_hash, salt

def verify_password(password, stored_hash, salt):
    try:
        new_hash, _ = hash_password(password, salt)
        return secrets.compare_digest(new_hash, stored_hash)
    except Exception: return False

def init_admin_config():
    if not os.path.exists(ADMIN_CONFIG_FILE):
        salt = secrets.token_hex(16)
        password_hash, _ = hash_password(DEFAULT_PASSWORD, salt)
        with open(ADMIN_CONFIG_FILE, 'w', encoding='utf-8') as f:
            f.write(f"{DEFAULT_USERNAME}\n{password_hash}\n{salt}")
        with open(SALT_FILE, 'w', encoding='utf-8') as f:
            f.write(salt)
        logging.info("创建默认管理员配置")

def load_admin_config():
    try:
        with open(ADMIN_CONFIG_FILE, 'r', encoding='utf-8') as f:
            lines = f.read().strip().split('\n')
            if len(lines) >= 3: return lines[0], lines[1], lines[2]
    except Exception as e: logging.error(f"加载管理员配置失败: {e}")
    salt = secrets.token_hex(16) if not os.path.exists(SALT_FILE) else open(SALT_FILE).read().strip()
    password_hash, _ = hash_password(DEFAULT_PASSWORD, salt)
    return DEFAULT_USERNAME, password_hash, salt

def save_admin_config(username, password):
    try:
        salt = secrets.token_hex(16)
        password_hash, _ = hash_password(password, salt)
        with open(ADMIN_CONFIG_FILE, 'w', encoding='utf-8') as f:
            f.write(f"{username}\n{password_hash}\n{salt}")
        with open(SALT_FILE, 'w', encoding='utf-8') as f:
            f.write(salt)
        return True
    except Exception as e: logging.error(f"保存管理员配置失败: {e}"); return False

def execute_in_code_directory(func, *args, **kwargs):
    """在 code 目录下执行函数，确保文件路径正确"""
    original_cwd = os.getcwd()
    code_dir = os.path.join(os.path.dirname(__file__), 'code')
    
    try:
        os.chdir(code_dir)
        result = func(*args, **kwargs)
        return result
    finally:
        os.chdir(original_cwd)

def load_main_module():
    try:
        code_dir = os.path.join(os.path.dirname(__file__), 'code')
        if code_dir not in sys.path: 
            sys.path.insert(0, code_dir)
        
        # 导入 main.py 中的函数
        from main import getB, get_user_info, nickname, get_save_data, draw_B_image, update_phigros_data, getInfoList
        logging.info("✅ 成功加载 main.py 模块")
        
        def wrap_function(original_func):
            def wrapper(*args, **kwargs):
                return execute_in_code_directory(original_func, *args, **kwargs)
            return wrapper
        
        return {
            'getB': wrap_function(getB),
            'get_user_info': wrap_function(get_user_info),
            'nickname': wrap_function(nickname),
            'get_save_data': wrap_function(get_save_data),
            'draw_B_image': wrap_function(draw_B_image),
            'update_phigros_data': wrap_function(update_phigros_data),
            'getInfoList': wrap_function(getInfoList)
        }
    except ImportError as e: 
        logging.error(f"❌ 导入失败: {e}")
        if "update_phigros_data" in str(e):
            logging.info("⚠️  未找到 update_phigros_data 函数，定时更新功能将不可用")
        return None
    except Exception as e: 
        logging.error(f"❌ 加载模块时出错: {e}")
        traceback.print_exc()
        return None

def run_data_update():
    global update_status
    if update_status["is_running"]: 
        logging.info("⏳ 更新任务运行中")
        return
    
    update_status["is_running"] = True
    update_status["last_run"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logging.info(f"🔄 开始数据更新: {update_status['last_run']}")
    
    try:
        main_functions = load_main_module()
        if main_functions and 'update_phigros_data' in main_functions:
            result = main_functions['update_phigros_data']()
            update_status["last_success"] = update_status["last_run"]
            update_status["last_error"] = None
            logging.info(f"✅ 数据更新成功: {result if result else '完成'}")
        else:
            update_status["last_error"] = "update_phigros_data 函数未找到"
            logging.error("❌ 更新失败: update_phigros_data 函数未找到")
            
    except Exception as e:
        error_msg = f"更新过程中出错: {str(e)}"
        update_status["last_error"] = error_msg
        logging.error(f"❌ {error_msg}")
        traceback.print_exc()
    finally:
        update_status["is_running"] = False

def schedule_updater():
    """定时任务调度器"""
    global scheduler_running
    
    schedule.every().day.at("17:01").do(run_data_update)
    schedule.every().day.at("00:01").do(run_data_update)
    
    logging.info("⏰ 定时任务: 每天 17:01 和 00:01")
    
    while scheduler_running:
        try:
            if update_status["scheduler_enabled"]: 
                schedule.run_pending()
            time.sleep(1)
        except Exception as e:
            if scheduler_running:
                logging.error(f"定时任务错误: {e}")
            break
    
    logging.info("⏹️  定时任务已停止")

def stop_scheduler():
    """停止调度器"""
    global scheduler_running
    scheduler_running = False
    logging.info("🛑 正在停止定时任务...")

def start_scheduler():
    """启动定时任务线程"""
    global scheduler_running
    scheduler_running = True
    
    scheduler_thread = threading.Thread(target=schedule_updater)
    scheduler_thread.daemon = False
    scheduler_thread.start()
    logging.info("🚀 定时任务线程已启动")

def get_page_list():
    """获取可用页面列表"""
    pages = []
    for route, filename in PAGE_INDEX.items():
        file_path = os.path.join(os.path.dirname(__file__), filename)
        exists = os.path.exists(file_path)
        pages.append({
            "route": f"/{route}" if route else "/",
            "filename": filename,
            "exists": exists,
            "url": f"http://127.0.0.1:5001/{route}" if route else "http://127.0.0.1:5001/"
        })
    return pages

def get_api_help_document():
    """获取API帮助文档"""
    return {
        "code": 200,
        "message": "API帮助文档",
        "usage": {
            "endpoint": "/api",
            "parameters": {
                "type": API_HELP_CONFIG["type"],
                "sessiontoken": API_HELP_CONFIG["sessiontoken"],
                "best": API_HELP_CONFIG["best"], 
                "phi": API_HELP_CONFIG["phi"],
                "ifNotImage": API_HELP_CONFIG["ifNotImage"],
                "text": API_HELP_CONFIG["text"],
                "xml": API_HELP_CONFIG["xml"]
            },
            "examples": [
                "/api?type=get&sessiontoken=xxx&best=30&phi=3&ifNotImage=true",
                "/api?type=image&sessiontoken=xxx&best=30&phi=3&text=自定义文案",
                "/api?type=help",
                "/api?type=data"
            ]
        }
    }

def get_chart_data():
    """获取谱面数据"""
    try:
        main_functions = load_main_module()
        if main_functions and 'getInfoList' in main_functions:
            return main_functions['getInfoList']()
        else:
            return {"error": "无法加载谱面数据模块"}
    except Exception as e:
        return {"error": f"获取谱面数据失败: {str(e)}"}

# ==================== 真正的重启系统 ====================

def restart_server():
    """真正的重启服务器 - 重新执行 python app.py"""
    print("🚀 正在重启服务器...")
    stop_scheduler()
    time.sleep(1)
    
    # 获取当前Python解释器和脚本路径
    python_executable = sys.executable
    script_path = os.path.abspath(__file__)
    
    print(f"📝 重新执行: {python_executable} {script_path}")
    
    # 使用子进程重新启动
    os.execv(python_executable, [python_executable, script_path])

def keyboard_listener():
    """跨平台非阻塞键盘监听"""
    print("⌨️  按 R 快速重启服务器 | 按 Ctrl+C 停止服务器")
    
    def listen_loop():
        while True:
            try:
                # Windows 平台
                if os.name == 'nt':
                    import msvcrt
                    if msvcrt.kbhit():
                        key = msvcrt.getch().decode('utf-8').lower()
                        if key == 'r':
                            print("\n🔄 检测到重启命令，正在重启服务器...")
                            restart_server()
                            break
                # Linux/Unix 平台
                else:
                    import select
                    if select.select([sys.stdin], [], [], 0.1)[0]:
                        key = sys.stdin.read(1).lower()
                        if key == 'r':
                            print("\n🔄 检测到重启命令，正在重启服务器...")
                            restart_server()
                            break
                
                # 短暂睡眠避免CPU占用过高
                time.sleep(0.1)
                
            except (KeyboardInterrupt, EOFError):
                break
            except Exception as e:
                # 忽略监听错误，继续运行
                time.sleep(1)
    
    listener_thread = threading.Thread(target=listen_loop, daemon=True)
    listener_thread.start()

# ==================== 用户认证路由 ====================

@app.route('/dashboard')
def dashboard():
    """仪表板主页面"""
    filename = PAGE_INDEX.get("dashboard", "dash.html")
    try:
        return render_template(filename)
    except:
        try:
            return open(filename, 'r', encoding='utf-8').read()
        except FileNotFoundError:
            return f"{pagenotfound}"

@app.route('/dashboard/<path:subpath>')
def dashboard_subpath(subpath):
    """仪表板子路径"""
    filename = PAGE_INDEX.get("dashboard", "dash.html")
    try:
        return render_template(filename)
    except:
        try:
            return open(filename, 'r', encoding='utf-8').read()
        except FileNotFoundError:
            return f"{pagenotfound}"

@app.route('/api/dash/login', methods=['POST'])
def api_dash_login():
    """用户登录API"""
    data = request.get_json()
    if not data:
        return jsonify({"code": 400, "error": "无效的请求数据"}), 400
    
    login_type = data.get('type', 'sessiontoken')
    password = data.get('password', '')
    sessiontoken = data.get('sessiontoken', '')
    username = data.get('username', '')
    
    user_data = load_user_data()
    
    if login_type == 'sessiontoken':
        if not sessiontoken:
            return jsonify({"code": 400, "error": "SessionToken不能为空"}), 400
        
        # 查找用户
        user_id, user_info = get_user_by_sessiontoken(sessiontoken)
        
        if user_info:
            # 已绑定用户名，需要密码验证
            if not password:
                return jsonify({"code": 401, "error": "需要密码"}), 401
            
            if verify_user_password(password, user_info['password_hash'], user_info['salt']):
                session['user_logged_in'] = True
                session['user_id'] = user_id
                session['username'] = user_info['username']
                session['sessiontoken'] = sessiontoken
                return jsonify({"code": 200, "message": "登录成功", "username": user_info['username']})
            else:
                return jsonify({"code": 401, "error": "密码错误"}), 401
        else:
            # 新SessionToken，自动绑定默认账号并登录
            user_id = generate_user_id()
            default_username = auto_bind_account(user_id, sessiontoken)
            
            if default_username:
                session['user_logged_in'] = True
                session['user_id'] = user_id
                session['username'] = default_username
                session['sessiontoken'] = sessiontoken
                return jsonify({
                    "code": 200, 
                    "message": "登录成功，已自动绑定默认账号", 
                    "username": default_username,
                    "auto_bind": True,
                    "default_password": "123456"
                })
            else:
                return jsonify({"code": 500, "error": "自动绑定账号失败"}), 500
    
    elif login_type == 'username':
        if not username or not password:
            return jsonify({"code": 400, "error": "用户名和密码不能为空"}), 400
        
        user_id, user_info = get_user_by_username(username)
        if not user_info:
            return jsonify({"code": 401, "error": "用户不存在"}), 401
        
        if verify_user_password(password, user_info['password_hash'], user_info['salt']):
            session['user_logged_in'] = True
            session['user_id'] = user_id
            session['username'] = username
            session['sessiontoken'] = user_info['sessiontoken']
            return jsonify({"code": 200, "message": "登录成功", "username": username})
        else:
            return jsonify({"code": 401, "error": "密码错误"}), 401
    
    else:
        return jsonify({"code": 400, "error": "无效的登录类型"}), 400

@app.route('/api/dash/register', methods=['POST'])
def api_dash_register():
    """用户注册API"""
    data = request.get_json()
    if not data:
        return jsonify({"code": 400, "error": "无效的请求数据"}), 400
    
    sessiontoken = data.get('sessiontoken', '')
    
    if not sessiontoken:
        return jsonify({"code": 400, "error": "SessionToken不能为空"}), 400
    
    # 检查是否已注册
    user_id, existing_user = get_user_by_sessiontoken(sessiontoken)
    if existing_user:
        return jsonify({"code": 400, "error": "该SessionToken已注册"}), 400
    
    # 创建新用户并自动绑定默认账号
    user_id = generate_user_id()
    user_data = load_user_data()
    
    # 生成默认用户名
    default_username = generate_default_username()
    default_password = "123456"
    password_hash, salt = hash_user_password(default_password)
    
    user_data[user_id] = {
        'sessiontoken': sessiontoken,
        'username': default_username,
        'password_hash': password_hash,
        'salt': salt,
        'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    save_user_data(user_data)
    
    session['user_logged_in'] = True
    session['user_id'] = user_id
    session['sessiontoken'] = sessiontoken
    session['username'] = default_username
    
    return jsonify({
        "code": 200, 
        "message": "注册成功，已自动绑定默认账号", 
        "username": default_username,
        "default_password": "123456"
    })

@app.route('/api/dash/logout', methods=['POST'])
def api_dash_logout():
    """退出登录API"""
    session.clear()
    response = jsonify({"code": 200, "message": "退出成功"})
    # 清除记住密码的cookie
    response.set_cookie('remember_me', '', expires=0)
    response.set_cookie('username', '', expires=0)
    return response

@app.route('/api/dash/delete-account', methods=['POST'])
@login_required
def api_dash_delete_account():
    """永久删除账户API"""
    data = request.get_json()
    if not data:
        return jsonify({"code": 400, "error": "无效的请求数据"}), 400
    
    password = data.get('password', '')
    
    if not password:
        return jsonify({"code": 400, "error": "需要密码确认"}), 400
    
    user_data = load_user_data()
    user_id = session.get('user_id')
    
    if user_id not in user_data:
        return jsonify({"code": 404, "error": "用户不存在"}), 404
    
    user_info = user_data[user_id]
    
    # 验证密码
    if user_info.get('username') and user_info.get('password_hash'):
        if not verify_user_password(password, user_info['password_hash'], user_info['salt']):
            return jsonify({"code": 401, "error": "密码错误"}), 401
    
    # 删除用户数据
    del user_data[user_id]
    save_user_data(user_data)
    
    # 清除session
    session.clear()
    
    response = jsonify({"code": 200, "message": "账户已永久删除"})
    # 清除记住密码的cookie
    response.set_cookie('remember_me', '', expires=0)
    response.set_cookie('username', '', expires=0)
    return response

@app.route('/api/dash/bind-account', methods=['POST'])
@login_required
def api_dash_bind_account():
    """绑定用户名和密码API"""
    data = request.get_json()
    if not data:
        return jsonify({"code": 400, "error": "无效的请求数据"}), 400
    
    username = data.get('username', '')
    password = data.get('password', '')
    
    if not username or not password:
        return jsonify({"code": 400, "error": "用户名和密码不能为空"}), 400
    
    if username_exists(username):
        return jsonify({"code": 400, "error": "用户名已存在"}), 400
    
    user_data = load_user_data()
    user_id = session.get('user_id')
    
    if user_id not in user_data:
        return jsonify({"code": 404, "error": "用户不存在"}), 404
    
    # 哈希密码
    password_hash, salt = hash_user_password(password)
    
    # 更新用户信息
    user_data[user_id]['username'] = username
    user_data[user_id]['password_hash'] = password_hash
    user_data[user_id]['salt'] = salt
    
    save_user_data(user_data)
    
    # 更新session
    session['username'] = username
    
    return jsonify({"code": 200, "message": "账号绑定成功"})

@app.route('/api/dash/unbind-account', methods=['POST'])
@login_required
def api_dash_unbind_account():
    """解绑用户名和密码API"""
    user_data = load_user_data()
    user_id = session.get('user_id')
    
    if user_id not in user_data:
        return jsonify({"code": 404, "error": "用户不存在"}), 404
    
    # 清除用户名和密码
    user_data[user_id]['username'] = None
    user_data[user_id]['password_hash'] = None
    user_data[user_id]['salt'] = None
    
    save_user_data(user_data)
    
    # 更新session
    session['username'] = None
    
    return jsonify({"code": 200, "message": "账号解绑成功"})

@app.route('/api/dash/user-info')
@login_required
def api_dash_user_info():
    """获取用户信息API"""
    user_data = load_user_data()
    user_id = session.get('user_id')
    
    if user_id not in user_data:
        return jsonify({"code": 404, "error": "用户不存在"}), 404
    
    user_info = user_data[user_id]
    return jsonify({
        "code": 200,
        "data": {
            "user_id": user_id,
            "username": user_info.get('username'),
            "sessiontoken": user_info.get('sessiontoken'),
            "created_at": user_info.get('created_at'),
            "has_password": user_info.get('password_hash') is not None
        }
    })

@app.route('/api/dash/remember-login', methods=['POST'])
def api_dash_remember_login():
    """记住登录状态API"""
    data = request.get_json()
    if not data:
        return jsonify({"code": 400, "error": "无效的请求数据"}), 400
    
    username = data.get('username', '')
    remember_me = data.get('remember_me', False)
    
    if not username:
        return jsonify({"code": 400, "error": "用户名不能为空"}), 400
    
    response = jsonify({"code": 200, "message": "记住登录状态设置成功"})
    
    if remember_me:
        # 设置cookie，有效期30天
        response.set_cookie('remember_me', 'true', max_age=30*24*60*60)
        response.set_cookie('username', username, max_age=30*24*60*60)
    else:
        # 清除cookie
        response.set_cookie('remember_me', '', expires=0)
        response.set_cookie('username', '', expires=0)
    
    return response

# ==================== 管理员路由 ====================

@app.route('/admin114514')
def admin_login_page():
    """管理员登录页面"""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>管理员登录 - TX查分器</title>
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
                padding: 20px;
                color: #ffffff;
            }
            
            .login-container {
                background: rgba(255, 255, 255, 0.1);
                padding: 40px;
                border-radius: 10px;
                backdrop-filter: blur(10px);
                width: 100%;
                max-width: 400px;
            }
            
            .login-container h1 {
                text-align: center;
                margin-bottom: 30px;
            }
            
            .form-group {
                margin-bottom: 20px;
            }
            
            .form-group label {
                display: block;
                margin-bottom: 5px;
                font-weight: bold;
            }
            
            .form-group input {
                width: 100%;
                padding: 12px;
                border: none;
                border-radius: 5px;
                background: rgba(255, 255, 255, 0.9);
            }
            
            .btn {
                width: 100%;
                padding: 12px;
                background: #007bff;
                color: white;
                border: none;
                border-radius: 5px;
                cursor: pointer;
                font-size: 16px;
            }
            
            .btn:hover {
                background: #0056b3;
            }
            
            .message {
                padding: 10px;
                border-radius: 5px;
                margin-bottom: 15px;
                text-align: center;
            }
            
            .success {
                background: rgba(40, 167, 69, 0.3);
                border: 1px solid #28a745;
            }
            
            .error {
                background: rgba(220, 53, 69, 0.3);
                border: 1px solid #dc3545;
            }
        </style>
    </head>
    <body>
        <div class="login-container">
            <h1>管理员登录</h1>
            <div id="messageArea"></div>
            <div class="form-group">
                <label for="username">用户名</label>
                <input type="text" id="username" placeholder="输入管理员用户名">
            </div>
            <div class="form-group">
                <label for="password">密码</label>
                <input type="password" id="password" placeholder="输入管理员密码">
            </div>
            <button class="btn" onclick="adminLogin()">登录</button>
        </div>

        <script>
            async function adminLogin() {
                const username = document.getElementById('username').value;
                const password = document.getElementById('password').value;
                
                if (!username || !password) {
                    showMessage('请输入用户名和密码', 'error');
                    return;
                }
                
                try {
                    const response = await fetch('/api/admin/login', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            username: username,
                            password: password
                        })
                    });
                    
                    const result = await response.json();
                    
                    if (result.code === 200) {
                        showMessage('登录成功，正在跳转...', 'success');
                        setTimeout(() => {
                            window.location.href = '/admin114514/dashboard';
                        }, 1000);
                    } else {
                        showMessage('登录失败: ' + result.error, 'error');
                    }
                } catch (error) {
                    showMessage('网络错误: ' + error.message, 'error');
                }
            }
            
            function showMessage(message, type) {
                const messageArea = document.getElementById('messageArea');
                messageArea.innerHTML = `<div class="message ${type}">${message}</div>`;
            }
        </script>
    </body>
    </html>
    '''

@app.route('/admin114514/dashboard')
@admin_login_required
def admin_dashboard():
    """管理员仪表板"""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>管理员面板 - TX查分器</title>
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
                color: #ffffff;
                margin: 0;
            }
            
            .header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 30px;
                padding: 20px;
                background: rgba(255, 255, 255, 0.1);
                border-radius: 10px;
                backdrop-filter: blur(10px);
            }
            
            .container {
                max-width: 1200px;
                margin: 0 auto;
            }
            
            .card {
                background: rgba(255, 255, 255, 0.1);
                padding: 30px;
                border-radius: 10px;
                margin-bottom: 20px;
                backdrop-filter: blur(10px);
            }
            
            .btn {
                padding: 10px 20px;
                background: rgba(255, 255, 255, 0.2);
                color: white;
                border: none;
                border-radius: 5px;
                cursor: pointer;
                text-decoration: none;
                font-size: 14px;
                transition: background 0.3s;
                margin-right: 10px;
            }
            
            .btn:hover {
                background: rgba(255, 255, 255, 0.3);
            }
            
            .btn-danger {
                background: #dc3545;
            }
            
            .btn-danger:hover {
                background: #c82333;
            }
            
            .stats {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }
            
            .stat-card {
                background: rgba(255, 255, 255, 0.1);
                padding: 20px;
                border-radius: 10px;
                text-align: center;
                backdrop-filter: blur(10px);
            }
            
            .stat-number {
                font-size: 2em;
                font-weight: bold;
                margin: 10px 0;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>管理员面板</h1>
                <div>
                    <button class="btn" onclick="window.location.href='/dashboard'">用户面板</button>
                    <button class="btn btn-danger" onclick="adminLogout()">退出</button>
                </div>
            </div>

            <div class="stats">
                <div class="stat-card">
                    <h3>总用户数</h3>
                    <div class="stat-number" id="totalUsers">0</div>
                </div>
                <div class="stat-card">
                    <h3>已绑定账号</h3>
                    <div class="stat-number" id="boundUsers">0</div>
                </div>
                <div class="stat-card">
                    <h3>今日注册</h3>
                    <div class="stat-number" id="todayUsers">0</div>
                </div>
            </div>

            <div class="card">
                <h2>系统状态</h2>
                <div id="systemStatus">加载中...</div>
                <button class="btn" onclick="updateSystemStatus()">刷新状态</button>
                <button class="btn" onclick="manualUpdate()">手动更新数据</button>
            </div>

            <div class="card">
                <h2>用户管理</h2>
                <div id="userList">加载中...</div>
                <button class="btn" onclick="loadUserList()">刷新用户列表</button>
            </div>
        </div>

        <script>
            // 加载统计数据
            async function loadStats() {
                try {
                    const response = await fetch('/api/admin/stats');
                    const data = await response.json();
                    
                    if (data.code === 200) {
                        document.getElementById('totalUsers').textContent = data.data.total_users;
                        document.getElementById('boundUsers').textContent = data.data.bound_users;
                        document.getElementById('todayUsers').textContent = data.data.today_users;
                    }
                } catch (error) {
                    console.error('加载统计失败:', error);
                }
            }
            
            // 加载系统状态
            async function updateSystemStatus() {
                try {
                    const response = await fetch('/api/status');
                    const data = await response.json();
                    
                    let statusHtml = `
                        <p><strong>最后运行:</strong> ${data.last_run || '从未'}</p>
                        <p><strong>最后成功:</strong> ${data.last_success || '从未'}</p>
                        <p><strong>最后错误:</strong> ${data.last_error || '无'}</p>
                        <p><strong>运行状态:</strong> ${data.is_running ? '运行中' : '空闲'}</p>
                    `;
                    
                    document.getElementById('systemStatus').innerHTML = statusHtml;
                } catch (error) {
                    document.getElementById('systemStatus').innerHTML = '加载失败';
                }
            }
            
            // 手动更新数据
            async function manualUpdate() {
                try {
                    const response = await fetch('/api/update', { method: 'POST' });
                    const data = await response.json();
                    alert(data.message);
                    updateSystemStatus();
                } catch (error) {
                    alert('更新失败: ' + error.message);
                }
            }
            
            // 加载用户列表
            async function loadUserList() {
                try {
                    const response = await fetch('/api/admin/users');
                    const data = await response.json();
                    
                    if (data.code === 200) {
                        let userHtml = '<table style="width: 100%; border-collapse: collapse; margin-top: 10px;">';
                        userHtml += '<tr><th style="text-align: left; padding: 8px; border-bottom: 1px solid rgba(255,255,255,0.3)">用户ID</th><th style="text-align: left; padding: 8px; border-bottom: 1px solid rgba(255,255,255,0.3)">用户名</th><th style="text-align: left; padding: 8px; border-bottom: 1px solid rgba(255,255,255,0.3)">注册时间</th></tr>';
                        
                        data.data.users.forEach(user => {
                            userHtml += `<tr>
                                <td style="padding: 8px; border-bottom: 1px solid rgba(255,255,255,0.1)">${user.user_id.substring(0, 8)}...</td>
                                <td style="padding: 8px; border-bottom: 1px solid rgba(255,255,255,0.1)">${user.username || '未绑定'}</td>
                                <td style="padding: 8px; border-bottom: 1px solid rgba(255,255,255,0.1)">${user.created_at}</td>
                            </tr>`;
                        });
                        
                        userHtml += '</table>';
                        document.getElementById('userList').innerHTML = userHtml;
                    }
                } catch (error) {
                    document.getElementById('userList').innerHTML = '加载失败';
                }
            }
            
            // 管理员退出
            async function adminLogout() {
                try {
                    const response = await fetch('/api/admin/logout', { method: 'POST' });
                    const data = await response.json();
                    
                    if (data.code === 200) {
                        window.location.href = '/admin114514';
                    }
                } catch (error) {
                    alert('退出失败: ' + error.message);
                }
            }
            
            // 页面加载时初始化
            document.addEventListener('DOMContentLoaded', function() {
                loadStats();
                updateSystemStatus();
                loadUserList();
            });
        </script>
    </body>
    </html>
    '''

@app.route('/api/admin/login', methods=['POST'])
def api_admin_login():
    """管理员登录API"""
    data = request.get_json()
    if not data:
        return jsonify({"code": 400, "error": "无效的请求数据"}), 400
    
    username = data.get('username', '')
    password = data.get('password', '')
    
    if not username or not password:
        return jsonify({"code": 400, "error": "用户名和密码不能为空"}), 400
    
    admin_username, admin_hash, admin_salt = load_admin_config()
    
    if username == admin_username and verify_password(password, admin_hash, admin_salt):
        session['admin_logged_in'] = True
        session['admin_username'] = username
        return jsonify({"code": 200, "message": "管理员登录成功"})
    else:
        return jsonify({"code": 401, "error": "用户名或密码错误"}), 401

@app.route('/api/admin/logout', methods=['POST'])
def api_admin_logout():
    """管理员退出API"""
    session.pop('admin_logged_in', None)
    session.pop('admin_username', None)
    return jsonify({"code": 200, "message": "管理员退出成功"})

@app.route('/api/admin/stats')
@admin_login_required
def api_admin_stats():
    """管理员统计数据API"""
    user_data = load_user_data()
    total_users = len(user_data)
    bound_users = len([u for u in user_data.values() if u.get('username')])
    
    # 计算今日注册用户
    today = datetime.now().strftime("%Y-%m-%d")
    today_users = len([u for u in user_data.values() if u.get('created_at', '').startswith(today)])
    
    return jsonify({
        "code": 200,
        "data": {
            "total_users": total_users,
            "bound_users": bound_users,
            "today_users": today_users
        }
    })

@app.route('/api/admin/users')
@admin_login_required
def api_admin_users():
    """管理员用户列表API"""
    user_data = load_user_data()
    users = []
    
    for user_id, user_info in user_data.items():
        users.append({
            "user_id": user_id,
            "username": user_info.get('username'),
            "created_at": user_info.get('created_at', '未知')
        })
    
    return jsonify({
        "code": 200,
        "data": {
            "users": users
        }
    })

# ==================== 页面路由系统 ====================

@app.route('/')
def index():
    """首页"""
    filename = PAGE_INDEX.get("", "index.html")
    try:
        return render_template(filename)
    except:
        try:
            return open(filename, 'r', encoding='utf-8').read()
        except FileNotFoundError:
            return f"{pagenotfound}"

@app.route('/<path:route>')
def serve_page(route):
    """动态页面路由"""
    if route in PAGE_INDEX:
        filename = PAGE_INDEX[route]
        try:
            return render_template(filename)
        except:
            try:
                return open(filename, 'r', encoding='utf-8').read()
            except FileNotFoundError:
                return f"{pagenotfound}", 404
    else:
        for dir_name, dir_path in STATIC_DIRS.items():
            if route.startswith(dir_name + '/'):
                filename = route[len(dir_name)+1:]
                return send_from_directory(dir_path, filename)
        
        return f"{pagenotfound}", 404

# ==================== 静态文件路由 ====================

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

@app.route('/css/<path:filename>')
def serve_css(filename):
    return send_from_directory('static/css', filename)

@app.route('/js/<path:filename>')
def serve_js(filename):
    return send_from_directory('static/js', filename)

@app.route('/images/<path:filename>')
def serve_images(filename):
    return send_from_directory('static/images', filename)

@app.route('/illustration/<path:filename>')
def serve_illustration(filename):
    """服务谱面插图"""
    illustration_dir = os.path.join('code', 'illustration')
    return send_from_directory(illustration_dir, filename)

# ==================== 页面管理API ====================

@app.route('/api/pages')
def list_pages():
    pages = get_page_list()
    return jsonify({
        "code": 200,
        "message": "页面列表获取成功",
        "data": {
            "pages": pages,
            "total": len(pages),
            "exists_count": len([p for p in pages if p["exists"]])
        }
    })

@app.route('/api/pages/<page_name>')
def get_page_info(page_name):
    if page_name in PAGE_INDEX:
        filename = PAGE_INDEX[page_name]
        file_path = os.path.join(os.path.dirname(__file__), filename)
        exists = os.path.exists(file_path)
        
        return jsonify({
            "code": 200,
            "message": "页面信息获取成功",
            "data": {
                "name": page_name,
                "filename": filename,
                "route": f"/{page_name}" if page_name else "/",
                "exists": exists,
                "file_path": file_path
            }
        })
    else:
        return jsonify({
            "code": 404,
            "error": "页面未在索引中定义"
        }), 404

# ==================== 原有的API路由 ====================

@app.route('/api/status')
def get_status(): 
    return jsonify(update_status)

@app.route('/api/update', methods=['POST'])
def manual_update():
    if update_status["is_running"]: 
        return jsonify({"code":409,"message":"更新任务运行中"}),409
    threading.Thread(target=run_data_update, daemon=True).start()
    return jsonify({"code":200,"message":"更新任务已开始"})

def handle_image_request(sessiontoken, best, phi, text, xml):
    if not sessiontoken: 
        return jsonify({"code":400,"error":"sessiontoken必需"}),400
    
    main_functions = load_main_module()
    if not main_functions: 
        return jsonify({"code":500,"error":"无法加载模块"}),500
    
    try:
        bC = main_functions['getB'](sessiontoken, best, phi)
        user_info = main_functions['get_user_info'](sessiontoken)
        name = main_functions['nickname'](sessiontoken)
        
        # 使用 main.py 中的 draw_B_image 函数生成图片
        img = main_functions['draw_B_image'](bC, user_info, name, text, xml)
        
        if not img: 
            return jsonify({"code":500,"error":"图片生成失败"}),500
        
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG')
        response = Response(img_byte_arr.getvalue(), mimetype='image/png')
        response.headers['Cache-Control'] = 'no-cache'
        return response
        
    except Exception as e:
        logging.error(f"❌ 图片请求失败: {e}")
        return jsonify({"code":500,"error":f"图片生成失败: {str(e)}"}),500

@app.route('/api', methods=['GET'])
def handle_api():
    request_type = request.args.get('type', 'help').lower()
    sessiontoken = request.args.get('sessiontoken', '')
    best_str = request.args.get('best', '0')
    phi_str = request.args.get('phi', '0')
    if_not_image_str = request.args.get('ifNotImage', 'false').lower()
    text = request.args.get('text', '')
    xml = request.args.get('xml', '')
    
    try: 
        best = int(best_str)
        phi = int(phi_str)
    except ValueError: 
        return jsonify({"code":400,"error":"best和phi必须是数字"}),400
    
    if_not_image = if_not_image_str in ['true', '1', 'yes']
    
    if request_type == 'image': 
        return handle_image_request(sessiontoken, best, phi, text, xml)
    
    elif request_type == 'get':
        if not sessiontoken: 
            return jsonify({"code":400,"error":"sessiontoken必需"}),400
        
        main_functions = load_main_module()
        if not main_functions: 
            return jsonify({"code":500,"error":"无法加载模块"}),500
        
        try:
            bC = main_functions['getB'](sessiontoken, best, phi)
            user_info = main_functions['get_user_info'](sessiontoken)
            name = main_functions['nickname'](sessiontoken)
            save_data = main_functions['get_save_data'](sessiontoken)
            
            result = {
                "list": bC, 
                "user_info": user_info, 
                "save_data": save_data, 
                "nickname": name
            }
            
            if not if_not_image:
                try: 
                    img = main_functions['draw_B_image'](bC, user_info, name, text, xml)
                except TypeError: 
                    img = main_functions['draw_B_image'](bC, user_info, name)
                
                if img:
                    img_byte_arr = io.BytesIO()
                    img.save(img_byte_arr, format='PNG')
                    result["_image_base64"] = base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')
            
            return jsonify({
                "code":200,
                "message":"请求成功",
                "data":result
            })
            
        except Exception as e:
            logging.error(f"❌ 执行失败: {e}")
            return jsonify({
                "code":500,
                "error":f"执行错误: {str(e)}"
            }),500
    
    elif request_type == 'help':
        return jsonify(get_api_help_document())
    
    elif request_type == 'data':
        # 获取谱面数据
        chart_data = get_chart_data()
        return jsonify({
            "code": 200,
            "message": "谱面数据获取成功",
            "data": chart_data
        })
    
    else: 
        return jsonify({"code":400,"message":"无效type参数"}),400

# 注册退出处理
def cleanup():
    """清理函数，在程序退出时调用"""
    logging.info("🧹 正在清理资源...")
    stop_scheduler()

atexit.register(cleanup)

if __name__ == '__main__':
    print("🚀 启动 Flask 服务器...")
    print("📍 访问 http://127.0.0.1:5001")
    
    # 初始化用户数据
    init_user_data()
    init_admin_config()
    
    # 显示页面索引信息
    pages = get_page_list()
    print("📄 配置的页面路由:")
    for page in pages:
        status = "✅" if page["exists"] else "❌"
        print(f"   {status} {page['route']} -> {page['filename']}")
    
    # 显示API帮助配置
    print("🔧 API帮助文档配置:")
    for param, description in API_HELP_CONFIG.items():
        print(f"   {param}: {description}")
    
    print("🔍 检查模块加载...")
    main_functions = load_main_module()
    if main_functions:
        print("✅ 模块检查通过")
        if 'update_phigros_data' in main_functions: 
            start_scheduler()
        else: 
            print("⚠️  未找到 update_phigros_data 函数，定时更新功能禁用")
    else: 
        print("❌ 模块检查失败，请检查 code/main.py")
    
    # 启动键盘监听
    keyboard_listener()
    
    try:
        app.run(debug=True, host='0.0.0.0', port=5001, use_reloader=False)
    except KeyboardInterrupt:
        print("\n🛑 接收到中断信号，正在关闭服务器...")
        stop_scheduler()
    finally:
        print("👋 服务器已关闭")