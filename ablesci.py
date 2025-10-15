#!/usr/bin/env python
# cron:40 7,21 * * *
# new Env("科研通签到")
# coding=utf-8

"""
AbleSci自动签到脚本 
创建日期：2025年8月8日
更新日期：2025年9月2日 >> 修复日志输出时间为北京时间 ; 修复签到前后用户信息显示 ; 优化登录失败处理 ; 优化签到已签到处理
更新日期：2025年9月3日 >> 保护隐私，不在日志中显示完整邮箱和用户名
作者：daitcl
"""

import os
import sys
import time
import requests
from bs4 import BeautifulSoup
import json
import datetime

# 检测运行环境
IS_GITHUB_ACTIONS = os.getenv("GITHUB_ACTIONS") == "true"
IS_QINGLONG = not IS_GITHUB_ACTIONS

# 设置环境变量名称
ENV_ACCOUNTS = "ABLESCI_ACCOUNTS" 

# 隐私保护函数
def protect_privacy(text):
    """保护隐私信息，隐藏部分邮箱和用户名"""
    if not text:
        return text
        
    # 邮箱隐私处理
    if "@" in text:
        parts = text.split("@")
        if len(parts[0]) > 2:
            protected_local = parts[0][:2] + "***"
        else:
            protected_local = "***"
        return f"{protected_local}@{parts[1]}"
    
    # 用户名隐私处理
    if len(text) > 2:
        return text[:2] + "***"
    else:
        return "***"

# 消息通知系统
class Notifier:
    def __init__(self):
        self.log_content = []
        self.title = "科研通签到"
        self.notify_enabled = False
        
        # 在所有环境尝试导入通知模块
        try:
            # 添加当前目录到系统路径确保能导入
            sys.path.append(os.path.dirname(os.path.abspath(__file__)))
            from sendNotify import send
            self.send = send
            self.notify_enabled = True
        except ImportError:
            # 在 GitHub Actions 中可能路径不同
            try:
                # 尝试从父目录导入
                parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                sys.path.append(parent_dir)
                from sendNotify import send
                self.send = send
                self.notify_enabled = True
            except Exception as e:
                self.log(f"导入通知模块失败: {str(e)}", "warning")
                self.notify_enabled = False
    
    def log(self, message, level="info"):
        """格式化日志输出并保存到内容 - 使用北京时间"""
        # 获取UTC时间并转换为北京时间 (UTC+8)
        utc_now = datetime.datetime.utcnow()
        beijing_time = utc_now + datetime.timedelta(hours=8)
        timestamp = beijing_time.strftime("%Y-%m-%d %H:%M:%S")
        
        level_map = {
            "info": "ℹ️",
            "success": "✅",
            "error": "❌",
            "warning": "⚠️"
        }
        symbol = level_map.get(level, "ℹ️")
        log_message = f"[{timestamp}] {symbol} {message}"
        print(log_message)
        self.log_content.append(log_message)
        
    def send_notification(self, title=None):
        """发送通知，支持传入动态标题"""
        if not self.notify_enabled:
            self.log("通知功能未启用", "warning")
            return False
    
        # 如果传入了新标题，则使用新标题，否则使用默认标题
        final_title = title if title else self.title
        content = "\n".join(self.log_content)
    
        try:
            self.send(final_title, content)
            self.log(f"通知发送成功", "success")
            return True
        except Exception as e:
            self.log(f"发送通知失败: {str(e)}", "error")
            return False
    
    def get_content(self):
        """获取日志内容"""
        return "\n".join(self.log_content)

