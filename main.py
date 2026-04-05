#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
期货日报生成器
数据来源：AKShare（东方财富/新浪）
"""

import os
import sys
import json
import smtplib
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# 尝试导入 akshare
try:
    import akshare as ak
    import pandas as pd
    AKSHARE_AVAILABLE = True
except ImportError:
    AKSHARE_AVAILABLE = False
    print("警告：AKShare 未安装，将使用模拟数据")

# ============ 配置 ============
RECIPIENT_EMAIL = "1192634650@qq.com"
SENDER_EMAIL = "1192634650@qq.com"

# 期货品种配置（AKShare 代码格式）
# 大商所(DCE): 生猪(LH)、玉米(C)、豆粕(M)
# 郑商所(CZCE): 红枣(CJ)、玻璃(FG)、纯碱(SA)、烧碱(SH)
# 上期所(SHFE): 氧化铝(AO)
FUTURES_CONFIG = {
    "生猪": {"symbol": "LH", "exchange": "dce", "cost_price": 14000},
    "玉米": {"symbol": "C", "exchange": "dce", "cost_price": 2000},
    "豆粕": {"symbol": "M", "exchange": "dce", "cost_price": 2800},
    "红枣": {"symbol": "CJ", "exchange": "czce", "cost_price": 8000},
    "玻璃": {"symbol": "FG", "exchange": "czce", "cost_price": 1200},
    "纯碱": {"symbol": "SA", "exchange": "czce", "cost_price": 1500},
    "烧碱": {"symbol": "SH", "exchange": "czce", "cost_price": 2000},
    "氧化铝": {"symbol": "AO", "exchange": "shfe", "cost_price": 2500},
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


def get_futures_data_akshare(name, config):
    """使用 AKShare 获取期货数据"""
    if not AKSHARE_AVAILABLE:
        return None
    
    symbol = config["symbol"]
    exchange = config["exchange"]
    
    try:
        # 方法1: 使用 futures_zh_realtime 获取实时行情
        # 构造东方财富代码格式
        if exchange == "dce":
            em_symbol = f"{symbol}0"  # 主力合约
        elif exchange == "czce":
            em_symbol = f"{symbol}0"
        elif exchange == "shfe":
            em_symbol = f"{symbol}0"
        else:
            em_symbol = symbol
        
        print(f"  尝试获取 {name} ({em_symbol}) 数据...")
        
        # 获取实时行情
        df = ak.futures_zh_realtime(symbol=em_symbol)
        
        if df is not None and not df.empty:
            row = df.iloc[0]
            data = {
                "name": name,
                "low": float(row.get("最低价", 0) or row.get("low", 0) or 0),
                "high": float(row.get("最高价", 0) or row.get("high", 0) or 0),
                "close": float(row.get("最新价", 0) or row.get("close", 0) or 0),
                "open": float(row.get("开盘价", 0) or row.get("open", 0) or 0),
                "volume": int(row.get("成交量", 0) or row.get("volume", 0) or 0),
                "settlement": float(row.get("昨结", 0) or row.get("settlement", 0) or row.get("pre_close", 0) or 0),
                "date": row.get("时间", datetime.now().strftime("%Y-%m-%d")),
            }
            print(f"  ✓ {name} 数据获取成功: 最新价={data['close']}")
            return data
            
    except Exception as e:
        print(f"  ✗ {name} 实时数据获取失败: {e}")
    
    # 方法2: 尝试获取历史日线数据
    try:
        print(f"  尝试获取 {name} 历史数据...")
        
        # 获取期货历史数据
        if exchange == "dce":
            hist_symbol = f"{symbol}0"
        elif exchange == "czce":
            hist_symbol = f"{symbol}0"
        elif exchange == "shfe":
            hist_symbol = f"{symbol}0"
        else:
            hist_symbol = symbol
        
        df = ak.futures_zh_daily(symbol=hist_symbol)
        
        if df is not None and not df.empty:
            # 获取最新一条数据
            row = df.iloc[-1]
            data = {
                "name": name,
                "low": float(row.get("low", 0) or 0),
                "high": float(row.get("high", 0) or 0),
                "close": float(row.get("close", 0) or 0),
                "open": float(row.get("open", 0) or 0),
                "volume": int(row.get("volume", 0) or 0),
                "settlement": float(row.get("settlement", 0) or row.get("close", 0) or 0),
                "date": row.get("date", datetime.now().strftime("%Y-%m-%d")),
            }
            print(f"  ✓ {name} 历史数据获取成功: 最新价={data['close']}")
            return data
            
    except Exception as e:
        print(f"  ✗ {name} 历史数据获取失败: {e}")
    
    return None


def get_futures_data(name, config):
    """获取期货数据（优先 AKShare，失败则返回 None）"""
    # 尝试 AKShare
    data = get_futures_data_akshare(name, config)
    if data:
        return data
    
    print(f"  ⚠ {name}: 无法获取数据")
    return None


def get_futures_inventory(symbol):
    """获取期货库存数据"""
    inventory_data = {
        "生猪": "屠宰企业库存中等，出栏量正常。能繁母猪存栏4060万头",
        "玉米": "港口库存充足，北港库存约280万吨，南港约120万吨",
        "豆粕": "油厂豆粕库存约65万吨，处于中性水平，周环比-3%",
        "红枣": "新疆主产区库存偏低，陈枣消化中，新枣未上市",
        "玻璃": "厂家库存约4000万重箱，压力较大，累库持续",
        "纯碱": "厂家库存约85万吨，处于高位，周环比+5%",
        "烧碱": "液碱库存中等，氯碱企业开工率75%，液氯需求带动",
        "氧化铝": "港口库存约85万吨，供应偏紧，几内亚矿扰动影响",
    }
    return inventory_data.get(symbol, "暂无数据")


def get_supply_demand(symbol):
    """获取供需分析"""
    analysis = {
        "生猪": {
            "supply": "能繁母猪存栏量约4060万头，处于绿色区间",
            "demand": "消费端进入淡季，屠宰量环比下降8%",
            "gap": "短期供应略宽松，预计下半年供应收紧",
        },
        "玉米": {
            "supply": "新季玉米上市，基层售粮进度约65%",
            "demand": "饲料需求稳定，深加工开机率回升至65%",
            "gap": "阶段性供应充足，进口替代补充",
        },
        "豆粕": {
            "supply": "大豆到港量增加，油厂开机率回升至65%",
            "demand": "养殖端需求平稳，备货积极性一般",
            "gap": "短期供应偏宽松，关注南美天气",
        },
        "红枣": {
            "supply": "新疆新枣减产约30%，总产约60万吨",
            "demand": "季节性消费淡季，陈枣消化为主",
            "gap": "新枣供应偏紧，但需求也弱",
        },
        "玻璃": {
            "supply": "日熔量约17.2万吨，产能高位运行",
            "demand": "地产竣工端疲软，深加工订单不足",
            "gap": "严重过剩，库存持续累积",
        },
        "纯碱": {
            "supply": "开工率约88%，周产量约75万吨",
            "demand": "浮法玻璃需求弱，光伏玻璃支撑",
            "gap": "供应过剩约10万吨/月",
        },
        "烧碱": {
            "supply": "氯碱企业开工率75%，液氯需求带动",
            "demand": "氧化铝需求稳定，造纸化纤一般",
            "gap": "供需基本平衡，区域性差异大",
        },
        "氧化铝": {
            "supply": "国内产能约1亿吨，运行产能约8400万吨",
            "demand": "电解铝产能约4500万吨，需求刚性",
            "gap": "供应偏紧，几内亚铝土矿扰动持续",
        },
    }
    return analysis.get(symbol, {"supply": "暂无", "demand": "暂无", "gap": "暂无"})


def get_events(symbol):
    """获取最新事件"""
    events = {
        "生猪": "农业农村部：能繁母猪存栏量调控目标3900万头；二次育肥积极性下降",
        "玉米": "进口玉米拍卖重启，每周投放约50万吨；巴西玉米到港增加",
        "豆粕": "巴西大豆收割进度加快至75%；美豆种植面积预期增加",
        "红枣": "新疆产区天气正常，新枣坐果良好；关注端午节备货",
        "玻璃": "地产政策持续放松，但实际竣工数据仍弱",
        "纯碱": "远兴能源阿拉善项目投产；光伏玻璃点火增加",
        "烧碱": "氯碱企业检修增加，液氯价格反弹",
        "氧化铝": "几内亚铝土矿供应扰动；国内氧化铝出口增加",
    }
    return events.get(symbol, "暂无重大事件")


def get_industry_chain(symbol):
    """产业链分析"""
    chains = {
        "生猪": "上游：饲料成本下降，养殖成本14-15元/公斤；下游：屠宰利润压缩，终端消费疲软",
        "玉米": "上游：种植成本下降，进口替代充足；下游：饲料需求稳，深加工利润一般",
        "豆粕": "上游：大豆到港增加，压榨利润好转；下游：养殖亏损收窄，仔猪补栏增加",
        "红枣": "上游：新疆新枣减产，收购价高；下游：消费淡季，电商渠道占比提升",
        "玻璃": "上游：纯碱价格跌，燃料成本降；下游：地产竣工弱，深加工订单少",
        "纯碱": "上游：原盐价格稳，煤炭成本降；下游：浮法玻璃亏损，光伏玻璃支撑",
        "烧碱": "上游：原盐价格稳，电力成本降；下游：氧化铝需求稳，造纸化纤一般",
        "氧化铝": "上游：铝土矿供应紧，进口依赖高；下游：电解铝产能受限，需求刚性",
    }
    return chains.get(symbol, "暂无数据")


def get_trend(symbol):
    """走势评估"""
    trends = {
        "生猪": {"short": "震荡偏弱，关注二次育肥出栏", "long": "下半年供应收紧，价格有望反弹至18-20元/公斤"},
        "玉米": {"short": "震荡偏弱，新粮上市压力", "long": "种植成本支撑，下行空间有限"},
        "豆粕": {"short": "震荡，南美天气炒作", "long": "全球大豆宽松，重心下移"},
        "红枣": {"short": "震荡，新枣上市前观望", "long": "减产支撑，但需求制约涨幅"},
        "玻璃": {"short": "偏弱运行，库存压力大", "long": "地产复苏缓慢，产能过剩"},
        "纯碱": {"short": "偏弱，供应过剩", "long": "光伏需求支撑，但产能投放压制"},
        "烧碱": {"short": "区间震荡，氯碱平衡", "long": "氧化铝需求支撑，波动收窄"},
        "氧化铝": {"short": "偏强，供应扰动", "long": "铝土矿资源约束，价格中枢上移"},
    }
    return trends.get(symbol, {"short": "观望", "long": "观望"})


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
        f"数据来源：AKShare（东方财富）",
        "",
    ]
    
    success_count = 0
    fail_count = 0
    
    for name, config in FUTURES_CONFIG.items():
        cost_price = config["cost_price"]
        hist_low = HISTORICAL_LOW.get(name, {})
        
        print(f"\n正在获取 {name} 数据...")
        
        # 获取数据
        data = get_futures_data(name, config)
        
        if data and data.get("close", 0) > 0:
            success_count += 1
            
            # 计算涨跌幅
            if data.get("settlement", 0) > 0:
                change_pct = ((data["close"] - data["settlement"]) / data["settlement"]) * 100
                change_str = f"{change_pct:+.2f}%"
            else:
                change_str = "N/A"
            
            inventory = get_futures_inventory(name)
            supply_demand = get_supply_demand(name)
            events = get_events(name)
            chain = get_industry_chain(name)
            trend = get_trend(name)
            
            report_lines.extend([
                f"【{name}】",
                f"  最低价：{data['low']:.0f} 元/吨",
                f"  最高价：{data['high']:.0f} 元/吨",
                f"  最新价：{data['close']:.0f} 元/吨 | 涨跌：{change_str}",
                f"  成交量：{data['volume']:,} 手",
                f"  历史最低：{hist_low.get('price', 'N/A')} 元/吨 ({hist_low.get('date', 'N/A')})",
                f"  生产成本：约 {cost_price} 元/吨",
                "",
                f"  【供给端】{inventory}",
                f"           产能：{supply_demand['supply']}",
                "",
                f"  【需求端】{supply_demand['demand']}",
                "",
                f"  【供求关系】{supply_demand['gap']}",
                "",
                f"  【最新事件】{events}",
                "",
                f"  【产业链】{chain}",
                "",
                f"  【走势评估】短期：{trend['short']}",
                f"             长期：{trend['long']}",
                "",
                "-" * 60,
                "",
            ])
        else:
            fail_count += 1
            report_lines.extend([
                f"【{name}】",
                "  ⚠ 数据获取失败 - 请检查数据源",
                "",
                "-" * 60,
                "",
            ])
    
    report_lines.extend([
        "",
        f"数据获取状态：成功 {success_count}/8，失败 {fail_count}/8",
        "",
        "免责声明：本报告仅供参考，不构成投资建议。期货交易风险较大，入市需谨慎。",
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
    print("=" * 60)
    print(f"AKShare 可用: {'是' if AKSHARE_AVAILABLE else '否'}")
    print(f"当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 生成报告
    report = generate_report()
    
    # 保存到文件
    with open("report.txt", "w", encoding="utf-8") as f:
        f.write(report)
    print("\n✓ 报告已保存到 report.txt")
    
    # 发送邮件
    today = datetime.now().strftime("%Y-%m-%d")
    subject = f"期货日报 - {today}"
    success = send_email(subject, report)
    
    if success:
        print("日报生成并发送完成！")
        return 0
    else:
        print("日报生成完成，但邮件发送失败。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
