"""
基于YOLO的水果识别系统 - 后端服务
文档参考：requirement.md, spec.md, api.md
"""

import os
import json
import hashlib
import uuid
import time
from datetime import datetime

from flask import Flask, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
import base64
from io import BytesIO
from PIL import Image

app = Flask(__name__)

# 配置数据库（使用SQLite，无需额外安装）
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///fruit_recognition.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['RESULT_FOLDER'] = 'results'

db = SQLAlchemy(app)

# 确保目录存在
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['RESULT_FOLDER'], exist_ok=True)

# Token缓存（实际生产环境应使用Redis）
token_cache = {}

# ==================== 数据库模型 ====================

class User(db.Model):
    """用户表"""
    __tablename__ = 'user'
    user_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(32), nullable=False)  # MD5加密
    create_time = db.Column(db.DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'user_id': self.user_id,
            'username': self.username,
            'create_time': self.create_time.strftime('%Y-%m-%d %H:%M:%S')
        }

class Record(db.Model):
    """识别记录表"""
    __tablename__ = 'record'
    record_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False)
    img_url = db.Column(db.String(255), nullable=False)
    fruit_name = db.Column(db.String(100), nullable=False)
    confidence = db.Column(db.Float, nullable=False)
    recognize_time = db.Column(db.DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'record_id': self.record_id,
            'user_id': self.user_id,
            'img_url': self.img_url,
            'fruit_name': self.fruit_name,
            'confidence': self.confidence,
            'recognize_time': self.recognize_time.strftime('%Y-%m-%d %H:%M:%S')
        }

# ==================== 工具函数 ====================

def md5(text):
    """MD5加密"""
    return hashlib.md5(text.encode('utf-8')).hexdigest()

def generate_token(user_id):
    """生成Token"""
    token = md5(f"{user_id}_{time.time()}_{uuid.uuid4()}")
    token_cache[token] = user_id
    return token

def check_token():
    """校验Token"""
    token = request.headers.get('token')
    if not token:
        return False, 'Token为空'
    if token not in token_cache:
        return False, 'Token无效'
    return True, token_cache[token]

def del_cache_token(token):
    """删除Token缓存"""
    if token in token_cache:
        del token_cache[token]

def base64_to_image(base64_str):
    """Base64转图片"""
    try:
        # 移除可能的前缀
        if 'base64,' in base64_str:
            base64_str = base64_str.split('base64,')[1]
        img_data = base64.b64decode(base64_str)
        return Image.open(BytesIO(img_data))
    except Exception as e:
        return None

def save_server_image(img, folder='uploads'):
    """保存图片到服务器"""
    filename = f"{uuid.uuid4().hex}.jpg"
    # 获取配置key（使用单数形式）
    config_key = 'UPLOAD_FOLDER' if folder == 'uploads' else 'RESULT_FOLDER'
    filepath = os.path.join(app.config[config_key], filename)
    img.save(filepath, format='JPEG')
    return f"/{folder}/{filename}"

# ==================== YOLO模型模拟（实际项目中替换为真实YOLO模型） ====================

class MockYOLOModel:
    """模拟YOLO模型"""
    FRUITS = ['苹果', '香蕉', '橙子', '梨', '草莓', '葡萄', '西瓜', '桃子', '柠檬', '芒果']
    
    def predict(self, img):
        """模拟预测"""
        import random
        results = []
        # 随机返回1-3个水果
        num_fruits = random.randint(1, 3)
        selected_fruits = random.sample(self.FRUITS, num_fruits)
        
        for i, fruit in enumerate(selected_fruits):
            results.append({
                'name': fruit,
                'confidence': round(random.uniform(0.85, 0.99), 2),
                'box': [10 + i*50, 20 + i*30, 100 + i*50, 150 + i*30]
            })
        return results

yolo_model = MockYOLOModel()

def load_yolo_model():
    """加载YOLO模型"""
    return yolo_model

def parse_yolo_result(result):
    """解析YOLO结果"""
    return result

def draw_box(img, result):
    """绘制检测框（模拟）"""
    return img

# ==================== 用户模块接口 ====================

@app.route('/api/v1/user/register', methods=['POST'])
def user_register():
    """用户注册接口"""
    try:
        # 1.接收前端参数
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        # 2.参数非空校验
        if not username or not password:
            return jsonify({'code': 400, 'msg': '参数不能为空', 'data': None})
        
        # 3.判断用户名是否重复
        if User.query.filter_by(username=username).first():
            return jsonify({'code': 400, 'msg': '用户名已存在', 'data': None})
        
        # 4.MD5加密密码
        md5_pwd = md5(password)
        
        # 5.存入数据库
        new_user = User(username=username, password=md5_pwd)
        db.session.add(new_user)
        db.session.commit()
        
        # 6.返回结果
        return jsonify({'code': 200, 'msg': '注册成功', 'data': None})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'msg': f'服务器错误: {str(e)}', 'data': None})

