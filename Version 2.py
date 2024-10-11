import requests
import mysql.connector
import math

# Database connection (same as before)
connection = mysql.connector.connect(
    host="localhost",
    port=3306,
    user="root",
    password="218468",
    database="flight_game",
    collation="latin1_swedish_ci",
    autocommit=True
)


# Weather checking function using OpenWeatherMap API
def check_weather(city_name):
    api_key = "#############"  #  OpenWeatherMap API key
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city_name}&appid={api_key}&units=metric"  # metric for Celsius temperature

    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        weather_condition = data['weather'][0]['main']  # 'Clear', 'Rain', 'Snow', 'Thunderstorm', etc.
        temperature = data['main']['temp']  # Temperature in Celsius

        print(f"Weather condition at {city_name}: {weather_condition}")
        print(f"Local temperature: {temperature}°C")

        # Check if the weather is bad (Thunderstorm or Snow)
        if weather_condition in ['Thunderstorm', 'Snow']:
            print(f"Weather is bad in {city_name} (Thunderstorm or Snow). Please choose another airport.")
            return False
        else:
            print(f"Weather is good at {city_name}. You can land.")
            return True  # Weather is good
    else:
        print(f"Failed to retrieve weather data. Status code: {response.status_code}")
        return False  # Treat as bad weather if request fails


def create_player(name):
    cursor.execute(f"SELECT player_id, name, airport_ident, number_of_play FROM player WHERE name='{name}'")
    result = cursor.fetchall()

    # if the name does not already exist
    if (result == []):
        cursor.execute(f"INSERT INTO player (name, airport_ident, number_of_play) VALUES ('{name}', 'WSSS', 1)")

    # if the name does already exist, also create a new user, set number_of_play + 1
    if (result != []):
        number_of_play = len(result) + 1
        cursor.execute(
            f"INSERT INTO player (name, airport_ident, number_of_play) VALUES ('{name}', 'WSSS', {number_of_play})")


def return_5000km_airport(now_airport_ident):
    def haversine(lat1, lon1, lat2, lon2):
        # Radius of Earth in kilometers
        R = 6371.0
        # Convert degrees to radians
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        # Haversine formula
        a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        # Distance in kilometers
        distance = R * c
        return distance


    # fetch all large airports (include log and lat and name) (exclude the current airport)
    cursor.execute(f"SELECT ident, name, latitude_deg, longitude_deg, municipality, iata_code FROM airport WHERE type='large_airport' AND ident!= '{now_airport_ident}'")
    result = cursor.fetchall()

    # fetch current airport informantion
    cursor.execute( f"SELECT ident, name, latitude_deg, longitude_deg, municipality, iata_code FROM airport WHERE ident='{now_airport_ident}'")
    now_airport_result = cursor.fetchall()

    ident_cur, name_cur, latitude_deg_cur, longitude_deg_cur, municipality_cur, iata_code_cur = now_airport_result[0]

    ret = []
    for row in result:
        ident, name, latitude_deg, longitude_deg, municipality, iata_code = row
        dist = haversine(latitude_deg_cur, longitude_deg_cur, latitude_deg, longitude_deg)
        if (dist <= 10000):
            ret.append([ident, name, municipality, iata_code, dist])

    return ret


def check_is_game_finished(player_id):
    cursor.execute(f"SELECT name, airport_ident, number_of_play FROM player WHERE player_id='{player_id}'")
    result = cursor.fetchall()
    name, airport_ident, number_of_play = result[0]

    if airport_ident != 'WSSS':
        return False
    elif airport_ident == 'WSSS':
        cursor.execute(f"SELECT ps.seq_id,                                          \
                           a_start.longitude_deg AS starting_longitude,                 \
                           a_end.longitude_deg AS ending_longitude,                      \
                            s.distance                                                  \
                            FROM player_seq ps                                             \
                            JOIN sequence s ON ps.seq_id = s.seq_id                     \
                            JOIN airport a_start ON s.starting_location = a_start.ident         \
                            JOIN airport a_end ON s.ending_location = a_end.ident           \
                            WHERE ps.player_id = '{player_id}'                 \
                            ORDER BY ps.seq_id                      \
                ")
        result = cursor.fetchall()
        visited_longitudes = set()
        total_distance = 0
        for row in result:
            seq_id, starting_longitude, ending_longitude, distance = row

            if starting_longitude < 0:
                start_longitude = int(starting_longitude) + 360
            else:
                start_longitude = int(starting_longitude)
            if ending_longitude < 0:
                end_longitude = int(ending_longitude) + 360
            else:
                end_longitude = int(ending_longitude)

            if start_longitude < end_longitude and abs(start_longitude - end_longitude) < 180:
                visited_longitudes.update(range(start_longitude, end_longitude + 1))
            elif start_longitude < end_longitude and abs(start_longitude - end_longitude) > 180:
                visited_longitudes.update(range(0, start_longitude + 1))
                visited_longitudes.update(range(end_longitude, 360 + 1))
            elif start_longitude > end_longitude and abs(start_longitude - end_longitude) < 180:
                visited_longitudes.update(range(end_longitude, start_longitude + 1))
            elif start_longitude > end_longitude and abs(start_longitude - end_longitude) > 180:
                visited_longitudes.update(range(0, end_longitude + 1))
                visited_longitudes.update(range(start_longitude, 360 + 1))

            total_distance = total_distance + distance

        if len(visited_longitudes) >= 360:
            return True, total_distance
        else:
            return False


