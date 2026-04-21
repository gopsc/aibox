#!/usr/bin/env python3
"""163邮箱工具 - 发送邮件、接收邮件、查看收件箱。"""

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

CREDENTIALS_FILE = os.path.expanduser("~/.cert/163mail.json")
IMAP_SERVER = "imap.163.com"
IMAP_PORT = 993
SMTP_SERVER = "smtp.163.com"
SMTP_PORT = 465


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
        
        if '@' not in username:
            username = f"{username}@163.com"
        
        return (username, password), None
    except json.JSONDecodeError:
        return None, f"❌ 凭证文件JSON格式错误: {CREDENTIALS_FILE}"
    except Exception as e:
        return None, f"❌ 读取凭证文件失败: {str(e)}"


# ==================== 邮件发送功能 ====================

def send_email(to_addrs, subject, body, cc_addrs=None, bcc_addrs=None, html=False):
    """发送邮件"""
    creds, error = load_credentials()
    if error:
        return False, error
    
    username, password = creds
    
    try:
        if isinstance(to_addrs, str):
            to_addrs = [to_addrs]
        
        cc_list = []
        if cc_addrs:
            cc_list = [cc_addrs] if isinstance(cc_addrs, str) else cc_addrs
        
        bcc_list = []
        if bcc_addrs:
            bcc_list = [bcc_addrs] if isinstance(bcc_addrs, str) else bcc_addrs
        
        msg = MIMEMultipart('alternative')
        msg['From'] = username
        msg['To'] = ', '.join(to_addrs)
        msg['Subject'] = subject
        msg['Date'] = email.utils.formatdate(localtime=True)
        
        if cc_list:
            msg['Cc'] = ', '.join(cc_list)
        
        if html:
            msg.attach(MIMEText(body, 'html', 'utf-8'))
        else:
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        all_recipients = to_addrs + cc_list + bcc_list
        
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, timeout=30) as server:
            server.login(username, password)
            server.sendmail(username, all_recipients, msg.as_string())
        
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
    
    return body if body else html_body


def fetch_emails(limit=10, folder="INBOX", mark_seen=False, since_days=None):
    """获取邮件列表"""
    creds, error = load_credentials()
    if error:
        return False, error
    
    username, password = creds
    
    try:
        imap = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT, timeout=30)
        imap.login(username, password)
        
        status, messages = imap.select(folder)
        if status != 'OK':
            imap.close()
            imap.logout()
            return False, f"❌ 无法打开邮件夹 {folder}"
        
        search_criteria = 'ALL'
        if since_days:
            date = (datetime.now() - timedelta(days=since_days)).strftime("%d-%b-%Y")
            search_criteria = f'SINCE "{date}"'
        
        status, message_ids = imap.search(None, search_criteria)
        if status != 'OK':
            imap.close()
            imap.logout()
            return False, "❌ 搜索邮件失败"
        
        msg_ids = message_ids[0].split()
        total = len(msg_ids)
        
        if total == 0:
            imap.close()
            imap.logout()
            return True, f"📭 邮件夹 '{folder}' 中没有邮件"
        
        start_idx = max(0, total - limit)
        msg_ids_to_fetch = msg_ids[start_idx:]
        
        emails = []
        for i, msg_id in enumerate(reversed(msg_ids_to_fetch)):
            try:
                status, msg_data = imap.fetch(msg_id, '(RFC822)')
                if status != 'OK':
                    continue
                
                email_body = msg_data[0][1]
                msg = email.message_from_bytes(email_body)
                
                subject = decode_mime_header(msg.get('Subject', '无主题'))
                from_addr = decode_mime_header(msg.get('From', '未知发件人'))
                to_addr = decode_mime_header(msg.get('To', '未知收件人'))
                date_str = msg.get('Date', '')
                
                try:
                    date_tuple = email.utils.parsedate_tz(date_str)
                    if date_tuple:
                        date = datetime.fromtimestamp(email.utils.mktime_tz(date_tuple))
                        date_formatted = date.strftime("%Y-%m-%d %H:%M:%S")
                    else:
                        date_formatted = date_str
                except:
                    date_formatted = date_str
                
                is_seen = '\\Seen' in msg.get('Flags', '')
                body = get_email_body(msg)
                preview = body[:200] + "..." if len(body) > 200 else body
                
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
                
                if not mark_seen and not is_seen:
                    imap.store(msg_id, '-FLAGS', '\\Seen')
                    
            except Exception as e:
                continue
        
        imap.close()
        imap.logout()
        
        result = f"📨 邮件夹 '{folder}' 中共有 {total} 封邮件，显示最新 {len(emails)} 封:\n\n"
        
        for email_data in emails:
            seen_mark = " " if email_data['is_seen'] else "●"
            attach_mark = " 📎" if email_data.get('has_attachments') else ""
            result += f"{seen_mark} [{email_data['index']}] {email_data['date']}\n"
            result += f"   📧 主题: {email_data['subject']}{attach_mark}\n"
            result += f"   👤 发件人: {email_data['from']}\n"
            result += f"   📝 预览: {email_data['preview']}\n\n"
        
        return True, result
        
    except Exception as e:
        return False, f"❌ 获取邮件失败: {str(e)}"


