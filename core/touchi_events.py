import random
import asyncio
import aiosqlite
import time
from datetime import datetime
import os

class TouchiEvents:
    """偷吃概率事件处理类"""
    
    def __init__(self, db_path, biaoqing_dir, chixiao_system=None):
        self.db_path = db_path
        self.biaoqing_dir = biaoqing_dir
        self.chixiao_system = chixiao_system  # 赤枢系统
        
        # 事件概率配置
        self.event_probabilities = {
            "broken_liutao": 0.04,      #  概率获得残缺刘涛
            "genius_kick": 0.04,        #  概率遇到天才少年被踢死
            "genius_fine": 0.04,        #  概率排到天才少年被追缴
            "noob_teammate": 0.04,      #  概率遇到唐氏队友
            "hunted_escape": 0.04,      #  概率被追杀丢包撤离
            "passerby_mouse": 0.04,     #  概率遇到路人鼠鼠
            "system_compensation": 0.04,  #  概率触发系统补偿局
            "chixiao_battle": 0.20       #  概率触发赤枢对抗（优先级最高）
        }
        
        # 事件表情映射配置
        self.event_emoji_mapping = {
            "broken_liutao": "event_canque.gif",
            "genius_kick": "event_beitisi.gif", 
            "genius_fine": "event_zhuijiao.gif",
            "noob_teammate": "event_tangshi.gif",
            "hunted_escape": "event_zhuisha.gif",
            "passerby_mouse": "event_luren.gif",
            "system_compensation": "event_buchang.gif"
        }
    
    def get_event_emoji_path(self, event_type):
        """获取事件对应的表情文件路径
        
        Args:
            event_type: 事件类型
            
        Returns:
            str: 表情文件的完整路径，如果文件不存在或事件类型无效则返回 None
        """
        try:
            if not event_type:
                print(f"[TouchiEvents] 事件类型为空")
                return None
                
            if event_type not in self.event_emoji_mapping:
                print(f"[TouchiEvents] 未知的事件类型: {event_type}")
                return None
            
            emoji_filename = self.event_emoji_mapping[event_type]
            emoji_path = os.path.join(self.biaoqing_dir, emoji_filename)
            
            # 检查文件是否存在
            if os.path.exists(emoji_path):
                print(f"[TouchiEvents] 找到事件表情文件: {event_type} -> {emoji_path}")
                return emoji_path
            else:
                print(f"[TouchiEvents] 表情文件不存在: {emoji_path}")
                return None
                
        except Exception as e:
            print(f"[TouchiEvents] 获取事件表情路径时出错: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def check_random_events(self, event, user_id, placed_items, total_value, is_menggong_active=False):
        """检查是否触发随机事件
        
        Args:
            event: 消息事件
            user_id: 用户ID
            placed_items: 偷吃获得的物品列表
            total_value: 物品总价值
            is_menggong_active: 是否在猛攻状态
            
        Returns:
            tuple: (是否触发事件, 事件类型, 修改后的物品列表, 修改后的总价值, 事件消息, 冷却时间倍率, 金色物品路径, 表情路径)
        """
        
        # 优先检查赤枢对抗（仅在价值>=50000时）
        if self.chixiao_system and total_value >= 50000:
            rand = random.random()
            print(f"[TouchiEvents] 赤枢对抗检查: user_id={user_id}, total_value={total_value:,}, rand={rand:.4f}, prob={self.event_probabilities['chixiao_battle']:.2f}, is_menggong_active={is_menggong_active}")
            if rand < self.event_probabilities["chixiao_battle"]:
                print(f"[TouchiEvents] ✅ 概率检查通过，调用chixiao_system")
                # 触发赤枢对抗
                result = await self._handle_chixiao_battle_event(event, user_id, total_value, is_menggong_active)
                print(f"[TouchiEvents] chixiao_system返回结果: triggered={result[0]}, result_type={result[1]}")
                if result[0]:  # 如果成功触发
                    return result[0], result[1], result[2], result[3], result[4], None, None, result[5]
            else:
                print(f"[TouchiEvents] ❌ 概率检查未通过")
        
        # 随机检查其他事件
        rand = random.random()
        cumulative_prob = 0
        
        # 事件1: 获得残缺刘涛 
        cumulative_prob += self.event_probabilities["broken_liutao"]
        if rand < cumulative_prob:
            result = await self._handle_broken_liutao_event(event, user_id, placed_items, total_value)
            # result 包含: (triggered, type, items, value, message, emoji_path)
            return result[0], result[1], result[2], result[3], result[4], None, None, result[5]
        
        # 事件2: 遇到天才少年被踢死 
        cumulative_prob += self.event_probabilities["genius_kick"]
        if rand < cumulative_prob:
            result = await self._handle_genius_kick_event(event, user_id, placed_items, total_value)
            # result 包含: (triggered, type, items, value, message, emoji_path)
            return result[0], result[1], result[2], result[3], result[4], None, None, result[5]
        
        # 事件3: 排到天才少年被追缴 
        cumulative_prob += self.event_probabilities["genius_fine"]
        if rand < cumulative_prob:
            result = await self._handle_genius_fine_event(event, user_id, placed_items, total_value)
            # result 包含: (triggered, type, items, value, message, emoji_path)
            return result[0], result[1], result[2], result[3], result[4], None, None, result[5]
        
        # 事件4: 遇到唐氏队友 
        cumulative_prob += self.event_probabilities["noob_teammate"]
        if rand < cumulative_prob:
            result = await self._handle_noob_teammate_event(event, user_id, placed_items, total_value)
            # result 包含: (triggered, type, items, value, message, emoji_path)
            return result[0], result[1], result[2], result[3], result[4], 2.0, None, result[5]  # 冷却时间翻倍
        
        # 事件5: 被追杀丢包撤离 
        cumulative_prob += self.event_probabilities["hunted_escape"]
        if rand < cumulative_prob:
            result = await self._handle_hunted_escape_event(event, user_id, placed_items, total_value)
            # result 包含: (triggered, type, items, value, message, emoji_path)
            return result[0], result[1], result[2], result[3], result[4], None, None, result[5]
        
        # 事件6: 遇到路人鼠鼠 
        cumulative_prob += self.event_probabilities["passerby_mouse"]
        if rand < cumulative_prob:
            result = await self._handle_passerby_mouse_event(event, user_id, placed_items, total_value)
            if len(result) == 7:  # 路人鼠鼠事件返回7个值
                return result[0], result[1], result[2], result[3], result[4], None, result[5], result[6]
            else:
                return result[0], result[1], result[2], result[3], result[4], None, None, result[5]
        
        # 事件7: 系统补偿局 
        cumulative_prob += self.event_probabilities["system_compensation"]
        if rand < cumulative_prob:
            result = await self._handle_system_compensation_event(event, user_id, placed_items, total_value)
            # result 包含: (triggered, type, items, value, message, emoji_path)
            return result[0], result[1], result[2], result[3], result[4], 0.5, None, result[5]  # 冷却时间减半
        
        # 无事件触发
        return False, None, placed_items, total_value, None, None, None, None
    
    async def _handle_broken_liutao_event(self, event, user_id, placed_items, total_value):
        """处理获得残缺刘涛事件"""
        try:
            # 获取时间倍率
            time_multiplier = await self._get_menggong_time_multiplier()
            
            # 激活六套加成时间（基础1分钟 * 倍率）
            current_time = int(time.time())
            base_duration = 60  # 基础1分钟
            actual_duration = int(base_duration * time_multiplier)
            menggong_end_time = current_time + actual_duration
            
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    "UPDATE user_economy SET menggong_active = 1, menggong_end_time = ? WHERE user_id = ?",
                    (menggong_end_time, user_id)
                )
                await db.commit()
            
            # 创建事件消息
            duration_text = f"{actual_duration//60}分{actual_duration%60}秒" if actual_duration >= 60 else f"{actual_duration}秒"
            event_message = (
                "🎉 特殊事件触发！\n"
                "💎 你额外获得了残缺的刘涛！\n"
                f"⚡ 六套加成时间已激活 {duration_text}！\n"
                "🔥 期间红色和金色物品概率大幅提升！"
            )
            
            # 获取表情路径
            emoji_path = self.get_event_emoji_path("broken_liutao")
            return True, "broken_liutao", placed_items, total_value, event_message, emoji_path
            
        except Exception as e:
            print(f"处理残缺刘涛事件时出错: {e}")
            return False, None, placed_items, total_value, None, None
    
    async def _handle_genius_kick_event(self, event, user_id, placed_items, total_value):
        """处理遇到天才少年被踢死事件"""
        try:
            # 创建事件消息
            event_message = (
                "💀 特殊事件触发！\n"
                "👦 你遇到了天才少年，被一脚踢死了！\n"
                "📦 本次偷吃展示如下，但物品不会计入仓库！\n"
                "💸 本次偷吃的物品全部丢失..."
            )
            
            # 返回原物品用于展示，但总价值设为0（因为不计入数据库）
            emoji_path = self.get_event_emoji_path("genius_kick")
            return True, "genius_kick", placed_items, 0, event_message, emoji_path
            
        except Exception as e:
            print(f"处理天才少年踢死事件时出错: {e}")
            return False, None, placed_items, total_value, None, None
    
    async def _handle_genius_fine_event(self, event, user_id, placed_items, total_value):
        """处理排到天才少年被追缴事件"""
        try:
            # 追缴金额为偷吃价值的60%
            fine_amount = int(total_value * 0.6)
            
            async with aiosqlite.connect(self.db_path) as db:
                # 检查当前仓库价值（本次偷吃前的价值）
                cursor = await db.execute(
                    "SELECT warehouse_value FROM user_economy WHERE user_id = ?",
                    (user_id,)
                )
                result = await cursor.fetchone()
                current_value = result[0] if result else 0
                
                # 计算净收益：本次偷吃价值 - 追缴金额
                net_profit = total_value - fine_amount
                
                # 更新仓库价值：原有价值 + 净收益
                new_value = current_value + net_profit
                await db.execute(
                    "UPDATE user_economy SET warehouse_value = ? WHERE user_id = ?",
                    (new_value, user_id)
                )
                await db.commit()
            
            # 创建事件消息
            if net_profit >= 0:
                profit_text = f"💰 净收益: +{net_profit:,}"
            else:
                profit_text = f"💸 净收益: {net_profit:,}"
            
            event_message = (
                "⚖️ 特殊事件触发！\n"
                "👦 你排到了天才少年！\n"
                "🍽️ 虽然成功偷吃了，但被追缴了哈夫币！\n"
                f"📦 本次偷吃价值: {total_value:,}\n"
                f"⚖️ 追缴金额: {fine_amount:,} (60%)\n"
                f"{profit_text}\n"
                f"💰 仓库总价值: {new_value:,}"
            )
            
            # 获取表情路径
            emoji_path = self.get_event_emoji_path("genius_fine")
            return True, "genius_fine", placed_items, total_value, event_message, emoji_path
            
        except Exception as e:
            print(f"处理天才少年追缴事件时出错: {e}")
            return False, None, placed_items, total_value, None, None
    
    async def _handle_noob_teammate_event(self, event, user_id, placed_items, total_value):
        """处理遇到唐氏队友事件"""
        try:
            # 创建事件消息
            event_message = (
                "🤦 特殊事件触发！\n"
                "👥 你遇到了唐氏队友，撤离时间翻倍！\n"
                "⏰ 下次偷吃冷却时间增加一倍！"
            )
            
            # 获取表情路径
            emoji_path = self.get_event_emoji_path("noob_teammate")
            return True, "noob_teammate", placed_items, total_value, event_message, emoji_path
            
        except Exception as e:
            print(f"处理菜b队友事件时出错: {e}")
            return False, None, placed_items, total_value, None, None
    
    async def _handle_hunted_escape_event(self, event, user_id, placed_items, total_value):
        """处理被追杀丢包撤离事件"""
        try:
            # 不删除数据库中的物品，只是不保留本次大物品记录到库中
            allowed_sizes = ['1x1', '1x2', '2x1', '1x3', '3x1']
            
            # 过滤当前偷吃的物品，只保留小尺寸物品
            filtered_items = []
            current_items_removed = 0
            
            for placed_item in placed_items:
                item = placed_item["item"]
                item_base_name = item["base_name"]
                item_size = self._extract_size_from_name(item_base_name)
                
                if item_size and item_size in allowed_sizes:
                    # 保留小尺寸物品
                    filtered_items.append(placed_item)
                else:
                    # 丢弃大尺寸物品（不记录到数据库）
                    current_items_removed += 1
            
            # 重新计算当前偷吃的总价值
            filtered_value = 0
            for item in filtered_items:
                if "item" in item:
                    item_data = item["item"]
                    item_value = item_data.get("value", 0)
                    filtered_value += item_value
            
            # 创建事件消息
            event_message = (
                "🏃 特殊事件触发！\n"
                "🔫 你被追杀到了丢包撤离点！\n"
                "📦 只能保留小尺寸物品！"
            )
            
            # 获取表情路径
            emoji_path = self.get_event_emoji_path("hunted_escape")
            return True, "hunted_escape", filtered_items, filtered_value, event_message, emoji_path
            
        except Exception as e:
            print(f"处理被追杀丢包撤离事件时出错: {e}")
            return False, None, placed_items, total_value, None, None
    
    def _extract_size_from_name(self, item_name):
        """从物品名称中提取尺寸信息"""
        # 物品名称格式通常是: 等级_尺寸_物品名
        # 例如: "1_1x1_物品名" 或 "2_2x1_物品名"
        parts = item_name.split('_')
        if len(parts) >= 2:
            potential_size = parts[1]
            if 'x' in potential_size:
                return potential_size
        return None
    
    async def _recalculate_warehouse_value(self, db, user_id):
        """重新计算用户仓库价值"""
        from .touchi import get_item_value
        
        # 获取用户所有剩余物品
        cursor = await db.execute(
            "SELECT item_name, COUNT(*) FROM user_touchi_collection WHERE user_id = ? GROUP BY item_name",
            (user_id,)
        )
        items = await cursor.fetchall()
        
        # 计算总价值
        total_value = 0
        for item_name, count in items:
            item_value = get_item_value(item_name)
            total_value += item_value * count
        
        # 更新仓库价值
        await db.execute(
            "UPDATE user_economy SET warehouse_value = ? WHERE user_id = ?",
            (total_value, user_id)
         )
    
    async def _handle_passerby_mouse_event(self, event, user_id, placed_items, total_value):
        """处理遇到路人鼠鼠事件"""
        try:
            import os
            import glob
            import random
            
            # 获取所有金色物品
            items_dir = os.path.join(os.path.dirname(__file__), "items")
            gold_items = glob.glob(os.path.join(items_dir, "gold_*.png"))
            
            if gold_items:
                # 随机选择一个金色物品
                selected_gold_item = random.choice(gold_items)
                item_name = os.path.splitext(os.path.basename(selected_gold_item))[0]
                
                # 创建事件消息
                event_message = (
                    "🐭 特殊事件触发！\n"
                    "👋 你遇到了路人鼠鼠，你们打了暗号！\n"
                    f"🎁 ta送给了你金色物品"
                )
                
                # 获取表情路径
                emoji_path = self.get_event_emoji_path("passerby_mouse")
                # 返回原始物品和价值，金色物品将在重新生成时添加
                return True, "passerby_mouse", placed_items, total_value, event_message, selected_gold_item, emoji_path
            else:
                # 如果没有金色物品，返回正常结果
                return False, None, placed_items, total_value, None, None, None
                
        except Exception as e:
            print(f"处理路人鼠鼠事件时出错: {e}")
            return False, None, placed_items, total_value, None, None, None
    
    async def _handle_system_compensation_event(self, event, user_id, placed_items, total_value):
        """处理系统补偿局事件"""
        try:
            # 创建事件消息
            event_message = (
                "🎯 特殊事件触发！\n"
                "🔧 系统补偿局已启动！\n"
                "⚡ 本次爆率巨幅提升\n"
                "🕐 下次偷吃冷却时间减半！"
            )
            
            # 获取表情路径
            emoji_path = self.get_event_emoji_path("system_compensation")
            return True, "system_compensation", placed_items, total_value, event_message, emoji_path
            
        except Exception as e:
            print(f"处理系统补偿局事件时出错: {e}")
            return False, None, placed_items, total_value, None, None
     
    def get_event_statistics(self):
        """获取事件概率统计信息"""
        total_prob = sum(self.event_probabilities.values())
        normal_prob = 1 - total_prob
        
        return {
            "normal": f"{normal_prob:.1%}",
            "broken_liutao": f"{self.event_probabilities['broken_liutao']:.1%}",
            "genius_kick": f"{self.event_probabilities['genius_kick']:.1%}",
            "genius_fine": f"{self.event_probabilities['genius_fine']:.1%}",
            "noob_teammate": f"{self.event_probabilities['noob_teammate']:.1%}",
            "hunted_escape": f"{self.event_probabilities['hunted_escape']:.1%}",
            "passerby_mouse": f"{self.event_probabilities['passerby_mouse']:.1%}",
            "system_compensation": f"{self.event_probabilities['system_compensation']:.1%}",
            "total_event": f"{total_prob:.1%}"
        }
    
    async def _get_menggong_time_multiplier(self):
        """获取当前六套时间倍率"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "SELECT config_value FROM system_config WHERE config_key = 'menggong_time_multiplier'"
                )
                result = await cursor.fetchone()
                if result:
                    return float(result[0])
                else:
                    return 1.0  # 默认倍率
        except Exception as e:
            print(f"获取六套时间倍率时出错: {e}")
            return 1.0  # 默认倍率

    async def _handle_chixiao_battle_event(self, event, user_id, total_value, is_menggong_active):
        """处理赤枭对抗事件"""
        if not self.chixiao_system:
            print(f"[TouchiEvents] ❌ chixiao_system 为 None")
            return False, None, None, 0, None, None
        
        try:
            # 检查是否存在赤枢玩家
            chixiao_players = await self.chixiao_system.get_all_chixiao_players()
            if not chixiao_players:
                print(f"[TouchiEvents] ❌ 没有赤枢玩家，跳过赤枭对抗")
                return False, None, None, 0, None, None
            
            print(f"[TouchiEvents] 调用 check_and_trigger_battle: user_id={user_id}, total_value={total_value:,}, is_menggong_active={is_menggong_active}, 赤枢数量={len(chixiao_players)}")
            # 调用赤枢系统的检查方法
            triggered, result_type, chixiao_id, amount, kills = await self.chixiao_system.check_and_trigger_battle(
                user_id, total_value, is_menggong_active
            )
            print(f"[TouchiEvents] check_and_trigger_battle 返回: triggered={triggered}, result_type={result_type}, chixiao_id={chixiao_id}, amount={amount}, kills={kills}")
            
            if not triggered:
                print(f"[TouchiEvents] ❌ 赤枢系统返回未触发（可能没有满足条件的赤枢）")
                return False, None, None, 0, None, None
            
            # 获取赤枭对抗的表情路径
            emoji_path = self.chixiao_system.get_emoji_path(result_type)
            
            # 根据结果构建消息
            if result_type == "chixiao_won":
                event_message = (
                    f"⚔️ 赤枭对抗触发！\n"
                    f"🎯 赤枭发动袭击！\n"
                    f"🆔 赤枭ID: {chixiao_id}\n"
                    f"💸 你的{amount:,}哈夫币被赤枭抢走了！\n"
                    f"💔 赤枭击杀数: {kills}"
                )
                # 赤枭获胜：偷吃价值归零
                final_value = 0
            elif result_type == "victim_won":
                event_message = (
                    f"⚔️ 赤枭对抗触发！\n"
                    f"🎉 你击败了赤枭！\n"
                    f"🆔 赤枭ID: {chixiao_id}\n"
                    f"💰 获得赤枭的{amount:,}哈夫币！\n"
                    f"🏆 赤枭已被击杀！"
                )
                # 玩家获胜：获得赤枭所有价值
                final_value = amount
            else:
                return False, None, None, 0, None, None
            
            # 返回结果（注意：赤枭对抗不返回物品列表，因为价值已经改变）
            return True, "chixiao_battle", None, final_value, event_message, emoji_path
            
        except Exception as e:
            print(f"处理赤枭对抗事件时出错: {e}")
            return False, None, None, 0, None, None
