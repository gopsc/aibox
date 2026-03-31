#!/usr/bin/env python3
"""
163邮箱发送/接收工具
功能：发送邮件、接收邮件、查看收件箱
凭证文件：~/.cert/163mail.json（格式：{"username": "your_email@163.com", "password": "your_password"}）
支持流式输出结果
"""

import os
import sys
import json
import argparse
import imaplib
import smtplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header
from email.utils import parseaddr
import time
from datetime import datetime, timedelta
import base64
import re

# ==================== 配置常量 ====================

# 凭证文件路径
CREDENTIALS_FILE = os.path.expanduser("~/.cert/163mail.json")

# 163邮箱服务器配置
IMAP_SERVER = "imap.163.com"
IMAP_PORT = 993
SMTP_SERVER = "smtp.163.com"
SMTP_PORT = 465  # SSL端口

# ==================== 凭证管理 ====================

def load_credentials():
    """加载163邮箱凭证"""
    if not os.path.exists(CREDENTIALS_FILE):
        return None, f"❌ 凭证文件不存在: {CREDENTIALS_FILE}\n请创建该文件，格式：{{\"username\": \"your_email@163.com\", \"password\": \"your_password\"}}"
    
    try:
        with open(CREDENTIALS_FILE, 'r', encoding='utf-8') as f:
            creds = json.load(f)
        
        username = creds.get('username')
        password = creds.get('password')
        
        if not username or not password:
            return None, "❌ 凭证文件格式错误，需要包含 username 和 password 字段"
        
        # 验证邮箱格式
        if '@' not in username:
            username = f"{username}@163.com"
        
        return (username, password), None
    except json.JSONDecodeError:
        return None, f"❌ 凭证文件JSON格式错误: {CREDENTIALS_FILE}"
    except Exception as e:
        return None, f"❌ 读取凭证文件失败: {str(e)}"

# ==================== 邮件发送功能 ====================

def send_email(to_addrs, subject, body, cc_addrs=None, bcc_addrs=None, html=False):
    """
    发送邮件
    
    Args:
        to_addrs: 收件人地址（字符串或列表）
        subject: 邮件主题
        body: 邮件正文
        cc_addrs: 抄送地址（字符串或列表）
        bcc_addrs: 密送地址（字符串或列表）
        html: 是否HTML格式
    
    Returns:
        (success, message)
    """
    # 加载凭证
    creds, error = load_credentials()
    if error:
        return False, error
    
    username, password = creds
    
    try:
        # 处理收件人
        if isinstance(to_addrs, str):
            to_addrs = [to_addrs]
        
        # 处理抄送
        cc_list = []
        if cc_addrs:
            if isinstance(cc_addrs, str):
                cc_list = [cc_addrs]
            else:
                cc_list = cc_addrs
        
        # 处理密送
        bcc_list = []
        if bcc_addrs:
            if isinstance(bcc_addrs, str):
                bcc_list = [bcc_addrs]
            else:
                bcc_list = bcc_addrs
        
        # 创建邮件
        msg = MIMEMultipart('alternative')
        msg['From'] = username
        msg['To'] = ', '.join(to_addrs)
        msg['Subject'] = subject
        msg['Date'] = email.utils.formatdate(localtime=True)
        
        if cc_list:
            msg['Cc'] = ', '.join(cc_list)
        
        # 添加正文
        if html:
            msg.attach(MIMEText(body, 'html', 'utf-8'))
        else:
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        # 所有收件人（用于SMTP发送）
        all_recipients = to_addrs + cc_list + bcc_list
        
        # 连接SMTP服务器
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, timeout=30) as server:
            server.login(username, password)
            server.sendmail(username, all_recipients, msg.as_string())
        
        # 构建成功消息
        result = f"✅ 邮件发送成功!\n"
        result += f"   📤 发件人: {username}\n"
        result += f"   📥 收件人: {', '.join(to_addrs)}\n"
        result += f"   📧 主题: {subject}\n"
        if cc_list:
            result += f"   👥 抄送: {', '.join(cc_list)}\n"
        result += f"   📏 正文长度: {len(body)} 字符"
        
        return True, result
        
    except smtplib.SMTPAuthenticationError:
        return False, "❌ SMTP认证失败，请检查邮箱密码。\n注意：163邮箱需要使用授权码而不是登录密码"
    except smtplib.SMTPException as e:
        return False, f"❌ SMTP错误: {str(e)}"
    except Exception as e:
        return False, f"❌ 发送邮件失败: {str(e)}"

