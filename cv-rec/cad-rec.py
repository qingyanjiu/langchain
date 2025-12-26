import json
import cv2
import numpy as np

# ======================
# 1. 读图 & 压缩
# ======================
img = cv2.imread("/Users/louisliu/Downloads/cad.png")

def resize_image(img, max_size=1200):
    h, w = img.shape[:2]
    scale = max_size / max(h, w)
    if scale < 1:
        img = cv2.resize(img, (int(w * scale), int(h * scale)))
    return img, scale

scale = 1
# img, scale = resize_image(img, max_size=1200)
hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

# ======================
# 2. 定义多颜色规则
# ======================

COLOR_RULES = {
    "security": {  # 安防设备
        "ranges": [
            (np.array([0, 40, 40]), np.array([10, 255, 255])),
            (np.array([170, 40, 40]), np.array([180, 255, 255]))
        ],
        "draw_color": (0, 0, 255)  # BGR
    },

    "energy": {  # 能耗设备
        "ranges": [
            (np.array([20, 60, 60]), np.array([35, 255, 255]))
        ],
        "draw_color": (0, 255, 255)
    },

    "pass": {  # 通行设备
        "ranges": [
            (np.array([45, 60, 60]), np.array([75, 255, 255]))
        ],
        "draw_color": (0, 255, 0)
    },

    "assert": {  # 资产
        "ranges": [
            (np.array([100, 60, 60]), np.array([130, 255, 255]))
        ],
        "draw_color": (255, 0, 0)
    }
}

# 转 BGR -> RGB
rgb_colors = {}
for k, v in COLOR_RULES.items():
    b, g, r = v["draw_color"]
    rgb_colors[k] = f"rgb({r}, {g}, {b})"

rgb_json_str = json.dumps(rgb_colors, indent=4, ensure_ascii=False)

print(rgb_json_str)
# 打印的结果，参考颜色
color = {
    "security": "rgb(255, 0, 0)",
    "energy": "rgb(255, 255, 0)",
    "pass": "rgb(0, 255, 0)",
    "assert": "rgb(0, 0, 255)"
}

# ======================
# 3. 通用mask函数
# ======================
def build_mask(hsv_img, ranges):
    mask = None
    for lower, upper in ranges:
        m = cv2.inRange(hsv_img, lower, upper)
        mask = m if mask is None else cv2.bitwise_or(mask, m)
    return mask

# ======================
# 4. 识别点位 + 可视化
# ======================
all_points = []

kernel = np.ones((3, 3), np.uint8)  # 去噪核

idx = 0

for device_type, cfg in COLOR_RULES.items():
    mask = build_mask(hsv, cfg["ranges"])
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    for c in contours:
        area = cv2.contourArea(c)
        if area < 20:
            continue

        M = cv2.moments(c)
        if M["m00"] == 0:
            continue

        x = int(M["m10"] / M["m00"])
        y = int(M["m01"] / M["m00"])

        all_points.append({
            "type": device_type,
            "x": int(x / scale),  # 原图坐标
            "y": int(y / scale)
        })

        # 在压缩图上画圆 + 坐标
        cv2.circle(img, (x, y), 6, cfg["draw_color"], 2)
        cv2.putText(
            img,
            f"{device_type}-{str(idx)}",
            (x - 10, y - 12),
            cv2.FONT_HERSHEY_PLAIN,
            0.6,
            cfg["draw_color"],
            1
        )
        
        idx += 1

# ======================
# 5. 保存结果
# ======================
cv2.imwrite("points_debug_multi.png", img)

print("检测到点位数量:", len(all_points))
for p in all_points:
    print(p)
