import os
import random
from PIL import Image, ImageDraw
from datetime import datetime
import glob
import math
import os

script_dir = os.path.dirname(os.path.abspath(__file__))
items_dir = os.path.join(script_dir, "items")
xinwuzi_dir = os.path.join(script_dir, "xinwuzi")
expressions_dir = os.path.join(script_dir, "expressions")
output_dir = os.path.join(script_dir, "output")

os.makedirs(items_dir, exist_ok=True)
os.makedirs(xinwuzi_dir, exist_ok=True)
os.makedirs(expressions_dir, exist_ok=True)
os.makedirs(output_dir, exist_ok=True)

# Define border color
ITEM_BORDER_COLOR = (100, 100, 110)
BORDER_WIDTH = 1

def get_size(size_str):
    if 'x' in size_str:
        parts = size_str.split('x')
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            return int(parts[0]), int(parts[1])
    return 1, 1

# 手动设置的稀有物品概率映射 - 保持不变
RARE_ITEMS = {
    "gold_1x1_1", "gold_1x1_2", "red_1x1_1", "red_1x1_2", "red_1x1_3",  "red_3x3_ecmo",
    "red_3x3_huxiji", "gold_3x2_bendishoushi", "purple_1x1_2", "purple_1x1_4","purple_1x1_3", "purple_1x1_1","red_4x3_cipanzhenlie","red_4x3_dongdidianchi","red_3x4_daopian","red_3x3_wanjinleiguan","red_3x3_tanke"
}

# 超稀有物品列表 - 保持不变
ULTRA_RARE_ITEMS = {
    "red_1x1_xin","red_1x1_lei"
}

# 自动生成的物品价值映射表
ITEM_VALUES = {}
_items_cache_time = 0

def generate_item_values():
    """自动从文件夹读取物品图片生成价值映射"""
    global ITEM_VALUES, _items_cache_time
    import time
    
    current_time = time.time()
    # 缓存5分钟，避免频繁读取文件系统
    if ITEM_VALUES and (current_time - _items_cache_time) < 300:
        return ITEM_VALUES
    
    print("[Touchi] 开始自动生成物品价值映射...")
    generated_values = {}
    valid_extensions = ('.png', '.jpg', '.jpeg', '.gif', '.bmp')
    
    def scan_directory_for_items(directory):
        """扫描目录中的物品文件"""
        if not os.path.exists(directory):
            return {}
            
        local_values = {}
        
        # 扫描当前目录
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            
            if os.path.isdir(file_path):
                # 递归扫描子目录
                sub_values = scan_directory_for_items(file_path)
                local_values.update(sub_values)
            elif filename.lower().endswith(valid_extensions):
                # 处理图片文件
                try:
                    name_without_ext = os.path.splitext(filename)[0]
                    parts = name_without_ext.split('_')
                    
                    if len(parts) >= 3:
                        # 解析文件名格式：颜色_尺寸x尺寸_名称_价格 或 颜色_尺寸x尺寸_名称
                        level = parts[0].lower()
                        size = parts[1]
                        
                        # 构建基础名称（不包含价格）
                        if len(parts) >= 3 and parts[-1].isdigit():
                            # 统一格式：颜色_尺寸x尺寸_名称_价格 或 颜色_尺寸x尺寸_名称_价格
                            item_base_name = '_'.join(parts[:-1])
                            price = int(parts[-1])
                        else:
                            # 兼容旧格式（不应该再出现，但保留以防万一）
                            item_base_name = name_without_ext
                            # 根据稀有度设置默认价格
                            default_prices = {
                                "blue": 10000,
                                "purple": 50000,
                                "gold": 100000,
                                "red": 500000
                            }
                            price = default_prices.get(level, 10000)
                        
                        generated_values[item_base_name] = price
                        
                except (ValueError, IndexError) as e:
                    print(f"[Touchi] 跳过无效文件名: {filename}, 错误: {e}")
                    continue
        
        return local_values
    
    try:
        # 扫描items目录
        items_values = scan_directory_for_items(items_dir)
        generated_values.update(items_values)
        
        # 扫描xinwuzi目录（包括子目录）
        xinwuzi_values = scan_directory_for_items(xinwuzi_dir)
        generated_values.update(xinwuzi_values)
        
        # 更新全局映射和缓存时间
        ITEM_VALUES = generated_values
        _items_cache_time = current_time
        
        print(f"[Touchi] 自动生成完成，共{len(generated_values)}个物品映射")
        
    except Exception as e:
        print(f"[Touchi] 自动生成物品映射时出错: {e}")
        # 如果自动生成失败，保持原有映射不为空
        if not ITEM_VALUES:
            # 设置最小的默认映射以确保系统正常运行
            ITEM_VALUES = {
                "blue_1x1_default": 10000,
                "purple_1x1_default": 50000,
                "gold_1x1_default": 100000,
                "red_1x1_default": 500000
            }
    
    return ITEM_VALUES

# 在模块加载时自动生成映射
generate_item_values()

def get_item_value(item_name):
    """获取物品价值"""
    return ITEM_VALUES.get(item_name, 1000)

# 缓存物品列表以提高性能
_items_cache = None
_items_cache_time = 0
CACHE_DURATION = 300  # 5分钟缓存

