import datetime
from .time_utils import get_ganzhi_year
from astrbot.api import logger
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star


class TimePromptPlugin(Star):
    def __init__(self, context: Context, config):
        """初始化插件，並從配置中解析場景資料。"""
        super().__init__(context)
        self.config = config
        self.last_message_time = {}  # 存儲用戶會話的最後訊息時間
        self.last_cleanup_time = datetime.datetime.now()  # 上次清理時間
        self.hour_to_scene = {}  # 預處理小時到場景的映射，用於快速查找
        self._initialize_scenes()

    def _initialize_scenes(self):
        """從配置中解析場景資料，構建小時到場景的映射以便高效查找。"""
        try:
            # 黃道十二宮時間名稱到其小時的硬編碼映射
            scene_hours = {
                "子時": [23, 0],
                "丑時": [1, 2],
                "寅時": [3, 4],
                "卯時": [5, 6],
                "辰時": [7, 8],
                "巳時": [9, 10],
                "午時": [11, 12],
                "未時": [13, 14],
                "申時": [15, 16],
                "酉時": [17, 18],
                "戌時": [19, 20],
                "亥時": [21, 22],
            }

            time_scenes_config = self.config.get("time_scenes", {})
            if not time_scenes_config:
                logger.warning("Hina Time: 'time_scenes' 為空，將使用預設場景。")
                return

            for scene_name, hours in scene_hours.items():
                scene_data = time_scenes_config.get(scene_name, {})
                full_scene_data = scene_data.copy()
                full_scene_data["name"] = scene_name
                full_scene_data["hours"] = hours
                for hour in hours:
                    self.hour_to_scene[hour] = full_scene_data

            logger.info(
                f"Hina Time: 成功初始化 {len(self.hour_to_scene)} 個小時的場景資料。"
            )
        except Exception as e:
            logger.error(
                f"Hina Time: 初始化場景資料時發生錯誤: {str(e)}", exc_info=True
            )

    def get_current_scene(self):
        """獲取目前時間對應的場景資料字典。"""
        current_hour = datetime.datetime.now().hour
        # 如果配置中未定義目前時間，提供一個預設值
        default_scene = {
            "name": "未知時辰",
            "hours": [],
            "location_name": "未知之地",
            "location_desc": "",
            "character_mood": "平静",
            "character_event": "思考",
            "character_status": "日常",
        }
        return self.hour_to_scene.get(current_hour, default_scene)

    def get_fuzzy_time_diff(self, diff_seconds):
        """根據秒數差異取得模糊化的時間間隔描述。"""
        if diff_seconds < 1800:
            return "不久之前"
        if diff_seconds < 7200:
            return "一個時辰前"
        if diff_seconds < 86400:
            return "數個時辰前"
        if diff_seconds < 259200:
            return "數日之前"
        return "許久之前"

    def cleanup_old_records(self):
        """清理超過 7 天的舊訊息記錄以防止記憶體洩漏。"""
        try:
            cutoff_time = datetime.datetime.now() - datetime.timedelta(days=7)
            users_to_remove = []
            for user_id, sessions in list(self.last_message_time.items()):
                sessions_to_remove = [
                    sid for sid, ltime in sessions.items() if ltime < cutoff_time
                ]
                for session_id in sessions_to_remove:
                    del sessions[session_id]
                if not sessions:
                    users_to_remove.append(user_id)
            for user_id in users_to_remove:
                del self.last_message_time[user_id]
        except Exception as e:
            logger.error(f"Hina Time：清理過期記錄時發生錯誤: {str(e)}", exc_info=True)

    @filter.on_llm_request(priority=-1)
    async def add_time_prompt(self, event: AstrMessageEvent, req):
        """在 System Prompt 尾部動態添加提示詞"""
        if not self.config.get("enable_time_tracking", True):
            return

        try:
            # --- 1. 定期清理舊記錄 (每日一次) ---
            current_time = datetime.datetime.now()
            if current_time - self.last_cleanup_time > datetime.timedelta(days=1):
                self.cleanup_old_records()
                self.last_cleanup_time = current_time

            # --- 2. 取得基本信息 ---
            user_id = event.get_sender_id()
            session_id = event.get_session_id()
            user_name = event.get_sender_name() or ""

            if not user_id or not session_id:
                logger.warning("Hina Time: 无法获取用户ID或会话ID，跳过处理。")
                return

            # --- 3. 取得對話間隔提示 ---
            if user_id not in self.last_message_time:
                self.last_message_time[user_id] = {}
            last_time = self.last_message_time[user_id].get(session_id)
            time_diff_prompt = ""
            if last_time:
                diff_seconds = (current_time - last_time).total_seconds()
                fuzzy_diff = self.get_fuzzy_time_diff(diff_seconds)
                if self.config.get("show_user_info", True):
                    time_diff_prompt = (
                        f"· 使用者 {user_name}{user_id} 在【{fuzzy_diff}】與你交談過"
                    )
                else:
                    time_diff_prompt = f"· 距離上次對話：{fuzzy_diff}"
            self.last_message_time[user_id][session_id] = current_time

            # --- 4. 建構核心情境提示 ---
            scene_data = self.get_current_scene()

            # 計算干支年份並加入場景數據，使其對模板可用
            ganzhi_year = get_ganzhi_year(current_time.year)
            scene_data["ganzhi_year"] = ganzhi_year

            scene_prompt = ""
            if self.config.get("use_prompt_template", True):
                template = self.config.get("prompt_template", "")
                # 使用 .get() 避免因缺少鍵而导致的 KeyError
                scene_prompt = template.format_map(scene_data)
            else:
                # 如果不使用模板，則使用預設的硬編碼格式
                scene_prompt = (
                    f"· 當今年歲：{ganzhi_year}\n"
                    f"· 當前時辰：{scene_data.get('name', '')}\n"
                    f"· 身處之地：{scene_data.get('location_name', '')}\n"
                    f"· 地點描述：{scene_data.get('location_desc', '')}\n"
                    f"· 當前心情：{scene_data.get('character_mood', '')}\n"
                    f"· 所行之事：{scene_data.get('character_event', '')}\n"
                    f"· 當前狀態：{scene_data.get('character_status', '')}"
                )

            # --- 5. 組合最終提示詞 ---
            final_prompt_parts = ["[世界觀與狀態]", scene_prompt]
            if time_diff_prompt:
                final_prompt_parts.append(time_diff_prompt)

            # 追加悖論解決指令
            paradox_instruction = self.config.get("paradox_resolution_instruction", "")
            if paradox_instruction:
                final_prompt_parts.append(f"\n{paradox_instruction}")

            final_prompt = "\n".join(final_prompt_parts)

            # --- 6. 注入提示詞 ---
            # 將情景提示詞注入到 System Prompt 的尾部，這將使快取命中提高。
            if req.system_prompt:
                req.system_prompt = f"{req.system_prompt.strip()}\n\n{final_prompt}"
            else:
                req.system_prompt = final_prompt

        except Exception as e:
            logger.error(
                f"Hina Time: 在 add_time_prompt 中發生嚴重錯誤: {str(e)}", exc_info=True
            )

    async def terminate(self):
        """插件終止時，進行清理"""
        self.last_message_time.clear()
        logger.info("Hina Time: 已終止並清理會話記錄")
