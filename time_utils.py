# time_utils.py
from datetime import datetime
import pytz

# 使用上海時區，確保時間準確
TIMEZONE = pytz.timezone("Asia/Shanghai")

# 定義時辰及其對應的小時範圍 (24小時制)
# 注意：子時(23-1)是跨日的，需要特殊處理
SHICHEN_MAP = {
    (1, 2): "丑時",
    (3, 4): "寅時",
    (5, 6): "卯時",
    (7, 8): "辰時",
    (9, 10): "巳時",
    (11, 12): "午時",
    (13, 14): "未時",
    (15, 16): "申時",
    (17, 18): "酉時",
    (19, 20): "戌時",
    (21, 22): "亥時",
}

# 天干
HEAVENLY_STEMS = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
# 地支
EARTHLY_BRANCHES = [
    "子",
    "丑",
    "寅",
    "卯",
    "辰",
    "巳",
    "午",
    "未",
    "申",
    "酉",
    "戌",
    "亥",
]

# 干支纪年的计算基准年份（公元4年为甲子年）
GANZHI_BASE_YEAR = 4


def get_ganzhi_year(year: int) -> str:
    """
    根据公元年份计算干支纪年。
    干支纪年以60年为一个循环。公元4年为甲子年。
    """
    # (year - GANZHI_BASE_YEAR) 是因为基准年是周期的开始（索引为0）
    stem_index = (year - GANZHI_BASE_YEAR) % 10
    branch_index = (year - GANZHI_BASE_YEAR) % 12
    return f"{HEAVENLY_STEMS[stem_index]}{EARTHLY_BRANCHES[branch_index]}年"


def get_current_shichen():
    """
    獲取當前伺服器時間對應的古代時辰。
    """
    now = datetime.now(TIMEZONE)
    current_hour = now.hour

    # 特殊處理跨日的子時 (23:00 - 00:59)
    if current_hour >= 23 or current_hour < 1:
        return "子時"

    # 遍歷查找對應的時辰
    for hours, name in SHICHEN_MAP.items():
        if hours[0] <= current_hour <= hours[1]:
            return name

    return "未知時辰"  # 備用，正常情況不會觸發
