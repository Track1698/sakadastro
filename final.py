import requests
from pyproj import Proj, transform
import json
from shapely.geometry import Polygon, Point
from bs4 import BeautifulSoup
import html
import warnings
from urllib3.exceptions import InsecureRequestWarning
import urllib3
import contextlib
from itertools import combinations
import time
import logging

logging.basicConfig(filename='application.log', level=logging.DEBUG, encoding='utf-8')


timeout_seconds = 10  # Set the timeout to 10 seconds


warnings.filterwarnings("ignore", category=urllib3.exceptions.InsecureRequestWarning)

# Save the original merge_environment_settings function
old_merge_environment_settings = requests.Session.merge_environment_settings

# Define the no_ssl_verification context manager
@contextlib.contextmanager
def no_ssl_verification():
    opened_adapters = set()

    def merge_environment_settings(self, url, proxies, stream, verify, cert):
        opened_adapters.add(self.get_adapter(url))

        settings = old_merge_environment_settings(self, url, proxies, stream, verify, cert)
        settings['verify'] = False

        return settings

    requests.Session.merge_environment_settings = merge_environment_settings

    try:
        with contextlib.suppress(InsecureRequestWarning):
            yield
    finally:
        requests.Session.merge_environment_settings = old_merge_environment_settings

        for adapter in opened_adapters:
            try:
                adapter.close()
            except:
                pass


warnings.simplefilter(action='ignore', category=FutureWarning)

def get_base_headers():
    return {
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.6',
        'Connection': 'keep-alive',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-GPC': '1',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'sec-ch-ua': '"Brave";v="119", "Chromium";v="119", "Not?A_Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
    }

def get_headers():
    base_headers = get_base_headers()
    return {
        **base_headers,
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Origin': 'https://maps.gov.ge',
        'Referer': 'https://maps.gov.ge/map/portal',
        'X-Requested-With': 'XMLHttpRequest',
    }

def get_headers2():
    base_headers = get_base_headers()
    return {
        **base_headers,
        'Referer': 'https://maps.gov.ge/map/portal',
    }

def get_headers3():
    base_headers = get_base_headers()
    return {
        **base_headers,
        'Accept': 'application/json, text/plain, */*',
        'Content-Type': 'application/json;charset=UTF-8',
        'Origin': 'https://maps.tbilisi.gov.ge',
        'Referer': 'https://maps.tbilisi.gov.ge/',
    }

def get_input_kadastr():
    return input("შეიყვანეთ საკადასტრო კოდი - ")

def get_coordinates_list(input_kadastr):
    base_headers = get_base_headers()
    headers3 = get_headers3()
    json_data1 = {'searchText': input_kadastr, 'orgId': 1, 'action': 'mapsearchws/searchAll'}
    second_source = False
    response1 = requests.post('https://maps.tbilisi.gov.ge/TbilisimapCoreProxyController/process.do',
                              headers=headers3, json=json_data1, timeout=timeout_seconds)
    response_data = json.loads(response1.text)
    logging.debug(f"Coordinates list response data: {response1.text}")

    try:
        success = response_data.get('success', False)
        if success:
            data = response_data.get('data', [])
            if not data:
                # Handle the case when success is True, but there is no data
                logging.warning("Success is True, but no data found in the response.")
                return "ArasworiSakadastro"  # Replace with your desired error code or value
            
            # Check if 'geometry' is present and not None
            geometry_data = data[0].get('geometry')
            logging.debug(f"Coordinates from First source: {geometry_data}")
            if geometry_data:
                # Handle the case when 'geometry' is None
                logging.debug(f"Couldn't get coordinates from first source")
                geometry_data = fetch_additional_info(input_kadastr, 2)
                logging.debug(f"Coordinates from second source: {geometry_data}")
                second_source = True
            
            coordinates_str = geometry_data.split("POLYGON ((")[1].split("))")[0]
            coordinates_str = coordinates_str.replace(')', '')
            coordinates_str = coordinates_str.replace('(', '')
            coordinates_list = [tuple(map(float, coord.split())) for coord in coordinates_str.split(",")]
            logging.debug(f"coordinates_list final: {coordinates_list}")
            return coordinates_list, second_source
        else:
            logging.warning("Success is False in the response.")
            return "Error"  # Replace with your desired error code or value

    except (KeyError, IndexError) as e:
        logging.error(f"Error processing response data: {e}")
        return []