# ==================== 邮件接收功能 ====================

def decode_mime_header(header):
    """解码MIME邮件头"""
    if header is None:
        return ""
    
    decoded_parts = decode_header(header)
    result = []
    for content, charset in decoded_parts:
        if isinstance(content, bytes):
            if charset:
                try:
                    result.append(content.decode(charset))
                except:
                    result.append(content.decode('utf-8', errors='ignore'))
            else:
                try:
                    result.append(content.decode('utf-8', errors='ignore'))
                except:
                    result.append(content.decode('gbk', errors='ignore'))
        else:
            result.append(content)
    return ' '.join(result)

def get_email_body(msg):
    """获取邮件正文"""
    body = ""
    html_body = ""
    
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))
            
            # 跳过附件
            if "attachment" in content_disposition:
                continue
            
            try:
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or 'utf-8'
                    try:
                        decoded = payload.decode(charset, errors='ignore')
                    except:
                        decoded = payload.decode('utf-8', errors='ignore')
                    
                    if content_type == "text/plain":
                        body += decoded
                    elif content_type == "text/html":
                        html_body += decoded
            except:
                continue
    else:
        content_type = msg.get_content_type()
        try:
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or 'utf-8'
                decoded = payload.decode(charset, errors='ignore')
                if content_type == "text/plain":
                    body = decoded
                elif content_type == "text/html":
                    html_body = decoded
        except:
            pass
    
    # 优先返回纯文本，如果没有则返回HTML
    return body if body else html_body

