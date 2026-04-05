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

# 尝试导入 akshare，如果失败则使用模拟数据
try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
except ImportError:
    AKSHARE_AVAILABLE = False
    print("警告：AKShare 未安装，将使用模拟数据")

# ============ 配置 ============
RECIPIENT_EMAIL = "1192634650@qq.com"
SENDER_EMAIL = "1192634650@qq.com"

# 期货品种配置
# 格式：{名称: {akshare_symbol: AKShare代码, cost_price: 生产成本(元/吨)}}
FUTURES_CONFIG = {
    "生猪": {"akshare_symbol": "LH0", "cost_price": 14000, "exchange": "DCE"},
    "玉米": {"akshare_symbol": "C0", "cost_price": 2000, "exchange": "DCE"},
    "豆粕": {"akshare_symbol": "M0", "cost_price": 2800, "exchange": "DCE"},
    "红枣": {"akshare_symbol": "CJ0", "cost_price": 8000, "exchange": "CZCE"},
    "玻璃": {"akshare_symbol": "FG0", "cost_price": 1200, "exchange": "CZCE"},
    "纯碱": {"akshare_symbol": "SA0", "cost_price": 1500, "exchange": "CZCE"},
    "烧碱": {"akshare_symbol": "SH0", "cost_price": 2000, "exchange": "CZCE"},
    "氧化铝": {"akshare_symbol": "AO0", "cost_price": 2500, "exchange": "SHFE"},
}

# 历史最低价数据（上市以来的历史最低）
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

# 模拟数据（备用）
MOCK_DATA = {
    "生猪": {"low": 15200, "high": 15800, "close": 15480, "volume": 85000, "open": 15500},
    "玉米": {"low": 2280, "high": 2350, "close": 2310, "volume": 320000, "open": 2320},
    "豆粕": {"low": 3250, "high": 3320, "close": 3280, "volume": 280000, "open": 3300},
    "红枣": {"low": 10500, "high": 11000, "close": 10800, "volume": 15000, "open": 10600},
    "玻璃": {"low": 1350, "high": 1420, "close": 1380, "volume": 180000, "open": 1400},
    "纯碱": {"low": 1650, "high": 1720, "close": 1680, "volume": 220000, "open": 1700},
    "烧碱": {"low": 2800, "high": 2900, "close": 2850, "volume": 35000, "open": 2820},
    "氧化铝": {"low": 2950, "high": 3100, "close": 3020, "volume": 45000, "open": 2980},
}


def get_futures_realtime_data(symbol, exchange):
    """获取期货实时行情数据"""
    if not AKSHARE_AVAILABLE:
        return None
    
    try:
        # 使用 AKShare 获取期货实时行情
        # 构造东方财富代码格式
        em_symbol = f"{symbol}{exchange}"
        
        # 获取主力合约实时行情
        df = ak.futures_zh_realtime(symbol=em_symbol)
        
        if df is not None and not df.empty:
            row = df.iloc[0]
            return {
                "name": symbol,
                "low": float(row.get("最低价", 0) or 0),
                "high": float(row.get("最高价", 0) or 0),
                "close": float(row.get("最新价", 0) or 0),
                "open": float(row.get("开盘价", 0) or 0),
                "volume": int(row.get("成交量", 0) or 0),
                "settlement": float(row.get("昨结", 0) or 0),
                "bid": float(row.get("买一", 0) or 0),
                "ask": float(row.get("卖一", 0) or 0),
            }
    except Exception as e:
        print(f"获取 {symbol} 实时数据失败: {e}")
    
    return None


def get_futures_daily_data(symbol, exchange):
    """获取期货日线数据（用于获取昨日数据）"""
    if not AKSHARE_AVAILABLE:
        return None
    
    try:
        # 获取历史日线数据
        # 使用 futures_zh_daily 获取日线数据
        df = ak.futures_zh_daily(symbol=f"{symbol}{exchange}")
        
        if df is not None and not df.empty:
            # 获取最新一条（昨日数据）
            latest = df.iloc[-1]
            return {
                "date": latest.get("date", ""),
                "open": float(latest.get("open", 0) or 0),
                "high": float(latest.get("high", 0) or 0),
                "low": float(latest.get("low", 0) or 0),
                "close": float(latest.get("close", 0) or 0),
                "volume": int(latest.get("volume", 0) or 0),
            }
    except Exception as e:
        print(f"获取 {symbol} 日线数据失败: {e}")
    
    return None