def get_centroid(coordinates_list):
    polygon = Polygon(coordinates_list)
    return polygon.centroid

from shapely.geometry import Point, Polygon
from itertools import combinations

def calculate_threshold(coordinates_list, distance_threshold_ratio=1e-5):
    num_coordinates = len(coordinates_list)

    # Calculate a dynamic threshold based on the number of coordinates
    target_num_coordinates = max(min(num_coordinates, 15), 10)
    dynamic_threshold = distance_threshold_ratio * (1 / target_num_coordinates)

    return dynamic_threshold

def remove_close_points(coordinates_list, distance_threshold_ratio=1e-5):
    num_coordinates = len(coordinates_list)
    dynamic_threshold = calculate_threshold(coordinates_list, distance_threshold_ratio)

    filtered_coordinates = []

    for i, coord1 in enumerate(coordinates_list):
        include_point = True
        for coord2 in coordinates_list[:i] + coordinates_list[i+1:]:
            # Use Euclidean distance between two points
            distance = Point(coord1).distance(Point(coord2))
            
            # Use the dynamically calculated threshold
            if distance < dynamic_threshold:
                include_point = False
                break
        if include_point:
            filtered_coordinates.append(coord1)

    return filtered_coordinates

def get_farthest_corners(coordinates_list):
    # Remove close points to speed up the process
    if len(coordinates_list) > 15:
        filtered_coordinates = remove_close_points(coordinates_list)
    else:
        filtered_coordinates = coordinates_list

    all_combinations = list(combinations(filtered_coordinates, 4))
    max_area = 0
    farthest_combination = None

    for combination in all_combinations:
        rectangle = Polygon(combination)
        area = rectangle.area

        if area > max_area:
            max_area = area
            farthest_combination = combination

    if farthest_combination is not None:
        return list(farthest_combination)
    else:
        print("No valid combination found.")
        return None



def move_towards_center(point, centroid, fraction):
    new_x = point[0] + (centroid.x - point[0]) * (1 - fraction)
    new_y = point[1] + (centroid.y - point[1]) * (1 - fraction)
    return new_x, new_y

def calculate_final_coordinates(coordinates_list, source_epsg, target_epsg):
    centroid = get_centroid(coordinates_list)
    farthest_corners = get_farthest_corners(coordinates_list)

    # Move each farthest corner 75% towards the center
    moved_coordinates = [move_towards_center(coord, centroid, 0.75) for coord in farthest_corners]

    # Add the centroid to the list of coordinates
    final_coordinates = [(centroid.x, centroid.y)] + moved_coordinates

    # Transform the coordinates if needed
    if source_epsg != target_epsg:
        final_coordinates = [transform_coordinates(coord, source_epsg, target_epsg) for coord in final_coordinates]

    return final_coordinates

def transform_coordinates(coord, source_epsg, target_epsg):
    if source_epsg != target_epsg:
        x, y = coord
        transformer = Proj(init=source_epsg), Proj(init=target_epsg)
        lon, lat = transform(transformer[0], transformer[1], x, y)
        return lon, lat
    else:
        # If source EPSG code matches the target EPSG code, no transformation is needed
        return coord

def get_json_data_lrs(lon, lat):
    return {
        'action': 'managelayersws/getLayersInfos',
        'lrsIds': '1007,323,16,11905,11887,11873,11886,11866,11865,11888,11867,11881,11884,11874,11891,11875,11868,11885,11870,11871,11877,11878,11882,11880,11889,11869,11872,11876,11883,11879,11890,13047,11822,11821,95,117,12295,11805,122,11811,11848,11810,11812,119,120,92,114,11813,13045,13305,11808,12585,11824,10520,11706,12766,10322,12911,12910,13330',
        'x': lon,
        'y': lat,
        'orgId': 1,
    }


def extract_link_from_json(detail_info):
    try:
        soup = BeautifulSoup(detail_info, 'html.parser')
        link = soup.a['href'] if soup.a else None
        logging.debug(f"Link of latest მშენებლობის ნებართვა: {link}")
        return link
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
        return None
    except (KeyError, TypeError):
        print("Invalid JSON structure or missing key.")
        return None

