from flask import Flask, render_template, request, redirect, url_for, flash, session
import requests
import os
from datetime import datetime
import json

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev_secret_key_change_in_production')

# RapidAPI credentials
RAPID_API_KEY = "5e1ecabc66msh694b39570340884p13dccdjsn1e9bc0e24113"
RAPID_API_HOST = "open-weather13.p.rapidapi.com"
BASE_URL = "https://open-weather13.p.rapidapi.com/city"
FORECAST_URL = "https://open-weather13.p.rapidapi.com/forecast"


def kelvin_to_celsius(kelvin):
    """Convert Kelvin to Celsius"""
    return round(kelvin - 273.15, 1)


def kelvin_to_fahrenheit(kelvin):
    """Convert Kelvin to Fahrenheit"""
    return round((kelvin - 273.15) * 9 / 5 + 32, 1)


def format_time(timestamp, timezone_offset):
    """Format timestamp to readable time, adjusting for timezone"""
    utc_time = datetime.utcfromtimestamp(timestamp)
    local_time = utc_time.replace(second=0)  # Ignoring seconds for cleaner display
    return local_time.strftime("%I:%M %p")  # 12-hour format


def get_weather_icon_url(icon_code):
    """Get the URL for the weather icon"""
    return f"https://openweathermap.org/img/wn/{icon_code}@2x.png"


def get_weather_data(city):
    """Get current weather data for a city"""
    headers = {
        'x-rapidapi-key': RAPID_API_KEY,
        'x-rapidapi-host': RAPID_API_HOST
    }

    url = f"{BASE_URL}/{city}"

    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        return None

    data = response.json()

    if 'recent_searches' not in session:
        session['recent_searches'] = []

    if city not in session['recent_searches']:
        session['recent_searches'].insert(0, city)
        if len(session['recent_searches']) > 5:
            session['recent_searches'].pop()
        session.modified = True

    weather_data = {
        'city': data['name'],
        'country': data['sys']['country'],
        'temp_c': kelvin_to_celsius(data['main']['temp']),
        'temp_f': kelvin_to_fahrenheit(data['main']['temp']),
        'feels_like_c': kelvin_to_celsius(data['main']['feels_like']),
        'feels_like_f': kelvin_to_fahrenheit(data['main']['feels_like']),
        'humidity': data['main']['humidity'],
        'pressure': data['main']['pressure'],
        'weather': data['weather'][0]['main'],
        'description': data['weather'][0]['description'].capitalize(),
        'icon': get_weather_icon_url(data['weather'][0]['icon']),
        'wind_speed': data['wind']['speed'],
        'wind_deg': data['wind']['deg'],
        'clouds': data['clouds']['all'],
        'sunrise': format_time(data['sys']['sunrise'], data['timezone']),
        'sunset': format_time(data['sys']['sunset'], data['timezone']),
        'timezone': data['timezone'],
        'dt': format_time(data['dt'], data['timezone']),
        'visibility': data.get('visibility', 0) / 1000,  # Convert to km
        'coord': data['coord']
    }

    return weather_data


def get_forecast_data(lat, lon):
    """Get 5-day forecast data"""
    headers = {
        'x-rapidapi-key': RAPID_API_KEY,
        'x-rapidapi-host': RAPID_API_HOST
    }

    url = f"{FORECAST_URL}/lat/{lat}/lon/{lon}"

    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        return None

    data = response.json()
    forecast_items = []

    day_tracker = None
    for item in data['list'][:40]:
        forecast_date = datetime.utcfromtimestamp(item['dt'])
        forecast_day = forecast_date.date()

        if day_tracker != forecast_day and len(forecast_items) < 5:
            day_tracker = forecast_day
            forecast_items.append({
                'date': forecast_date.strftime("%A, %b %d"),
                'temp_c': kelvin_to_celsius(item['main']['temp']),
                'temp_f': kelvin_to_fahrenheit(item['main']['temp']),
                'description': item['weather'][0]['description'].capitalize(),
                'icon': get_weather_icon_url(item['weather'][0]['icon']),
                'humidity': item['main']['humidity'],
                'wind_speed': item['wind']['speed'],
            })

    return forecast_items


@app.route('/')
def index():
    """Home page"""
    recent_searches = session.get('recent_searches', [])
    return render_template('index.html', recent_searches=recent_searches)


@app.route('/weather', methods=['GET', 'POST'])
def weather():
    """Weather results page"""
    if request.method == 'POST':
        city = request.form.get('city')
        if not city:
            flash('Please enter a city name')
            return redirect(url_for('index'))

        return redirect(url_for('weather', city=city))

    city = request.args.get('city')
    if not city:
        flash('Please enter a city name')
        return redirect(url_for('index'))

    weather_data = get_weather_data(city)

    if not weather_data:
        flash(f'City "{city}" not found. Please check the spelling and try again.')
        return redirect(url_for('index'))

    forecast_data = get_forecast_data(
        weather_data['coord']['lat'],
        weather_data['coord']['lon']
    )

    recent_searches = session.get('recent_searches', [])
    return render_template(
        'weather.html',
        weather=weather_data,
        forecast=forecast_data,
        recent_searches=recent_searches
    )


@app.route('/clear-history')
def clear_history():
    """Clear search history"""
    if 'recent_searches' in session:
        session.pop('recent_searches')
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True)
