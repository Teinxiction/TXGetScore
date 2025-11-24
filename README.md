# TXGetScore
## 项目说明
1. 本项目由TeinxictionMC开发
2. 本项目使用了 [VGMStream](https://github.com/vgmstream/vgmstream)，[PhigrosResource](https://github.com/7aGiven/Phigros_Resource)以及[PhiCloudAction](https://github.com/wms26/Phi-CloudAction-python)
## 使用方法
1. 安装所有依赖
```bash
pip install -r requirements.txt
```
2. 修改配置
   1. 请删除`AdminPassword.txt`和`admin_salt.txt`这两个测试使用的默认管理员密码存储下
   2. 打开`app.py`并且修改88行的`DEFAULT_PASSWORD`为你自己的管理员密码

3. 运行
```bash
python main.py
```
4. 初始化
打开**127.0.0.1/admin114514**，输入你的用户名和密码，登录后点击`手动更新数据`按钮，随后等待终端提示所有代码执行完成
5. 安全选项(选做)
   1. 立即停止服务器，打开app.py，将`DEFAULT_USERNAME`和`DEFAULT_PASSWORD`行设为其他字符，例如
   ```python
   DEFAULT_USERNAME = 'FakeUserName'
   DEFAULT_PASSWORD = 'FakePassword'
   ```

   因为密码应该只存在于新生成的`AdminPassword.txt`和`admin_salt.txt`文件
   2. 重新开启服务器
   ```bash
	python main.py
	```
## 实现功能
### 用户界面
- [x] 生成B30图片
- [x] 生成文字B30
- [x] 查询曲目信息
- [ ] 自定义B30图片文案和XML
- [x] 查询单曲成绩 
### API
- [x] 生成B30图片
- [x] 生成文字B30
- [x] 查询曲目信息
- [x] 自定义B30图片文案和XML
- [x] 查询单曲成绩 
## 官网(应该算是吧)
[官网？](https://killkpa.miraheze.org/wiki/TXGetScore)