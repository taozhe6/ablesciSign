#!/usr/bin/env python3
# _*_ coding:utf-8 _*_

import os
import requests
import json
import urllib.parse

# 通知服务配置
SCKEY = os.getenv("SCKEY", "")  # Server酱的SCKEY
XZKEY = os.getenv("XZKEY", "")  # 息知的XZKEY
PUSH_PLUS_TOKEN = os.getenv("PUSH_PLUS_TOKEN", "")  # PushPlus的TOKEN

# 消息容器
message_info = ''''''

def serverJ(title, content):
    """Server酱通知"""
    if not SCKEY:
        print("Server酱的SCKEY未设置")
        return
    
    print("Server酱服务启动")
    data = {
        "text": title,
        "desp": content.replace("\n", "\n\n")
    }
    response = requests.post(f"https://sctapi.ftqq.com/{SCKEY}.send", data=data).json()
    if response.get('code') == 0 or response.get('data', {}).get('errno') == 0:
        print('Server酱推送成功！')
    else:
        print('Server酱推送失败！')

def xizhi(title, content):
    """息知通知"""
    if not XZKEY:
        print("息知的XZKEY未设置")
        return
    
    print("息知服务启动")
    headers = {'Content-Type': 'application/json'}
    json_data = {
        'title': title,
        'content': content.replace("\n", "\n\n")
    }
    data = json.dumps(json_data).encode('utf-8')
    try:
        response = requests.post(f"https://xizhi.qqoq.net/{XZKEY}.send", data=data, headers=headers)
        if response.status_code == 200:
            print('息知推送成功！')
        else:
            print(f'息知推送失败，状态码: {response.status_code}')
    except Exception as e:
        print(f'息知推送失败: {str(e)}')

def pushplus_bot(title, content):
    """PushPlus通知"""
    if not PUSH_PLUS_TOKEN:
        print("PushPlus的TOKEN未设置")
        return
    
    print("PushPlus服务启动")
    url = 'http://www.pushplus.plus/send'
    data = {
        "token": PUSH_PLUS_TOKEN,
        "title": title,
        "content": content
        "channel": "mail"
        "webhook":"" 
    }
    headers = {'Content-Type': 'application/json'}
    try:
        response = requests.post(url, json=data, headers=headers)
        result = response.json()
        if result.get('code') == 200:
            print('PushPlus推送成功！')
        else:
            print(f'PushPlus推送失败: {result.get("msg", "未知错误")}')
    except Exception as e:
        print(f'PushPlus推送失败: {str(e)}')

def send(title, content):
    """
    发送通知
    :param title: 通知标题
    :param content: 通知内容
    """
    # 记录日志
    print(f"通知标题: {title}")
    print(f"通知内容:\n{content}")
    
    # 依次尝试三种通知方式
    if SCKEY:
        serverJ(title, content)
    
    if XZKEY:
        xizhi(title, content)
    
    if PUSH_PLUS_TOKEN:
        pushplus_bot(title, content)
    
    # 如果没有设置任何通知方式
    if not SCKEY and not XZKEY and not PUSH_PLUS_TOKEN:
        print("未配置任何通知方式，跳过通知发送")

if __name__ == '__main__':
    # 测试通知
    send("测试通知", "这是一条测试通知消息")
