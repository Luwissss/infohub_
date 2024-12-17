import cv2
import pytesseract

# Path for Windows
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Read in image as grayscale
image = cv2.imread('test1.png',0)
thresh = cv2.threshold(image, 150, 255, cv2.THRESH_BINARY)[1]
kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3,3))
close = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

# Invert image to use for Tesseract
result = 255 - close
cv2.imshow('image', image)
cv2.imshow('thresh', thresh)    
cv2.imshow('close', close)
cv2.imshow('result', result)

# Throw image into tesseract
print(pytesseract.image_to_string(result))
cv2.waitKey()