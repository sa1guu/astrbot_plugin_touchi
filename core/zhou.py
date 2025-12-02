import random
import os
import asyncio
import aiosqlite
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
import json
import math

class ZhouGame:
    """洲了个洲游戏类 - 基于羊了个羊的正确游戏规则"""
    
    def __init__(self, db_path, items_dir, output_dir):
        self.db_path = db_path
        self.items_dir = items_dir
        self.output_dir = output_dir
        
        # 游戏配置
        self.CARD_SIZE = (80, 80)  # 卡牌大小（放大）
        self.BOARD_SIZE = (1000, 750)  # 游戏板大小（相应放大）
        self.CARD_RADIUS = 12  # 卡牌圆角半径
        self.CARD_THICKNESS = 6  # 卡牌厚度效果（增加厚度）
        self.CORNER_RADIUS = 20  # 左上角圆弧半径
        
        # 难度配置
        self.DIFFICULTY_CONFIGS = {
            'easy': {
                'slot_size': 6,
                'max_layers': 6,
                'overlap_factor': 0.7,  # 重叠程度
                'card_density': 0.8,    # 卡牌密度
            },
            'medium': {
                'slot_size': 5,
                'max_layers': 8,
                'overlap_factor': 0.8,
                'card_density': 0.9,
            },
            'hard': {
                'slot_size': 5,
                'max_layers': 10,
                'overlap_factor': 0.9,
                'card_density': 1.0,
            }
        }
        
        # 道具次数
        self.DEFAULT_UNDO = 2      # 撤回次数
        self.DEFAULT_SHUFFLE = 2   # 洗牌次数
        self.DEFAULT_REMOVE = 1    # 移出卡槽次数
        
    async def init_game_tables(self):
        """初始化游戏数据库表"""
        async with aiosqlite.connect(self.db_path) as db:
            # 群组游戏状态表
            await db.execute("""
                CREATE TABLE IF NOT EXISTS zhou_group_games (
                    group_id TEXT PRIMARY KEY,
                    game_data TEXT,
                    players TEXT,  -- JSON格式的玩家列表
                    current_player TEXT,  -- 当前轮到的玩家ID
                    turn_order TEXT,  -- JSON格式的轮次顺序
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 个人游戏状态表（保留兼容性）
            await db.execute("""
                CREATE TABLE IF NOT EXISTS zhou_games (
                    user_id TEXT PRIMARY KEY,
                    game_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 游戏统计表
            await db.execute("""
                CREATE TABLE IF NOT EXISTS zhou_stats (
                    user_id TEXT PRIMARY KEY,
                    games_played INTEGER DEFAULT 0,
                    games_won INTEGER DEFAULT 0,
                    best_score INTEGER DEFAULT 0,
                    total_score INTEGER DEFAULT 0
                )
            """)
            
            await db.commit()
    
    def get_available_items(self):
        """获取可用的物品图片 - 只选择1x1, 2x2, 3x3的物品"""
        items = []
        valid_sizes = ['1x1', '2x2', '3x3']
        for filename in os.listdir(self.items_dir):
            if filename.endswith('.png'):
                # 检查文件名是否包含有效尺寸
                if any(size in filename for size in valid_sizes):
                    items.append(filename)
        return items
    
    def generate_layered_cards(self, difficulty=None):
        """生成分层卡牌布局 - 模拟羊了个羊的层级结构"""
        available_items = self.get_available_items()
        if len(available_items) < 8:
            raise ValueError("需要至少8种不同的物品图片")
        
        # 随机选择难度（如果未指定）
        if difficulty is None:
            difficulty = random.choice(['easy', 'medium', 'hard'])
        
        difficulty_config = self.DIFFICULTY_CONFIGS[difficulty]
        
        # 选择8种物品类型
        selected_items = random.sample(available_items, 8)
        
        # 生成卡牌数据，确保每种类型的数量是3的倍数
        cards = []
        card_id = 1
        
        # 根据难度调整卡牌数量
        base_counts = [3, 6, 9]
        if difficulty == 'hard':
            base_counts = [6, 9, 12]  # 困难模式更多卡牌
        elif difficulty == 'medium':
            base_counts = [3, 6, 9, 12]
        
        # 为每种物品生成卡牌
        for item in selected_items:
            count = random.choice(base_counts)
            for _ in range(count):
                cards.append({
                    'id': card_id,
                    'type': item,
                    'image_path': os.path.join(self.items_dir, item),
                    'x': 0,
                    'y': 0,
                    'layer': 0,
                    'clickable': False
                })
                card_id += 1
        
        # 打乱卡牌
        random.shuffle(cards)
        
        # 生成层级布局
        self.arrange_cards_in_layers(cards, difficulty_config)
        
        return cards, difficulty
    
    def arrange_cards_in_layers(self, cards, difficulty_config):
        """安排卡牌的层级布局"""
        # 严格定义游戏区域：上方为卡牌区域，下方为卡槽区域
        game_area_height = 500  # 卡牌游戏区域高度
        slot_area_start = 550   # 卡槽区域开始位置
        
        max_layers = difficulty_config['max_layers']
        overlap_factor = difficulty_config['overlap_factor']
        
        # 根据难度动态生成层级布局
        layouts = []
        base_radius = 200
        
        for layer in range(max_layers):
            # 随机化每层的中心位置和半径
            center_x = random.randint(400, 600)
            center_y = random.randint(200, 350)
            radius = base_radius - (layer * 15) + random.randint(-20, 20)
            spread = 1.5 - (layer * 0.1) + random.uniform(-0.1, 0.1)
            
            layouts.append({
                'center': (center_x, center_y),
                'radius': max(40, radius),
                'layer': layer,
                'spread': max(0.5, spread)
            })
        
        # 底部隐藏牌区域（4排）- 调整位置避开卡槽
        bottom_cards = cards[-16:] if len(cards) >= 16 else cards[-len(cards)//4:]
        remaining_cards = cards[:-len(bottom_cards)] if bottom_cards else cards
        
        # 安排底部隐藏牌 - 严格限制在游戏区域内
        for i, card in enumerate(bottom_cards):
            if i < 8:  # 左侧
                row = i // 2
                col = i % 2
                card['x'] = 30 + col * 45
                card['y'] = 400 + row * 30
            else:  # 右侧
                row = (i - 8) // 2
                col = (i - 8) % 2
                card['x'] = 850 + col * 45
                card['y'] = 400 + row * 30
            
            # 确保不超出游戏区域
            card['y'] = min(card['y'], game_area_height - self.CARD_SIZE[1])
            
            # 底部隐藏牌的层级设置：从底层到顶层递增
            # 最底层为0，向上递增，最顶层为3
            card['layer'] = i // 4  # 每4张卡牌为一层
            card['clickable'] = (i >= len(bottom_cards) - 4)  # 只有最上面一排可点击
        
        # 安排主要区域卡牌 - 根据难度优化分布策略
        card_index = 0
        total_remaining = len(remaining_cards)
        
        # 根据难度动态计算每层的卡牌数量分布
        layer_distribution = {}
        remaining_percentage = 1.0
        
        for layer in range(max_layers):
            if layer < max_layers - 1:
                # 前面的层级分配更多卡牌，后面的层级逐渐减少
                if layer < max_layers // 2:
                    percentage = remaining_percentage * random.uniform(0.2, 0.4)
                else:
                    percentage = remaining_percentage * random.uniform(0.1, 0.3)
                layer_distribution[layer] = int(total_remaining * percentage)
                remaining_percentage -= percentage
            else:
                # 最后一层分配剩余的卡牌
                layer_distribution[layer] = int(total_remaining * remaining_percentage)
        
        for layout in layouts:
            layer = layout['layer']
            layer_card_count = layer_distribution.get(layer, 0)
            
            # 确保不超过剩余卡牌数
            layer_card_count = min(layer_card_count, len(remaining_cards) - card_index)
            
            for i in range(layer_card_count):
                if card_index >= len(remaining_cards):
                    break
                    
                card = remaining_cards[card_index]
                
                # 更散开的分布算法
                attempts = 0
                while attempts < 10:  # 最多尝试10次找到合适位置
                    angle = random.uniform(0, 2 * math.pi)
                    # 使用更大的随机范围，让卡牌更散开
                    radius = random.uniform(layout['radius'] * 0.3, layout['radius'] * layout['spread'])
                    
                    x = int(layout['center'][0] + radius * math.cos(angle))
                    y = int(layout['center'][1] + radius * math.sin(angle))
                    
                    # 严格限制在游戏区域内
                    x = max(10, min(x, self.BOARD_SIZE[0] - self.CARD_SIZE[0] - 10))
                    y = max(80, min(y, game_area_height - self.CARD_SIZE[1]))
                    
                    # 检查是否与已放置的卡牌距离太近（根据难度调整重叠程度）
                    too_close = False
                    base_distance = 30
                    min_distance = int(base_distance * (1 - overlap_factor))  # 重叠因子越大，最小距离越小
                    
                    for placed_card in remaining_cards[:card_index]:
                        if placed_card.get('x') is not None:
                            distance = math.sqrt((x - placed_card['x'])**2 + (y - placed_card['y'])**2)
                            if distance < min_distance:
                                too_close = True
                                break
                    
                    if not too_close:
                        break
                    attempts += 1
                
                card['x'] = x
                card['y'] = y
                # 主要区域卡牌的层级需要高于底部隐藏牌（底部隐藏牌最高层级为3）
                card['layer'] = layout['layer'] + 4  # 从层级4开始
                
                card_index += 1
        
        # 计算可点击性
        self.update_clickable_status(cards)
    
    def update_clickable_status(self, cards):
        """更新卡牌的可点击状态 - 基于完整遮挡检测"""
        # 过滤有效卡牌
        valid_cards = [c for c in cards if c.get('id') is not None]
        
        # 为每张卡牌检查可点击状态
        for card in valid_cards:
            visited = set()
            card['clickable'] = self._is_card_truly_clickable(card, valid_cards, visited)
    
    def _is_card_clickable_by_center_distance(self, target_card, all_cards):
        """检查卡牌是否可点击 - 基于中心点距离的遮挡检测"""
        # 只有顶层未被遮挡的卡片可以点击
        # 检查是否有更高层级的卡牌遮挡当前卡牌
        for other_card in all_cards:
            if (other_card['id'] != target_card['id'] and 
                other_card['layer'] > target_card['layer'] and 
                self._rectangles_intersect_by_center_distance(target_card, other_card)):
                return False
        return True
    
    def _rectangles_intersect_by_center_distance(self, card1, card2):
        """基于矩形相交判断的遮挡检测方法
        
        通过计算两个矩形中心点在X轴和Y轴的距离是否小于各自宽度/高度一半的和，
        来判断是否存在遮挡。同时考虑卡片的层级(level)，只有上层卡片可能遮挡下层卡片。
        排除细长条重叠的情况。
        """
        x1, y1 = card1['x'], card1['y']
        x2, y2 = card2['x'], card2['y']
        w, h = self.CARD_SIZE
        
        # 计算两个矩形的中心点
        center1_x = x1 + w // 2
        center1_y = y1 + h // 2
        center2_x = x2 + w // 2
        center2_y = y2 + h // 2
        
        # 计算中心点在X轴和Y轴的距离
        dx = abs(center1_x - center2_x)
        dy = abs(center1_y - center2_y)
        
        # 计算各自宽度/高度一半的和
        half_width_sum = w  # w/2 + w/2 = w
        half_height_sum = h  # h/2 + h/2 = h
        
        # 如果中心点距离小于各自宽度/高度一半的和，则可能存在遮挡
        if dx < half_width_sum and dy < half_height_sum:
            # 计算实际重叠区域，排除细长条重叠
            left1, top1, right1, bottom1 = x1, y1, x1 + w, y1 + h
            left2, top2, right2, bottom2 = x2, y2, x2 + w, y2 + h
            
            # 计算重叠区域
            overlap_left = max(left1, left2)
            overlap_top = max(top1, top2)
            overlap_right = min(right1, right2)
            overlap_bottom = min(bottom1, bottom2)
            
            if overlap_right > overlap_left and overlap_bottom > overlap_top:
                overlap_width = overlap_right - overlap_left
                overlap_height = overlap_bottom - overlap_top
                
                # 排除细长条重叠：如果重叠区域的最小维度小于20像素，不算遮挡
                min_overlap_dimension = min(overlap_width, overlap_height)
                if min_overlap_dimension < 20:
                    return False
                
                # 计算重叠面积比例
                overlap_area = overlap_width * overlap_height
                card_area = w * h
                overlap_ratio = overlap_area / card_area
                
                # 如果重叠面积超过30%，认为被遮挡
                return overlap_ratio > 0.3
        
        return False
    
    def _is_card_truly_clickable(self, target_card, all_cards, visited):
        """递归检查卡牌是否真正可点击
        
        用户需求的逻辑：
        - 既要检查单个显著遮挡，也要检查累积遮挡效应
        - 如果一张卡牌被遮挡，且遮挡它的卡牌也被遮挡，那么这张卡牌无论被遮挡多少像素都应显示为灰色且不可拿取
        
        实现逻辑：
        1. 首先检查是否有单个显著遮挡（使用cards_overlap方法）
        2. 如果没有单个显著遮挡，再检查累积遮挡是否超过阈值
        3. 任一条件满足都不可点击
        """
        # 避免无限递归
        if target_card['id'] in visited:
            return False
        
        visited.add(target_card['id'])
        
        # 第一步：检查是否有单个显著遮挡
        for other_card in all_cards:
            if (other_card['id'] != target_card['id'] and 
                other_card['layer'] > target_card['layer']):
                
                # 使用cards_overlap方法进行完整的遮挡判断
                if self.cards_overlap(target_card, other_card):
                    # 有显著遮挡，直接不可点击
                    visited.remove(target_card['id'])
                    return False
        
        # 第二步：检查累积遮挡效应
        total_overlap_area = 0
        total_thin_strip_area = 0
        card_area = self.CARD_SIZE[0] * self.CARD_SIZE[1]  # 80 * 80 = 6400
        
        for other_card in all_cards:
            if (other_card['id'] != target_card['id'] and 
                other_card['layer'] > target_card['layer']):
                
                # 计算重叠区域
                x1, y1 = target_card['x'], target_card['y']
                x2, y2 = other_card['x'], other_card['y']
                w, h = self.CARD_SIZE
                
                overlap_left = max(x1, x2)
                overlap_top = max(y1, y2)
                overlap_right = min(x1 + w, x2 + w)
                overlap_bottom = min(y1 + h, y2 + h)
                
                if overlap_left < overlap_right and overlap_top < overlap_bottom:
                    overlap_width = overlap_right - overlap_left
                    overlap_height = overlap_bottom - overlap_top
                    overlap_area = overlap_width * overlap_height
                    
                    min_overlap_dimension = min(overlap_width, overlap_height)
                    if min_overlap_dimension < 15:
                        # 细长条重叠，累积计算细长条面积
                        total_thin_strip_area += overlap_area
                    else:
                        # 非细长条重叠，累积计算总面积
                        total_overlap_area += overlap_area
                        # 递归检查遮挡卡牌是否可点击，若不可点击则视为有效遮挡
                        if not self._is_card_truly_clickable(other_card, all_cards, visited):
                            visited.remove(target_card['id'])
                            return False
        
        # 计算累积遮挡比例
        cumulative_overlap_ratio = total_overlap_area / card_area
        thin_strip_ratio = total_thin_strip_area / card_area
        
        # 如果非细长条累积遮挡超过30%，则认为不可点击
        if cumulative_overlap_ratio >= 0.30:
            visited.remove(target_card['id'])
            return False
        
        # 如果细长条累积遮挡超过30%，也认为不可点击
        if thin_strip_ratio >= 0.30:
            visited.remove(target_card['id'])
            return False
        
        # 没有被显著遮挡，可点击
        visited.remove(target_card['id'])
        return True
    
    def cards_overlap(self, card1, card2):
        """检查card2是否遮挡card1 - 基于矩形相交和视觉遮挡的综合判断
        
        Args:
            card1: 被检查的卡牌（可能被遮挡）
            card2: 检查是否遮挡card1的卡牌
            
        Returns:
            bool: 如果card2显著遮挡了card1，返回True
        """
        x1, y1 = card1['x'], card1['y']
        x2, y2 = card2['x'], card2['y']
        w, h = self.CARD_SIZE
        
        # 方法1: 基于矩形中心点距离的快速判断
        center1_x, center1_y = x1 + w // 2, y1 + h // 2
        center2_x, center2_y = x2 + w // 2, y2 + h // 2
        
        dx = abs(center1_x - center2_x)
        dy = abs(center1_y - center2_y)
        
        # 如果中心点距离太远，直接判定无遮挡
        if dx >= w or dy >= h:
            return False
        
        # 方法2: 精确的矩形相交检测
        left1, top1, right1, bottom1 = x1, y1, x1 + w, y1 + h
        left2, top2, right2, bottom2 = x2, y2, x2 + w, y2 + h
        
        # 检查是否有重叠
        if right1 <= left2 or right2 <= left1 or bottom1 <= top2 or bottom2 <= top1:
            return False
        
        # 计算重叠区域
        overlap_left = max(left1, left2)
        overlap_top = max(top1, top2)
        overlap_right = min(right1, right2)
        overlap_bottom = min(bottom1, bottom2)
        
        overlap_width = overlap_right - overlap_left
        overlap_height = overlap_bottom - overlap_top
        
        if overlap_width <= 0 or overlap_height <= 0:
            return False
        
        # 方法3: 统一的遮挡判断算法
        overlap_area = overlap_width * overlap_height
        card_area = w * h
        overlap_ratio = overlap_area / card_area
        
        # 排除细长条重叠（降低阈值到8像素，更合理）
        min_overlap_dimension = min(overlap_width, overlap_height)
        if min_overlap_dimension < 8:
            return False
        
        # 统一的面积阈值判断：20%面积阈值或800像素绝对阈值
        if overlap_ratio >= 0.20 or overlap_area >= 800:
            return True
        
        # 中心区域遮挡检测（修复逻辑错误）
        center_margin = 15  # 减少边距，避免中心区域过小
        
        # 确保中心区域有效（边界检查）
        if w > 2 * center_margin and h > 2 * center_margin:
            center_left = x1 + center_margin
            center_top = y1 + center_margin
            center_right = x1 + w - center_margin
            center_bottom = y1 + h - center_margin
            
            # 计算中心区域与重叠区域的交集
            center_overlap_left = max(overlap_left, center_left)
            center_overlap_top = max(overlap_top, center_top)
            center_overlap_right = min(overlap_right, center_right)
            center_overlap_bottom = min(overlap_bottom, center_bottom)
            
            # 检查是否有有效的中心区域重叠
            if (center_overlap_right > center_overlap_left and 
                center_overlap_bottom > center_overlap_top):
                # 计算中心区域遮挡比例
                center_area = (center_right - center_left) * (center_bottom - center_top)
                center_overlap_area = (center_overlap_right - center_overlap_left) * (center_overlap_bottom - center_overlap_top)
                center_overlap_ratio = center_overlap_area / center_area
                
                # 中心区域遮挡超过30%才认为是显著遮挡
                if center_overlap_ratio >= 0.30:
                    return True
        
        return False
    
    async def start_new_game(self, user_id, is_triggered=False):
        """开始新游戏
        
        Args:
            user_id: 用户ID
            is_triggered: 是否为偷吃触发的游戏（True为偷吃触发，False为主动发送）
        """
        try:
            # 生成分层卡牌（随机难度）
            cards, difficulty = self.generate_layered_cards()
            difficulty_config = self.DIFFICULTY_CONFIGS[difficulty]
            
            # 初始化游戏状态
            game_start_time = datetime.now().strftime("%Y%m%d_%H%M%S")
            game_state = {
                'cards': cards,
                'slot': [],  # 卡槽
                'undo_count': self.DEFAULT_UNDO,
                'shuffle_count': self.DEFAULT_SHUFFLE,
                'remove_count': self.DEFAULT_REMOVE,
                'history': [],  # 操作历史
                'status': 'playing',  # playing, won, lost
                'score': 0,
                'difficulty': difficulty,  # 保存难度信息
                'slot_size': difficulty_config['slot_size'],  # 动态卡槽大小
                'game_start_time': game_start_time,  # 游戏开始时间，用于保持图片文件名一致
                'is_triggered': is_triggered  # 标记是否为偷吃触发的游戏
            }
            
            # 保存游戏状态
            await self.save_game_state(user_id, game_state)
            
            # 生成游戏图片
            image_path = await self.generate_game_image(user_id, game_state)
            
            # 检查图片是否生成成功
            if image_path is None:
                print(f"用户 {user_id} 的游戏图片生成失败")
                return False, None, "游戏图片生成失败，请稍后重试"
            
            # 根据难度显示不同的开始消息
            difficulty_names = {'easy': '简单', 'medium': '中等', 'hard': '困难'}
            difficulty_name = difficulty_names.get(difficulty, difficulty)
            
            return True, image_path, f"🎮 洲了个洲游戏开始！\n🎯 难度: {difficulty_name} | 卡槽: {difficulty_config['slot_size']}个"
            
        except Exception as e:
            print(f"开始新游戏时出错: {e}")
            return False, None, "游戏初始化失败，请稍后重试"
    
    async def save_game_state(self, user_id, game_state):
        """保存游戏状态"""
        async with aiosqlite.connect(self.db_path) as db:
            game_data = json.dumps(game_state, ensure_ascii=False)
            await db.execute(
                "INSERT OR REPLACE INTO zhou_games (user_id, game_data, updated_at) VALUES (?, ?, ?)",
                (user_id, game_data, datetime.now().isoformat())
            )
            await db.commit()
    
    async def load_game_state(self, user_id):
        """加载游戏状态"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT game_data FROM zhou_games WHERE user_id = ?",
                (user_id,)
            )
            result = await cursor.fetchone()
            
            if result:
                return json.loads(result[0])
            return None
    
    async def take_cards(self, user_id, card_numbers):
        """拿取卡牌"""
        try:
            game_state = await self.load_game_state(user_id)
            if not game_state or game_state['status'] != 'playing':
                return False, None, "没有进行中的游戏，请先开始新游戏"
            
            # 获取可点击的卡牌
            clickable_cards = [card for card in game_state['cards'] if card['clickable']]
            valid_cards = []
            
            for num in card_numbers:
                card = next((c for c in clickable_cards if c['id'] == num), None)
                if card:
                    valid_cards.append(card)
                else:
                    return False, None, f"卡牌 {num} 不存在或被遮挡，无法点击！"
            
            if not valid_cards:
                return False, None, "没有有效的卡牌"
            
            # 检查卡槽空间（使用动态卡槽大小）
            slot_size = game_state.get('slot_size', 7)  # 兼容旧存档
            if len(game_state['slot']) + len(valid_cards) > slot_size:
                return False, None, f"卡槽空间不足！当前: {len(game_state['slot'])}/{slot_size}"
            
            # 保存操作历史（保存完整的卡牌信息和场上状态）
            game_state['history'].append({
                'action': 'take',
                'cards': [card.copy() for card in valid_cards],  # 保存完整卡牌信息
                'slot_before': game_state['slot'].copy(),
                'cards_before': game_state['cards'].copy()  # 保存场上卡牌状态
            })
            
            # 将卡牌移到卡槽
            for card in valid_cards:
                game_state['slot'].append(card)
                # 从场上移除卡牌
                game_state['cards'] = [c for c in game_state['cards'] if c['id'] != card['id']]
            
            # 更新可点击状态
            self.update_clickable_status(game_state['cards'])
            
            # 保存消除前的状态（用于撤回）
            slot_before_elimination = game_state['slot'].copy()
            score_before_elimination = game_state['score']
            
            # 检查消除
            eliminated = self.check_elimination(game_state)
            
            # 如果有消除，更新历史记录
            if eliminated > 0:
                game_state['history'][-1]['eliminated'] = eliminated
                game_state['history'][-1]['slot_after_elimination'] = game_state['slot'].copy()
                game_state['history'][-1]['score_before_elimination'] = score_before_elimination
            
            # 检查游戏状态
            if not game_state['cards']:
                game_state['status'] = 'won'
                await self.update_stats(user_id, True, game_state['score'])
                # 发放哈夫币奖励
                async with aiosqlite.connect(self.db_path) as db:
                    await self._check_and_reward_trigger_event(user_id, db, game_state)
            elif len(game_state['slot']) >= slot_size:
                # 检查是否还有可消除的组合
                if not self.has_possible_elimination(game_state['slot']):
                    game_state['status'] = 'lost'
                    await self.update_stats(user_id, False, game_state['score'])
            
            # 保存游戏状态
            await self.save_game_state(user_id, game_state)
            
            # 生成游戏图片
            image_path = await self.generate_game_image(user_id, game_state)
            
            # 生成消息
            message = ""
            if game_state['status'] == 'won':
                # 检查是否有触发事件奖励
                reward_message = await self._check_trigger_reward_message(user_id, game_state)
                base_message = "🏆 恭喜获胜！所有卡牌已清空！"
                message = base_message + reward_message if reward_message else base_message
            elif game_state['status'] == 'lost':
                message = "💀 游戏失败！卡槽已满且无法消除！"
            else:
                # 拿取成功，不显示消除提示
                message = f"✅ 成功拿取 {len(valid_cards)} 张卡牌！卡槽: {len(game_state['slot'])}/{slot_size}"
            
            return True, image_path, message
            
        except Exception as e:
            print(f"拿取卡牌时出错: {e}")
            return False, None, "操作失败，请稍后重试"
    
    def check_elimination(self, game_state):
        """检查并执行消除"""
        eliminated_count = 0
        
        # 统计卡槽中每种卡牌的数量
        card_counts = {}
        for card in game_state['slot']:
            card_type = card['type']
            if card_type not in card_counts:
                card_counts[card_type] = []
            card_counts[card_type].append(card)
        
        # 消除3张相同的卡牌
        for card_type, cards in card_counts.items():
            while len(cards) >= 3:
                # 移除3张相同卡牌
                for _ in range(3):
                    card_to_remove = cards.pop(0)
                    game_state['slot'].remove(card_to_remove)
                eliminated_count += 1
                game_state['score'] += 100  # 每消除一组得100分
        
        return eliminated_count
    
    def has_possible_elimination(self, slot):
        """检查卡槽中是否还有可能的消除组合"""
        card_counts = {}
        for card in slot:
            card_type = card['type']
            card_counts[card_type] = card_counts.get(card_type, 0) + 1
        
        # 如果有任何类型的卡牌数量达到3张，就可以消除
        return any(count >= 3 for count in card_counts.values())
    
    async def use_undo(self, user_id):
        """使用撤回道具"""
        try:
            game_state = await self.load_game_state(user_id)
            if not game_state or game_state['status'] != 'playing':
                return False, None, "没有进行中的游戏"
            
            if game_state['undo_count'] <= 0:
                return False, None, "撤回次数已用完"
            
            if not game_state['history']:
                return False, None, "没有可撤回的操作"
            
            # 撤回最后一次操作
            last_action = game_state['history'].pop()
            if last_action['action'] == 'take':
                # 恢复场上卡牌状态（如果有保存的话）
                if 'cards_before' in last_action:
                    game_state['cards'] = last_action['cards_before'].copy()
                else:
                    # 兼容旧版本历史记录，将拿取的卡牌放回场上
                    taken_cards = last_action['cards']
                    for card in taken_cards:
                        if isinstance(card, dict):  # 新版本保存的完整卡牌信息
                            game_state['cards'].append(card.copy())
                        else:  # 旧版本只保存了ID
                            # 这种情况下无法完全恢复，只能跳过
                            pass
                
                # 恢复卡槽状态（撤回拿取操作）
                game_state['slot'] = last_action['slot_before'].copy()
                
                # 如果有消除操作，恢复分数
                if 'eliminated' in last_action and last_action['eliminated'] > 0:
                    if 'score_before_elimination' in last_action:
                        game_state['score'] = last_action['score_before_elimination']
            
            # 更新可点击状态
            self.update_clickable_status(game_state['cards'])
            
            game_state['undo_count'] -= 1
            game_state['status'] = 'playing'  # 重置游戏状态
            
            await self.save_game_state(user_id, game_state)
            image_path = await self.generate_game_image(user_id, game_state)
            
            return True, image_path, f"⏪ 撤回成功！剩余撤回次数: {game_state['undo_count']}"
            
        except Exception as e:
            print(f"使用撤回时出错: {e}")
            return False, None, "撤回失败，请稍后重试"
    
    async def use_shuffle(self, user_id):
        """使用洗牌道具"""
        try:
            game_state = await self.load_game_state(user_id)
            if not game_state or game_state['status'] != 'playing':
                return False, None, "没有进行中的游戏"
            
            if game_state['shuffle_count'] <= 0:
                return False, None, "洗牌次数已用完"
            
            if len(game_state['cards']) <= 1:
                return False, None, "场上卡牌太少，无需洗牌"
            
            # 重新安排卡牌布局
            difficulty = game_state.get('difficulty', 'medium')
            difficulty_config = self.DIFFICULTY_CONFIGS[difficulty]
            self.arrange_cards_in_layers(game_state['cards'], difficulty_config)
            
            # 更新可点击状态
            self.update_clickable_status(game_state['cards'])
            
            game_state['shuffle_count'] -= 1
            
            await self.save_game_state(user_id, game_state)
            image_path = await self.generate_game_image(user_id, game_state)
            
            return True, image_path, f"🔀 洗牌成功！剩余洗牌次数: {game_state['shuffle_count']}"
            
        except Exception as e:
            print(f"使用洗牌时出错: {e}")
            return False, None, "洗牌失败，请稍后重试"
    
    async def use_remove_slot(self, user_id):
        """使用移出卡槽道具"""
        try:
            game_state = await self.load_game_state(user_id)
            if not game_state or game_state['status'] != 'playing':
                return False, None, "没有进行中的游戏"
            
            if game_state['remove_count'] <= 0:
                return False, None, "移出卡槽次数已用完"
            
            if len(game_state['slot']) < 3:
                return False, None, "卡槽中卡牌不足3张，无需移出"
            
            # 移出卡槽中的前3张卡牌
            removed_cards = []
            for _ in range(min(3, len(game_state['slot']))):
                removed_cards.append(game_state['slot'].pop(0))
            
            game_state['remove_count'] -= 1
            
            await self.save_game_state(user_id, game_state)
            image_path = await self.generate_game_image(user_id, game_state)
            
            return True, image_path, f"🗑️ 移出3张卡牌成功！剩余移出次数: {game_state['remove_count']}"
            
        except Exception as e:
            print(f"使用移出卡槽时出错: {e}")
            return False, None, "移出卡槽失败，请稍后重试"
    
    def cleanup_old_images(self, user_id, max_images=3):
        """清理用户的旧游戏图片，保留最新的max_images张"""
        try:
            # 获取该用户的所有游戏图片
            user_images = []
            for filename in os.listdir(self.output_dir):
                if filename.startswith(f"zhou_game_{user_id}_") and filename.endswith('.png'):
                    file_path = os.path.join(self.output_dir, filename)
                    # 获取文件修改时间
                    mtime = os.path.getmtime(file_path)
                    user_images.append((mtime, file_path, filename))
            
            # 按修改时间排序，最新的在前
            user_images.sort(key=lambda x: x[0], reverse=True)
            
            # 删除超过限制数量的旧图片
            if len(user_images) > max_images:
                for _, file_path, filename in user_images[max_images:]:
                    try:
                        os.remove(file_path)
                        print(f"已删除旧游戏图片: {filename}")
                    except Exception as e:
                        print(f"删除图片失败 {filename}: {e}")
                        
        except Exception as e:
            print(f"清理旧图片时出错: {e}")
    
    async def generate_game_image(self, user_id, game_state):
        """生成游戏图片"""
        try:
            # 先清理旧图片
            self.cleanup_old_images(user_id)
            
            # 创建画布
            image = Image.new('RGB', self.BOARD_SIZE, (240, 248, 255))
            draw = ImageDraw.Draw(image)
            
            # 尝试加载字体
            try:
                # 尝试加载支持中文的字体
                font = ImageFont.truetype("msyh.ttc", 12)  # 微软雅黑
                big_font = ImageFont.truetype("msyh.ttc", 16)
                number_font = ImageFont.truetype("msyh.ttc", 10)
            except:
                try:
                    font = ImageFont.truetype("arial.ttf", 12)
                    big_font = ImageFont.truetype("arial.ttf", 16)
                    number_font = ImageFont.truetype("arial.ttf", 10)
                except:
                    font = ImageFont.load_default()
                    big_font = ImageFont.load_default()
                    number_font = ImageFont.load_default()
            
            # 定义物品等级对应的背景色
            level_colors = {
                'blue': (135, 206, 250),    # 蓝色物品
                'purple': (147, 112, 219),  # 紫色物品
                'gold': (255, 215, 0),      # 金色物品
                'red': (220, 20, 60),       # 红色物品
                'default': (200, 200, 200)  # 默认灰色
            }
            
            # 绘制标题 - 移到右上角避免被物品遮挡
            title_text = "洲了个洲"
            try:
                title_bbox = draw.textbbox((0, 0), title_text, font=big_font)
                title_width = title_bbox[2] - title_bbox[0]
            except:
                title_width = len(title_text) * 12  # 估算宽度
            draw.text((self.BOARD_SIZE[0] - title_width - 10, 10), title_text, fill=(0, 0, 0), font=big_font)
            
            # 绘制道具信息 - 移到右上角避免被物品遮挡
            props_text = f"撤回: {game_state['undo_count']} | 洗牌: {game_state['shuffle_count']} | 移出: {game_state['remove_count']} | 分数: {game_state['score']}"
            try:
                props_bbox = draw.textbbox((0, 0), props_text, font=font)
                props_width = props_bbox[2] - props_bbox[0]
            except:
                props_width = len(props_text) * 8  # 估算宽度
            draw.text((self.BOARD_SIZE[0] - props_width - 10, 35), props_text, fill=(0, 0, 0), font=font)
            
            # 绘制场上卡牌（按层级从低到高绘制）
            sorted_cards = sorted([c for c in game_state['cards'] if c.get('id') is not None], key=lambda c: c['layer'])
            
            for card in sorted_cards:
                x, y = card['x'], card['y']
                w, h = self.CARD_SIZE
                
                # 根据物品等级确定背景色
                item_type = card['type'].lower()
                if 'blue_' in item_type:
                    bg_color = level_colors['blue']
                elif 'purple_' in item_type:
                    bg_color = level_colors['purple']
                elif 'gold_' in item_type:
                    bg_color = level_colors['gold']
                elif 'red_' in item_type:
                    bg_color = level_colors['red']
                else:
                    bg_color = level_colors['default']
                
                # 如果不可点击，将颜色变暗
                if not card['clickable']:
                    bg_color = tuple(int(c * 0.5) for c in bg_color)
                
                # 创建圆角卡牌
                card_img = Image.new('RGBA', (w + self.CARD_THICKNESS, h + self.CARD_THICKNESS), (0, 0, 0, 0))
                card_draw = ImageDraw.Draw(card_img)
                
                # 绘制厚度效果（阴影）
                shadow_color = tuple(int(c * 0.3) for c in bg_color) + (180,)
                card_draw.rounded_rectangle(
                    [self.CARD_THICKNESS, self.CARD_THICKNESS, w + self.CARD_THICKNESS, h + self.CARD_THICKNESS],
                    radius=self.CARD_RADIUS, fill=shadow_color
                )
                
                # 绘制主卡牌
                card_draw.rounded_rectangle(
                    [0, 0, w, h],
                    radius=self.CARD_RADIUS, fill=bg_color + (255,)
                )
                
                # 粘贴到主图像
                image.paste(card_img, (x, y), card_img)
                
                # 绘制物品图片
                try:
                    if os.path.exists(card['image_path']):
                        item_image = Image.open(card['image_path'])
                        # 放大物品图片显示，减少边距
                        item_size = (w - 16, h - 16)  # 从24改为16，放大物品显示
                        item_image = item_image.resize(item_size, Image.Resampling.LANCZOS)
                        
                        # 居中粘贴物品图片
                        item_x = x + (w - item_size[0]) // 2
                        item_y = y + (h - item_size[1]) // 2
                        
                        # 如果卡牌不可点击，将物品图片变暗
                        if not card['clickable']:
                            # 创建半透明遮罩
                            overlay = Image.new('RGBA', item_size, (0, 0, 0, 120))
                            item_image = item_image.convert('RGBA')
                            item_image = Image.alpha_composite(item_image, overlay)
                        
                        image.paste(item_image, (item_x, item_y), item_image if item_image.mode == 'RGBA' else None)
                    else:
                        print(f"物品图片文件不存在: {card['image_path']}")
                        # 显示物品ID作为备用
                        id_text = f"#{card['id']}"
                        try:
                            text_bbox = draw.textbbox((0, 0), id_text, font=font)
                            text_w = text_bbox[2] - text_bbox[0]
                            text_h = text_bbox[3] - text_bbox[1]
                        except:
                            text_w, text_h = 20, 12
                        text_x = x + (w - text_w) // 2
                        text_y = y + (h - text_h) // 2
                        draw.text((text_x, text_y), id_text, fill=(0, 0, 0), font=font)
                except Exception as e:
                     print(f"加载物品图片时出错: {e}, 路径: {card.get('image_path', 'Unknown')}")
                     # 如果无法加载图片，显示物品ID
                     id_text = f"#{card['id']}"
                     try:
                         text_bbox = draw.textbbox((0, 0), id_text, font=font)
                         text_w = text_bbox[2] - text_bbox[0]
                         text_h = text_bbox[3] - text_bbox[1]
                     except:
                         text_w, text_h = 20, 12
                     text_x = x + (w - text_w) // 2
                     text_y = y + (h - text_h) // 2
                     draw.text((text_x, text_y), id_text, fill=(0, 0, 0), font=font)
                
                # 绘制左上角数字（简洁版本，无阴影无包边）
                number_text = str(card['id'])
                
                # 直接绘制深绿色数字
                number_x = x + 5
                number_y = y + 5
                draw.text((number_x, number_y), number_text, fill=(0, 120, 0), font=number_font)
            
            # 绘制卡槽区域背景 - 严格分离的区域
            slot_bg_y = 550
            slot_bg_height = 180
            draw.rectangle([0, slot_bg_y, self.BOARD_SIZE[0], slot_bg_y + slot_bg_height], 
                         fill=(240, 245, 250), outline=(180, 180, 180), width=3)
            
            # 绘制卡槽标题（使用动态卡槽大小）
            slot_title_y = 560
            slot_size = game_state.get('slot_size', 7)  # 兼容旧存档
            draw.text((30, slot_title_y), f"卡槽 ({len(game_state['slot'])}/{slot_size}):", fill=(0, 0, 0), font=font)
            
            # 绘制卡槽卡牌
            slot_start_y = 590
            for i, card in enumerate(game_state['slot']):
                x = 60 + i * 100
                y = slot_start_y
                w, h = self.CARD_SIZE
                
                # 根据物品等级确定背景色
                item_type = card['type'].lower()
                if 'blue_' in item_type:
                    bg_color = level_colors['blue']
                elif 'purple_' in item_type:
                    bg_color = level_colors['purple']
                elif 'gold_' in item_type:
                    bg_color = level_colors['gold']
                elif 'red_' in item_type:
                    bg_color = level_colors['red']
                else:
                    bg_color = level_colors['default']
                
                # 创建圆角卡牌（卡槽中的卡牌更亮一些）
                slot_card_img = Image.new('RGBA', (w + self.CARD_THICKNESS, h + self.CARD_THICKNESS), (0, 0, 0, 0))
                slot_card_draw = ImageDraw.Draw(slot_card_img)
                
                # 绘制厚度效果
                shadow_color = tuple(int(c * 0.4) for c in bg_color) + (200,)
                slot_card_draw.rounded_rectangle(
                    [self.CARD_THICKNESS, self.CARD_THICKNESS, w + self.CARD_THICKNESS, h + self.CARD_THICKNESS],
                    radius=self.CARD_RADIUS, fill=shadow_color
                )
                
                # 绘制主卡牌（卡槽中的卡牌有发光效果）
                bright_color = tuple(min(255, int(c * 1.2)) for c in bg_color) + (255,)
                slot_card_draw.rounded_rectangle(
                    [0, 0, w, h],
                    radius=self.CARD_RADIUS, fill=bright_color
                )
                
                # 粘贴到主图像
                image.paste(slot_card_img, (x, y), slot_card_img)
                
                # 绘制物品图片
                try:
                    if os.path.exists(card['image_path']):
                        item_image = Image.open(card['image_path'])
                        item_size = (w - 16, h - 16)  # 放大物品显示
                        item_image = item_image.resize(item_size, Image.Resampling.LANCZOS)
                        item_x = x + (w - item_size[0]) // 2
                        item_y = y + (h - item_size[1]) // 2
                        image.paste(item_image, (item_x, item_y), item_image if item_image.mode == 'RGBA' else None)
                    else:
                        print(f"卡槽物品图片文件不存在: {card['image_path']}")
                        # 显示物品ID作为备用
                        id_text = f"#{card['id']}"
                        try:
                            text_bbox = draw.textbbox((0, 0), id_text, font=font)
                            text_w = text_bbox[2] - text_bbox[0]
                            text_h = text_bbox[3] - text_bbox[1]
                        except:
                            text_w, text_h = 20, 12
                        text_x = x + (w - text_w) // 2
                        text_y = y + (h - text_h) // 2
                        draw.text((text_x, text_y), id_text, fill=(0, 0, 0), font=font)
                except Exception as e:
                     print(f"加载卡槽物品图片时出错: {e}, 路径: {card.get('image_path', 'Unknown')}")
                     # 备用显示
                     id_text = f"#{card['id']}"
                     try:
                         text_bbox = draw.textbbox((0, 0), id_text, font=font)
                         text_w = text_bbox[2] - text_bbox[0]
                         text_h = text_bbox[3] - text_bbox[1]
                     except:
                         text_w, text_h = 20, 12
                     text_x = x + (w - text_w) // 2
                     text_y = y + (h - text_h) // 2
                     draw.text((text_x, text_y), id_text, fill=(0, 0, 0), font=font)
            
            # 绘制游戏状态
            if game_state['status'] == 'won':
                draw.text((400, 15), "🏆 游戏获胜！", fill=(0, 200, 0), font=big_font)
            elif game_state['status'] == 'lost':
                draw.text((400, 15), "💀 游戏失败！", fill=(200, 0, 0), font=big_font)
            
            # 游戏说明已移除
            
            # 保存图片 - 使用游戏开始时间保持同一局游戏的文件名一致
            game_start_time = game_state.get('game_start_time', datetime.now().strftime("%Y%m%d_%H%M%S"))
            filename = f"zhou_game_{user_id}_{game_start_time}.png"
            image_path = os.path.join(self.output_dir, filename)
            
            # 确保输出目录存在
            os.makedirs(self.output_dir, exist_ok=True)
            
            image.save(image_path)
            print(f"游戏图片已保存到: {image_path}")
            
            return image_path
            
        except Exception as e:
            print(f"生成游戏图片时出错: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def update_stats(self, user_id, won, score):
        """更新游戏统计"""
        async with aiosqlite.connect(self.db_path) as db:
            # 获取当前统计
            cursor = await db.execute(
                "SELECT games_played, games_won, best_score, total_score FROM zhou_stats WHERE user_id = ?",
                (user_id,)
            )
            result = await cursor.fetchone()
            
            if result:
                games_played, games_won, best_score, total_score = result
                games_played += 1
                if won:
                    games_won += 1
                best_score = max(best_score, score)
                total_score += score
                
                await db.execute(
                    "UPDATE zhou_stats SET games_played = ?, games_won = ?, best_score = ?, total_score = ? WHERE user_id = ?",
                    (games_played, games_won, best_score, total_score, user_id)
                )
            else:
                await db.execute(
                    "INSERT INTO zhou_stats (user_id, games_played, games_won, best_score, total_score) VALUES (?, ?, ?, ?, ?)",
                    (user_id, 1, 1 if won else 0, score, score)
                )
            
            # 如果游戏获胜，检查是否有触发事件并发放奖励
            if won:
                # 需要重新获取游戏状态以获取is_triggered信息
                game_state = await self.load_game_state(user_id)
                if game_state:
                    await self._check_and_reward_trigger_event(user_id, db, game_state)
            
            await db.commit()
    
    async def _check_trigger_reward_message(self, user_id, game_state):
        """检查是否有触发事件奖励消息"""
        try:
            # 检查是否为偷吃触发的游戏
            is_triggered = game_state.get('is_triggered', False)
            
            if is_triggered:
                # 偷吃触发的游戏，检查触发事件表
                async with aiosqlite.connect(self.db_path) as db:
                    cursor = await db.execute(
                        "SELECT id FROM zhou_trigger_events WHERE user_id = ? AND reward_claimed = 0 ORDER BY trigger_time DESC LIMIT 1",
                        (user_id,)
                    )
                    trigger_event = await cursor.fetchone()
                    
                    if trigger_event:
                        return "\n💰 特殊奖励：获得100万哈夫币！"
            else:
                # 主动发送的游戏，直接给予50万奖励
                return "\n💰 游戏奖励：获得50万哈夫币！"
                
            return None
        except Exception as e:
            print(f"检查触发事件奖励消息时出错: {e}")
            return None
    
    async def _check_and_reward_trigger_event(self, user_id, db, game_state):
        """检查并发放触发事件奖励"""
        try:
            # 检查是否为偷吃触发的游戏
            is_triggered = game_state.get('is_triggered', False)
            reward_amount = 0
            
            if is_triggered:
                # 偷吃触发的游戏，检查是否有未领取的触发事件奖励
                cursor = await db.execute(
                    "SELECT id FROM zhou_trigger_events WHERE user_id = ? AND reward_claimed = 0 ORDER BY trigger_time DESC LIMIT 1",
                    (user_id,)
                )
                trigger_event = await cursor.fetchone()
                
                if trigger_event:
                    trigger_id = trigger_event[0]
                    
                    # 标记奖励已领取
                    await db.execute(
                        "UPDATE zhou_trigger_events SET reward_claimed = 1 WHERE id = ?",
                        (trigger_id,)
                    )
                    
                    reward_amount = 1000000  # 100万哈夫币
            else:
                # 主动发送的游戏，直接给予50万奖励
                reward_amount = 500000  # 50万哈夫币
            
            # 发放奖励
            if reward_amount > 0:
                # 首先检查用户是否在经济系统中存在
                cursor = await db.execute(
                    "SELECT warehouse_value FROM user_economy WHERE user_id = ?",
                    (user_id,)
                )
                economy_result = await cursor.fetchone()
                
                if economy_result:
                    # 用户存在，增加哈夫币
                    await db.execute(
                        "UPDATE user_economy SET warehouse_value = warehouse_value + ? WHERE user_id = ?",
                        (reward_amount, user_id)
                    )
                else:
                    # 用户不存在，创建新记录
                    await db.execute(
                        "INSERT INTO user_economy (user_id, warehouse_value, grid_size, teqin_level, menggong_active, menggong_end_time, auto_touchi_active, auto_touchi_start_time) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (user_id, reward_amount, 3, 0, 0, 0, 0, 0)
                    )
                
                reward_type = "偷吃触发" if is_triggered else "主动游戏"
                print(f"用户 {user_id} 洲了个洲游戏获胜（{reward_type}），已发放{reward_amount//10000}万哈夫币奖励")
                
        except Exception as e:
            print(f"检查和发放触发事件奖励时出错: {e}")
            import traceback
            traceback.print_exc()
    
    async def get_game_stats(self, user_id):
        """获取游戏统计"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT games_played, games_won, best_score, total_score FROM zhou_stats WHERE user_id = ?",
                (user_id,)
            )
            result = await cursor.fetchone()
            
            if result:
                games_played, games_won, best_score, total_score = result
                win_rate = (games_won / games_played * 100) if games_played > 0 else 0
                return {
                    'games_played': games_played,
                    'games_won': games_won,
                    'win_rate': win_rate,
                    'best_score': best_score,
                    'total_score': total_score
                }
            return None
    
    # ==================== 群组游戏方法 ====================
    
    async def start_group_game(self, group_id, starter_id):
        """开始群组游戏"""
        try:
            # 生成分层卡牌
            cards, difficulty = self.generate_layered_cards()
            
            # 初始化群组游戏状态
            game_start_time = datetime.now().strftime("%Y%m%d_%H%M%S")
            game_state = {
                'cards': cards,
                'slot': [],  # 卡槽
                'undo_count': self.DEFAULT_UNDO,
                'shuffle_count': self.DEFAULT_SHUFFLE,
                'remove_count': self.DEFAULT_REMOVE,
                'history': [],  # 操作历史
                'status': 'playing',  # playing, won, lost
                'score': 0,
                'last_player': starter_id,  # 最后操作的玩家
                'total_operations': 0,  # 总操作次数
                'game_start_time': game_start_time  # 游戏开始时间，用于保持图片文件名一致
            }
            
            # 保存群组游戏状态
            await self.save_group_game_state(group_id, game_state, [starter_id])
            
            # 生成游戏图片（使用个人游戏的图片生成方法）
            image_path = await self.generate_game_image(group_id, game_state)
            
            return True, image_path, f"🎮 群组洲了个洲游戏开始！\n👤 发起者: {starter_id}\n📝 群内任何人都可以使用 '拿 数字' 来选择卡牌\n🎯 集齐3张相同卡牌自动消除\n🏆 清空场上所有卡牌即可获胜！\n⚠️ 被遮挡的卡牌无法点击！"
            
        except Exception as e:
            print(f"开始群组游戏时出错: {e}")
            return False, None, "群组游戏初始化失败，请稍后重试"
    
    async def save_group_game_state(self, group_id, game_state, players):
        """保存群组游戏状态"""
        async with aiosqlite.connect(self.db_path) as db:
            game_data = json.dumps(game_state, ensure_ascii=False)
            players_data = json.dumps(players, ensure_ascii=False)
            
            await db.execute(
                "INSERT OR REPLACE INTO zhou_group_games (group_id, game_data, players, current_player, turn_order, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                (group_id, game_data, players_data, game_state.get('last_player', ''), '[]', datetime.now().isoformat())
            )
            await db.commit()
    
    async def load_group_game_state(self, group_id):
        """加载群组游戏状态"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT game_data, players FROM zhou_group_games WHERE group_id = ?",
                (group_id,)
            )
            result = await cursor.fetchone()
            
            if result:
                game_state = json.loads(result[0])
                players = json.loads(result[1])
                return game_state, players
            return None, None
    
    async def take_group_cards(self, group_id, user_id, card_numbers):
        """群组游戏拿取卡牌"""
        try:
            game_state, players = await self.load_group_game_state(group_id)
            if not game_state or game_state['status'] != 'playing':
                return False, None, "没有进行中的群组游戏，请先开始新游戏"
            
            # 添加玩家到游戏中（如果还不在列表中）
            if user_id not in players:
                players.append(user_id)
            
            # 获取可点击的卡牌
            clickable_cards = [card for card in game_state['cards'] if card['clickable']]
            valid_cards = []
            
            for num in card_numbers:
                card = next((c for c in clickable_cards if c['id'] == num), None)
                if card:
                    valid_cards.append(card)
                else:
                    return False, None, f"卡牌 {num} 不存在或被遮挡，无法点击！"
            
            if not valid_cards:
                return False, None, "没有有效的卡牌"
            
            # 检查卡槽空间
            slot_size = 7  # 群组游戏固定卡槽大小
            if len(game_state['slot']) + len(valid_cards) > slot_size:
                return False, None, f"卡槽空间不足！当前: {len(game_state['slot'])}/{slot_size}"
            
            # 保存操作历史
            game_state['history'].append({
                'action': 'take',
                'player': user_id,
                'cards': [card.copy() for card in valid_cards],
                'slot_before': game_state['slot'].copy(),
                'cards_before': game_state['cards'].copy()
            })
            
            # 将卡牌移到卡槽
            for card in valid_cards:
                game_state['slot'].append(card)
                game_state['cards'] = [c for c in game_state['cards'] if c['id'] != card['id']]
            
            # 更新可点击状态
            self.update_clickable_status(game_state['cards'])
            
            # 保存消除前的状态
            slot_before_elimination = game_state['slot'].copy()
            score_before_elimination = game_state['score']
            
            # 检查消除
            eliminated = self.check_elimination(game_state)
            
            # 如果有消除，更新历史记录
            if eliminated > 0:
                game_state['history'][-1]['eliminated'] = eliminated
                game_state['history'][-1]['slot_after_elimination'] = game_state['slot'].copy()
                game_state['history'][-1]['score_before_elimination'] = score_before_elimination
            
            # 更新游戏状态
            game_state['last_player'] = user_id
            game_state['total_operations'] += 1
            
            # 检查游戏状态
            if not game_state['cards']:
                game_state['status'] = 'won'
            elif len(game_state['slot']) >= slot_size:
                if not self.has_possible_elimination(game_state['slot']):
                    game_state['status'] = 'lost'
            
            # 保存群组游戏状态
            await self.save_group_game_state(group_id, game_state, players)
            
            # 生成游戏图片
            image_path = await self.generate_game_image(group_id, game_state)
            
            # 生成消息
            message = ""
            if game_state['status'] == 'won':
                message = f"🏆 恭喜获胜！所有卡牌已清空！\n👤 最后操作者: {user_id}"
            elif game_state['status'] == 'lost':
                message = f"💀 游戏失败！卡槽已满且无法消除！\n👤 最后操作者: {user_id}"
            else:
                # 拿取成功，不显示消除提示
                message = f"✅ {user_id} 成功拿取 {len(valid_cards)} 张卡牌！卡槽: {len(game_state['slot'])}/{slot_size}"
            
            return True, image_path, message
            
        except Exception as e:
            print(f"群组拿取卡牌时出错: {e}")
            return False, None, "操作失败，请稍后重试"
    
    async def use_group_undo(self, group_id, user_id):
        """群组游戏撤回"""
        try:
            game_state, players = await self.load_group_game_state(group_id)
            if not game_state or game_state['status'] != 'playing':
                return False, None, "没有进行中的群组游戏"
            
            if game_state['undo_count'] <= 0:
                return False, None, "撤回次数已用完！"
            
            if not game_state['history']:
                return False, None, "没有可撤回的操作！"
            
            # 撤回最后一次操作
            last_operation = game_state['history'].pop()
            
            # 恢复场上卡牌状态
            game_state['cards'] = last_operation['cards_before'].copy()
            
            # 恢复卡槽状态
            game_state['slot'] = last_operation['slot_before'].copy()
            
            # 如果有消除操作，恢复分数
            if 'score_before_elimination' in last_operation:
                game_state['score'] = last_operation['score_before_elimination']
            
            # 更新可点击状态
            self.update_clickable_status(game_state['cards'])
            
            # 减少撤回次数
            game_state['undo_count'] -= 1
            game_state['last_player'] = user_id
            
            # 保存游戏状态
            await self.save_group_game_state(group_id, game_state, players)
            
            # 生成游戏图片
            image_path = await self.generate_game_image(group_id, game_state)
            
            message = f"↩️ {user_id} 使用了撤回！剩余次数: {game_state['undo_count']}"
            return True, image_path, message
            
        except Exception as e:
            print(f"群组撤回时出错: {e}")
            return False, None, "撤回失败，请稍后重试"
    
    async def use_group_shuffle(self, group_id, user_id):
        """群组游戏洗牌"""
        try:
            game_state, players = await self.load_group_game_state(group_id)
            if not game_state or game_state['status'] != 'playing':
                return False, None, "没有进行中的群组游戏"
            
            if game_state['shuffle_count'] <= 0:
                return False, None, "洗牌次数已用完！"
            
            # 重新安排卡牌布局
            difficulty_config = self.DIFFICULTY_CONFIGS['medium']  # 群组游戏使用中等难度
            self.arrange_cards_in_layers(game_state['cards'], difficulty_config)
            
            # 减少洗牌次数
            game_state['shuffle_count'] -= 1
            game_state['last_player'] = user_id
            
            # 保存游戏状态
            await self.save_group_game_state(group_id, game_state, players)
            
            # 生成游戏图片
            image_path = await self.generate_game_image(group_id, game_state)
            
            message = f"🔀 {user_id} 使用了洗牌！剩余次数: {game_state['shuffle_count']}"
            return True, image_path, message
            
        except Exception as e:
            print(f"群组洗牌时出错: {e}")
            return False, None, "洗牌失败，请稍后重试"
    
    async def use_group_remove_slot(self, group_id, user_id):
        """群组游戏移出卡槽"""
        try:
            game_state, players = await self.load_group_game_state(group_id)
            if not game_state or game_state['status'] != 'playing':
                return False, None, "没有进行中的群组游戏"
            
            if game_state['remove_count'] <= 0:
                return False, None, "移出卡槽次数已用完！"
            
            if len(game_state['slot']) < 3:
                return False, None, "卡槽中卡牌不足3张，无法使用移出卡槽！"
            
            # 移出最后3张卡牌
            removed_cards = game_state['slot'][-3:]
            game_state['slot'] = game_state['slot'][:-3]
            
            # 减少移出次数
            game_state['remove_count'] -= 1
            game_state['last_player'] = user_id
            
            # 保存游戏状态
            await self.save_group_game_state(group_id, game_state, players)
            
            # 生成游戏图片
            image_path = await self.generate_game_image(group_id, game_state)
            
            message = f"🗑️ {user_id} 使用了移出卡槽！移出了3张卡牌，剩余次数: {game_state['remove_count']}"
            return True, image_path, message
            
        except Exception as e:
            print(f"群组移出卡槽时出错: {e}")
            return False, None, "移出卡槽失败，请稍后重试"