class AbleSciAuto:
    def __init__(self, email, password):
        self.session = requests.Session()
        self.email = email
        self.password = password
        self.username = None  # 存储用户名
        self.points = None    # 存储当前积分
        self.sign_days = None # 存储连续签到天数
        self.status = "失败"  # 存储最终状态
        self.notifier = Notifier()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
            "sec-ch-ua": "\"Not)A;Brand\";v=\"8\", \"Chromium\";v=\"138\", \"Google Chrome\";v=\"138\"",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "\"Windows\"",
            "X-Requested-With": "XMLHttpRequest"
        }
        self.start_time = time.time()
        # 使用隐私保护函数处理邮箱显示
        protected_email = protect_privacy(self.email)
        self.notifier.log(f"处理账号: {protected_email}", "info")
        
    def log(self, message, level="info"):
        """代理日志到通知系统"""
        self.notifier.log(message, level)
        
    def get_csrf_token(self):
        """获取CSRF令牌"""
        login_url = "https://www.ablesci.com/site/login"
        try:
            response = self.session.get(login_url, headers=self.headers, timeout=30)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                csrf_token = soup.find('input', {'name': '_csrf'})
                if csrf_token:
                    return csrf_token.get('value', '')
            else:
                self.log(f"获取CSRF令牌失败，状态码: {response.status_code}", "error")
        except Exception as e:
            self.log(f"获取CSRF令牌时出错: {str(e)}", "error")
        return ''

    def login(self):
        """执行登录操作"""
        if not self.email or not self.password:
            self.log("邮箱或密码为空", "error")
            return False
            
        login_url = "https://www.ablesci.com/site/login"
        csrf_token = self.get_csrf_token()
        
        if not csrf_token:
            self.log("无法获取CSRF令牌", "error")
            return False
        
        login_data = {
            "_csrf": csrf_token,
            "email": self.email,
            "password": self.password,
            "remember": "off"
        }
        
        headers = self.headers.copy()
        headers["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"
        headers["Referer"] = "https://www.ablesci.com/site/login"
        
        try:
            response = self.session.post(
                login_url,
                data=login_data,
                headers=headers,
                timeout=30
            )
            
            # 检查登录结果
            if response.status_code == 200:
                try:
                    # 尝试解析JSON响应
                    result = response.json()
                    if result.get("code") == 0:
                        self.log(f"登录成功: {result.get('msg')}", "success")
                        return True
                    else:
                        self.log(f"登录失败: {result.get('msg')}", "error")
                except json.JSONDecodeError:
                    # 如果不是JSON，可能是HTML响应
                    if "退出" in response.text:  # 检查登录成功标志
                        self.log("登录成功", "success")
                        return True
                    else:
                        self.log("登录失败: 无法解析响应", "error")
            else:
                self.log(f"登录请求失败，状态码: {response.status_code}", "error")
        except Exception as e:
            self.log(f"登录过程中出错: {str(e)}", "error")
        return False

    def get_user_info(self):
        """获取用户信息（包括用户名、积分和签到天数）"""
        # 访问首页（登录后通常会显示用户名）
        home_url = "https://www.ablesci.com/"
        headers = self.headers.copy()
        headers["Referer"] = "https://www.ablesci.com/"
        
        try:
            response = self.session.get(home_url, headers=headers, timeout=30)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 1. 获取用户名
                username_element = soup.select_one('.mobile-hide.able-head-user-vip-username')
                if username_element:
                    self.username = username_element.text.strip()
                    # 使用隐私保护函数处理用户名显示
                    protected_username = protect_privacy(self.username)
                    self.log(f"用户名: {protected_username}", "info")
                else:
                    self.log("无法定位用户名元素", "warning")
                
                # 2. 获取积分信息
                points_element = soup.select_one('#user-point-now')
                if points_element:
                    self.points = points_element.text.strip()
                    self.log(f"当前积分: {self.points}", "info")
                else:
                    self.log("无法获取积分信息", "warning")
                
                # 3. 获取连续签到天数
                sign_days_element = soup.select_one('#sign-count')
                if sign_days_element:
                    self.sign_days = sign_days_element.text.strip()
                    self.log(f"连续签到天数: {self.sign_days}", "info")
                else:
                    self.log("无法获取连续签到天数", "warning")
                
                return True
            else:
                self.log(f"获取首页失败，状态码: {response.status_code}", "error")
        except Exception as e:
            self.log(f"获取用户信息时出错: {str(e)}", "error")
        return False

    def sign_in(self):
        """执行签到操作 - 修复已签到处理"""
        sign_url = "https://www.ablesci.com/user/sign"
        headers = self.headers.copy()
        headers["Referer"] = "https://www.ablesci.com/"
        
        try:
            response = self.session.get(sign_url, headers=headers, timeout=30)
            if response.status_code == 200:
                try:
                    result = response.json()
                    if result.get("code") == 0:
                        self.log(f"签到成功: {result.get('msg')}", "success")
                        self.status = "成功"
                        
                        # 尝试从响应中获取新的积分和签到天数
                        data = result.get("data", {})
                        if data:
                            if "points" in data:
                                self.points = data["points"]
                                self.log(f"更新积分: {self.points}", "info")
                            if "sign_days" in data:
                                self.sign_days = data["sign_days"]
                                self.log(f"更新连续签到天数: {self.sign_days}", "info")
                        
                        return True
                    else:
                        msg = result.get('msg', '')
                        # 特殊处理已签到情况
                        if "已经签到" in msg or "已签到" in msg:
                            self.log(f"今日已签到: {msg}", "info")
                            self.status = "已签到"
                            return True
                        else:
                            self.log(f"签到失败: {msg}", "error")
                            self.status = "失败"
                except json.JSONDecodeError:
                    self.log("签到响应不是有效的JSON", "error")
            else:
                self.log(f"签到请求失败，状态码: {response.status_code}", "error")
        except Exception as e:
            self.log(f"签到过程中出错: {str(e)}", "error")
        return False

    def display_summary(self, is_before_sign=False):
        """显示执行摘要"""
        elapsed = round(time.time() - self.start_time, 2)
        title = "签到前信息" if is_before_sign else "签到后信息"
        self.log("=" * 50)
        self.log(f"用户 {protect_privacy(self.username)} {title}:")
        if self.username:
            # 使用隐私保护函数处理用户名显示
            protected_username = protect_privacy(self.username)
            self.log(f"  • 用户名: {protected_username}")
        if self.points:
            self.log(f"  • 当前积分: {self.points}")
        if self.sign_days:
            self.log(f"  • 连续签到: {self.sign_days}天")
        self.log(f"  • 执行耗时: {elapsed}秒")
        self.log("=" * 50)
        
        # 添加额外空行
        self.log("")
    def run(self):
        """执行完整的登录和签到流程，并返回结果"""
        if self.login():
            self.get_user_info()
            self.display_summary(is_before_sign=True)
    
            sign_result = self.sign_in()
    
            # 只有在签到成功时才刷新信息，已签到或失败则无需刷新
            if sign_result and self.status == "成功":
                self.log("签到成功，刷新用户信息...", "info")
                time.sleep(2)
                self.get_user_info()
                self.display_summary(is_before_sign=False)
    
        # 返回一个包含所有重要信息的字典
        return {
            "log": self.notifier.get_content(),
            "status": self.status,
            "points": self.points
        }

def get_accounts():
    """从环境变量获取所有账号"""
    accounts_env = os.getenv(ENV_ACCOUNTS)
    if not accounts_env:
        return []
    
    accounts = []
    # 支持多种分隔符：换行符、分号、逗号
    for line in accounts_env.splitlines():
        # 跳过空行
        if not line.strip():
            continue
            
        # 支持分号和逗号分隔的多个账号
        if ";" in line:
            accounts.extend(line.split(";"))
        elif "," in line:
            accounts.extend(line.split(","))
        else:
            accounts.append(line)
    
    # 验证账号格式并分离邮箱密码
    valid_accounts = []
    for account in accounts:
        # 支持邮箱和密码用冒号、分号或竖线分隔
        if ":" in account:
            email, password = account.split(":", 1)
        elif ";" in account:
            email, password = account.split(";", 1)
        elif "|" in account:
            email, password = account.split("|", 1)
        else:
            continue  # 跳过格式不正确的账号
            
        email = email.strip()
        password = password.strip()
        
        if email and password:
            valid_accounts.append((email, password))
    
    return valid_accounts

def main():
    """主函数，处理多账号签到"""
    global_notifier = Notifier()
    global_notifier.log("科研通多账号签到任务开始", "info")

    accounts = get_accounts()
    if not accounts:
        global_notifier.log("未找到有效的账号配置", "error")
        global_notifier.log(f"请设置环境变量 {ENV_ACCOUNTS}，格式为：邮箱1:密码1", "warning")
        if global_notifier.notify_enabled:
            global_notifier.send_notification()
        return

    global_notifier.log(f"找到 {len(accounts)} 个账号", "info")

    all_logs = []
    is_already_signed_for_all = True # 新增一个标志，假设所有账号都已签到

    for i, (email, password) in enumerate(accounts, 1):
        global_notifier.log(f"\n===== 开始处理第 {i}/{len(accounts)} 个账号 =====", "info")

        automator = AbleSciAuto(email, password)
        account_log = automator.run()
        all_logs.append(account_log)

        # 检查当前账号是否不是“已签到”状态
        if "今日已签到" not in account_log:
            is_already_signed_for_all = False # 只要有一个不是“已签到”，就将标志设为False

        global_notifier.log(f"===== 完成第 {i}/{len(accounts)} 个账号处理 =====", "info")

    global_notifier.log("\n===== 所有账号处理完成 =====", "info")
    full_log = "\n\n".join(all_logs)

    # 只有在并非“所有账号都已签到”的情况下，才发送通知
    if not is_already_signed_for_all:
        if global_notifier.notify_enabled:
            summary_notifier = Notifier()
            summary_notifier.log_content = full_log.splitlines()
            summary_notifier.send_notification()
    else:
        global_notifier.log("所有账号今日均已签到，无需发送通知。")

    if IS_GITHUB_ACTIONS:
        print(f"::set-output name=log_content::{full_log}")
        
if __name__ == "__main__":
    main()
