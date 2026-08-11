from PIL import Image, ImageFilter
from rembg import remove
import io

def process_3d_emote(cell_img):
    """
    真正的「沿輪廓貼紙切割」(Contour Crop Sticker)：
    1. AI (rembg) 精確扣出主體（無視複雜背景或白底）
    2. 自動沿著主體邊緣擴充純白貼紙邊框 (White Outline)
    3. 加上底部懸浮立體陰影
    """
    # 確保圖片為 RGBA 模式
    if cell_img.mode != 'RGBA':
        cell_img = cell_img.convert('RGBA')

    # 1. 執行 AI 去背 (精準將人物、文字、音符與背景分離)
    nobg_img = remove(cell_img)
    
    # 取得去背後的 Alpha 遮罩
    alpha = nobg_img.split()[3]

    # 2. 設定貼紙邊框與畫布邊距
    outline_thickness = 8  # 白邊粗細 (可自由調整 5~12)
    pad = outline_thickness + 15
    
    w, h = nobg_img.size
    canvas_w, canvas_h = w + pad * 2, h + pad * 2

    # 3. 生成順應 AI 輪廓的 White Outline (貼紙白邊)
    # 使用 MaxFilter 將 Alpha 遮罩向外膨脹
    stroke_mask = alpha.filter(ImageFilter.MaxFilter(outline_thickness * 2 + 1))
    
    outline_layer = Image.new('RGBA', (canvas_w, canvas_h), (0, 0, 0, 0))
    white_fill = Image.new('RGBA', (canvas_w, canvas_h), (255, 255, 255, 255))
    outline_layer.paste(white_fill, (pad, pad), stroke_mask)

    # 4. 製作底層懸浮陰影 (Drop Shadow)
    shadow_layer = Image.new('RGBA', (canvas_w, canvas_h), (0, 0, 0, 0))
    shadow_fill = Image.new('RGBA', (canvas_w, canvas_h), (0, 0, 0, 75))
    sticker_alpha = outline_layer.split()[3]
    
    # 陰影向下微移 4px 並模糊化
    shadow_layer.paste(shadow_fill, (0, 4), sticker_alpha)
    shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(radius=4))

    # 5. 最終合成 (底層陰影 -> 中層白邊 -> 頂層人物主體)
    final_canvas = Image.new('RGBA', (canvas_w, canvas_h), (0, 0, 0, 0))
    final_canvas.alpha_composite(shadow_layer)
    final_canvas.alpha_composite(outline_layer)
    final_canvas.paste(nobg_img, (pad, pad), nobg_img)

    # 6. 自動精確裁切並置中放進正方形透明畫布
    final_bbox = final_canvas.getbbox()
    out = final_canvas.crop(final_bbox) if final_bbox else final_canvas

    max_side = max(out.width, out.height) + 10
    square_img = Image.new('RGBA', (max_side, max_side), (0, 0, 0, 0))
    square_img.paste(out, ((max_side - out.width) // 2, (max_side - out.height) // 2), out)

    return square_img
