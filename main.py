from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import datetime
import time

@register("time_prompt", "wuyan1003", "为LLM对话添加时间相关的系统提示词", "1.0.0")
class TimePromptPlugin(Star):
    def __init__(self, context: Context, config):
        """初始化插件
        
        Args:
            context: AstrBot上下文
            config: 插件配置对象
        """
        super().__init__(context)
        self.config = config
        # 存储用户在不同会话中的最后消息时间
        # 格式: {用户ID: {会话ID: 最后消息时间}}
        self.last_message_time = {}

    @filter.on_llm_request()
    async def add_time_prompt(self, event: AstrMessageEvent, req):
        """为LLM请求添加时间相关的系统提示词
        
        Args:
            event: 消息事件对象
            req: LLM请求对象
        """
        try:
            # 检查是否启用时间追踪功能
            if not self.config.get('enable_time_tracking', True):
                return

            # 获取当前时间
            current_time = datetime.datetime.now()
            current_time_str = current_time.strftime("%Y-%m-%d %H:%M:%S")
            
            # 获取用户信息
            user_id = event.get_sender_id()
            session_id = event.get_session_id()
            user_name = event.get_sender_name()
            
            # 初始化用户的会话字典
            if user_id not in self.last_message_time:
                self.last_message_time[user_id] = {}
            
            # 获取该会话的最后消息时间
            last_time = self.last_message_time[user_id].get(session_id)
            
            # 计算时间间隔
            time_diff = ""
            if last_time:
                diff_seconds = (current_time - last_time).total_seconds()
                # 根据时间间隔选择合适的显示格式
                if diff_seconds < 60:
                    time_diff = f"距离上次对话已经过去了 {int(diff_seconds)} 秒"
                elif diff_seconds < 3600:
                    time_diff = f"距离上次对话已经过去了 {int(diff_seconds/60)} 分钟"
                else:
                    time_diff = f"距离上次对话已经过去了 {int(diff_seconds/3600)} 小时"
                
                # 如果启用了用户信息显示，添加用户名和ID
                if self.config.get('show_user_info', True):
                    time_diff = f"上次用户 {user_name}（ID：{user_id}）跟你对话{time_diff}"
            
            # 更新最后消息时间
            self.last_message_time[user_id][session_id] = current_time
            
            # 构建系统提示词
            system_prompt = "[系统提示]请记住以下时间信息："
            system_prompt += f"\n当前时间是: {current_time_str}"
            if time_diff:
                system_prompt += f"\n{time_diff}"
            system_prompt += "\n请根据这些时间信息来调整你的回答，使其更符合当前的时间背景。"
            
            # 添加到现有系统提示词中
            if req.system_prompt:
                req.system_prompt = f"{req.system_prompt}\n\n{system_prompt}"
            else:
                req.system_prompt = system_prompt
                
        except Exception as e:
            logger.error(f"时间提示词插件错误: {str(e)}")

    async def terminate(self):
        """插件终止时清理资源"""
        self.last_message_time.clear() 