from PIL import Image, ImageChops, ImageFilter
import io

def process_3d_emote(cell_img):
    """
    製作 3D 立體緣邊 (Pop-out 3D Sticker) 表情包：
    1. 自動切除白底
    2. 生成圓潤白色 3D 外框
    3. 生成向下延伸的 3D 厚度 (Extrusion)
    4. 加上底部立體投影
    """
    # 確保圖片為 RGBA 模式
    if cell_img.mode != 'RGBA':
        cell_img = cell_img.convert('RGBA')

    # 1. 自動去除原圖白色背景，只保留人物與文字主體
    bg = Image.new('RGBA', cell_img.size, (255, 255, 255, 255))
    diff = ImageChops.difference(cell_img, bg)
    bbox = diff.getbbox()
    cropped = cell_img.crop(bbox) if bbox else cell_img

    c_w, c_h = cropped.size
    alpha = cropped.split()[3]

    # 2. 製作圓潤的 3D 白色外框 (Border)
    border_radius = 8  # 外框擴展像素
    
    # 使用 Alpha 遮罩進行膨脹，產出外框形狀
    stroke_mask = alpha.filter(ImageFilter.MaxFilter(border_radius * 2 + 1))
    
    # 建立外框與主體的結合圖層 (精確計算尺寸)
    stk_w = c_w + border_radius * 2
    stk_h = c_h + border_radius * 2
    
    sticker = Image.new('RGBA', (stk_w, stk_h), (0, 0, 0, 0))
    white_fill = Image.new('RGBA', (stk_w, stk_h), (255, 255, 255, 255))
    
    # 貼上白色外框與人物主體
    sticker.paste(white_fill, (0, 0), stroke_mask)
    sticker.paste(cropped, (border_radius, border_radius), cropped)

    # 3. 製作 3D 厚度側邊與立體陰影
    stk_alpha = sticker.split()[3]
    depth = 8  # 3D 厚度深度
    
    pad = 15  # 畫布邊緣留白
    canvas_w = stk_w + depth + pad * 2
    canvas_h = stk_h + depth + pad * 2
    
    final_canvas = Image.new('RGBA', (canvas_w, canvas_h), (0, 0, 0, 0))

    # (A) 繪製底部懸浮柔和陰影
    shadow_color = (0, 0, 0, 90)
    shadow_layer = Image.new('RGBA', (stk_w, stk_h), shadow_color)
    shadow_canvas = Image.new('RGBA', (canvas_w, canvas_h), (0, 0, 0, 0))
    shadow_canvas.paste(shadow_layer, (pad + depth, pad + depth), stk_alpha)
    shadow_canvas = shadow_canvas.filter(ImageFilter.GaussianBlur(radius=4))
    final_canvas.alpha_composite(shadow_canvas)

    # (B) 繪製 3D 灰色側邊厚度
    edge_color = (210, 210, 215, 255)
    edge_layer = Image.new('RGBA', (stk_w, stk_h), edge_color)

    for i in range(depth, 0, -1):
        final_canvas.paste(edge_layer, (pad + i, pad + i), stk_alpha)

    # (C) 最頂層貼上白框貼紙
    final_canvas.paste(sticker, (pad, pad), sticker)

    # 4. 自動裁切並置中於正方形畫布
    final_bbox = final_canvas.getbbox()
    out = final_canvas.crop(final_bbox) if final_bbox else final_canvas
    
    max_side = max(out.width, out.height) + 10
    square_img = Image.new('RGBA', (max_side, max_side), (0, 0, 0, 0))
    square_img.paste(out, ((max_side - out.width) // 2, (max_side - out.height) // 2), out)

    return square_img
