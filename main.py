import os
import asyncio
import aiosqlite  # Import the standard SQLite library
from datetime import datetime
from astrbot.api.event import AstrMessageEvent
from astrbot.api.star import Context, Star, register, StarTools
from astrbot.api import logger, AstrBotConfig
from astrbot.api.event.filter import command
from .core.touchi_tools import TouchiTools
from .core.tujian import TujianTools

@register("astrbot_plugin_touchi", "touchi", "这是一个为 AstrBot 开发的鼠鼠偷吃插件，增加了图鉴特勤处鼠鼠榜功能", "2.4.7")
class Main(Star):
    @classmethod
    def info(cls):
        return {
            "name": "astrbot_plugin_touchi",
            "version": "2.4.7",
            "description": "这是一个为 AstrBot 开发的鼠鼠偷吃插件，增加了图鉴特勤处刘涛功能",
            "author": "sa1guu"
        }
    


    def __init__(self, context: Context, config: AstrBotConfig = None):
        super().__init__(context)
        
        self.config = config or {}
        self.enable_touchi = self.config.get("enable_touchi", True)
        self.enable_beauty_pic = self.config.get("enable_beauty_pic", True)
        
        # 读取群聊白名单配置
        self.enable_group_whitelist = self.config.get("enable_group_whitelist", False)
        self.group_whitelist = self.config.get("group_whitelist", [])
        
        # 读取时间限制配置
        self.enable_time_limit = self.config.get("enable_time_limit", False)
        self.time_limit_start = self.config.get("time_limit_start", "09:00:00")
        self.time_limit_end = self.config.get("time_limit_end", "22:00:00")
        
        # 读取静态图片配置
        self.enable_static_image = self.config.get("enable_static_image", False)
        
        # Define path for the plugin's private database in its data directory
        data_dir = StarTools.get_data_dir("astrbot_plugin_touchi")
        os.makedirs(data_dir, exist_ok=True)
        self.db_path = os.path.join(data_dir, "collection.db")
        
        # Initialize the database table
        asyncio.create_task(self._initialize_database())
        
        # Pass the database file PATH to the tools
        self.touchi_tools = TouchiTools(
            enable_touchi=self.enable_touchi,
            enable_beauty_pic=self.enable_beauty_pic,
            cd=5,
            db_path=self.db_path,
            enable_static_image=self.enable_static_image
        )

        self.tujian_tools = TujianTools(db_path=self.db_path)

    async def _initialize_database(self):
        """Initializes the database and creates the table if it doesn't exist."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS user_touchi_collection (
                        user_id TEXT NOT NULL,
                        item_name TEXT NOT NULL,
                        item_level TEXT NOT NULL,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (user_id, item_name)
                    );
                """)
                # 新增经济系统表
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS user_economy (
                        user_id TEXT PRIMARY KEY,
                        warehouse_value INTEGER DEFAULT 0,
                        teqin_level INTEGER DEFAULT 0,
                        grid_size INTEGER DEFAULT 2,
                        menggong_active INTEGER DEFAULT 0,
                        menggong_end_time REAL DEFAULT 0,
                        auto_touchi_active INTEGER DEFAULT 0,
                        auto_touchi_start_time REAL DEFAULT 0
                    );
                """)
                
                # 新增系统配置表
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS system_config (
                        config_key TEXT PRIMARY KEY,
                        config_value TEXT NOT NULL
                    );
                """)
                
                # 初始化基础等级配置
                await db.execute("""
                    INSERT OR IGNORE INTO system_config (config_key, config_value) 
                    VALUES ('base_teqin_level', '0')
                """)
                
                # 添加新字段（如果不存在）
                try:
                    await db.execute("ALTER TABLE user_economy ADD COLUMN auto_touchi_active INTEGER DEFAULT 0")
                except:
                    pass  # 字段已存在
                
                try:
                    await db.execute("ALTER TABLE user_economy ADD COLUMN auto_touchi_start_time REAL DEFAULT 0")
                except:
                    pass  # 字段已存在
                
                # 添加六套时间倍率配置
                await db.execute("""
                    INSERT OR IGNORE INTO system_config (config_key, config_value) 
                    VALUES ('menggong_time_multiplier', '1.0')
                """)
                await db.commit()
            logger.info("偷吃插件数据库[collection.db]初始化成功。")
        except Exception as e:
            logger.error(f"初始化偷吃插件数据库[collection.db]时出错: {e}")
    
    def _check_group_permission(self, message_event):
        """
        检查群聊白名单权限
        返回: 是否允许
        """
        # 如果未启用白名单功能，直接允许
        if not self.enable_group_whitelist:
            return True
        
        # 私聊始终允许
        if message_event.session_id.startswith("person_"):
            return True
        
        # 获取群号
        group_id = message_event.session_id.replace("group_", "")
        
        # 检查是否在白名单中（支持字符串和数字类型的群号）
        # 将群号转换为字符串进行比较，同时也检查数字类型
        group_id_str = str(group_id)
        try:
            group_id_int = int(group_id)
        except ValueError:
            group_id_int = None
        
        for whitelist_group in self.group_whitelist:
            # 支持字符串比较
            if str(whitelist_group) == group_id_str:
                return True
            # 支持数字比较
            if group_id_int is not None and whitelist_group == group_id_int:
                return True
        
        # 非白名单群聊禁用
        return False
    
    def _check_time_permission(self):
        """
        检查时间限制权限
        返回: 是否允许
        """
        # 如果未启用时间限制功能，直接允许
        if not self.enable_time_limit:
            return True
        
        # 获取当前时间
        current_time = datetime.now().strftime("%H:%M:%S")
        
        # 检查是否在允许的时间范围内
        if self.time_limit_start <= self.time_limit_end:
            # 正常时间范围（如 09:00:00 到 22:00:00）
            return self.time_limit_start <= current_time <= self.time_limit_end
        else:
            # 跨日时间范围（如 22:00:00 到 09:00:00）
            return current_time >= self.time_limit_start or current_time <= self.time_limit_end
    
    def _check_all_permissions(self, message_event):
        """
        检查所有权限（群聊白名单 + 时间限制）
        返回: (是否允许, 错误信息)
        """
        # 检查群聊权限
        if not self._check_group_permission(message_event):
            return False, "🐭 此群聊未在白名单中，无法使用鼠鼠功能"
        
        # 检查时间权限
        if not self._check_time_permission():
            # 时间限制失败时返回提示信息
            time_range = f"{self.time_limit_start} - {self.time_limit_end}"
            return False, f"🐭 鼠鼠休息中 {time_range} 可偷吃"
        
        return True, None

    @command("偷吃")
    async def touchi(self, event: AstrMessageEvent):
        """盲盒功能"""
        allowed, error_msg = self._check_all_permissions(event)
        if not allowed:
            if error_msg:
                yield event.plain_result(error_msg)
            return
        
        async for result in self.touchi_tools.get_touchi(event):
            yield result

    @command("鼠鼠图鉴")
    async def tujian(self, event: AstrMessageEvent):
        """显示用户稀有物品图鉴（金色和红色）"""
        allowed, error_msg = self._check_all_permissions(event)
        if not allowed:
            if error_msg:
                yield event.plain_result(error_msg)
            return
        
        try:
            user_id = event.get_sender_id()
            result_path_or_msg = await self.tujian_tools.generate_tujian(user_id)
            
            if os.path.exists(result_path_or_msg):
                yield event.image_result(result_path_or_msg)
            else:
                yield event.plain_result(result_path_or_msg)
        except Exception as e:
            logger.error(f"生成图鉴时出错: {e}")
            yield event.plain_result("生成图鉴时发生内部错误，请联系管理员。")

    @command("鼠鼠冷却倍率")
    async def set_multiplier(self, event: AstrMessageEvent):
       """设置偷吃和猛攻的速度倍率（仅管理员）"""
       # 检查用户是否为管理员
       if event.role != "admin":
           yield event.plain_result("❌ 此指令仅限管理员使用")
           return
           
       try:
           plain_text = event.message_str.strip()
           args = plain_text.split()
           
           if len(args) < 2:
               yield event.plain_result("请提供倍率值，例如：鼠鼠冷却倍率 0.5")
               return
        
           multiplier = float(args[1])
           if multiplier < 0.01 or multiplier > 100:
               yield event.plain_result("倍率必须在0.01到100之间")
               return
            
           msg = self.touchi_tools.set_multiplier(multiplier)
           yield event.plain_result(msg)
        
       except ValueError:
           yield event.plain_result("倍率必须是数字")
       except Exception as e:
           logger.error(f"设置倍率时出错: {e}")
           yield event.plain_result("设置倍率失败，请重试")

    @command("六套猛攻")
    async def menggong(self, event: AstrMessageEvent):
        """六套猛攻功能"""
        allowed, error_msg = self._check_all_permissions(event)
        if not allowed:
            if error_msg:
                yield event.plain_result(error_msg)
            return
        
        async for result in self.touchi_tools.menggong_attack(event):
            yield result

    @command("特勤处升级")
    async def upgrade_teqin(self, event: AstrMessageEvent):
        """特勤处升级功能"""
        allowed, error_msg = self._check_all_permissions(event)
        if not allowed:
            if error_msg:
                yield event.plain_result(error_msg)
            return
        
        async for result in self.touchi_tools.upgrade_teqin(event):
            yield result

    @command("鼠鼠仓库")
    async def warehouse_value(self, event: AstrMessageEvent):
        """查看仓库价值"""
        allowed, error_msg = self._check_all_permissions(event)
        if not allowed:
            if error_msg:
                yield event.plain_result(error_msg)
            return
        
        async for result in self.touchi_tools.get_warehouse_info(event):
            yield result

    @command("鼠鼠榜")
    async def leaderboard(self, event: AstrMessageEvent):
        """显示图鉴数量榜和仓库价值榜前五位"""
        allowed, error_msg = self._check_all_permissions(event)
        if not allowed:
            if error_msg:
                yield event.plain_result(error_msg)
            return
        
        async for result in self.touchi_tools.get_leaderboard(event):
            yield result

    @command("开启自动偷吃")
    async def start_auto_touchi(self, event: AstrMessageEvent):
        """开启自动偷吃功能"""
        allowed, error_msg = self._check_all_permissions(event)
        if not allowed:
            if error_msg:
                yield event.plain_result(error_msg)
            return
        
        async for result in self.touchi_tools.start_auto_touchi(event):
            yield result

    @command("关闭自动偷吃")
    async def stop_auto_touchi(self, event: AstrMessageEvent):
        """关闭自动偷吃功能"""
        allowed, error_msg = self._check_all_permissions(event)
        if not allowed:
            if error_msg:
                yield event.plain_result(error_msg)
            return
        
        async for result in self.touchi_tools.stop_auto_touchi(event):
            yield result

    @command("鼠鼠库清除")
    async def clear_user_data(self, event: AstrMessageEvent):
        """清除用户数据（仅管理员）"""
        # 检查用户是否为管理员
        if event.role != "admin":
            yield event.plain_result("❌ 此指令仅限管理员使用")
            return
        
        try:
            plain_text = event.message_str.strip()
            args = plain_text.split()
            
            if len(args) == 1:
                # 清除所有用户数据
                result = await self.touchi_tools.clear_user_data()
                yield event.plain_result(f"⚠️ {result}")
            elif len(args) == 2:
                # 清除指定用户数据
                target_user_id = args[1]
                result = await self.touchi_tools.clear_user_data(target_user_id)
                yield event.plain_result(f"⚠️ {result}")
            else:
                yield event.plain_result("用法：\n鼠鼠库清除 - 清除所有用户数据\n鼠鼠库清除 [用户ID] - 清除指定用户数据")
                
        except Exception as e:
            logger.error(f"清除用户数据时出错: {e}")
            yield event.plain_result("清除数据失败，请重试")

    @command("特勤处等级")
    async def set_base_teqin_level(self, event: AstrMessageEvent):
        """设置特勤处基础等级（仅管理员）"""
        # 检查用户是否为管理员
        if event.role != "admin":
            yield event.plain_result("❌ 此指令仅限管理员使用")
            return
            
        try:
            plain_text = event.message_str.strip()
            args = plain_text.split()
            
            if len(args) < 2:
                yield event.plain_result("请提供等级值，例如：设置特勤处基础等级 2")
                return
        
            level = int(args[1])
            if level < 0 or level > 5:
                yield event.plain_result("特勤处基础等级必须在0到5之间")
                return
            
            result = await self.touchi_tools.set_base_teqin_level(level)
            yield event.plain_result(result)
        
        except ValueError:
            yield event.plain_result("等级必须是整数")
        except Exception as e:
            logger.error(f"设置特勤处基础等级时出错: {e}")
            yield event.plain_result("设置特勤处基础等级失败，请重试")

    @command("鼠鼠限时")
    async def set_time_limit(self, event: AstrMessageEvent):
        """设置插件使用时间限制"""
        # 管理员权限检查
        if not event.is_admin():
            yield event.plain_result("❌ 此功能仅限管理员使用")
            return
        
        try:
            args = event.get_message_str().strip().split()
            
            if len(args) == 1:  # 只有命令，显示当前设置
                status = "启用" if self.enable_time_limit else "禁用"
                yield event.plain_result(f"🕐 当前时间限制状态: {status}\n⏰ 允许使用时间: {self.time_limit_start} - {self.time_limit_end}")
                return
            
            if len(args) == 2:  # 启用/禁用
                action = args[1]
                if action == "启用":
                    self.enable_time_limit = True
                    yield event.plain_result(f"✅ 已启用时间限制功能\n⏰ 允许使用时间: {self.time_limit_start} - {self.time_limit_end}")
                elif action == "禁用":
                    self.enable_time_limit = False
                    yield event.plain_result("✅ 已禁用时间限制功能")
                else:
                    yield event.plain_result("❌ 参数错误，请使用: 鼠鼠限时 [启用/禁用] 或 鼠鼠限时 [开始时间] [结束时间]")
                return
            
            if len(args) == 3:  # 设置时间范围
                start_time = args[1]
                end_time = args[2]
                
                # 验证时间格式
                try:
                    datetime.strptime(start_time, "%H:%M:%S")
                    datetime.strptime(end_time, "%H:%M:%S")
                except ValueError:
                    yield event.plain_result("❌ 时间格式错误，请使用 HH:MM:SS 格式（如: 09:00:00）")
                    return
                
                self.time_limit_start = start_time
                self.time_limit_end = end_time
                self.enable_time_limit = True
                yield event.plain_result(f"✅ 已设置时间限制\n⏰ 允许使用时间: {start_time} - {end_time}")
                return
            
            yield event.plain_result("❌ 参数错误\n\n📖 使用说明:\n• 鼠鼠限时 - 查看当前设置\n• 鼠鼠限时 启用/禁用 - 启用或禁用时间限制\n• 鼠鼠限时 [开始时间] [结束时间] - 设置时间范围\n\n⏰ 时间格式: HH:MM:SS（如: 09:00:00 22:00:00）")
            
        except Exception as e:
            logger.error(f"设置时间限制时出错: {e}")
            yield event.plain_result("❌ 设置时间限制失败，请重试")

    @command("touchi")
    async def help_command(self, event: AstrMessageEvent):
        """显示所有可用指令的帮助信息"""
        allowed, error_msg = self._check_all_permissions(event)
        if not allowed:
            if error_msg:
                yield event.plain_result(error_msg)
            return
        
        help_text = """🐭 鼠鼠偷吃插件 - 指令帮助 🐭

📦 基础功能：
• 偷吃 - 开启偷吃盲盒，获得随机物品
• 鼠鼠图鉴 - 查看你收集的稀有物品图鉴
• 鼠鼠仓库 - 查看仓库总价值和统计信息

⚡ 高级功能：
• 六套猛攻 - 消耗哈夫币进行猛攻模式
• 特勤处升级 - 升级特勤处等级，扩大仓库容量

🏆 排行榜：
• 鼠鼠榜 - 查看图鉴数量榜和仓库价值榜前五名

🤖 自动功能：
• 开启自动偷吃 - 启动自动偷吃模式(每10分钟，最多4小时)
• 关闭自动偷吃 - 停止自动偷吃模式

🎲 概率事件：
• 偷吃事件 - 查看偷吃概率事件统计和说明

🗝️ 密码功能：
• 鼠鼠密码 - 获取地图密码信息(缓存至晚上12点)

⚙️ 管理员功能：
• 鼠鼠冷却倍率 [数值] - 设置偷吃冷却倍率(0.01-100)
• 鼠鼠库清除 - 清除所有用户数据
• 特勤处等级 [等级] - 设置新用户的初始特勤处等级(0-5)
• 鼠鼠限时 - 设置插件使用时间范围限制 如 09:00:00 22:00:00
• 刷新密码 - 强制刷新密码缓存
• 六套时间倍率 [倍率] - 设置六套时间倍率(0.1-10.0)

更新：配置文件中开设置群聊启用白名单
💡 提示：
• 自动偷吃期间无法手动偷吃
• 偷吃时有概率触发特殊事件，详见"偷吃事件"指令
• 首次使用请先输入"偷吃"开始游戏！"""
        yield event.plain_result(help_text)

    @command("鼠鼠密码")
    async def mima(self, event: AstrMessageEvent):
        """获取地图密码信息"""
        allowed, error_msg = self._check_all_permissions(event)
        if not allowed:
            if error_msg:
                yield event.plain_result(error_msg)
            return
        
        try:
            # 优先从TXT文件读取密码信息
            from .mima_standalone import get_mima_from_txt, get_mima_async
            
            # 尝试从TXT文件读取
            txt_result = get_mima_from_txt()
            if txt_result:
                yield event.plain_result(txt_result)
                return
            
            # TXT文件不存在或读取失败，从网络获取
            logger.info("TXT文件不存在或读取失败，正在从网络获取密码信息")
            result = await get_mima_async()
            yield event.plain_result(result)
            
        except ImportError as e:
            logger.error(f"导入playwright模块失败: {e}")
            yield event.plain_result("🐭 获取密码功能需要playwright依赖\n\n🔧 解决方案:\n1. 检查网络连接\n2. 重新安装playwright:\n   pip install playwright\n   playwright install chromium")
        except Exception as e:
            error_msg = str(e).lower()
            logger.error(f"获取密码信息时出错: {e}")
            
            # 检查是否为网络或playwright相关错误
            if any(keyword in error_msg for keyword in ['network', 'connection', 'timeout', 'playwright', 'browser', 'chromium']):
                yield event.plain_result("🐭 获取密码信息失败\n\n🔧 可能的解决方案:\n1. 检查网络连接是否正常\n2. 重新安装playwright依赖:\n   pip install playwright\n   playwright install chromium\n3. 稍后再试")
            else:
                yield event.plain_result("🐭 获取密码信息时发生错误，请稍后再试")

    @command("刷新密码")
    async def refresh_mima(self, event: AstrMessageEvent):
        """强制刷新密码缓存（仅管理员）"""
        # 检查用户是否为管理员
        if event.role != "admin":
            yield event.plain_result("❌ 此指令仅限管理员使用")
            return
        
        try:
            # 调用完全独立的 mima_standalone.py
            from .mima_standalone import MimaTools
            mima_tools = MimaTools()
            result = await mima_tools.refresh_mima_cache()
            yield event.plain_result(result)
        except ImportError as e:
            logger.error(f"导入playwright模块失败: {e}")
            yield event.plain_result("🐭 刷新密码功能需要playwright依赖\n\n🔧 解决方案:\n1. 检查网络连接\n2. 重新安装playwright:\n   pip install playwright\n   playwright install chromium")
        except Exception as e:
            error_msg = str(e).lower()
            logger.error(f"刷新密码缓存时出错: {e}")
            
            # 检查是否为网络或playwright相关错误
            if any(keyword in error_msg for keyword in ['network', 'connection', 'timeout', 'playwright', 'browser', 'chromium']):
                yield event.plain_result("🐭 刷新密码缓存失败\n\n🔧 可能的解决方案:\n1. 检查网络连接是否正常\n2. 重新安装playwright依赖:\n   pip install playwright\n   playwright install chromium\n3. 稍后再试")
            else:
                yield event.plain_result("🐭 刷新密码缓存时发生错误，请稍后再试")

    @command("六套时间倍率")
    async def set_menggong_time_multiplier(self, event: AstrMessageEvent):
        """设置六套时间倍率（仅管理员）"""
        # 检查用户是否为管理员
        if event.role != "admin":
            yield event.plain_result("❌ 此指令仅限管理员使用")
            return
        
        try:
            plain_text = event.message_str.strip()
            args = plain_text.split()
            
            if len(args) < 2:
                yield event.plain_result("❌ 参数不足\n\n📖 使用说明:\n• 六套时间倍率 [倍率] - 设置六套时间倍率\n\n💡 示例:\n• 六套时间倍率 2.0 - 设置2倍时长倍率\n• 六套时间倍率 0.5 - 设置0.5倍时长倍率")
                return
            
            try:
                time_multiplier = float(args[1])
            except ValueError:
                yield event.plain_result("❌ 倍率必须是数字")
                return
            
            if time_multiplier <= 0:
                yield event.plain_result("❌ 倍率必须大于0")
                return
            
            if time_multiplier > 10.0:
                yield event.plain_result("❌ 倍率不能超过10.0")
                return
            
            if time_multiplier < 0.1:
                yield event.plain_result("❌ 倍率不能小于0.1")
                return
            
            result = await self.touchi_tools.set_menggong_time_multiplier(time_multiplier)
            yield event.plain_result(result)
            
        except Exception as e:
            logger.error(f"设置六套时间时出错: {e}")
            yield event.plain_result("❌ 设置六套时间失败，请重试")

    @command("偷吃事件")
    async def touchi_events_info(self, event: AstrMessageEvent):
        """查看偷吃概率事件信息"""
        allowed, error_msg = self._check_all_permissions(event)
        if not allowed:
            if error_msg:
                yield event.plain_result(error_msg)
            return
        
        try:
            stats = self.touchi_tools.events.get_event_statistics()
            
            event_info = f"""🎲 偷吃概率事件统计 🎲

📊 事件触发概率：
• 🎯 正常偷吃: {stats['normal']}
• 💎 获得残缺刘涛: {stats['broken_liutao']}
• 💀 遇到天才少年被踢死: {stats['genius_kick']}
• ⚖️ 排到天才少年被追缴: {stats['genius_fine']}
• 🤦 遇到菜b队友: {stats['noob_teammate']}
• 🏃 被追杀丢包撤离: {stats['hunted_escape']}
• 🐭 遇到路人鼠鼠: {stats['passerby_mouse']}
• 🎲 总事件概率: {stats['total_event']}

📝 事件详细说明：

💎 【残缺刘涛】
• 概率: {stats['broken_liutao']}
• 效果: 额外获得残缺的刘涛
• 奖励: 激活1分钟六套加成时间
• 特殊: 期间红色和金色物品概率大幅提升

💀 【天才少年踢死】
• 概率: {stats['genius_kick']}
• 效果: 展示偷吃结果但不计入数据库
• 惩罚: 清空所有物品和仓库价值
• 提示: 重新开始收集之旅

⚖️ 【天才少年追缴】
• 概率: {stats['genius_fine']}
• 效果: 正常获得物品
• 惩罚: 被追缴30万哈夫币
• 备注: 哈夫币可以为负数

🤦 【菜b队友】
• 概率: {stats['noob_teammate']}
• 效果: 正常获得物品
• 惩罚: 撤离时间翻倍，下次偷吃冷却时间增加一倍
• 备注: 影响下次偷吃的等待时间

🏃 【被追杀丢包撤离】
• 概率: {stats['hunted_escape']}
• 效果: 正常获得本次物品
• 惩罚: 只能保留小尺寸物品(1x1,1x2,2x1,1x3,3x1)
• 备注: 删除收藏中的大尺寸物品并重新计算仓库价值

🐭 【路人鼠鼠】
• 概率: {stats['passerby_mouse']}
• 效果: 正常获得物品
• 奖励: 获得金色物品，格子扩展到最大(7x7)
• 备注: 特勤处等级直接提升到最高级

💡 提示：事件在每次偷吃时独立计算概率"""
            
            yield event.plain_result(event_info)
            
        except Exception as e:
            logger.error(f"获取偷吃事件信息时出错: {e}")
            yield event.plain_result("❌ 获取偷吃事件信息失败，请重试")