def load_items():
    global _items_cache, _items_cache_time
    import time
    
    current_time = time.time()
    # 检查缓存是否有效
    if _items_cache is not None and (current_time - _items_cache_time) < CACHE_DURATION:
        return _items_cache
    
    items = []
    valid_extensions = ('.png', '.jpg', '.jpeg', '.gif', '.bmp')  # 使用元组提高性能
    
    def process_items_from_dir(directory):
        """处理指定目录中的物品文件"""
        if not os.path.exists(directory):
            return
            
        for filename in os.listdir(directory):
            if not filename.lower().endswith(valid_extensions):
                continue
                
            file_path = os.path.join(directory, filename)
            if not os.path.isfile(file_path):
                continue
                
            parts = os.path.splitext(filename)[0].split('_')
            
            # 判断是否为新物资格式（等级_大小_名称_价格）
            if len(parts) >= 4 and parts[-1].isdigit():
                # 新物资格式：等级_大小_名称_价格
                level = parts[0].lower()
                size = parts[1]
                # 物品名称为除了等级、大小和价格之外的部分
                name_parts = parts[2:-1]
                item_name = '_'.join(name_parts)
                # 构建基础名称（用于查找价值）
                item_base_name = f"{level}_{size}_{item_name}"
            else:
                # 原有格式：等级_大小_名称
                level = parts[0].lower() if len(parts) >= 2 else "purple"
                size = parts[1] if len(parts) >= 2 else "1x1"
                item_base_name = os.path.splitext(filename)[0]
            
            width, height = get_size(size)
            item_value = get_item_value(item_base_name)
            
            items.append({
                "path": file_path, "level": level, "size": size,
                "grid_width": width, "grid_height": height,
                "base_name": item_base_name, "value": item_value,
                "name": f"{item_base_name} (价值: {item_value:,})"
            })
    
    try:
        # 处理原有items文件夹
        process_items_from_dir(items_dir)
        
        # 处理新的xinwuzi文件夹
        process_items_from_dir(xinwuzi_dir)
        
    except Exception as e:
        print(f"Error loading items: {e}")
        return []
    
    # 更新缓存
    _items_cache = items
    _items_cache_time = current_time
    return items

def load_expressions():
    expressions = {}
    valid_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.bmp']
    for filename in os.listdir(expressions_dir):
        file_path = os.path.join(expressions_dir, filename)
        if os.path.isfile(file_path) and any(filename.lower().endswith(ext) for ext in valid_extensions):
            expressions[os.path.splitext(filename)[0]] = file_path
    return expressions

def place_items(items, grid_width, grid_height, total_grid_size=2):
    # 优化：使用一维数组代替二维数组提高性能
    grid = [0] * (grid_width * grid_height)
    placed = []
    
    # 修复大物品放置偏向问题：使用随机顺序而不是按尺寸排序
    # 这样可以给所有物品相等的放置机会，避免大物品优先占用空间
    sorted_items = items.copy()
    random.shuffle(sorted_items)
    
    for item in sorted_items:
        # Generate orientation options (consider rotation)
        orientations = [(item["grid_width"], item["grid_height"], False)]
        if item["grid_width"] != item["grid_height"]:
            orientations.append((item["grid_height"], item["grid_width"], True))
        
        placed_success = False
        
        # Try to place the item - 优化循环
        for y in range(grid_height):
            if placed_success:
                break
            for x in range(grid_width):
                if placed_success:
                    break
                for width, height, rotated in orientations:
                    # 新的边界检查：物品左上角必须在放置格子内，但物品整体必须在总格子内
                    # 左上角在放置格子内的检查（x, y必须在grid_width, grid_height范围内）
                    if x >= grid_width or y >= grid_height:
                        continue
                    
                    # 物品整体在总格子内的检查
                    if x + width > total_grid_size or y + height > total_grid_size:
                        continue
                        
                    # Check if space is available - 只检查在放置格子内的部分
                    can_place = True
                    for i in range(height):
                        if not can_place:
                            break
                        for j in range(width):
                            # 只检查在放置格子范围内的格子是否被占用
                            check_x = x + j
                            check_y = y + i
                            if check_x < grid_width and check_y < grid_height:
                                if grid[check_y * grid_width + check_x] != 0:
                                    can_place = False
                                    break
                    
                    if can_place:
                        # Mark space as occupied - 只标记在放置格子内的部分
                        for i in range(height):
                            for j in range(width):
                                mark_x = x + j
                                mark_y = y + i
                                if mark_x < grid_width and mark_y < grid_height:
                                    grid[mark_y * grid_width + mark_x] = 1
                        
                        placed.append({
                            "item": item, 
                            "x": x, 
                            "y": y, 
                            "width": width, 
                            "height": height, 
                            "rotated": rotated
                        })
                        placed_success = True
                        break
    
    return placed