def fetch_emails(limit=10, folder="INBOX", mark_seen=False, since_days=None):
    """
    获取邮件列表
    
    Args:
        limit: 获取数量
        folder: 邮件夹（INBOX, Sent, Drafts等）
        mark_seen: 是否标记为已读
        since_days: 获取最近几天的邮件
    
    Returns:
        (success, result)
    """
    # 加载凭证
    creds, error = load_credentials()
    if error:
        return False, error
    
    username, password = creds
    
    try:
        # 连接IMAP服务器
        imap = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT, timeout=30)
        imap.login(username, password)
        
        # 选择邮件夹
        status, messages = imap.select(folder)
        if status != 'OK':
            imap.close()
            imap.logout()
            return False, f"❌ 无法打开邮件夹 {folder}"
        
        # 构建搜索条件
        search_criteria = 'ALL'
        if since_days:
            date = (datetime.now() - timedelta(days=since_days)).strftime("%d-%b-%Y")
            search_criteria = f'SINCE "{date}"'
        
        # 搜索邮件
        status, message_ids = imap.search(None, search_criteria)
        if status != 'OK':
            imap.close()
            imap.logout()
            return False, "❌ 搜索邮件失败"
        
        # 获取邮件ID列表
        msg_ids = message_ids[0].split()
        total = len(msg_ids)
        
        if total == 0:
            imap.close()
            imap.logout()
            return True, f"📭 邮件夹 '{folder}' 中没有邮件"
        
        # 获取最新的limit封邮件
        start_idx = max(0, total - limit)
        msg_ids_to_fetch = msg_ids[start_idx:]
        
        emails = []
        for i, msg_id in enumerate(reversed(msg_ids_to_fetch)):  # 从最新的开始
            try:
                # 获取邮件
                status, msg_data = imap.fetch(msg_id, '(RFC822)')
                if status != 'OK':
                    continue
                
                # 解析邮件
                email_body = msg_data[0][1]
                msg = email.message_from_bytes(email_body)
                
                # 解码邮件头
                subject = decode_mime_header(msg.get('Subject', '无主题'))
                from_addr = decode_mime_header(msg.get('From', '未知发件人'))
                to_addr = decode_mime_header(msg.get('To', '未知收件人'))
                date_str = msg.get('Date', '')
                
                # 解析日期
                try:
                    date_tuple = email.utils.parsedate_tz(date_str)
                    if date_tuple:
                        date = datetime.fromtimestamp(email.utils.mktime_tz(date_tuple))
                        date_formatted = date.strftime("%Y-%m-%d %H:%M:%S")
                    else:
                        date_formatted = date_str
                except:
                    date_formatted = date_str
                
                # 检查是否已读
                is_seen = '\\Seen' in msg.get('Flags', '')
                
                # 获取正文预览
                body = get_email_body(msg)
                preview = body[:200] + "..." if len(body) > 200 else body
                
                # 提取发件人名称和邮箱
                name, email_addr = parseaddr(from_addr)
                
                emails.append({
                    'id': msg_id.decode() if isinstance(msg_id, bytes) else str(msg_id),
                    'index': i + 1,
                    'subject': subject,
                    'from': from_addr,
                    'from_name': name or email_addr,
                    'from_email': email_addr,
                    'to': to_addr,
                    'date': date_formatted,
                    'preview': preview,
                    'is_seen': is_seen,
                    'has_attachments': msg.get_content_maintype() == 'multipart' and any(part.get_filename() for part in msg.walk())
                })
                
                # 如果不标记为已读，需要取消\Seen标志
                if not mark_seen and not is_seen:
                    imap.store(msg_id, '-FLAGS', '\\Seen')
                    
            except Exception as e:
                continue
        
        imap.close()
        imap.logout()
        
        # 构建结果
        result = f"📨 邮件夹 '{folder}' 中共有 {total} 封邮件，显示最新 {len(emails)} 封:\n\n"
        
        for email_data in emails:
            seen_mark = " " if email_data['is_seen'] else "●"
            attach_mark = " 📎" if email_data.get('has_attachments') else ""
            result += f"{seen_mark} [{email_data['index']}] {email_data['date']}\n"
            result += f"   📧 主题: {email_data['subject']}{attach_mark}\n"
            result += f"   👤 发件人: {email_data['from']}\n"
            result += f"   📝 预览: {email_data['preview']}\n\n"
        
        return True, result
        
    except imaplib.IMAP4.error as e:
        return False, f"❌ IMAP错误: {str(e)}"
    except Exception as e:
        return False, f"❌ 获取邮件失败: {str(e)}"