def get_latest_info(layer_data):
    latest_info = {
        "latest_ganxN": layer_data.get("განცხN"),
        "nebartvislink": extract_link_from_json(layer_data.get("დეტალური", "")),
        "address": layer_data.get("მისამართი"),
        "k1": layer_data.get("k1"),
        "k2": layer_data.get("k2"),
        "k3": layer_data.get("k3"),
        "kategoria": layer_data.get("kategoria"),
        "kveZona": layer_data.get("kveZona"),
    }
    logging.debug(f"Latest info from extract_link_from_json: {latest_info}")
    return latest_info

def handle_msheneblobi(layer_data):
    return {"latest_ganxN": layer_data.get("განცხN")}

def handle_gamtsvanebuli(layer_data):
    return {"kategoria": layer_data.get("kategoria")}

def extract_float_value(layer_data, key):
    value = None
    for data in layer_data:
        if key in data and isinstance(data[key], (float, int)):
            value = data[key]
            break
    return value

def extract_k_values(response_json):

    # List to store layers with valid values
    layers_with_data = []

    # Iterate through layers in the 'data' array
    for layer in response_json.get('data', []):
        # Check if 'layerData' is present and not empty
        if 'layerData' in layer and layer['layerData']:
            # Extract 'k1', 'k2', and 'k3' values if they exist and are floats
            k1_value = extract_float_value(layer['layerData'], 'k1')
            k2_value = extract_float_value(layer['layerData'], 'k2')
            k3_value = extract_float_value(layer['layerData'], 'k3')

            # Check if valid values are found
            if k1_value is not None and k2_value is not None and k3_value is not None:
                layers_with_data.append({
                    "Layer": layer['layerName'],
                    "k1": k1_value,
                    "k2": k2_value,
                    "k3": k3_value
                })

    return layers_with_data

def process_layer_data(response_data):
    latest_info = {
        "latest_ganxN": None,
        "nebartvislink": None,
        "address": None,
        "k1": None,
        "k2": None,
        "k3": None,
        "kategoria": None,
        "dzegli": False,  # Initialize dzegli to False
        "kveZona": None,
    }

    layer_handlers = {
        "მშენებლობის ნებართვები": handle_msheneblobi,
        "გამწვანებული ტერიტორიები": handle_gamtsvanebuli,
        # Add more layer handlers as needed
    }

    for layer in response_data.get("data", []):
        if "layerName" in layer and layer.get("layerData"):
            layer_name = layer["layerName"]
            layer_data = layer["layerData"][-1]  # Assuming latest data is at the end
            handler_result = layer_handlers.get(layer_name, lambda x: {})(layer_data)
            latest_info.update(handler_result)


            if layer_name == "კულტურული მემკვიდრეობის უძრავი ძეგლები":
                latest_info["dzegli"] = True

    # Find additional values
    detailuri_link = None
    kveZona_value = None

    for layer in response_data["data"]:
        if "layerData" in layer:
            for data_entry in layer["layerData"]:
                if "kveZona" in data_entry:
                    kveZona_value = data_entry["kveZona"]
                if "დეტალური" in data_entry:
                    soup = BeautifulSoup(data_entry["დეტალური"], "html.parser")
                    detailuri_link = soup.a["href"]

    latest_info['kveZona'] = kveZona_value
    latest_info['nebartvislink'] = detailuri_link
    result = extract_k_values(response_data)[0]
    logging.debug(f"extracted k value result: {result}")
    latest_info.update(result)
    #print(f"Latest info from process_layer_data: {latest_info}")
    return latest_info






def fetch_amonaweri_pdf_link(input_kadastr):
    url = f'http://abstract.reestri.gov.ge/abstract/cad_amo.php?cad_code={input_kadastr}'
    response2 = requests.get(url)
    logging.debug(f"Response from response2: {response2.text}")
    
    if response2.status_code == 200:
        soup = BeautifulSoup(response2.text, 'html.parser')
        td_elements = soup.find_all('td')
        
        for td_element in td_elements:
            td_text = html.unescape(td_element.get_text(strip=True))
                        
            if len(td_text) == 27:
                tr_element = td_element.find_parent('tr')
                onclick_value = tr_element.get('onclick')
                
                if onclick_value:
                    start_quote_index = onclick_value.find("'")
                    end_quote_index = onclick_value.rfind("'")
                    
                    if start_quote_index != -1 and end_quote_index != -1:
                        pdf_link = onclick_value[start_quote_index + 1: end_quote_index]
                        return pdf_link
                    else:
                        print("PDF link not found.")
                else:
                    print("onclick attribute not found.")    
    else:
        print(f"Failed to fetch URL. Status code: {response2.status_code}")