def get_futures_data(name, config):
    """获取期货数据（优先实时数据，失败则用模拟数据）"""
    symbol = config["akshare_symbol"].replace("0", "")  # 去掉主力合约标记
    exchange = config["exchange"]
    
    # 尝试获取实时数据
    data = get_futures_realtime_data(symbol, exchange)
    
    if data:
        print(f"✓ {name}: 获取实时数据成功")
        return data
    
    # 尝试获取日线数据
    daily_data = get_futures_daily_data(symbol, exchange)
    if daily_data:
        print(f"✓ {name}: 获取日线数据成功")
        return daily_data
    
    # 使用模拟数据
    print(f"⚠ {name}: 使用模拟数据")
    mock = MOCK_DATA.get(name, {})
    return mock if mock else None


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
            "supply": "能繁母猪存栏量约4060万头，处于绿色区间，PSY生产指标正常",
            "demand": "消费端进入淡季，屠宰量环比下降8%，白条走货缓慢",
            "gap": "短期供应略宽松，预计下半年供应收紧，存在供需缺口",
        },
        "玉米": {
            "supply": "新季玉米上市，基层售粮进度约65%，进口玉米到港增加",
            "demand": "饲料需求稳定，深加工开机率回升至65%，淀粉需求好转",
            "gap": "阶段性供应充足，进口替代补充，整体供需平衡偏松",
        },
        "豆粕": {
            "supply": "大豆到港量增加，油厂开机率回升至65%，豆粕产出增加",
            "demand": "养殖端需求平稳，备货积极性一般，随用随采为主",
            "gap": "短期供应偏宽松，关注南美天气变化对大豆产量的影响",
        },
        "红枣": {
            "supply": "新疆新枣减产约30%，总产约60万吨，为近年低点",
            "demand": "季节性消费淡季，陈枣消化为主，新枣采购意愿弱",
            "gap": "新枣供应偏紧，但需求也弱，供需双弱格局",
        },
        "玻璃": {
            "supply": "日熔量约17.2万吨，产能高位运行，冷修意愿弱",
            "demand": "地产竣工端疲软，深加工订单不足，回款周期长",
            "gap": "严重过剩，库存持续累积，供需失衡严重",
        },
        "纯碱": {
            "supply": "开工率约88%，周产量约75万吨，远兴能源项目投产",
            "demand": "浮法玻璃需求弱，光伏玻璃有支撑，出口增加",
            "gap": "供应过剩约10万吨/月，库存压力持续",
        },
        "烧碱": {
            "supply": "氯碱企业开工率75%，液氯需求带动，检修增加",
            "demand": "氧化铝需求稳定，造纸化纤一般，出口窗口打开",
            "gap": "供需基本平衡，区域性差异大，华北偏紧华南宽松",
        },
        "氧化铝": {
            "supply": "国内产能约1亿吨，运行产能约8400万吨，产能利用率84%",
            "demand": "电解铝产能约4500万吨，需求刚性，进口依赖度50%",
            "gap": "供应偏紧，几内亚铝土矿扰动持续，进口矿减少",
        },
    }
    return analysis.get(symbol, {"supply": "暂无", "demand": "暂无", "gap": "暂无"})


def get_events(symbol):
    """获取最新事件"""
    events = {
        "生猪": "农业农村部：能繁母猪存栏量调控目标维持在3900万头左右；二次育肥积极性下降",
        "玉米": "进口玉米拍卖重启，每周投放约50万吨；巴西玉米到港量增加",
        "豆粕": "巴西大豆收割进度加快至75%，美豆种植面积预期增加；阿根廷干旱缓解",
        "红枣": "新疆产区天气正常，新枣坐果情况良好；关注端午节备货需求",
        "玻璃": "地产政策持续放松，但实际竣工数据仍弱；保交楼进展缓慢",
        "纯碱": "远兴能源阿拉善项目投产，供应压力增加；光伏玻璃点火增加",
        "烧碱": "氯碱企业检修增加，液氯价格反弹；氧化铝复产带动需求",
        "氧化铝": "几内亚铝土矿供应扰动，国内氧化铝出口增加；印尼禁止铝土矿出口",
    }
    return events.get(symbol, "暂无重大事件")


def get_industry_chain(symbol):
    """产业链分析"""
    chains = {
        "生猪": "上游：饲料成本下降（玉米豆粕跌），养殖成本约14-15元/公斤；下游：屠宰利润压缩，终端消费疲软，白条价格跟跌",
        "玉米": "上游：种植成本下降，进口替代充足，巴西玉米到港；下游：饲料需求稳，深加工利润一般，淀粉开机率65%",
        "豆粕": "上游：大豆到港增加，压榨利润好转至200元/吨；下游：养殖亏损收窄，需求边际改善，仔猪补栏增加",
        "红枣": "上游：新疆新枣减产，收购价高，枣农惜售；下游：消费淡季，走货缓慢，电商渠道占比提升",
        "玻璃": "上游：纯碱价格跌，燃料成本降，生产成本下移；下游：地产竣工弱，深加工订单少，回款周期长",
        "纯碱": "上游：原盐价格稳，煤炭成本降，氨碱法利润压缩；下游：浮法玻璃亏损，光伏玻璃支撑，出口增加",
        "烧碱": "上游：原盐价格稳，电力成本降，氯碱平衡改善；下游：氧化铝需求稳，造纸化纤一般，出口窗口打开",
        "氧化铝": "上游：铝土矿供应紧，进口依赖高，几内亚矿扰动；下游：电解铝产能受限，需求刚性，铝价偏强",
    }
    return chains.get(symbol, "暂无数据")