def read_email(msg_id, folder="INBOX", mark_seen=True):
    """
    读取指定邮件内容
    
    Args:
        msg_id: 邮件ID
        folder: 邮件夹
        mark_seen: 是否标记为已读
    
    Returns:
        (success, result)
    """
    # 加载凭证
    creds, error = load_credentials()
    if error:
        return False, error
    
    username, password = creds
    
    try:
        # 连接IMAP服务器
        imap = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT, timeout=30)
        imap.login(username, password)
        
        # 选择邮件夹
        status, messages = imap.select(folder)
        if status != 'OK':
            imap.close()
            imap.logout()
            return False, f"❌ 无法打开邮件夹 {folder}"
        
        # 获取邮件
        status, msg_data = imap.fetch(str(msg_id).encode(), '(RFC822)')
        if status != 'OK':
            imap.close()
            imap.logout()
            return False, f"❌ 无法获取邮件 ID: {msg_id}"
        
        # 解析邮件
        email_body = msg_data[0][1]
        msg = email.message_from_bytes(email_body)
        
        # 解码邮件头
        subject = decode_mime_header(msg.get('Subject', '无主题'))
        from_addr = decode_mime_header(msg.get('From', '未知发件人'))
        to_addr = decode_mime_header(msg.get('To', '未知收件人'))
        cc_addr = decode_mime_header(msg.get('Cc', ''))
        date_str = msg.get('Date', '')
        
        # 解析日期
        try:
            date_tuple = email.utils.parsedate_tz(date_str)
            if date_tuple:
                date = datetime.fromtimestamp(email.utils.mktime_tz(date_tuple))
                date_formatted = date.strftime("%Y-%m-%d %H:%M:%S")
            else:
                date_formatted = date_str
        except:
            date_formatted = date_str
        
        # 获取正文
        body = get_email_body(msg)
        
        # 获取附件信息
        attachments = []
        if msg.is_multipart():
            for part in msg.walk():
                filename = part.get_filename()
                if filename:
                    # 解码文件名
                    filename = decode_mime_header(filename)
                    size = len(part.get_payload(decode=True) or b'')
                    attachments.append({
                        'name': filename,
                        'size': size
                    })
        
        # 标记为已读
        if not mark_seen:
            imap.store(str(msg_id).encode(), '-FLAGS', '\\Seen')
        
        imap.close()
        imap.logout()
        
        # 构建结果
        result = f"📧 邮件详情 (ID: {msg_id})\n"
        result += f"{'='*50}\n"
        result += f"📅 日期: {date_formatted}\n"
        result += f"📧 主题: {subject}\n"
        result += f"👤 发件人: {from_addr}\n"
        result += f"📥 收件人: {to_addr}\n"
        if cc_addr:
            result += f"👥 抄送: {cc_addr}\n"
        result += f"{'='*50}\n"
        result += f"📝 正文内容:\n{body}\n"
        
        if attachments:
            result += f"\n📎 附件 ({len(attachments)}):\n"
            for att in attachments:
                size_str = f"{att['size']/1024:.1f}KB" if att['size'] > 0 else "0KB"
                result += f"  - {att['name']} ({size_str})\n"
        
        return True, result
        
    except imaplib.IMAP4.error as e:
        return False, f"❌ IMAP错误: {str(e)}"
    except Exception as e:
        return False, f"❌ 读取邮件失败: {str(e)}"

def list_folders():
    """列出所有邮件夹"""
    # 加载凭证
    creds, error = load_credentials()
    if error:
        return False, error
    
    username, password = creds
    
    try:
        # 连接IMAP服务器
        imap = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT, timeout=30)
        imap.login(username, password)
        
        # 获取邮件夹列表
        status, folders = imap.list()
        if status != 'OK':
            imap.close()
            imap.logout()
            return False, "❌ 无法获取邮件夹列表"
        
        folder_list = []
        for folder_info in folders:
            # 解析邮件夹信息
            folder_str = folder_info.decode()
            # 格式通常是: (\HasNoChildren) "/" "INBOX"
            parts = folder_str.split(' "/" ')
            if len(parts) > 1:
                folder_name = parts[1].strip('"')
                folder_list.append(folder_name)
        
        imap.close()
        imap.logout()
        
        result = "📂 邮件夹列表:\n"
        for i, folder in enumerate(folder_list, 1):
            result += f"  {i}. {folder}\n"
        
        return True, result
        
    except Exception as e:
        return False, f"❌ 获取邮件夹列表失败: {str(e)}"

# ==================== 命令行接口 ====================

def cmd_description():
    """输出工具描述"""
    description = """163邮箱发送/接收工具

功能：
- 发送邮件（支持纯文本/HTML、抄送、密送）
- 接收邮件（查看收件箱、阅读邮件内容）
- 列出邮件夹
- 查看邮件统计

凭证文件：
  ~/.cert/163mail.json
  格式：{"username": "your_email@163.com", "password": "your_password"}

注意：
- 163邮箱需要使用授权码而不是登录密码
- 授权码需要在163邮箱网页版设置中获取

操作类型：
- send: 发送邮件
- inbox: 查看收件箱
- read: 读取指定邮件
- folders: 列出邮件夹
- stats: 查看邮箱统计

----------------
示例：
{"action": "send", "to": "friend@example.com", "subject": "Hello", "body": "邮件内容"}
{"action": "inbox", "limit": 5}
{"action": "read", "msg_id": 1}
"""
    return description

