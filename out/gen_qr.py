import qrcode
from qrcode.constants import ERROR_CORRECT_M

FILE_ID = "1IxAxCbFoLNNcK_AQhPffS823-hkVP0Xy"
# Direct-download endpoint that also skips the virus-scan "confirm" page for larger files
url = f"https://drive.usercontent.google.com/download?id={FILE_ID}&export=download&confirm=t"

qr = qrcode.QRCode(error_correction=ERROR_CORRECT_M, box_size=12, border=4)
qr.add_data(url)
qr.make(fit=True)
img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
out = "/home/user/Empty/out/drive-download-qr.jpg"
img.save(out, "JPEG", quality=95)
print("URL:", url)
print("Saved:", out, img.size)
