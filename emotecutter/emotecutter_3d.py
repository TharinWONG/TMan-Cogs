from PIL import Image, ImageChops, ImageFilter, ImageDraw
import io

def process_3d_emote(cell_img):
    """
    製作 3D 立體緣邊 (Pop-out 3D Sticker) 表情包：
    1. 自動切除白底
    2. 生成圓潤白色 3D 外框
    3. 生成向下延伸的 3D 厚度 (Extrusion)
    4. 加上底部立體投影
    """
    # 1. 自動去除原圖白色背景，只保留人物與文字主體
    bg = Image.new('RGBA', cell_img.size, (255, 255, 255, 255))
    diff = ImageChops.difference(cell_img, bg)
    bbox = diff.getbbox()
    cropped = cell_img.crop(bbox) if bbox else cell_img

    # 取得主體的 Alpha 通道 (形狀遮罩)
    if cropped.mode != 'RGBA':
        cropped = cropped.convert('RGBA')
    alpha = cropped.split()[3]

    # 2. 製作圓潤的 3D 白色外框 (Border)
    border_radius = 10  # 立體外框粗細
    stroke_mask = alpha.filter(ImageFilter.MaxFilter(border_radius * 2 + 1))
    
    border_w = cropped.width + border_radius * 4
    border_h = cropped.height + border_radius * 4
    
    # 建立外框與主體的結合圖層
    sticker = Image.new('RGBA', (border_w, border_h), (0, 0, 0, 0))
    white_border = Image.new('RGBA', (border_w, border_h), (255, 255, 255, 255))
    
    # 貼上白色外框
    sticker.paste(white_border, (border_radius * 2, border_radius * 2), stroke_mask)
    # 貼上人物主體
    sticker.paste(cropped, (border_radius * 2, border_radius * 2), cropped)

    # 3. 製作 3D 厚度側邊 (Extrusion Thickness)
    sticker_alpha = sticker.split()[3]
    depth = 8  # 3D 厚度的深度 (像素)
    
    canvas_w = border_w + depth + 20
    canvas_h = border_h + depth + 20
    final_canvas = Image.new('RGBA', (canvas_w, canvas_h), (0, 0, 0, 0))

    # 繪製底部深色立體陰影 (3D Drop Shadow)
    shadow_color = (0, 0, 0, 80)
    shadow = Image.new('RGBA', (border_w, border_h), shadow_color)
    shadow_canvas = Image.new('RGBA', (canvas_w, canvas_h), (0, 0, 0, 0))
    shadow_canvas.paste(shadow, (10 + depth, 10 + depth), sticker_alpha)
    shadow_canvas = shadow_canvas.filter(ImageFilter.GaussianBlur(radius=4))
    final_canvas.alpha_composite(shadow_canvas)

    # 一層層向下偏移繪製 3D 灰色側邊厚度 (立體緣邊)
    edge_color = (210, 210, 215, 255) # 3D 側邊的立體灰色
    edge_layer = Image.new('RGBA', (border_w, border_h), edge_color)

    for i in range(depth, 0, -1):
        final_canvas.paste(edge_layer, (10 + i, 10 + i), sticker_alpha)

    # 4. 最頂層貼上主體貼紙
    final_canvas.paste(sticker, (10, 10), sticker)

    # 5. 自動裁切並置中於正方形畫布
    final_bbox = final_canvas.getbbox()
    out = final_canvas.crop(final_bbox) if final_bbox else final_canvas
    
    max_side = max(out.width, out.height) + 10
    square_img = Image.new('RGBA', (max_side, max_side), (0, 0, 0, 0))
    square_img.paste(out, ((max_side - out.width) // 2, (max_side - out.height) // 2), out)

    return square_img