def read_email(msg_id, folder="INBOX", mark_seen=True):
    """读取指定邮件内容"""
    creds, error = load_credentials()
    if error:
        return False, error
    
    username, password = creds
    
    try:
        imap = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT, timeout=30)
        imap.login(username, password)
        
        status, messages = imap.select(folder)
        if status != 'OK':
            imap.close()
            imap.logout()
            return False, f"❌ 无法打开邮件夹 {folder}"
        
        status, msg_data = imap.fetch(str(msg_id).encode(), '(RFC822)')
        if status != 'OK':
            imap.close()
            imap.logout()
            return False, f"❌ 无法获取邮件 ID: {msg_id}"
        
        email_body = msg_data[0][1]
        msg = email.message_from_bytes(email_body)
        
        subject = decode_mime_header(msg.get('Subject', '无主题'))
        from_addr = decode_mime_header(msg.get('From', '未知发件人'))
        to_addr = decode_mime_header(msg.get('To', '未知收件人'))
        cc_addr = decode_mime_header(msg.get('Cc', ''))
        date_str = msg.get('Date', '')
        
        try:
            date_tuple = email.utils.parsedate_tz(date_str)
            if date_tuple:
                date = datetime.fromtimestamp(email.utils.mktime_tz(date_tuple))
                date_formatted = date.strftime("%Y-%m-%d %H:%M:%S")
            else:
                date_formatted = date_str
        except:
            date_formatted = date_str
        
        body = get_email_body(msg)
        
        attachments = []
        if msg.is_multipart():
            for part in msg.walk():
                filename = part.get_filename()
                if filename:
                    filename = decode_mime_header(filename)
                    size = len(part.get_payload(decode=True) or b'')
                    attachments.append({'name': filename, 'size': size})
        
        if not mark_seen:
            imap.store(str(msg_id).encode(), '-FLAGS', '\\Seen')
        
        imap.close()
        imap.logout()
        
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
        
    except Exception as e:
        return False, f"❌ 读取邮件失败: {str(e)}"


def list_folders():
    """列出所有邮件夹"""
    creds, error = load_credentials()
    if error:
        return False, error
    
    username, password = creds
    
    try:
        imap = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT, timeout=30)
        imap.login(username, password)
        
        status, folders = imap.list()
        if status != 'OK':
            imap.close()
            imap.logout()
            return False, "❌ 无法获取邮件夹列表"
        
        folder_list = []
        for folder_info in folders:
            folder_str = folder_info.decode()
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


def get_email_stats():
    """获取邮箱统计信息"""
    creds, error = load_credentials()
    if error:
        return False, error
    
    username, password = creds
    
    try:
        imap = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT, timeout=30)
        imap.login(username, password)
        
        stats = {}
        total_unseen = 0
        folders = ['INBOX', 'Sent Messages', 'Drafts', 'Trash', 'Spam']
        
        for folder in folders:
            try:
                status, messages = imap.select(folder)
                if status == 'OK':
                    status, msg_ids = imap.search(None, 'ALL')
                    if status == 'OK':
                        count = len(msg_ids[0].split())
                        stats[folder] = count
                    
                    status, unseen_ids = imap.search(None, 'UNSEEN')
                    if status == 'OK' and folder == 'INBOX':
                        total_unseen = len(unseen_ids[0].split())
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
        
        return True, result
        
    except Exception as e:
        return False, f"❌ 获取统计信息失败: {str(e)}"


