from flask import Flask, render_template, request
import requests
from bs4 import BeautifulSoup
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import matplotlib.pyplot as plt
from io import BytesIO
import csv
import os

app = Flask(__name__)

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
HEADERS = {"User-Agent": USER_AGENT, "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8"}

def get_price(url, selector):
    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "lxml")
        price_str = soup.select_one(selector).get_text()
        price = int(price_str.replace("₹", "").replace(",", "").split(".")[0])
        return price
    except (requests.RequestException, AttributeError, ValueError) as e:
        print(f"Error fetching price from {url}: {e}")
        return None

def send_notification_email(email, message, pdf_data):
    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    sender_email = "pricedropalertssystem@gmail.com"
    sender_password = "qpafqzqmpcphrbyi"

    server = smtplib.SMTP(smtp_server, smtp_port)
    server.starttls()
    server.login(sender_email, sender_password)

    msg = MIMEMultipart()
    msg["Subject"] = "Price Notification"
    msg["From"] = sender_email
    msg["To"] = email

    msg.attach(MIMEText(message, "plain"))

    pdf_part = MIMEApplication(pdf_data, Name="price_comparison.pdf")
    pdf_part['Content-Disposition'] = 'attachment; filename="price_comparison.pdf"'
    msg.attach(pdf_part)

    server.sendmail(sender_email, email, msg.as_string())

    server.quit()

def create_csv_with_headers():
    headers = ['Amazon Price', 'Flipkart Price', 'Timestamp', 'Price Limit', 'User Email','Price drop']
    file_exists = os.path.isfile('database.csv')
    with open('database.csv', mode='a', newline='') as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow(headers)

def write_to_csv(amazon_price, flipkart_price, time_stamp, price_limit, user_email, status):
    with open('database.csv', mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([amazon_price, flipkart_price, time_stamp, price_limit, user_email, status])

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/select')
def select():
    return render_template('select.html')

@app.route('/result', methods=['POST'])
def result():
    amazon_url = request.form['amazon_url']
    flipkart_url = request.form['flipkart_url']
    price_limit = float(request.form['price_limit'])
    user_email = request.form['user_email']

    create_csv_with_headers()
    
    # Attempt to fetch initial prices
    initial_amazon_price = get_price(amazon_url, ".a-offscreen")
    initial_flipkart_price = get_price(flipkart_url, "._30jeq3 _16Jk6d")
    current_time = time.strftime('%Y-%m-%d %H:%M:%S')

    # Check if initial prices were fetched successfully
    if initial_amazon_price is None:
        return render_template('result.html', message='Error fetching initial Amazon price. Please check the URL and try again.')
    if initial_flipkart_price is None:
        return render_template('result.html', message='Error fetching initial Flipkart price. Please check the URL and try again.')

    prices_amazon = [initial_amazon_price]
    prices_flipkart = [initial_flipkart_price]

    while True:
        amazon_price = get_price(amazon_url, ".a-price-whole")
        flipkart_price = get_price(flipkart_url, "._30jeq3 _16Jk6d")

        if amazon_price is None:
            return render_template('result.html', message='Error fetching Amazon price. Please check the URL and try again.')
        if flipkart_price is None:
            return render_template('result.html', message='Error fetching Flipkart price. Please check the URL and try again.')

        prices_amazon.append(amazon_price)
        prices_flipkart.append(flipkart_price)

        if amazon_price <= price_limit or flipkart_price <= price_limit:
            message = ""
            if amazon_price <= price_limit:
                message += f"Amazon price is below the set limit!\n"
                message += f"Amazon Price: ₹{amazon_price}\n"
                message += f"Amazon Product Link: {amazon_url}\n"
            if flipkart_price <= price_limit:
                message += f"Flipkart price is below the set limit!\n"
                message += f"Flipkart Price: ₹{flipkart_price}\n"
                message += f"Flipkart Product Link: {flipkart_url}\n"
            send_notification_email(user_email, message, pdf_data)
            status = "Yes"
            break
        else:
            status = "No"
            time.sleep(3600)

    write_to_csv(initial_amazon_price, initial_flipkart_price, current_time, price_limit, user_email, status)
    return render_template('result.html', message='Email sent successfully!')


if __name__ == '__main__':
    app.run(debug=True)