def create_safe_layout(items, menggong_mode=False, grid_size=2, auto_mode=False, time_multiplier=1.0, 
                     custom_normal_rates=None, custom_menggong_rates=None):
    selected_items = []
    
    # 根据模式调整概率
    if auto_mode:
        # 自动模式：金红概率降低
        if menggong_mode:
            level_chances = {"purple": 0.55, "blue": 0.0, "gold": 0.15, "red": 0.033}
        else:
            level_chances = {"purple": 0.52, "blue": 0.35, "gold": 0.093, "red": 0.017}
    elif menggong_mode:
        # 猛攻模式：优先使用自定义概率，否则使用默认概率
        if custom_menggong_rates:
            level_chances = custom_menggong_rates.copy()
            # 猛攻模式应该没有蓝色物品
            level_chances["blue"] = 0.0
        else:
            level_chances = {"purple": 0.45, "blue": 0.0, "gold": 0.45, "red": 0.10}
    else:
        # 正常模式：优先使用自定义概率，否则使用默认概率
        if custom_normal_rates:
            level_chances = custom_normal_rates.copy()
        else:
            level_chances = {"purple": 0.42, "blue": 0.25, "gold": 0.28, "red": 0.05}
    
    # 根据时间倍率调整爆率
    # time_multiplier范围0.6-1.4，1.0为基准
    # 时间倍率越大（>1.0）略微提高red和gold爆率
    # 时间倍率越小（<1.0）下调red和gold爆率
    if not auto_mode:  # 只在非自动模式下应用时间倍率影响
        rate_adjustment = (time_multiplier - 1.0) * 0.05  # 调整幅度为±10%
        
        # 调整red和gold概率
        original_red = level_chances["red"]
        original_gold = level_chances["gold"]
        
        level_chances["red"] = max(0.01, original_red + original_red * rate_adjustment)
        level_chances["gold"] = max(0.05, original_gold + original_gold * rate_adjustment)
        
        # 为了保持总概率平衡，相应调整purple概率
        red_diff = level_chances["red"] - original_red
        gold_diff = level_chances["gold"] - original_gold
        level_chances["purple"] = max(0.1, level_chances["purple"] - red_diff - gold_diff)
    
    # Probabilistic item selection with rare item handling
    for item in items:
        base_chance = level_chances.get(item["level"], 0)
        item_name = item["base_name"]
        
        # 调整稀有物品概率
        if item_name in ULTRA_RARE_ITEMS:
            # 超稀有物品：红色物资的百分之一概率
            red_base_chance = level_chances.get("red", 0.05)
            final_chance = red_base_chance / 100
        elif item_name in RARE_ITEMS:
            # 稀有物品：原概率的三分之一
            final_chance = base_chance / 3
        else:
            final_chance = base_chance
            
        if random.random() <= final_chance:
            selected_items.append(item)
    
    # Limit number of items
    num_items = random.randint(2, 6)
    if len(selected_items) > num_items:
        selected_items = random.sample(selected_items, num_items)
    elif len(selected_items) < num_items:
        # Supplement with purple items (excluding rare ones)
        purple_items = [item for item in items if item["level"] == "purple" and item["base_name"] not in RARE_ITEMS]
        if purple_items:
            needed = min(num_items - len(selected_items), len(purple_items))
            selected_items.extend(random.sample(purple_items, needed))
    
    random.shuffle(selected_items)
    
    # Region selection (with weights) - 根据特勤处等级调整
    base_options = [(2, 1), (3, 1), (4, 1), (4, 2), (4, 3), (4, 4)]
    
    # 根据grid_size扩展region_options
    if grid_size == 3:  # 特勤处1级
        region_options = [(w+1, h+1) for w, h in base_options] + base_options
    elif grid_size == 4:  # 特勤处2级
        region_options = [(w+2, h+2) for w, h in base_options] + [(w+1, h+1) for w, h in base_options] + base_options
    elif grid_size == 5:  # 特勤处3级
        region_options = [(w+3, h+3) for w, h in base_options] + [(w+2, h+2) for w, h in base_options] + [(w+1, h+1) for w, h in base_options] + base_options
    elif grid_size == 6:  # 特勤处4级
        region_options = [(w+4, h+4) for w, h in base_options] + [(w+3, h+3) for w, h in base_options] + [(w+2, h+2) for w, h in base_options] + [(w+1, h+1) for w, h in base_options] + base_options
    elif grid_size == 7:  # 特勤处5级
        region_options = [(w+5, h+5) for w, h in base_options] + [(w+4, h+4) for w, h in base_options] + [(w+3, h+3) for w, h in base_options] + [(w+2, h+2) for w, h in base_options] + [(w+1, h+1) for w, h in base_options] + base_options
    else:
        region_options = base_options
    
    # 确保region不超过grid_size
    region_options = [(w, h) for w, h in region_options if w <= grid_size and h <= grid_size]
    
    weights = [1] * len(region_options)
    region_width, region_height = random.choices(region_options, weights=weights, k=1)[0]
    
    # Fixed placement in top-left corner
    placed_items = place_items(selected_items, region_width, region_height, grid_size)
    return placed_items, 0, 0, region_width, region_height