# ==================== 命令行接口 ====================

def main():
    parser = argparse.ArgumentParser(
        description="163邮箱工具 - 发送邮件、接收邮件、查看收件箱。",
        epilog="""
使用示例:
  # 发送邮件
  163mail --action send --to "friend@example.com" --subject "Hello" --body "邮件内容"

  # 发送HTML邮件
  163mail --action send --to "friend@example.com" --subject "Hello" --body "<h1>标题</h1><p>内容</p>" --html

  # 发送给多人，带抄送
  163mail --action send --to "a@example.com,b@example.com" --cc "cc@example.com" --subject "主题" --body "内容"

  # 查看收件箱
  163mail --action inbox --limit 5

  # 查看最近7天的邮件
  163mail --action inbox --since-days 7

  # 读取指定邮件
  163mail --action read --msg-id 1

  # 列出所有邮件夹
  163mail --action folders

  # 查看邮箱统计
  163mail --action stats

环境变量:
  凭证文件: ~/.cert/163mail.json
  格式: {"username": "your_email@163.com", "password": "your_password"}

注意:
  - 163邮箱需要使用授权码而不是登录密码
  - 授权码需要在163邮箱网页版设置中获取
        """
    )
    
    parser.add_argument("--action", "-a", required=True,
        choices=["send", "inbox", "read", "folders", "stats"],
        help="操作类型")
    
    # 发送邮件参数
    parser.add_argument("--to", "-t", help="收件人邮箱地址，多个地址用逗号分隔")
    parser.add_argument("--cc", help="抄送地址，多个地址用逗号分隔")
    parser.add_argument("--bcc", help="密送地址，多个地址用逗号分隔")
    parser.add_argument("--subject", "-s", help="邮件主题")
    parser.add_argument("--body", "-b", help="邮件正文")
    parser.add_argument("--html", action="store_true", help="是否HTML格式")
    
    # 接收邮件参数
    parser.add_argument("--limit", "-l", type=int, default=10, help="获取邮件数量（默认10）")
    parser.add_argument("--folder", "-f", default="INBOX", help="邮件夹名称（默认INBOX）")
    parser.add_argument("--msg-id", type=int, help="邮件ID（用于read操作）")
    parser.add_argument("--since-days", type=int, help="获取最近几天的邮件")
    parser.add_argument("--mark-seen", action="store_true", help="是否标记为已读")
    
    args = parser.parse_args()
    
    # 参数验证
    if args.action == "send":
        if not args.to or not args.subject or not args.body:
            print("❌ 发送邮件需要提供 --to, --subject, --body 参数")
            sys.exit(1)
    
    if args.action == "read" and not args.msg_id:
        print("❌ 读取邮件需要提供 --msg-id 参数")
        sys.exit(1)
    
    # 执行操作
    try:
        if args.action == "send":
            to_list = [addr.strip() for addr in args.to.split(',') if addr.strip()]
            cc_list = [addr.strip() for addr in args.cc.split(',') if addr.strip()] if args.cc else None
            bcc_list = [addr.strip() for addr in args.bcc.split(',') if addr.strip()] if args.bcc else None
            
            success, message = send_email(
                to_addrs=to_list,
                subject=args.subject,
                body=args.body,
                cc_addrs=cc_list,
                bcc_addrs=bcc_list,
                html=args.html
            )
            print(message)
            sys.exit(0 if success else 1)
        
        elif args.action == "inbox":
            success, message = fetch_emails(
                limit=args.limit,
                folder=args.folder,
                mark_seen=args.mark_seen,
                since_days=args.since_days
            )
            print(message)
            sys.exit(0 if success else 1)
        
        elif args.action == "read":
            success, message = read_email(
                msg_id=args.msg_id,
                folder=args.folder,
                mark_seen=args.mark_seen
            )
            print(message)
            sys.exit(0 if success else 1)
        
        elif args.action == "folders":
            success, message = list_folders()
            print(message)
            sys.exit(0 if success else 1)
        
        elif args.action == "stats":
            success, message = get_email_stats()
            print(message)
            sys.exit(0 if success else 1)
        
    except Exception as e:
        print(f"❌ 执行错误: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()