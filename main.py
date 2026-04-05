#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
期货日报生成器
数据来源：新浪财经期货
"""

import os
import sys
import json
import smtplib
import requests
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ============ 配置 ============
RECIPIENT_EMAIL = "1192634650@qq.com"
SENDER_EMAIL = "1192634650@qq.com"

# 期货品种配置（新浪代码格式）
FUTURES_CONFIG = {
    "生猪": {"sina_code": "LH2509", "cost_price": 14000},
    "玉米": {"sina_code": "C2509", "cost_price": 2000},
    "豆粕": {"sina_code": "M2509", "cost_price": 2800},
    "红枣": {"sina_code": "CJ2509", "cost_price": 8000},
    "玻璃": {"sina_code": "FG2509", "cost_price": 1200},
    "纯碱": {"sina_code": "SA2509", "cost_price": 1500},
    "烧碱": {"sina_code": "SH2509", "cost_price": 2000},
    "氧化铝": {"sina_code": "AO2509", "cost_price": 2500},
}

# 历史最低价数据
HISTORICAL_LOW = {
    "生猪": {"price": 10635, "date": "2021-10-08"},
    "玉米": {"price": 1460, "date": "2016-09-30"},
    "豆粕": {"price": 2150, "date": "2016-05-31"},
    "红枣": {"price": 8400, "date": "2021-06-01"},
    "玻璃": {"price": 780, "date": "2016-04-29"},
    "纯碱": {"price": 1180, "date": "2020-04-29"},
    "烧碱": {"price": 2100, "date": "2024-01-01"},
    "氧化铝": {"price": 2800, "date": "2024-01-01"},
}


def get_futures_from_sina(name, sina_code):
    """从新浪获取期货数据"""
    try:
        url = f"https://hq.sinajs.cn/list=NF_{sina_code}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://finance.sina.com.cn"
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = 'gb2312'
        
        if response.status_code == 200:
            data_text = response.text
            if '="' in data_text:
                data_str = data_text.split('="')[1].strip('";')
                fields = data_str.split(',')
                
                if len(fields) >= 14:
                    return {
                        "name": name,
                        "open": float(fields[2]) if fields[2] else 0,
                        "high": float(fields[3]) if fields[3] else 0,
                        "low": float(fields[4]) if fields[4] else 0,
                        "close": float(fields[7]) if fields[7] else 0,
                        "settlement": float(fields[9]) if fields[9] else 0,
                        "volume": int(float(fields[13])) if fields[13] else 0,
                    }
    except Exception as e:
        print(f"  ✗ 新浪接口获取 {name} 失败: {e}")
    
    return None


def generate_report():
    """生成日报"""
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    report_date = datetime.now().strftime("%Y-%m-%d")
    
    report_lines = [
        "=" * 60,
        f"                     期货日报 - {report_date}",
        "=" * 60,
        f"数据日期：{yesterday}",
        f"报告生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"数据来源：新浪财经期货",
        "",
    ]
    
    success_count = 0
    
    for name, config in FUTURES_CONFIG.items():
        cost_price = config["cost_price"]
        hist_low = HISTORICAL_LOW.get(name, {})
        
        print(f"\n正在获取 {name} ({config['sina_code']}) 数据...")
        data = get_futures_from_sina(name, config["sina_code"])
        
        if data and data.get("close", 0) > 0:
            success_count += 1
            print(f"  ✓ {name} 成功: 最新价={data['close']}")
            
            change_str = "N/A"
            if data.get("settlement", 0) > 0:
                change_pct = ((data["close"] - data["settlement"]) / data["settlement"]) * 100
                change_str = f"{change_pct:+.2f}%"
            
            report_lines.extend([
                f"【{name}】",
                f"  合约：{config['sina_code']}",
                f"  最低价：{data['low']:.0f} 元/吨",
                f"  最高价：{data['high']:.0f} 元/吨",
                f"  最新价：{data['close']:.0f} 元/吨 | 涨跌：{change_str}",
                f"  成交量：{data['volume']:,} 手",
                f"  历史最低：{hist_low.get('price', 'N/A')} 元/吨 ({hist_low.get('date', 'N/A')})",
                f"  生产成本：约 {cost_price} 元/吨",
                "",
                "-" * 60,
                "",
            ])
        else:
            report_lines.extend([
                f"【{name}】",
                f"  ⚠ 数据获取失败 - 合约代码: {config['sina_code']}",
                "",
                "-" * 60,
                "",
            ])
    
    report_lines.extend([
        "",
        f"数据获取状态：成功 {success_count}/8",
        "",
        "免责声明：本报告仅供参考，不构成投资建议。",
        "",
    ])
    
    return "\n".join(report_lines)


def send_email(subject, body):
    """发送邮件"""
    password = os.environ.get("EMAIL_PASSWORD")
    if not password:
        print("错误：未设置 EMAIL_PASSWORD 环境变量")
        return False
    
    try:
        msg = MIMEMultipart()
        msg["From"] = SENDER_EMAIL
        msg["To"] = RECIPIENT_EMAIL
        msg["Subject"] = subject
        
        msg.attach(MIMEText(body, "plain", "utf-8"))
        
        server = smtplib.SMTP_SSL("smtp.qq.com", 465)
        server.login(SENDER_EMAIL, password)
        server.sendmail(SENDER_EMAIL, RECIPIENT_EMAIL, msg.as_string())
        server.quit()
        
        print(f"\n✓ 邮件发送成功至 {RECIPIENT_EMAIL}")
        return True
    except Exception as e:
        print(f"\n✗ 邮件发送失败: {e}")
        return False


def main():
    """主函数"""
    print("=" * 60)
    print("期货日报生成系统")
    print(f"当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    report = generate_report()
    
    with open("report.txt", "w", encoding="utf-8") as f:
        f.write(report)
    print("\n✓ 报告已保存到 report.txt")
    
    today = datetime.now().strftime("%Y-%m-%d")
    success = send_email(f"期货日报 - {today}", report)
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