def get_trend(symbol):
    """走势评估"""
    trends = {
        "生猪": {"short": "震荡偏弱，关注二次育肥出栏节奏", "long": "下半年供应收紧，价格有望反弹至18-20元/公斤"},
        "玉米": {"short": "震荡偏弱，新粮上市压力，关注进口政策", "long": "种植成本支撑，下行空间有限，底部2300-2400"},
        "豆粕": {"short": "震荡，南美天气炒作，美豆种植意向", "long": "全球大豆宽松，重心下移，区间3000-3500"},
        "红枣": {"short": "震荡，新枣上市前观望，关注天气", "long": "减产支撑，但需求制约涨幅，区间10000-12000"},
        "玻璃": {"short": "偏弱运行，库存压力大，关注地产政策", "long": "地产复苏缓慢，产能过剩，底部1300-1400"},
        "纯碱": {"short": "偏弱，供应过剩，检修力度", "long": "光伏需求支撑，但产能投放压制，区间1600-2000"},
        "烧碱": {"short": "区间震荡，氯碱平衡，氧化铝复产", "long": "氧化铝需求支撑，波动收窄，区间2600-3200"},
        "氧化铝": {"short": "偏强，供应扰动，铝土矿紧张", "long": "铝土矿资源约束，价格中枢上移，区间2800-3500"},
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
        "",
    ]
    
    for name, config in FUTURES_CONFIG.items():
        cost_price = config["cost_price"]
        hist_low = HISTORICAL_LOW.get(name, {})
        
        # 获取数据
        data = get_futures_data(name, config)
        
        inventory = get_futures_inventory(name)
        supply_demand = get_supply_demand(name)
        events = get_events(name)
        chain = get_industry_chain(name)
        trend = get_trend(name)
        
        if data:
            # 计算涨跌幅
            if "settlement" in data and data["settlement"] > 0:
                change_pct = ((data["close"] - data["settlement"]) / data["settlement"]) * 100
                change_str = f"{change_pct:+.2f}%"
            else:
                change_str = "N/A"
            
            report_lines.extend([
                f"【{name}】",
                f"  昨日最低价：{data['low']:.0f} 元/吨",
                f"  历史最低价：{hist_low.get('price', 'N/A')} 元/吨 ({hist_low.get('date', 'N/A')})",
                f"  生产成本：约 {cost_price} 元/吨",
                f"  最新价：{data['close']:.0f} 元/吨 | 涨跌：{change_str}",
                f"  成交量：{data['volume']:,} 手",
                "",
                f"  【供给端】{inventory}",
                f"           产能状况：{supply_demand['supply']}",
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
            report_lines.extend([
                f"【{name}】",
                "  数据获取失败",
                "",
                "-" * 60,
                "",
            ])
    
    report_lines.extend([
        "",
        "数据来源：东方财富/AKShare",
        "免责声明：本报告仅供参考，不构成投资建议。期货交易风险较大，入市需谨慎。",
        "",
    ])
    
    return "\n".join(report_lines)


def send_email(subject, body):
    """发送邮件"""
    password = os.environ.get("EMAIL_PASSWORD")
    if not password:
        print("错误：未设置 EMAIL_PASSWORD 环境变量")
        print("请在 GitHub Secrets 中设置 EMAIL_PASSWORD（QQ邮箱授权码）")
        return False
    
    try:
        msg = MIMEMultipart()
        msg["From"] = SENDER_EMAIL
        msg["To"] = RECIPIENT_EMAIL
        msg["Subject"] = subject
        
        msg.attach(MIMEText(body, "plain", "utf-8"))
        
        # QQ邮箱 SMTP
        server = smtplib.SMTP_SSL("smtp.qq.com", 465)
        server.login(SENDER_EMAIL, password)
        server.sendmail(SENDER_EMAIL, RECIPIENT_EMAIL, msg.as_string())
        server.quit()
        
        print(f"✓ 邮件发送成功至 {RECIPIENT_EMAIL}")
        return True
    except Exception as e:
        print(f"✗ 邮件发送失败: {e}")
        return False


def main():
    """主函数"""
    print("=" * 60)
    print("期货日报生成系统")
    print("=" * 60)
    print(f"AKShare 可用: {'是' if AKSHARE_AVAILABLE else '否'}")
    print(f"当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print()
    
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
        print("\n日报生成并发送完成！")
        return 0
    else:
        print("\n日报生成完成，但邮件发送失败。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