def fetch_sakadastro_pdf_link(input_kadastr):
    url = f'http://abstract.reestri.gov.ge/abstract/cad_amo.php?cad_code={input_kadastr}'
    response2 = requests.get(url)
    logging.debug(f"Response from response2: {response2.text}")
    
    if response2.status_code == 200:
        soup = BeautifulSoup(response2.text, 'html.parser')
        td_elements = soup.find_all('td')
        
        for td_element in td_elements:
            td_text = html.unescape(td_element.get_text(strip=True))
                        
            if len(td_text) == 43:
                tr_element = td_element.find_parent('tr')
                onclick_value = tr_element.get('onclick')
                
                if onclick_value:
                    start_quote_index = onclick_value.find("'")
                    end_quote_index = onclick_value.rfind("'")
                    
                    if start_quote_index != -1 and end_quote_index != -1:
                        pdf_link = onclick_value[start_quote_index + 1: end_quote_index]
                        return pdf_link
                    else:
                        print("PDF link not found.")
                else:
                    print("onclick attribute not found.")    
    else:
        print(f"Failed to fetch URL. Status code: {response2.status_code}")

def fetch_additional_info(input_kadastr, id):
    data = {
        'keyword': input_kadastr,
        'keyword_description[coords][]': '',
        'keyword_description[zoom]': '8',
        'keyword_description[bbox][]': '',
        'keyword_description[screen_width]': '1216',
        'keyword_description[screen_height]': '941',
        'keyword_description[projection]': 'EPSG:4326',
        'keyword_description[orientation_angle]': '0',
        'keyword_description[getinfo_type]': '',
        'keyword_description[layers][]': ['92', '97'],
        'keyword_description[lang]': 'ka',
    }
    headers = get_headers()
    #print(headers, data)
    with no_ssl_verification():
        response = requests.post('https://maps.gov.ge/map/portal/search', headers=headers, data=data, timeout=timeout_seconds, verify=False)
        data = json.loads(response.text)
        logging.debug(f"Response from map/portal/search: {data}")
        result_link_value = data["result"][0]["resultlink"]
        result_link_value_without_prefix = result_link_value.replace("/map/portal/getbylbl?lbl=", "")
        if id == 1:
            response2 = requests.get(
                f'https://maps.gov.ge/lr/bo/mg/getinfo.alpha?lbl={result_link_value_without_prefix}&lang=ka',
                headers=headers,
            )
            soup = BeautifulSoup(response2.text, 'html.parser')
            logging.debug(f"Response from response2 in fetch_additional_info: {response2.text}")
            visible_text_array = [element.get_text(strip=True) for element in soup.find_all(
                lambda x: x.name not in ['script', 'style']) if element.get_text(strip=True)]

            return extract_additional_info(visible_text_array)
        else:
            response2 = requests.get(
                f'https://maps.gov.ge/lr/bo/mg/getinfo.alpha?lbl={result_link_value_without_prefix}&lang=ka&bbox=4985540.514541853,5117024.188684258,4985688.999363005,5117107.711396155&res=shp',
                headers=headers,
            )
            response_data = json.loads(response2.text)

            # Extract coordinates from the "shape" field
            #coordinates = []
            for item in response_data.get("data", []):
                shape = item.get("shape")
                logging.debug(f"shape from second source: {shape}")
            return shape
    

def extract_additional_info(visible_text_array):
    fartobi = nakveti = misamarti = sakutreba = mesakutre = zoma = None
    
    for i in range(len(visible_text_array)):
        if visible_text_array[i] == 'ფართობი':
            fartobi = visible_text_array[i + 1]
            zoma = visible_text_array[i + 2]
        elif visible_text_array[i] == 'ნაკვეთის ტიპი':
            nakveti = visible_text_array[i + 1]
        elif visible_text_array[i] == 'მისამართი':
            misamarti = visible_text_array[i + 1]
        elif visible_text_array[i] == 'საკუთრების ტიპი':
            sakutreba = visible_text_array[i + 1]
        elif visible_text_array[i] == 'მესაკუთრე(ებ)ი':
            mesakutre = visible_text_array[i + 2]
    
    return fartobi, zoma, nakveti, misamarti, sakutreba, mesakutre