def render_safe_layout_gif(placed_items, start_x, start_y, region_width, region_height,
                           grid_size=2, cell_size=100):
    """
    返回:
        frames: List[PIL.Image]  # 每一帧
        total_frames: int        # 总帧数（== len(frames)）
    """
    img_size = grid_size * cell_size
    frames = []
    
    # 动画参数
    frames_per_item = 8  # 每个物品显示时的帧数
    rotation_frames = 6  # 转圈动画帧数
    
    # 根据物品级别设置转圈时长（与下面的函数保持一致）
    def get_rotation_duration(item_level):
        duration_map = {
            "blue": 4,    # 蓝色最短
            "purple": 6,  # 紫色稍长
            "gold": 10,    # 金色更长
            "red": 25     # 红色最长
        }
        return duration_map.get(item_level, 6)
    
    # 计算总动画时长
    if len(placed_items) > 0:
        # 计算所有物品的总搜索时长
        total_search_time = 0
        for i in range(len(placed_items)):
            item_rotation_duration = get_rotation_duration(placed_items[i]["item"]["level"])
            total_search_time += item_rotation_duration
        
        # 总动画时长 = 总搜索时长 + 15帧
        total_frames = total_search_time + 15
    else:
        total_frames = 5 # 如果没有物品，默认30帧
    
    # Define item background colors (with transparency)
    background_colors = {
        "purple": (50, 43, 97, 90), 
        "blue": (49, 91, 126, 90), 
        "gold": (153, 116, 22, 90), 
        "red": (139, 35, 35, 90)
    }
    
    # 预加载所有物品图片
    item_images = {}
    for i, placed in enumerate(placed_items):
        item = placed["item"]
        try:
            with Image.open(item["path"]).convert("RGBA") as item_img:
                if placed["rotated"]:
                    item_img = item_img.rotate(90, expand=True)
                
                inner_width = placed["width"] * cell_size
                inner_height = placed["height"] * cell_size
                item_img.thumbnail((inner_width, inner_height), Image.LANCZOS)
                item_images[i] = item_img.copy()
        except Exception as e:
            print(f"Error loading item image: {item['path']}, error: {e}")
            item_images[i] = None
    
    # 根据物品级别设置转圈时长
    def get_rotation_duration(item_level):
        duration_map = {
            "blue": 4,    # 蓝色最短
            "purple": 6,  # 紫色稍长
            "gold": 10,    # 金色更长
            "red": 25     # 红色最长
        }
        return duration_map.get(item_level, 6)
    
    for frame_idx in range(total_frames):
        # 创建基础图像
        safe_img = Image.new("RGB", (img_size, img_size), (50, 50, 50))
        draw = ImageDraw.Draw(safe_img)
        
        # 绘制网格线
        for i in range(1, grid_size):
            draw.line([(i * cell_size, 0), (i * cell_size, img_size)], fill=(80, 80, 80), width=1)
            draw.line([(0, i * cell_size), (img_size, i * cell_size)], fill=(80, 80, 80), width=1)
        
        # 创建透明层
        overlay = Image.new("RGBA", safe_img.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        
        # 计算当前应该显示的物品数量
        # 物品在其转圈动画开始时才被认为是"显示"的
        current_item_count = 0
        total_rotation_time = 0
        for i in range(len(placed_items)):
            # 转圈开始帧直接等于累积转圈时间
            rotation_start_frame = total_rotation_time
            if frame_idx >= rotation_start_frame:
                current_item_count = i + 1
            else:
                break
            # 累加当前物品的转圈时长，实现紧密连接
            item = placed_items[i]["item"]
            item_rotation_duration = get_rotation_duration(item["level"])
            total_rotation_time += item_rotation_duration
        
        # 绘制未显示物品的黑色阴影线遮罩
        for i in range(current_item_count, len(placed_items)):
            placed = placed_items[i]
            x0, y0 = placed["x"] * cell_size, placed["y"] * cell_size
            x1, y1 = x0 + placed["width"] * cell_size, y0 + placed["height"] * cell_size
            
            # 绘制黑色半透明遮罩（调淡）
            overlay_draw.rectangle([x0, y0, x1, y1], fill=(0, 0, 0, 80))
            
            # 绘制网格状阴影线纹理（调淡）
            for y in range(int(y0), int(y1), 6):
                overlay_draw.line([(int(x0), y), (int(x1), y)], fill=(0, 0, 0, 80), width=1)
            for x in range(int(x0), int(x1), 6):
                overlay_draw.line([(x, int(y0)), (x, int(y1))], fill=(0, 0, 0, 80), width=1)
            
            # 在遮罩上方叠加向左倾斜45度的平行灰色斜线
            line_spacing = 15  # 斜线间距（统一为15）
            line_color = (128, 128, 128, 150)  # 灰色
            line_width = 2  # 斜线粗细（增加）
            border_color = (80, 80, 80, 180)   # 更深的边框颜色
            border_width = 1   # 边框宽度
            
            # 绘制矩形边框
            overlay_draw.rectangle([int(x0), int(y0), int(x1), int(y1)], outline=border_color, width=border_width)
            
            # 计算需要绘制的斜线范围
            width = int(x1 - x0)
            height = int(y1 - y0)
            diagonal_length = int(math.sqrt(width**2 + height**2))
            
            # 绘制向左倾斜45度的平行斜线
            # 使用更大的范围确保完全覆盖
            for line_idx in range(-width - height, width + height, line_spacing):
                # 计算斜线穿过矩形的所有可能交点
                # 斜线方程: y - y0 = -1 * (x - (x0 + line_idx))
                # 即: y = -x + (x0 + line_idx + y0)
                
                # 计算与四条边的交点
                intersections = []
                
                # 与左边界 x = x0 的交点
                y_left = -(int(x0)) + (int(x0) + line_idx + int(y0))
                if int(y0) <= y_left <= int(y1):
                    intersections.append((int(x0), int(y_left)))
                
                # 与右边界 x = x1 的交点
                y_right = -(int(x1)) + (int(x0) + line_idx + int(y0))
                if int(y0) <= y_right <= int(y1):
                    intersections.append((int(x1), int(y_right)))
                
                # 与上边界 y = y0 的交点
                x_top = (int(x0) + line_idx + int(y0)) - int(y0)
                if int(x0) <= x_top <= int(x1):
                    intersections.append((int(x_top), int(y0)))
                
                # 与下边界 y = y1 的交点
                x_bottom = (int(x0) + line_idx + int(y0)) - int(y1)
                if int(x0) <= x_bottom <= int(x1):
                    intersections.append((int(x_bottom), int(y1)))
                
                # 如果有两个交点，绘制线段
                if len(intersections) >= 2:
                    # 取前两个交点
                    start_point = intersections[0]
                    end_point = intersections[1]
                    overlay_draw.line([start_point, end_point], fill=line_color, width=line_width)
        
        # 绘制已显示物品
        for i in range(current_item_count):
            placed = placed_items[i]
            item = placed["item"]
            x0, y0 = placed["x"] * cell_size, placed["y"] * cell_size
            x1, y1 = x0 + placed["width"] * cell_size, y0 + placed["height"] * cell_size
            
            # 获取物品背景色
            bg_color = background_colors.get(item["level"], (128, 128, 128, 200))
            
            # 为每个物品添加转圈动画效果，根据级别调整时长
            item_rotation_duration = get_rotation_duration(item["level"])
            
            # 判断是否在转圈动画期间
            # 优化时序：去掉物品显示帧间隔，让转圈动画紧密连接
            # 计算全局转圈时序：每个物品的转圈开始时间 = 前面所有物品的累积转圈时间
            entrance_duration = 2  # 进场动画时长
            total_previous_rotation_time = 0
            for j in range(i):
                if j < len(placed_items):
                    prev_item = placed_items[j]["item"]
                    prev_rotation_duration = get_rotation_duration(prev_item["level"])
                    # 累积前面所有物品的转圈时间，实现紧密连接
                    total_previous_rotation_time += prev_rotation_duration
            
            # 当前物品的转圈开始时间（直接等于累积转圈时间）
            rotation_start_frame = total_previous_rotation_time
            rotation_end_frame = rotation_start_frame + item_rotation_duration
            
            is_rotating = (frame_idx >= rotation_start_frame and 
                          frame_idx < rotation_end_frame and
                          i < current_item_count)
            
            if is_rotating:
                # 转圈动画期间，先绘制阴影遮罩，再绘制转圈效果
                # 绘制黑色半透明遮罩（调淡）
                overlay_draw.rectangle([x0, y0, x1, y1], fill=(0, 0, 0, 80))
                
                # 绘制网格状阴影线纹理（调淡）
                for y in range(int(y0), int(y1), 6):
                    overlay_draw.line([(int(x0), y), (int(x1), y)], fill=(0, 0, 0, 80), width=1)
                for x in range(int(x0), int(x1), 6):
                    overlay_draw.line([(x, int(y0)), (x, int(y1))], fill=(0, 0, 0, 80), width=1)
                
                # 在遮罩上方叠加向左倾斜45度的平行灰色斜线
                line_spacing = 15  # 斜线间距（统一为15）
                line_color = (128, 128, 128, 150)  # 灰色
                line_width = 2  # 斜线粗细（增加）
                border_color = (80, 80, 80, 180)   # 更深的边框颜色
                border_width = 1   # 边框宽度
                
                # 绘制矩形边框
                overlay_draw.rectangle([int(x0), int(y0), int(x1), int(y1)], outline=border_color, width=border_width)
                
                # 计算需要绘制的斜线范围
                width = int(x1 - x0)
                height = int(y1 - y0)
                diagonal_length = int(math.sqrt(width**2 + height**2))
                
                # 绘制向左倾斜45度的平行斜线
                # 使用更大的范围确保完全覆盖
                for line_offset in range(-width - height, width + height, line_spacing):
                    # 计算斜线穿过矩形的所有可能交点
                    # 斜线方程: y - y0 = -1 * (x - (x0 + line_offset))
                    # 即: y = -x + (x0 + line_offset + y0)
                    
                    # 计算与四条边的交点
                    intersections = []
                    
                    # 与左边界 x = x0 的交点
                    y_left = -(int(x0)) + (int(x0) + line_offset + int(y0))
                    if int(y0) <= y_left <= int(y1):
                        intersections.append((int(x0), int(y_left)))
                    
                    # 与右边界 x = x1 的交点
                    y_right = -(int(x1)) + (int(x0) + line_offset + int(y0))
                    if int(y0) <= y_right <= int(y1):
                        intersections.append((int(x1), int(y_right)))
                    
                    # 与上边界 y = y0 的交点
                    x_top = (int(x0) + line_offset + int(y0)) - int(y0)
                    if int(x0) <= x_top <= int(x1):
                        intersections.append((int(x_top), int(y0)))
                    
                    # 与下边界 y = y1 的交点
                    x_bottom = (int(x0) + line_offset + int(y0)) - int(y1)
                    if int(x0) <= x_bottom <= int(x1):
                        intersections.append((int(x_bottom), int(y1)))
                    
                    # 如果有两个交点，绘制线段
                    if len(intersections) >= 2:
                        # 取前两个交点
                        start_point = intersections[0]
                        end_point = intersections[1]
                        overlay_draw.line([start_point, end_point], fill=line_color, width=line_width)
                
                # 计算转圈动画参数
                rotation_frame = (frame_idx - rotation_start_frame) % item_rotation_duration
                # 根据转圈时长调整角速度，确保sousuo.png移动速度一致
                # 使用基准时长20帧来标准化角速度，并增加速度倍数
                base_duration = 20
                speed_multiplier = item_rotation_duration / base_duration
                speed_boost = 3.0  # 增加速度倍数，让转圈更快
                rotation_angle = (rotation_frame * 360 * speed_multiplier * speed_boost // item_rotation_duration) % 360
                
                # 创建带旋转效果的背景
                center_x = (x0 + x1) // 2
                center_y = (y0 + y1) // 2
                
                # 计算转圈动画的参数，使用固定半径确保大小格物品轨迹一致
                radius = cell_size // 14  # 缩小圆圈半径，让转圈轨迹更小
                
                # 使用 sousuo.png 图片代替弧线进行转圈动画
                sousuo_path = os.path.join(expressions_dir, "sousuo.png")
                if os.path.exists(sousuo_path):
                    try:
                        with Image.open(sousuo_path).convert("RGBA") as sousuo_img:
                            # 调整 sousuo.png 的大小，增大图标尺寸
                            sousuo_size = 60 # 增大图标大小，从50增加到65
                            sousuo_img = sousuo_img.resize((sousuo_size, sousuo_size), Image.LANCZOS)
                            
                            # 计算图片中心点的转圈轨迹位置
                            angle_rad = math.radians(rotation_angle)
                            orbit_x = center_x + radius * math.cos(angle_rad)
                            orbit_y = center_y + radius * math.sin(angle_rad)
                            
                            # 计算图片左上角位置，让60px sousuo.png的中心偏左上一点作为轨迹圆上的一点
                            # 偏移量：向左上偏移图标大小的1/6
                            offset_x = sousuo_size // 6  # 向左偏移
                            offset_y = sousuo_size // 6  # 向上偏移
                            paste_x = int(orbit_x - sousuo_size // 2 + offset_x)
                            paste_y = int(orbit_y - sousuo_size // 2 + offset_y)
                            
                            # 粘贴图片（保持图片方向不变）
                            overlay.paste(sousuo_img, (paste_x, paste_y), sousuo_img)
                    except Exception as e:
                        # 如果加载图片失败，回退到原来的弧线绘制
                        arc_length = 150
                        start_angle = rotation_angle
                        end_angle = rotation_angle + arc_length
                        bbox = [center_x - radius, center_y - radius, 
                               center_x + radius, center_y + radius]
                        overlay_draw.arc(bbox, start_angle, end_angle, 
                                        fill=(255, 255, 255, 220), width=3)
                else:
                    # 如果 sousuo.png 不存在，回退到原来的弧线绘制
                    arc_length = 150
                    start_angle = rotation_angle
                    end_angle = rotation_angle + arc_length
                    bbox = [center_x - radius, center_y - radius, 
                           center_x + radius, center_y + radius]
                    overlay_draw.arc(bbox, start_angle, end_angle, 
                                    fill=(255, 255, 255, 220), width=3)
            else:
                # 转圈动画结束后，显示物品背景色和图片，添加从大变小的进场效果
                
                # 计算进场动画参数
                entrance_duration = 2  # 进场动画时长 
                # 进场动画在转圈动画结束后开始，使用新的转圈时序
                entrance_start_frame = rotation_end_frame
                entrance_frame = frame_idx - entrance_start_frame
                
                # 判断是否在进场动画期间
                # 每个物品在转圈结束后都应该有进场动画
                # entrance_frame >= 0 已经确保了转圈动画结束，无需重复判断
                is_entrance_animation = (entrance_frame >= 0 and entrance_frame < entrance_duration)  # 转圈结束后立即播放进场动画
                
                if is_entrance_animation:
                    # 进场动画
                    # 使用线性缩放效果，不使用缓动
                    progress = entrance_frame / entrance_duration
                    # 线性进度，匀速缩放
                    scale_factor = 1.5 - 0.5 * progress  # 从1.5缩放到1.0
                else:
                    # 进场动画结束，显示正常大小
                    scale_factor = 1.0
                
                # 绘制色块动画效果（位于背景色上方、物品下方）
                # 色块只在进场动画期间显示，进场动画结束后不再绘制
                if is_entrance_animation:
                    # 色块动画：从浅到深、从格子大小到1.2倍
                    progress = entrance_frame / entrance_duration
                    
                    # 计算色块颜色：从背景色基础上由浅变深
                    base_r, base_g, base_b, base_a = bg_color
                    # 浅色：增加亮度（向255靠近）
                    light_factor = 0.3  # 浅色程度，调整得不那么浅
                    light_r = int(base_r + (255 - base_r) * light_factor)
                    light_g = int(base_g + (255 - base_g) * light_factor)
                    light_b = int(base_b + (255 - base_b) * light_factor)
                    
                    # 深色：降低亮度（向0靠近）
                    dark_factor = 0.1  # 深色程度，调整得更深
                    dark_r = int(base_r * dark_factor)
                    dark_g = int(base_g * dark_factor)
                    dark_b = int(base_b * dark_factor)
                    
                    # 根据进度插值颜色（从浅到深）
                    current_r = int(light_r + (dark_r - light_r) * progress)
                    current_g = int(light_g + (dark_g - light_g) * progress)
                    current_b = int(light_b + (dark_b - light_b) * progress)
                    current_a = int(base_a + (255 - base_a) * progress * 0.5)  # 透明度也逐渐增加
                    
                    # 计算色块大小：从格子大小到1.2倍
                    start_scale = 1.0
                    end_scale = 1.3
                    current_scale = start_scale + (end_scale - start_scale) * progress
                    
                    # 计算色块位置和大小
                    block_width = int((placed["width"] * cell_size) * current_scale)
                    block_height = int((placed["height"] * cell_size) * current_scale)
                    
                    # 居中放置色块
                    block_x = x0 + (placed["width"] * cell_size - block_width) // 2
                    block_y = y0 + (placed["height"] * cell_size - block_height) // 2
                    
                    # 绘制色块
                    overlay_draw.rectangle([block_x, block_y, block_x + block_width, block_y + block_height], 
                                         fill=(current_r, current_g, current_b, current_a))
                
                # 绘制物品背景（只在进场动画结束后显示）
                if not is_entrance_animation:
                    overlay_draw.rectangle([x0, y0, x1, y1], fill=bg_color)
                
                # 绘制物品图片（应用缩放效果）
                if i in item_images and item_images[i] is not None:
                    item_img = item_images[i]
                    
                    if scale_factor != 1.0:
                        # 应用缩放效果
                        scaled_width = int(item_img.width * scale_factor)
                        scaled_height = int(item_img.height * scale_factor)
                        scaled_img = item_img.resize((scaled_width, scaled_height), Image.LANCZOS)
                        
                        # 计算缩放后的居中位置
                        paste_x = x0 + (placed["width"] * cell_size - scaled_width) // 2
                        paste_y = y0 + (placed["height"] * cell_size - scaled_height) // 2
                        overlay.paste(scaled_img, (int(paste_x), int(paste_y)), scaled_img)
                    else:
                        # 正常大小显示
                        paste_x = x0 + (placed["width"] * cell_size - item_img.width) // 2
                        paste_y = y0 + (placed["height"] * cell_size - item_img.height) // 2
                        overlay.paste(item_img, (int(paste_x), int(paste_y)), item_img)
                
                # 绘制物品边框
                draw.rectangle([x0, y0, x1, y1], outline=ITEM_BORDER_COLOR, width=BORDER_WIDTH)
        
        # 合并图层
        frame_img = Image.alpha_composite(safe_img.convert("RGBA"), overlay).convert("RGB")
        frames.append(frame_img)
    
    return frames, len(frames)

def get_highest_level(placed_items):
    if not placed_items: return "purple"
    levels = {"purple": 2, "blue": 1, "gold": 3, "red": 4}
    return max((p["item"]["level"] for p in placed_items), key=lambda level: levels.get(level, 0), default="purple")

def cleanup_old_images(keep_recent=2):
    try:
        image_files = glob.glob(os.path.join(output_dir, "*.png"))
        image_files.sort(key=os.path.getmtime, reverse=True)
        for old_file in image_files[keep_recent:]:
            os.remove(old_file)
    except Exception as e:
        print(f"Error cleaning up old images: {e}")

def cleanup_old_gifs(keep_recent=2):
    try:
        gif_files = glob.glob(os.path.join(output_dir, "*.gif"))
        gif_files.sort(key=os.path.getmtime, reverse=True)
        for old_file in gif_files[keep_recent:]:
            os.remove(old_file)
    except Exception as e:
        print(f"Error cleaning up old GIFs: {e}")

def generate_safe_image(menggong_mode=False, grid_size=2, time_multiplier=1.0,
                        gif_scale=0.7, optimize_size=False, enable_static_image=False,
                        custom_normal_rates=None, custom_menggong_rates=None):
    """
    Generate a safe GIF animation and return the image path and list of placed items.

    Args:
        menggong_mode (bool): Whether to use menggong mode
        grid_size (int): Size of the grid
        time_multiplier (float): Time multiplier for animation
        gif_scale (float): Scale factor for the final GIF size (1.0 = original size, 0.5 = half size, 2.0 = double size)
        optimize_size (bool): Whether to optimize GIF file size (reduces colors and enables compression, may affect quality)
        enable_static_image (bool): Whether to generate static image (only last frame) instead of GIF animation
        custom_normal_rates (dict): Custom drop rates for normal mode (optional)
        custom_menggong_rates (dict): Custom drop rates for menggong mode (optional)

    Returns:
        tuple: (output_path, placed_items)
    """
    items = load_items()
    expressions = load_expressions()

    if not items or not expressions:
        print("Error: Missing image resources in items or expressions folders.")
        return None, []

    placed_items, start_x, start_y, region_width, region_height = create_safe_layout(
        items, menggong_mode, grid_size, auto_mode=False, time_multiplier=time_multiplier,
        custom_normal_rates=custom_normal_rates, custom_menggong_rates=custom_menggong_rates
    )

    # ============ ① 一体化写法：直接拿帧序列 + 总帧数 ============
    safe_frames, total_frames = render_safe_layout_gif(
        placed_items, start_x, start_y, region_width, region_height, grid_size
    )

    highest_level = get_highest_level(placed_items)
    total_value = sum(placed["item"]["value"] for placed in placed_items)
    has_gold_items = any(placed["item"]["level"] == "gold" for placed in placed_items)

    # 静态图终点：最后一帧（留 5 帧缓冲可自己调）
    static_frame_index = max(0, total_frames - 1 - 5) if total_frames > 5 else max(0, total_frames - 1)

    # 表情选择逻辑
    expression_map = {"gold": "happy", "red": "eat"}
    if highest_level == "red":
        final_expression = "eat"
    elif highest_level == "gold":
        final_expression = "happy"
    elif total_value > 300000 and not has_gold_items:
        final_expression = "happy"
    else:
        final_expression = "cry"

    eating_path = expressions.get("eating")
    final_expr_path = expressions.get(final_expression)
    if not eating_path or not final_expr_path:
        return None, []

    try:
        expression_size = grid_size * 100          # 与格子对齐
        # 预加载 eating.gif 所有帧
        eating_frames = []
        with Image.open(eating_path) as eating_gif:
            for idx in range(eating_gif.n_frames):
                eating_gif.seek(idx)
                frame = eating_gif.convert("RGBA").resize((expression_size, expression_size), Image.LANCZOS)
                eating_frames.append(frame.copy())

        # 加载最终表情
        with Image.open(final_expr_path).convert("RGBA") as final_expr_img:
            final_expr_img = final_expr_img.resize((expression_size, expression_size), Image.LANCZOS)

            # 合成每一帧
            final_frames = []
            for idx, safe_frame in enumerate(safe_frames):
                canvas = Image.new("RGB", (expression_size + safe_frame.width, safe_frame.height), (50, 50, 50))
                # 第一帧放最终表情，其余放 eating 循环
                expr = final_expr_img if idx == 0 else eating_frames[(idx - 1) % len(eating_frames)]
                if expr.mode == 'RGBA':
                    canvas.paste(expr, (0, 0), expr)
                else:
                    canvas.paste(expr, (0, 0))
                canvas.paste(safe_frame, (expression_size, 0))

                if gif_scale != 1.0:
                    new_size = (int(canvas.width * gif_scale), int(canvas.height * gif_scale))
                    canvas = canvas.resize(new_size, Image.LANCZOS)
                if optimize_size:
                    canvas = canvas.convert('P', palette=Image.ADAPTIVE, colors=128)
                final_frames.append(canvas)

    except Exception as e:
        print(f"Error creating final GIF: {e}")
        return None, []

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # ================= ② 静态 PNG 分支 =================
    if enable_static_image:
        output_path = os.path.join(output_dir, f"safe_{timestamp}.png")
        safe_frame = safe_frames[static_frame_index]          # 用计算好的终点帧
        static_img = Image.new("RGB", (expression_size + safe_frame.width, safe_frame.height), (50, 50, 50))
        if final_expr_img.mode == 'RGBA':
            static_img.paste(final_expr_img, (0, 0), final_expr_img)
        else:
            static_img.paste(final_expr_img, (0, 0))
        static_img.paste(safe_frame, (expression_size, 0))

        if gif_scale != 1.0:
            new_size = (int(static_img.width * gif_scale), int(static_img.height * gif_scale))
            static_img = static_img.resize(new_size, Image.LANCZOS)
        static_img.save(output_path, 'PNG')
        cleanup_old_images()          # 清理旧 PNG
        return output_path, placed_items

    # ================= ③ GIF 分支
    else:
        # GIF动画模式
        output_path = os.path.join(output_dir, f"safe_{timestamp}.gif")
        
        # 保存GIF动画
        if final_frames:
            # 根据optimize_size参数设置保存选项
            save_kwargs = {
                'save_all': True,
                'append_images': final_frames[1:],
                'duration': 150,  # 每帧150毫秒
                'loop': 0  # 无限循环
            }
            
            if optimize_size:
                # 启用优化选项以减少文件大小
                save_kwargs.update({
                    'optimize': True,  # 启用优化
                    'disposal': 2,     # 恢复到背景色
                    'transparency': 0  # 设置透明色索引
                })
            
            final_frames[0].save(output_path, **save_kwargs)
        
        cleanup_old_gifs()  # 清理旧的GIF文件
    
    return output_path, placed_items
