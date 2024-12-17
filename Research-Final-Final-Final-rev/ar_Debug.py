
import pytesseract
from PIL import Image
from flask import Flask, request, render_template, redirect, url_for, session, Response, flash, jsonify
import re
import cv2
import io 
import base64
import sqlite3
import csv

app = Flask(__name__)
app.secret_key = "super secret key"

def query_database(name):
    conn = sqlite3.connect('test.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM trial WHERE name = ?", (name,))
    result = cursor.fetchone()
    conn.close()
    return result

@app.route('/')
def home():
    return render_template("ar6.html")




if __name__ == '__main__':
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    app.run(host="0.0.0.0", port=8000, debug=True)
   
