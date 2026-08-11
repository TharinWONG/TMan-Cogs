from PIL import Image, ImageChops, ImageDraw, ImageFilter
import numpy as np

def find_coeffs(pa, pb):
    """計算 Perspective 變換矩陣的幾何係數"""
    matrix = []
    for p1, p2 in zip(pa, pb):
        matrix.append([p1[0], p1[1], 1, 0, 0, 0, -p2[0]*p1[0], -p2[0]*p1[1]])
        matrix.append([0, 0, 0, p1[0], p1[1], 1, -p2[1]*p1[0], -p2[1]*p1[1]])
    A = np.matrix(matrix, dtype=float)
    B = np.array(pb).reshape(8, 1)
    res = np.dot(A.I, B)
    return np.array(res).flatten()

def process_3d_emote(cell_img):
    """
    真正的 3D 切割：自動去除白底，並加上立體斜角透視 + 側邊 3D 厚度 + 懸浮陰影
    """
    # 1. 自動裁剪去掉白色背景
    bg = Image.new('RGBA', cell_img.size, (255, 255, 255, 255))
    diff = ImageChops.difference(cell_img, bg)
    bbox = diff.getbbox()
    cropped = cell_img.crop(bbox) if bbox else cell_img

    w, h = cropped.size

    # 2. 定義 3D 斜角透視座標 (將矩形變形為向右上傾斜的立體卡牌)
    tilt_x = int(w * 0.12)  # X 軸傾斜幅度
    tilt_y = int(h * 0.08)  # Y 軸縮放幅度

    # 原圖四個角
    src_corners = [(0, 0), (w, 0), (w, h), (0, h)]
    # 3D 變形後的四個角 (左低右高、呈現 3D 斜角)
    dst_corners = [
        (tilt_x, tilt_y), 
        (w + tilt_x, 0), 
        (w, h - tilt_y), 
        (0, h)
    ]

    # 進行 Perspective 3D 變換
    coeffs = find_coeffs(dst_corners, src_corners)
    canvas_w = w + tilt_x + 30
    canvas_h = h + 30
    
    transformed_img = cropped.transform(
        (canvas_w, canvas_h), 
        Image.Transform.PERSPECTIVE, 
        coeffs, 
        Image.Resampling.BICUBIC
    )

    # 3. 疊加 3D 厚度層 (Extrusion / Depth Layer)
    depth_layers = 12  # 3D 側邊厚度像素
    base_3d = Image.new('RGBA', (canvas_w + depth_layers + 20, canvas_h + depth_layers + 20), (0, 0, 0, 0))

    # 繪製底下沉積的 3D 厚度陰影
    shadow_mask = transformed_img.split()[3]
    shadow = Image.new('RGBA', (canvas_w, canvas_h), (30, 30, 30, 180)) # 暗色厚度邊

    for i in range(depth_layers, 0, -1):
        # 一層層複製位移，營造 3D 實體側邊
        base_3d.paste(shadow, (i + 10, i + 15), shadow_mask)

    # 4. 加上底部懸浮軟陰影 (Floor Drop Shadow)
    base_3d = base_3d.filter(ImageFilter.GaussianBlur(radius=3))

    # 5. 貼上最頂層的 3D 變形主圖案
    base_3d.paste(transformed_img, (10, 10), transformed_img)

    # 6. 裁切並放到透明正方形畫布中
    final_bbox = base_3d.getbbox()
    if final_bbox:
        final_cropped = base_3d.crop(final_bbox)
    else:
        final_cropped = base_3d

    fc_w, fc_h = final_cropped.size
    max_dim = max(fc_w, fc_h) + 20
    
    final_square = Image.new('RGBA', (max_dim, max_dim), (0, 0, 0, 0))
    paste_x = (max_dim - fc_w) // 2
    paste_y = (max_dim - fc_h) // 2
    final_square.paste(final_cropped, (paste_x, paste_y), final_cropped)

    return final_square
