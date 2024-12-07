from PIL import Image
import cairosvg
import io

# 生成多个尺寸的图标
sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
images = []

for size in sizes:
    png_data = cairosvg.svg2png(url="icons/video.svg", output_width=size[0], output_height=size[1])
    img = Image.open(io.BytesIO(png_data))
    images.append(img)

# 保存为包含多个尺寸的ICO文件
images[0].save("video.ico", format="ICO", sizes=sizes, append_images=images[1:]) 