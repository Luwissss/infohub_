
import pytesseract
from PIL import Image
from flask import Flask, request, render_template, redirect, url_for, session, Response, flash, jsonify, send_from_directory
import re
import cv2
import io 
import base64
import sqlite3
import csv

app = Flask(__name__)
app.secret_key = "super secret key"
def connect():
    conn = sqlite3.connect('test.db')
    conn.row_factory = sqlite3.Row
    return conn 

def get_image_from_db(image_name):
    connection = connect()
    cursor = connection.cursor()
    cursor.execute("SELECT image FROM tests WHERE name = ?", (image_name ,))
    result = cursor.fetchone()
    connection.close()
    if result:
        image_data = result[0]
        print(type(image_data))
        output_path = "static/student/test.jpg"
        with open(output_path, 'wb') as file:
            file.write(image_data)
        return (image_data)
    return None



@app.route('/')
def home():
    cursor = connect()
    check = cursor.execute('SELECT * FROM tests WHERE name LIKE ?', ('%' + 'Luis' + '%',)).fetchone()
    cursor.close()
    get_image_from_db(check['name'])

    return render_template("ar2.html", name = check['name'])


if __name__ == '__main__':
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    app.run(host="0.0.0.0", port=8000, debug=True)
   