if __name__ == '__main__':
    print("Welcome to the round-world trip game.")
    print("You will depart from Singapore Changi Airport, cross every longitude, and finally return to Singapore.")

    cursor = connection.cursor()
    # each game
    while (True):
        player = input("Please enter your name: ")
        create_player(player)

        # choosing the place
        while (True):
            cursor.execute(
                f"SELECT player_id, name, airport_ident, number_of_play FROM player WHERE name='{player}' ORDER BY number_of_play DESC LIMIT 1")
            result = cursor.fetchall()
            player_id, name, airport_ident, number_of_play = result[0]

            # get the list of next destination
            list_of_next = return_5000km_airport(airport_ident)

            # sort
            sorted_data = sorted(list_of_next, key=lambda x: x[4], reverse=True)

            # print
            print(f"{'Ident':<10} {'Name':<50} {'City':<23} {'Distance (km)':<15}")
            print('-' * 110)
            for row in sorted_data:
                print(f"{row[0]:<10} {row[1]:<50} {row[2]:<23} {row[4]:<15.2f}")
            print('-' * 110)

            # let player choose the next place
            while True:
                next_fly_ident = input("Please choose a place to fly next (type the Ident): ")

                cursor.execute(f"SELECT municipality FROM airport WHERE ident='{next_fly_ident}'")
                city_name_result = cursor.fetchone()
                city_name = city_name_result[0]

                # Check the weather at the chosen airport
                if check_weather(city_name):
                    break  # Weather is good, proceed
                else:
                    print("Please choose a different airport.")

            cursor.execute(f"UPDATE player SET airport_ident='{next_fly_ident}' WHERE player_id='{player_id}'")

            # Insert one record in sequence
            distance = None  # Initialize distance variable
            for row in sorted_data:
                if row[0] == next_fly_ident:
                    distance = row[4]  # Assign the correct distance
                    break

            # Check if distance was found, if not handle the case
            if distance is not None:
                cursor.execute(
                    "INSERT INTO sequence (starting_location, ending_location, distance) VALUES (%s, %s, %s)",
                    (airport_ident, next_fly_ident, distance)
                )
            else:
                print(
                    f"Error: Could not find the distance for airport {next_fly_ident}. Please check the airport code.")

            last_inserted_id = cursor.lastrowid
            cursor.execute(
                "INSERT INTO player_seq (player_id, seq_id) VALUES (%s, %s)",
                (player_id, last_inserted_id)
            )
            if check_is_game_finished(player_id):
                _, total_distance = check_is_game_finished(player_id)
                cursor.execute(
                    "INSERT INTO ranking (player_id, total_distance) VALUES (%s, %s)",
                    (player_id, total_distance)
                )

                print('-' * 40)
                print("You successfully finished the round-world trip!")
                print('-' * 40)
                cursor.execute(
                    f"SELECT p.player_id, p.name, r.total_distance FROM ranking r JOIN player p ON r.player_id = p.player_id ORDER BY r.total_distance ASC"
                )
                result = cursor.fetchall()
                print("Ranking Table")
                print(f"{'player Name':<15} {'Total Distance':<15}")
                print('-' * 40)
                for row in result:
                    print(f"{row[1]:<15} {row[2]:<15}")
                print('-' * 40)
                break

    cursor.close()
    connection.close()