def cmd_parameters():
    """输出参数定义（JSON Schema格式）"""
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "description": "操作类型",
                "enum": ["send", "inbox", "read", "folders", "stats"]
            },
            # 发送邮件参数
            "to": {
                "type": "string",
                "description": "收件人邮箱地址，多个地址用逗号分隔（用于send操作）"
            },
            "cc": {
                "type": "string",
                "description": "抄送地址，多个地址用逗号分隔（可选）"
            },
            "bcc": {
                "type": "string",
                "description": "密送地址，多个地址用逗号分隔（可选）"
            },
            "subject": {
                "type": "string",
                "description": "邮件主题（用于send操作）"
            },
            "body": {
                "type": "string",
                "description": "邮件正文（用于send操作）"
            },
            "html": {
                "type": "boolean",
                "description": "是否HTML格式（默认false）",
                "default": False
            },
            # 接收邮件参数
            "limit": {
                "type": "integer",
                "description": "获取邮件数量（默认10）",
                "default": 10
            },
            "folder": {
                "type": "string",
                "description": "邮件夹名称（默认INBOX）",
                "default": "INBOX"
            },
            "msg_id": {
                "type": "integer",
                "description": "邮件ID（用于read操作）"
            },
            "since_days": {
                "type": "integer",
                "description": "获取最近几天的邮件"
            },
            "mark_seen": {
                "type": "boolean",
                "description": "是否标记为已读（默认false）",
                "default": False
            },
            "stream": {
                "type": "boolean",
                "description": "是否流式输出进度信息",
                "default": True
            }
        },
        "required": ["action"]
    }
    return parameters

def get_email_stats():
    """获取邮箱统计信息"""
    # 加载凭证
    creds, error = load_credentials()
    if error:
        return False, error
    
    username, password = creds
    
    try:
        # 连接IMAP服务器
        imap = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT, timeout=30)
        imap.login(username, password)
        
        stats = {}
        total_emails = 0
        total_unseen = 0
        
        # 获取主要邮件夹的统计
        folders = ['INBOX', 'Sent Messages', 'Drafts', 'Trash', 'Spam']
        for folder in folders:
            try:
                status, messages = imap.select(folder)
                if status == 'OK':
                    # 获取邮件总数
                    status, msg_ids = imap.search(None, 'ALL')
                    if status == 'OK':
                        count = len(msg_ids[0].split())
                        stats[folder] = count
                        total_emails += count
                    
                    # 获取未读邮件数
                    status, unseen_ids = imap.search(None, 'UNSEEN')
                    if status == 'OK':
                        unseen = len(unseen_ids[0].split())
                        if folder == 'INBOX':
                            total_unseen = unseen
            except:
                continue
        
        imap.close()
        imap.logout()
        
        result = f"📊 邮箱统计 ({username})\n"
        result += f"{'='*50}\n"
        result += f"📥 收件箱: {stats.get('INBOX', 0)} 封 (未读: {total_unseen})\n"
        result += f"📤 已发送: {stats.get('Sent Messages', 0)} 封\n"
        result += f"📝 草稿箱: {stats.get('Drafts', 0)} 封\n"
        result += f"🗑️ 已删除: {stats.get('Trash', 0)} 封\n"
        result += f"⚠️ 垃圾邮件: {stats.get('Spam', 0)} 封\n"
        result += f"{'='*50}\n"
        result += f"📧 总邮件数: {total_emails} 封"
        
        return True, result
        
    except Exception as e:
        return False, f"❌ 获取统计信息失败: {str(e)}"

