from PIL import Image, ImageChops, ImageFilter
import io

def process_3d_emote(cell_img):
    """
    製作純白邊框貼紙風 (White Outline Sticker Style) 表情包：
    1. 自動切除多餘白底
    2. 生成圓潤厚實的純白外框 (White Outline)
    3. 加上柔和懸浮陰影，凸顯貼紙立體感
    """
    if cell_img.mode != 'RGBA':
        cell_img = cell_img.convert('RGBA')

    # 1. 自動去除原圖白色背景（去殘影，只保留人物與文字）
    bg = Image.new('RGBA', cell_img.size, (255, 255, 255, 255))
    diff = ImageChops.difference(cell_img, bg)
    bbox = diff.getbbox()
    cropped = cell_img.crop(bbox) if bbox else cell_img

    c_w, c_h = cropped.size
    alpha = cropped.split()[3]

    # 2. 畫布留白設定 (留足空間給白邊與陰影)
    outline_thickness = 7  # 白邊粗細 (可自行調整：5~10)
    pad = outline_thickness + 15
    
    canvas_w = c_w + pad * 2
    canvas_h = c_h + pad * 2

    # 3. 製作白邊遮罩 (使用圓形矩陣擴散，效果最圓潤)
    white_mask = Image.new('L', (c_w, c_h), 0)
    white_fill = Image.new('RGBA', (c_w, c_h), (255, 255, 255, 255))
    
    outline_layer = Image.new('RGBA', (canvas_w, canvas_h), (0, 0, 0, 0))

    # 多角度疊加生成 360 度無死角圓潤白邊
    r = outline_thickness
    for dx in range(-r, r + 1):
        for dy in range(-r, r + 1):
            if dx*dx + dy*dy <= r*r:  # 圓形距離判定
                outline_layer.paste(white_fill, (pad + dx, pad + dy), alpha)

    # 4. 製作貼紙懸浮陰影 (Drop Shadow)
    shadow_layer = Image.new('RGBA', (canvas_w, canvas_h), (0, 0, 0, 0))
    shadow_fill = Image.new('RGBA', (canvas_w, canvas_h), (0, 0, 0, 70))
    
    # 提取完整白邊貼紙的輪廓來做陰影
    sticker_alpha = outline_layer.split()[3]
    shadow_layer.paste(shadow_fill, (0, 3), sticker_alpha)  # 陰影向下偏移 3px
    shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(radius=3))  # 柔化陰影

    # 5. 最終合成 (陰影 -> 白邊 -> 人物主體)
    final_canvas = Image.new('RGBA', (canvas_w, canvas_h), (0, 0, 0, 0))
    final_canvas.alpha_composite(shadow_layer)    # 底層：柔和陰影
    final_canvas.alpha_composite(outline_layer)   # 中層：純白外框 (White Outline)
    final_canvas.paste(cropped, (pad, pad), cropped) # 頂層：人物/文字

    # 6. 置中裁切至正方形
    final_bbox = final_canvas.getbbox()
    out = final_canvas.crop(final_bbox) if final_bbox else final_canvas

    max_side = max(out.width, out.height) + 10
    square_img = Image.new('RGBA', (max_side, max_side), (0, 0, 0, 0))
    square_img.paste(out, ((max_side - out.width) // 2, (max_side - out.height) // 2), out)

    return square_img
