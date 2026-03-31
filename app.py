#!/usr/bin/env python3
"""
简化的 Flask 服务器 - 仅托管前端页面
前端直接连接 WebSocket 服务器
"""

from flask import Flask, render_template, send_from_directory
import os
import uuid

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)


@app.route('/')
def index():
    """主页面"""
    # 生成会话ID用于前端标识
    session_id = str(uuid.uuid4())
    return render_template('index.html', session_id=session_id)


@app.route('/static/<path:filename>')
def serve_static(filename):
    """提供静态文件服务（如果需要）"""
    return send_from_directory('static', filename)


# 错误处理
@app.errorhandler(404)
def not_found(error):
    return render_template('index.html'), 404


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--dev':
        # 开发模式
        print("=" * 60)
        print("Flask 静态服务器 (开发模式)")
        print("=" * 60)
        print("启动服务器...")
        print("访问地址: http://localhost:5000")
        print("前端将直接连接 WebSocket 服务器: ws://localhost:8765")
        print("=" * 60)
        app.run(debug=True, host='0.0.0.0', port=5000)
    else:
        # 生产模式
        try:
            from waitress import serve
            print("=" * 60)
            print("Flask 静态服务器 (使用 Waitress)")
            print("=" * 60)
            print("启动服务器...")
            print("访问地址: http://0.0.0.0:5000")
            print("前端将直接连接 WebSocket 服务器: ws://localhost:8765")
            print("=" * 60)
            serve(app, host='0.0.0.0', port=5000, threads=4)
        except ImportError:
            print("waitress未安装，使用开发服务器")
            print("请运行: pip install waitress")
            app.run(debug=True, host='0.0.0.0', port=5000)