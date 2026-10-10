from PIL import Image, ImageDraw

def create_icon():
    image = Image.new('RGBA', (256, 256), color=(0, 120, 215, 255))
    draw = ImageDraw.Draw(image)
    
    # T'nin ust yatay cizgisi (kalinlik ve boyut buyutuldu)
    draw.rectangle((64, 64, 192, 96), fill=(255, 255, 255, 255))
    # T'nin alt dikey cizgisi
    draw.rectangle((112, 96, 144, 208), fill=(255, 255, 255, 255))
    
    image.save('icon.ico', format='ICO', sizes=[(256, 256), (64, 64), (32, 32), (16, 16)])
    print("icon.ico created.")

if __name__ == '__main__':
    create_icon()
