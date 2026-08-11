from PIL import Image, ImageChops, ImageFilter
import io

def process_3d_emote(cell_img):
    """
    製作 3D 立體緣邊 (Pop-out 3D Sticker) 表情包
    防錯版：使用安全 offset 合成，絕不跳出 images do not match 錯誤
    """
    # 1. 確保為 RGBA 模式
    if cell_img.mode != 'RGBA':
        cell_img = cell_img.convert('RGBA')

    # 2. 自動切除多餘白底 (去殘影)
    bg = Image.new('RGBA', cell_img.size, (255, 255, 255, 255))
    diff = ImageChops.difference(cell_img, bg)
    bbox = diff.getbbox()
    cropped = cell_img.crop(bbox) if bbox else cell_img

    c_w, c_h = cropped.size

    # 3. 建立大畫布 (給予足夠留白放入 3D 厚度與陰影)
    pad = 25
    depth = 8  # 3D 側邊厚度
    
    canvas_w = c_w + pad * 2
    canvas_h = c_h + pad * 2
    
    # --- (A) 製作懸浮 3D 陰影 ---
    shadow_canvas = Image.new('RGBA', (canvas_w, canvas_h), (0, 0, 0, 0))
    # 提取 alpha 製作陰影
    shadow_color = Image.new('RGBA', (c_w, c_h), (0, 0, 0, 100))
    shadow_canvas.paste(shadow_color, (pad + depth + 2, pad + depth + 4), cropped.split()[3])
    shadow_canvas = shadow_canvas.filter(ImageFilter.GaussianBlur(radius=4))

    # --- (B) 製作 3D 白色外框 (Sticker Outline) ---
    border_canvas = Image.new('RGBA', (canvas_w, canvas_h), (0, 0, 0, 0))
    white_fill = Image.new('RGBA', (c_w, c_h), (255, 255, 255, 255))
    
    # 向八個方向微幅偏移，生成圓潤白色外框
    border_size = 5
    for dx in range(-border_size, border_size + 1):
        for dy in range(-border_size, border_size + 1):
            if dx*dx + dy*dy <= border_size*border_size:
                border_canvas.paste(white_fill, (pad + dx, pad + dy), cropped.split()[3])

    # --- (C) 製作向下延伸的 3D 立體灰色側邊 ---
    depth_canvas = Image.new('RGBA', (canvas_w, canvas_h), (0, 0, 0, 0))
    edge_fill = Image.new('RGBA', (c_w, c_h), (200, 200, 205, 255))
    
    for i in range(depth, 0, -1):
        depth_canvas.paste(edge_fill, (pad, pad + i), cropped.split()[3])

    # --- (D) 最終 3D 圖層大合成 ---
    final_canvas = Image.new('RGBA', (canvas_w, canvas_h), (0, 0, 0, 0))
    
    # 1. 貼底層陰影
    final_canvas.alpha_composite(shadow_canvas)
    # 2. 貼 3D 厚度側邊
    final_canvas.alpha_composite(depth_canvas)
    # 3. 貼白色立體外框
    final_canvas.alpha_composite(border_canvas)
    # 4. 最頂層貼上原圖案
    final_canvas.paste(cropped, (pad, pad), cropped)

    # 4. 自動裁切並置中於正方形畫布
    final_bbox = final_canvas.getbbox()
    out = final_canvas.crop(final_bbox) if final_bbox else final_canvas
    
    max_side = max(out.width, out.height) + 10
    square_img = Image.new('RGBA', (max_side, max_side), (0, 0, 0, 0))
    square_img.paste(out, ((max_side - out.width) // 2, (max_side - out.height) // 2), out)

    return square_img
