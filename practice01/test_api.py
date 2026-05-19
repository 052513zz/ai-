"""
水果识别系统测试脚本
按照 test.md 的测试计划进行测试
"""

import requests
import json
import base64
from PIL import Image
from io import BytesIO

# 基础URL
BASE_URL = 'http://localhost:5000/api/v1'

# 测试结果记录
test_results = []

def test_case(name):
    """测试用例装饰器"""
    def decorator(test_func):
        def wrapper():
            try:
                result = test_func()
                test_results.append({'name': name, 'result': '通过', 'msg': result})
                print(f"✅ {name}: 通过 - {result}")
                return True
            except Exception as e:
                test_results.append({'name': name, 'result': '失败', 'msg': str(e)})
                print(f"❌ {name}: 失败 - {str(e)}")
                return False
        return wrapper
    return decorator

# ==================== 用户模块测试 ====================

@test_case('U001 - 正常注册')
def test_register():
    data = {'username': 'test_user', 'password': '123456'}
    response = requests.post(f'{BASE_URL}/user/register', json=data)
    assert response.json()['code'] == 200, f"注册失败: {response.json()}"
    return '注册成功'

@test_case('U002 - 重复注册')
def test_register_duplicate():
    data = {'username': 'test_user', 'password': '123456'}
    response = requests.post(f'{BASE_URL}/user/register', json=data)
    assert response.json()['code'] == 400, "应该拦截重复注册"
    assert '用户名已存在' in response.json()['msg']
    return '重复注册拦截成功'

@test_case('U003 - 正常登录')
def test_login():
    data = {'username': 'test_user', 'password': '123456'}
    response = requests.post(f'{BASE_URL}/user/login', json=data)
    assert response.json()['code'] == 200, f"登录失败: {response.json()}"
    assert 'token' in response.json()['data']
    global token, user_id
    token = response.json()['data']['token']
    user_id = response.json()['data']['user_id']
    return '登录成功'

@test_case('U004 - 错误密码登录')
def test_login_wrong_password():
    data = {'username': 'test_user', 'password': 'wrong_pass'}
    response = requests.post(f'{BASE_URL}/user/login', json=data)
    assert response.json()['code'] == 400, "应该登录失败"
    return '错误密码拦截成功'

# ==================== 水果识别模块测试 ====================

@test_case('F001 - 水果识别')
def test_fruit_detect():
    # 创建一张测试图片
    img = Image.new('RGB', (200, 200), color='red')
    buffered = BytesIO()
    img.save(buffered, format='JPEG')
    img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
    
    headers = {'token': token}
    data = {'img_base64': img_base64, 'user_id': user_id}
    response = requests.post(f'{BASE_URL}/fruit/detect', json=data, headers=headers)
    
    assert response.json()['code'] == 200, f"识别失败: {response.json()}"
    assert 'fruit_list' in response.json()['data']
    return '识别成功'

# ==================== 历史记录模块测试 ====================

@test_case('R001 - 查询历史记录')
def test_record_list():
    headers = {'token': token}
    params = {'user_id': user_id}
    response = requests.get(f'{BASE_URL}/record/list', params=params, headers=headers)
    
    assert response.json()['code'] == 200, f"查询失败: {response.json()}"
    assert isinstance(response.json()['data'], list)
    return '查询成功'

@test_case('R002 - 删除历史记录')
def test_record_delete():
    # 先获取记录
    headers = {'token': token}
    params = {'user_id': user_id}
    response = requests.get(f'{BASE_URL}/record/list', params=params, headers=headers)
    records = response.json()['data']
    
    if records:
        record_id = records[0]['record_id']
        data = {'record_id': record_id}
        response = requests.post(f'{BASE_URL}/record/delete', json=data, headers=headers)
        assert response.json()['code'] == 200, f"删除失败: {response.json()}"
        return '删除成功'
    else:
        return '无记录可删除（跳过）'

@test_case('U005 - 退出登录')
def test_logout():
    headers = {'token': token}
    response = requests.post(f'{BASE_URL}/user/logout', headers=headers)
    assert response.json()['code'] == 200, f"退出失败: {response.json()}"
    return '退出成功'

# ==================== 参数异常测试 ====================

@test_case('P001 - 空参数注册')
def test_register_empty_params():
    data = {'username': '', 'password': ''}
    response = requests.post(f'{BASE_URL}/user/register', json=data)
    assert response.json()['code'] == 400, "应该拦截空参数"
    return '空参数拦截成功'

@test_case('P002 - 无效Token请求')
def test_invalid_token():
    headers = {'token': 'invalid_token_12345'}
    params = {'user_id': user_id}
    response = requests.get(f'{BASE_URL}/record/list', params=params, headers=headers)
    assert response.json()['code'] == 401, "应该拦截无效Token"
    return '无效Token拦截成功'

def run_tests():
    """运行所有测试"""
    print("=" * 60)
    print("水果识别系统 API 测试")
    print("=" * 60)
    
    # 运行测试
    test_register()
    test_register_duplicate()
    test_login()
    test_login_wrong_password()
    test_fruit_detect()
    test_record_list()
    test_record_delete()
    test_logout()
    test_register_empty_params()
    test_invalid_token()
    
    # 输出测试报告
    print("\n" + "=" * 60)
    print("测试报告")
    print("=" * 60)
    
    passed = sum(1 for r in test_results if r['result'] == '通过')
    total = len(test_results)
    
    for result in test_results:
        status = '✅' if result['result'] == '通过' else '❌'
        print(f"{status} {result['name']}: {result['result']}")
        if result['msg']:
            print(f"     {result['msg']}")
    
    print("\n" + "=" * 60)
    print(f"测试结果: {passed}/{total} 通过")
    print("=" * 60)
    
    return passed == total

if __name__ == '__main__':
    success = run_tests()
    exit(0 if success else 1)