def cmd_execute(args_json):
    """执行邮件操作"""
    try:
        # 解析参数
        args = json.loads(args_json) if args_json else {}
        action = args.get("action")
        stream = args.get("stream", True)
        
        if not action:
            return json.dumps({
                "success": False,
                "message": "❌ 错误：缺少必需参数 'action'"
            }, ensure_ascii=False)
        
        # 根据操作类型执行
        if action == "send":
            to = args.get("to")
            subject = args.get("subject")
            body = args.get("body")
            
            if not to or not subject or not body:
                return json.dumps({
                    "success": False,
                    "message": "❌ 发送邮件需要提供 to, subject, body 参数"
                }, ensure_ascii=False)
            
            # 处理多个收件人
            to_list = [addr.strip() for addr in to.split(',') if addr.strip()]
            
            cc = args.get("cc")
            cc_list = [addr.strip() for addr in cc.split(',') if addr.strip()] if cc else None
            
            bcc = args.get("bcc")
            bcc_list = [addr.strip() for addr in bcc.split(',') if addr.strip()] if bcc else None
            
            html = args.get("html", False)
            
            success, message = send_email(
                to_addrs=to_list,
                subject=subject,
                body=body,
                cc_addrs=cc_list,
                bcc_addrs=bcc_list,
                html=html
            )
            
            return json.dumps({
                "success": success,
                "message": message,
                "action": "send",
                "to": to,
                "subject": subject
            }, ensure_ascii=False)
            
        elif action == "inbox":
            limit = args.get("limit", 10)
            folder = args.get("folder", "INBOX")
            mark_seen = args.get("mark_seen", False)
            since_days = args.get("since_days")
            
            success, message = fetch_emails(
                limit=limit,
                folder=folder,
                mark_seen=mark_seen,
                since_days=since_days
            )
            
            return json.dumps({
                "success": success,
                "message": message,
                "action": "inbox",
                "folder": folder,
                "limit": limit
            }, ensure_ascii=False)
            
        elif action == "read":
            msg_id = args.get("msg_id")
            if not msg_id:
                return json.dumps({
                    "success": False,
                    "message": "❌ 读取邮件需要提供 msg_id 参数"
                }, ensure_ascii=False)
            
            folder = args.get("folder", "INBOX")
            mark_seen = args.get("mark_seen", True)
            
            success, message = read_email(
                msg_id=msg_id,
                folder=folder,
                mark_seen=mark_seen
            )
            
            return json.dumps({
                "success": success,
                "message": message,
                "action": "read",
                "msg_id": msg_id
            }, ensure_ascii=False)
            
        elif action == "folders":
            success, message = list_folders()
            
            return json.dumps({
                "success": success,
                "message": message,
                "action": "folders"
            }, ensure_ascii=False)
            
        elif action == "stats":
            success, message = get_email_stats()
            
            return json.dumps({
                "success": success,
                "message": message,
                "action": "stats"
            }, ensure_ascii=False)
            
        else:
            return json.dumps({
                "success": False,
                "message": f"❌ 未知操作: {action}"
            }, ensure_ascii=False)
            
    except json.JSONDecodeError:
        return json.dumps({
            "success": False,
            "message": f"❌ 参数解析错误: {args_json}"
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({
            "success": False,
            "message": f"❌ 执行错误: {str(e)}"
        }, ensure_ascii=False)

# ==================== 主入口 ====================

def main():
    """主函数 - 处理命令行参数"""
    parser = argparse.ArgumentParser(description='163邮箱工具')
    parser.add_argument('--description', action='store_true', help='输出工具描述')
    parser.add_argument('--parameters', action='store_true', help='输出参数定义')
    parser.add_argument('--execute', action='store_true', help='执行工具')
    parser.add_argument('--args', type=str, help='参数JSON字符串')
    
    args = parser.parse_args()
    
    if args.description:
        print(cmd_description())
    elif args.parameters:
        print(json.dumps(cmd_parameters(), ensure_ascii=False, indent=2))
    elif args.execute:
        result = cmd_execute(args.args)
        print(result)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()