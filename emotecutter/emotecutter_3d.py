from PIL import Image, ImageChops, ImageFilter, ImageOps
import io

def process_3d_emote(cell_img, is_row_start=False):
    """
    處理單張 Emote，去除殘影並加上 3D 外框與立體陰影
    """
    # 1. 自動裁剪掉白色背景（去殘影）
    bg = Image.new('RGBA', cell_img.size, (255, 255, 255, 255))
    diff = ImageChops.difference(cell_img, bg)
    bbox = diff.getbbox()
    
    if bbox:
        cropped = cell_img.crop(bbox)
    else:
        cropped = cell_img

    # 2. 建立立體陰影 (Shadow)
    shadow_offset = (10, 10)
    shadow_color = (0, 0, 0, 120)
    
    # 用 alpha 通道建立陰影遮罩
    alpha = cropped.split()[3] if cropped.mode == 'RGBA' else Image.new('L', cropped.size, 255)
    shadow = Image.new('RGBA', cropped.size, shadow_color)
    
    # 擴展畫布以容納 3D 陰影與外框
    pad = 20
    canvas_w = cropped.width + shadow_offset[0] + (pad * 2)
    canvas_h = cropped.height + shadow_offset[1] + (pad * 2)
    canvas = Image.new('RGBA', (canvas_w, canvas_h), (0, 0, 0, 0))

    # 貼上軟陰影 (模糊處理)
    shadow_canvas = Image.new('RGBA', (canvas_w, canvas_h), (0, 0, 0, 0))
    shadow_canvas.paste(shadow, (pad + shadow_offset[0], pad + shadow_offset[1]), alpha)
    shadow_canvas = shadow_canvas.filter(ImageFilter.GaussianBlur(radius=6))
    
    # 將陰影貼到主畫布
    canvas.alpha_composite(shadow_canvas)

    # 3. 加上白邊 3D 梗圖外框效果 (Border Effect)
    border_size = 6
    stroke_mask = Image.new('L', (cropped.width + border_size * 2, cropped.height + border_size * 2), 0)
    stroke_mask.paste(alpha, (border_size, border_size))
    stroke_mask = stroke_mask.filter(ImageFilter.MaxFilter(border_size * 2 + 1))
    
    stroke = Image.new('RGBA', stroke_mask.size, (255, 255, 255, 255))
    canvas.paste(stroke, (pad - border_size, pad - border_size), stroke_mask)

    # 貼上主體圖案
    canvas.paste(cropped, (pad, pad), cropped)

    # 4. 調整為正方形邊界
    max_dim = max(canvas.width, canvas.height)
    final_square = Image.new('RGBA', (max_dim, max_dim), (0, 0, 0, 0))
    paste_x = (max_dim - canvas.width) // 2
    paste_y = (max_dim - canvas.height) // 2
    final_square.paste(canvas, (paste_x, paste_y), canvas)

    return final_square