@app.route('/api/v1/user/login', methods=['POST'])
def user_login():
    """用户登录接口"""
    try:
        # 1.接收参数
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({'code': 400, 'msg': '参数不能为空', 'data': None})
        
        # 2.密码加密比对
        md5_pwd = md5(password)
        
        # 3.查询用户
        user = User.query.filter_by(username=username, password=md5_pwd).first()
        if not user:
            return jsonify({'code': 400, 'msg': '账号或密码错误', 'data': None})
        
        # 4.生成Token
        token = generate_token(user.user_id)
        
        # 5.返回用户信息+token
        return jsonify({
            'code': 200, 
            'msg': '登录成功', 
            'data': {
                'user_id': user.user_id,
                'username': user.username,
                'token': token
            }
        })
    
    except Exception as e:
        return jsonify({'code': 500, 'msg': f'服务器错误: {str(e)}', 'data': None})

@app.route('/api/v1/user/logout', methods=['POST'])
def user_logout():
    """退出登录接口"""
    try:
        token = request.headers.get('token')
        del_cache_token(token)
        return jsonify({'code': 200, 'msg': '退出成功', 'data': None})
    except Exception as e:
        return jsonify({'code': 500, 'msg': f'服务器错误: {str(e)}', 'data': None})

# ==================== 水果识别核心接口 ====================

@app.route('/api/v1/fruit/detect', methods=['POST'])
def fruit_detect():
    """水果识别接口"""
    try:
        # 1.校验token
        success, user_id = check_token()
        if not success:
            return jsonify({'code': 401, 'msg': user_id, 'data': None})
        
        # 2.接收base64图片
        data = request.get_json()
        img_base64 = data.get('img_base64')
        req_user_id = data.get('user_id')
        
        if not img_base64 or not req_user_id:
            return jsonify({'code': 400, 'msg': '参数不能为空', 'data': None})
        
        # 3.base64转图片并保存
        img = base64_to_image(img_base64)
        if img is None:
            return jsonify({'code': 400, 'msg': '图片解析失败', 'data': None})
        
        # 压缩图片
        img.thumbnail((640, 640))
        save_path = save_server_image(img)
        
        # 4.YOLO模型推理
        model = load_yolo_model()
        result = model.predict(img)
        
        # 5.解析检测框、类别、置信度
        fruit_list = parse_yolo_result(result)
        
        # 6.绘制标注框生成结果图
        result_img = draw_box(img, result)
        result_path = save_server_image(result_img, 'results')
        
        # 7.保存识别记录到数据库（只在识别成功时保存）
        for fruit in fruit_list:
            record = Record(
                user_id=req_user_id,
                img_url=save_path,
                fruit_name=fruit['name'],
                confidence=fruit['confidence']
            )
            db.session.add(record)
        db.session.commit()
        
        # 8.返回结果
        return jsonify({
            'code': 200,
            'msg': '识别成功',
            'data': {
                'result_img': f"http://localhost:5000{result_path}",
                'fruit_list': fruit_list
            }
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'msg': f'服务器错误: {str(e)}', 'data': None})

# ==================== 历史记录模块接口 ====================

@app.route('/api/v1/record/list', methods=['GET'])
def record_list():
    """获取历史记录接口"""
    try:
        # 1.校验token
        success, user_id = check_token()
        if not success:
            return jsonify({'code': 401, 'msg': user_id, 'data': None})
        
        # 2.获取用户ID参数
        req_user_id = request.args.get('user_id', type=int)
        if not req_user_id:
            return jsonify({'code': 400, 'msg': '参数不能为空', 'data': None})
        
        # 3.查询用户记录（按时间倒序）
        records = Record.query.filter_by(user_id=req_user_id)\
                            .order_by(Record.recognize_time.desc())\
                            .all()
        
        # 4.返回结果
        return jsonify({
            'code': 200,
            'msg': '查询成功',
            'data': [record.to_dict() for record in records]
        })
    
    except Exception as e:
        return jsonify({'code': 500, 'msg': f'服务器错误: {str(e)}', 'data': None})

@app.route('/api/v1/record/delete', methods=['POST'])
def record_delete():
    """删除历史记录接口"""
    try:
        # 1.校验token
        success, user_id = check_token()
        if not success:
            return jsonify({'code': 401, 'msg': user_id, 'data': None})
        
        # 2.接收参数
        data = request.get_json()
        record_id = data.get('record_id')
        
        if not record_id:
            return jsonify({'code': 400, 'msg': '参数不能为空', 'data': None})
        
        # 3.查询记录
        record = Record.query.get(record_id)
        if not record:
            return jsonify({'code': 400, 'msg': '记录不存在', 'data': None})
        
        # 4.删除服务器图片
        img_path = record.img_url.lstrip('/')
        if os.path.exists(img_path):
            os.remove(img_path)
        
        # 5.删除数据库记录
        db.session.delete(record)
        db.session.commit()
        
        # 6.返回结果
        return jsonify({'code': 200, 'msg': '删除成功', 'data': None})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'msg': f'服务器错误: {str(e)}', 'data': None})

# ==================== 静态文件服务 ====================

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/results/<filename>')
def result_file(filename):
    return send_from_directory(app.config['RESULT_FOLDER'], filename)

# ==================== 初始化数据库 ====================

def init_db():
    """初始化数据库"""
    with app.app_context():
        db.create_all()
        print('数据库初始化完成')

# ==================== 主函数 ====================

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)