def backend_function(input_kadastr, max_retries=3, retry_delay=2):
    logging.info(f"Processing started for input_kadastr={input_kadastr}")
    
    for attempt in range(max_retries + 1):
        try:
            logging.info(f"Attempt {attempt + 1} started")
            coordinates_list, returned_second_source = get_coordinates_list(input_kadastr)
            
            if coordinates_list == "ArasworiSakadastro":
                logging.warning("Error in coordinates result. Returning error response.")
                return {"error": "ArasworiSakadastro"}
                
            if returned_second_source == False:
                final_coordinates = calculate_final_coordinates(coordinates_list, source_epsg='EPSG:900913', target_epsg='EPSG:4326')
                transformed_coordinates = [transform_coordinates(coord, source_epsg='EPSG:900913', target_epsg='EPSG:4326') for coord in coordinates_list]
            else:
                final_coordinates = calculate_final_coordinates(coordinates_list, source_epsg='EPSG:4326', target_epsg='EPSG:4326')
                transformed_coordinates = coordinates_list
            
            

            found_desired_layer = False

            for each_coordinate in final_coordinates:
                json_data_lrs = get_json_data_lrs(*each_coordinate)
                logging.debug(f"Sending request with json_data_lrs: {json_data_lrs}")

                headers3 = get_headers3()
                response = requests.post('https://maps.tbilisi.gov.ge/TbilisimapCoreProxyController/process.do',
                                         headers=headers3, json=json_data_lrs, timeout=timeout_seconds)
                logging.debug(f"Response from main: {response.text}")
                response_data = json.loads(response.text)

                # Check if the desired layer exists in the response
                for layer in response_data.get("data", []):
                    if "layerName" in layer and layer["layerName"] == "შენობა-ნაგებობები":
                        # Process the data from the desired layer
                        latest_info = process_layer_data(response_data)
                        logging.debug(f"Latest info inside loop: {latest_info}")
                        found_desired_layer = True
                        break
                    
                if found_desired_layer:
                    # Break out of the outer loop if the layer is found
                    break
            else:
                # If the loop completes without finding the layer, use information from the first coordinate
                latest_info = process_layer_data(response_data)
                logging.debug(f"Latest info outside loop: {latest_info}")


            # Fetch PDF link and additional info using the current coordinate data
            amonaweri_pdf = fetch_amonaweri_pdf_link(input_kadastr)
            sakadastro_pdf = fetch_sakadastro_pdf_link(input_kadastr)

            fartobi, zoma, nakveti, misamarti, sakutreba, mesakutre = fetch_additional_info(input_kadastr, 1)
            logging.debug(f"Fartobi: {fartobi}, Zoma: {zoma}, Nakveti: {nakveti}, Misamarti: {misamarti}, "
                          f"Sakutreba: {sakutreba}, Mesakutre: {mesakutre}")
            

            result = {
                "latest_ganxN": latest_info["latest_ganxN"],
                "nebartvislink": latest_info["nebartvislink"],
                "kveZona": latest_info["kveZona"],
                "k1": latest_info["k1"],
                "k2": latest_info["k2"],
                "k3": latest_info["k3"],
                "kategoria": latest_info["kategoria"],
                "dzegli": latest_info["dzegli"],
                "amonaweri_pdf": amonaweri_pdf,
                'sakadastro_pdf': sakadastro_pdf,
                'fartobi': fartobi,
                'zoma': zoma,
                'nakveti': nakveti,
                'misamarti': misamarti,
                'sakutreba': sakutreba,
                'mesakutre': mesakutre,
                'transformed_coordinates': transformed_coordinates,
                'kadastrback': input_kadastr,
                'centroidx': each_coordinate[0],
                'centroidy': each_coordinate[1],
            }

            logging.info(f"Processing completed for input_kadastr={input_kadastr}")
            return result

        except Exception as e:
            logging.error(f"Error in attempt {attempt + 1}: {e}")
            if attempt < max_retries:
                logging.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                logging.error("Max retries reached. Exiting.")
                raise



#print(backend_function(get_input_kadastr()))